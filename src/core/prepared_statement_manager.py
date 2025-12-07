"""
Prepared Statement Manager for Query Compilation

Manages prepared statements lifecycle with lazy preparation, LRU eviction, and cleanup.

Architecture:
- Lazy Preparation: Only prepare after 2+ executions (avoid overhead for one-off queries)
- LRU Eviction: Max 100 statements per connection pool
- Per-Connection Isolation: Statements tracked by (connection_id, normalized_hash)
- Background Cleanup: Removes unused statements (30-minute TTL)
- Portability: Uses SQLAlchemy text() with parameters (works across all databases)
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PreparedStatement:
    """Prepared statement tracking"""
    statement_id: str              # "{connection_id}_{normalized_hash}"
    normalized_hash: str           # Hash of normalized query
    template_sql: str              # Parameterized SQL template
    database_type: str             # postgresql, mysql, sqlite, duckdb
    connection_id: int             # Which database connection
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    execution_count: int = 0       # Number of times executed
    total_execution_ms: float = 0.0  # Cumulative execution time
    is_prepared: bool = False      # Whether statement is actually prepared


class PreparedStatementManager:
    """
    Manages prepared statement lifecycle with lazy preparation and LRU eviction.

    Strategy:
    1. Track statement execution count
    2. Prepare only after 2+ executions (avoid overhead for one-off queries)
    3. Evict oldest unused statements when limit exceeded (max 100 per connection)
    4. Background cleanup removes statements with 30-minute TTL
    5. Use SQLAlchemy text() for database portability
    """

    # Configuration
    EXECUTION_THRESHOLD = 2        # Prepare after N executions
    MAX_STATEMENTS = 100           # Max prepared statements per connection
    CLEANUP_TTL = 1800             # 30 minutes - remove if not used
    CLEANUP_INTERVAL = 300         # Run cleanup every 5 minutes

    def __init__(self):
        """Initialize statement manager"""
        self._statements: Dict[str, PreparedStatement] = {}
        self._connection_statements: Dict[int, List[str]] = {}  # connection_id -> [statement_ids]
        self._cleanup_task = None

    async def get_or_create_statement(
        self,
        connection_id: int,
        normalized_hash: str,
        template_sql: str,
        database_type: str,
    ) -> PreparedStatement:
        """
        Get or create a prepared statement.

        Args:
            connection_id: Connection ID
            normalized_hash: Hash of normalized query
            template_sql: Parameterized SQL template
            database_type: postgresql, mysql, sqlite, duckdb

        Returns:
            PreparedStatement object
        """
        statement_id = f"{connection_id}_{normalized_hash}"

        # Return existing statement
        if statement_id in self._statements:
            stmt = self._statements[statement_id]
            stmt.execution_count += 1
            stmt.last_used = datetime.utcnow().isoformat()

            # Check if we should prepare now
            if not stmt.is_prepared and stmt.execution_count >= self.EXECUTION_THRESHOLD:
                stmt.is_prepared = True
                logger.info(
                    f"Prepared statement: {statement_id} "
                    f"(after {stmt.execution_count} executions)"
                )

            logger.debug(
                f"Reused prepared statement: {statement_id} "
                f"(executions: {stmt.execution_count}, prepared: {stmt.is_prepared})"
            )
            return stmt

        # Create new statement
        stmt = PreparedStatement(
            statement_id=statement_id,
            normalized_hash=normalized_hash,
            template_sql=template_sql,
            database_type=database_type,
            connection_id=connection_id,
            execution_count=1,
        )

        # Store statement
        self._statements[statement_id] = stmt

        # Add to connection index
        if connection_id not in self._connection_statements:
            self._connection_statements[connection_id] = []
        self._connection_statements[connection_id].append(statement_id)

        # Check if we should prepare (after EXECUTION_THRESHOLD executions)
        if stmt.execution_count >= self.EXECUTION_THRESHOLD:
            stmt.is_prepared = True
            logger.info(
                f"Prepared statement: {statement_id} "
                f"(after {stmt.execution_count} executions)"
            )

        # Evict oldest if over limit
        if len(self._connection_statements[connection_id]) > self.MAX_STATEMENTS:
            self._evict_oldest(connection_id)

        logger.debug(
            f"Created prepared statement: {statement_id} "
            f"(total: {len(self._statements)})"
        )

        return stmt

    def record_execution(
        self,
        statement_id: str,
        execution_ms: float,
    ) -> None:
        """
        Record execution of a prepared statement.

        Args:
            statement_id: Statement ID
            execution_ms: Execution time in milliseconds
        """
        if statement_id not in self._statements:
            return

        stmt = self._statements[statement_id]
        stmt.total_execution_ms += execution_ms
        stmt.last_used = datetime.utcnow().isoformat()

        # Update preparation status if needed
        if not stmt.is_prepared and stmt.execution_count >= self.EXECUTION_THRESHOLD:
            stmt.is_prepared = True
            logger.info(
                f"Prepared statement: {statement_id} "
                f"(avg: {stmt.total_execution_ms / stmt.execution_count:.2f}ms)"
            )

    def _evict_oldest(self, connection_id: int) -> None:
        """
        Evict oldest unused statement for a connection.

        Args:
            connection_id: Connection to evict from
        """
        statement_ids = self._connection_statements.get(connection_id, [])
        if not statement_ids:
            return

        # Find oldest by last_used time
        oldest_id = min(
            statement_ids,
            key=lambda sid: self._statements[sid].last_used,
        )

        # Remove statement
        if oldest_id in self._statements:
            stmt = self._statements[oldest_id]
            del self._statements[oldest_id]
            statement_ids.remove(oldest_id)

            logger.info(
                f"Evicted prepared statement: {oldest_id} "
                f"(LRU, executions: {stmt.execution_count})"
            )

    async def cleanup_expired(self) -> int:
        """
        Clean up expired statements (not used in CLEANUP_TTL seconds).

        Returns:
            Number of statements removed
        """
        now = datetime.utcnow()
        expired_ids = []

        for statement_id, stmt in self._statements.items():
            last_used = datetime.fromisoformat(stmt.last_used)
            age = (now - last_used).total_seconds()

            if age > self.CLEANUP_TTL:
                expired_ids.append(statement_id)

        # Remove expired statements
        for statement_id in expired_ids:
            stmt = self._statements[statement_id]
            del self._statements[statement_id]

            # Remove from connection index
            conn_id = stmt.connection_id
            if conn_id in self._connection_statements:
                try:
                    self._connection_statements[conn_id].remove(statement_id)
                except ValueError:
                    pass

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired prepared statements")

        return len(expired_ids)

    async def start_cleanup_loop(self) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is not None:
            return

        logger.info("Starting prepared statement cleanup loop")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def stop_cleanup_loop(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cleanup loop stopped")

    async def invalidate_connection(self, connection_id: int) -> int:
        """
        Invalidate all statements for a connection.

        Args:
            connection_id: Connection to invalidate

        Returns:
            Number of statements removed
        """
        statement_ids = self._connection_statements.pop(connection_id, [])

        count = 0
        for statement_id in statement_ids:
            if statement_id in self._statements:
                del self._statements[statement_id]
                count += 1

        logger.info(
            f"Invalidated {count} prepared statements for connection {connection_id}"
        )

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statement manager statistics.

        Returns:
            Dictionary of statistics
        """
        prepared_count = sum(1 for s in self._statements.values() if s.is_prepared)
        total_executions = sum(s.execution_count for s in self._statements.values())
        avg_executions = total_executions / max(len(self._statements), 1)

        return {
            "total_statements": len(self._statements),
            "prepared_statements": prepared_count,
            "total_executions": total_executions,
            "avg_executions_per_statement": avg_executions,
            "total_execution_ms": sum(s.total_execution_ms for s in self._statements.values()),
            "avg_execution_ms": (
                sum(s.total_execution_ms for s in self._statements.values()) /
                max(total_executions, 1)
            ),
        }

    def clear_cache(self) -> None:
        """Clear all statements"""
        self._statements.clear()
        self._connection_statements.clear()
        logger.info("Cleared prepared statement cache")


# Global singleton
_statement_manager: Optional[PreparedStatementManager] = None


def get_prepared_statement_manager() -> PreparedStatementManager:
    """
    Get global prepared statement manager instance.

    Returns:
        Singleton PreparedStatementManager instance
    """
    global _statement_manager
    if _statement_manager is None:
        _statement_manager = PreparedStatementManager()
    return _statement_manager
