"""DML executor — runs parameterized DML against user databases (Phase 18).

Two-session architecture:
- User DB session (via UserDatabaseConnector) for DML execution
- Metadata DB session for audit logging via log_action()
"""
import asyncio
import logging
from typing import List, Optional, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.auth.audit import log_action
from src.core.user_db_connector import UserDatabaseConnector
from src.database.models import DatabaseConnection
from src.dml.models import DMLStatement, ExecutionResult

logger = logging.getLogger(__name__)


class DMLExecutor:
    """Executes DML statements against user databases with transaction support."""

    async def execute(
        self,
        connection: DatabaseConnection,
        statements: List[DMLStatement],
        metadata_db: AsyncSession,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute DML statements against user database.

        All statements run within a single transaction.
        On failure, rolls back and logs the error.
        On success, commits and logs each change.
        """
        if not statements:
            return ExecutionResult(success=True, rows_affected=0)

        display_sql = "\n".join(s.display_sql for s in statements)

        try:
            async with UserDatabaseConnector.get_user_db_session(connection) as session:
                if isinstance(session, Session):
                    total = await asyncio.get_running_loop().run_in_executor(
                        None,
                        self._execute_sync,
                        session,
                        statements,
                    )
                else:
                    total = await self._execute_async(session, statements)

            # Audit log each statement on success
            for stmt in statements:
                await log_action(
                    metadata_db,
                    action="dml_execute",
                    resource_type="connection",
                    resource_id=str(connection.id),
                    user_id=user_id,
                    username=username,
                    details={
                        "change_type": stmt.change_type.value,
                        "table_name": stmt.table_name,
                        "sql": stmt.display_sql,
                        "connection_name": connection.name,
                        "database_type": connection.database_type,
                    },
                    ip_address=ip_address,
                )

            return ExecutionResult(
                success=True,
                rows_affected=total,
                executed_sql=display_sql,
            )

        except Exception as e:
            logger.error(f"DML execution failed on {connection.name}: {e}")

            # Audit log the failure
            await log_action(
                metadata_db,
                action="dml_failed",
                resource_type="connection",
                resource_id=str(connection.id),
                user_id=user_id,
                username=username,
                details={
                    "sql": display_sql,
                    "error": str(e),
                    "connection_name": connection.name,
                    "database_type": connection.database_type,
                },
                ip_address=ip_address,
            )

            return ExecutionResult(
                success=False,
                rows_affected=0,
                error_message=str(e),
                executed_sql=display_sql,
            )

    async def _execute_async(
        self,
        session: AsyncSession,
        statements: List[DMLStatement],
    ) -> int:
        """Execute statements in an async session with transaction."""
        total_affected = 0
        for stmt in statements:
            result = await session.execute(
                text(stmt.parameterized_sql), stmt.params
            )
            total_affected += result.rowcount
        await session.commit()
        return total_affected

    @staticmethod
    def _execute_sync(
        session: Session,
        statements: List[DMLStatement],
    ) -> int:
        """Execute statements in a sync session with transaction."""
        total_affected = 0
        try:
            for stmt in statements:
                result = session.execute(
                    text(stmt.parameterized_sql), stmt.params
                )
                total_affected += result.rowcount
            session.commit()
            return total_affected
        except Exception:
            session.rollback()
            raise
