"""SQL Execution Engine with safety checks"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, DBAPIError, OperationalError

logger = logging.getLogger(__name__)


class QueryTimeout(Exception):
    """Exception raised when query execution times out"""
    pass


class SQLExecutor:
    """
    Safe SQL execution engine with timeout protection and result pagination
    """

    def __init__(
        self,
        max_rows: int = 1000,
        timeout_seconds: int = 30,
        allow_write: bool = False,
    ):
        """
        Initialize SQL executor

        Args:
            max_rows: Maximum number of rows to return
            timeout_seconds: Query timeout in seconds
            allow_write: Whether to allow write operations
        """
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.allow_write = allow_write

    async def execute_query(
        self,
        session: Union[AsyncSession, Session],
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute SQL query with safety checks and timeout protection

        Args:
            session: Database session (async or sync)
            sql: SQL query to execute
            params: Optional query parameters

        Returns:
            Dictionary with:
                - success: bool
                - data: List of result rows
                - columns: List of column names
                - row_count: Number of rows returned
                - execution_time_ms: Execution time
                - truncated: Whether results were truncated
                - error: Error message if failed
        """
        start_time = datetime.utcnow()

        try:
            # Check if this is a sync session (e.g., DuckDB)
            if isinstance(session, Session):
                # Execute sync session in thread pool to not block event loop
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._execute_with_sync_session,
                    session,
                    sql,
                    params
                )
            else:
                # Execute with timeout for async sessions
                result = await asyncio.wait_for(
                    self._execute_with_session(session, sql, params),
                    timeout=self.timeout_seconds
                )

            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            return {
                "success": True,
                "data": result["data"],
                "columns": result["columns"],
                "row_count": result["row_count"],
                "execution_time_ms": round(execution_time_ms, 2),
                "truncated": result["truncated"],
                "error": None,
            }

        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Query timeout after {execution_time}s: {sql[:100]}")
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": execution_time * 1000,
                "truncated": False,
                "error": f"Query timeout after {self.timeout_seconds} seconds",
            }

        except OperationalError as e:
            logger.error(f"Database operational error: {e}")
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "truncated": False,
                "error": f"Database error: {str(e)}",
            }

        except DBAPIError as e:
            logger.error(f"Database API error: {e}")
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "truncated": False,
                "error": f"SQL error: {str(e.orig) if hasattr(e, 'orig') else str(e)}",
            }

        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error: {e}")
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "truncated": False,
                "error": f"Database error: {str(e)}",
            }

        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}", exc_info=True)
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "truncated": False,
                "error": f"Execution error: {str(e)}",
            }

    def _execute_with_sync_session(
        self,
        session: Session,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Internal method to execute SQL with synchronous session (for DuckDB)

        Args:
            session: Synchronous database session
            sql: SQL query
            params: Query parameters

        Returns:
            Dictionary with data, columns, row_count, truncated
        """
        # Create SQL statement
        stmt = text(sql)

        # Execute query
        result = session.execute(stmt, params or {})

        # Check if this is a SELECT query (has results to fetch)
        if result.returns_rows:
            # Fetch results with limit
            rows = result.fetchmany(self.max_rows + 1)

            # Check if results were truncated
            truncated = len(rows) > self.max_rows
            if truncated:
                rows = rows[:self.max_rows]

            # Get column names
            columns = list(result.keys())

            # Convert rows to dictionaries
            data = [
                {col: self._serialize_value(row[i]) for i, col in enumerate(columns)}
                for row in rows
            ]

            return {
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "truncated": truncated,
            }
        else:
            # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
            session.commit()
            row_count = result.rowcount

            return {
                "data": [],
                "columns": [],
                "row_count": row_count,
                "truncated": False,
            }

    async def _execute_with_session(
        self,
        session: AsyncSession,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Internal method to execute SQL with async session

        Args:
            session: Database session
            sql: SQL query
            params: Query parameters

        Returns:
            Dictionary with data, columns, row_count, truncated
        """
        # Create SQL statement
        stmt = text(sql)

        # Execute query
        result = await session.execute(stmt, params or {})

        # Check if this is a SELECT query (has results to fetch)
        if result.returns_rows:
            # Fetch results with limit
            rows = result.fetchmany(self.max_rows + 1)

            # Check if results were truncated
            truncated = len(rows) > self.max_rows
            if truncated:
                rows = rows[:self.max_rows]

            # Get column names
            columns = list(result.keys())

            # Convert rows to dictionaries
            data = [
                {col: self._serialize_value(row[i]) for i, col in enumerate(columns)}
                for row in rows
            ]

            return {
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "truncated": truncated,
            }
        else:
            # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
            await session.commit()
            row_count = result.rowcount

            return {
                "data": [],
                "columns": [],
                "row_count": row_count,
                "truncated": False,
            }

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """
        Serialize database values to JSON-compatible types

        Args:
            value: Value from database

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None

        # Handle datetime objects
        if isinstance(value, datetime):
            return value.isoformat()

        # Handle date objects
        if hasattr(value, 'isoformat'):
            return value.isoformat()

        # Handle decimal/numeric types
        if hasattr(value, '__float__'):
            try:
                return float(value)
            except (ValueError, TypeError):
                pass

        # Handle bytes
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8')
            except UnicodeDecodeError:
                return str(value)

        # Default: convert to string
        try:
            return str(value)
        except Exception:
            return None

    async def execute_with_pagination(
        self,
        session: AsyncSession,
        sql: str,
        page: int = 1,
        page_size: int = 50,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute query with pagination

        Args:
            session: Database session
            sql: SQL query
            page: Page number (1-indexed)
            page_size: Number of rows per page
            params: Query parameters

        Returns:
            Result dictionary with pagination info
        """
        # Validate inputs
        page = max(1, page)
        page_size = min(page_size, self.max_rows)

        # Calculate offset
        offset = (page - 1) * page_size

        # Add LIMIT and OFFSET to query
        paginated_sql = f"{sql.rstrip(';')} LIMIT {page_size} OFFSET {offset}"

        # Execute query
        result = await self.execute_query(session, paginated_sql, params)

        if result["success"]:
            result["pagination"] = {
                "page": page,
                "page_size": page_size,
                "has_more": result["row_count"] == page_size,
            }

        return result

    def validate_query_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate query for dangerous operations

        Args:
            sql: SQL query to validate

        Returns:
            (is_safe, error_message)
        """
        sql_upper = sql.upper().strip()

        # Check for write operations if not allowed
        if not self.allow_write:
            write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE']
            for keyword in write_keywords:
                if f' {keyword} ' in f' {sql_upper} ' or sql_upper.startswith(keyword):
                    return False, f"Write operation not allowed: {keyword}"

        # Check for dangerous operations (always blocked)
        dangerous_keywords = ['DROP', 'TRUNCATE', 'ALTER TABLE', 'CREATE TABLE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Dangerous operation not allowed: {keyword}"

        return True, None
