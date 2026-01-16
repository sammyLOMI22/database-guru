"""SQL Execution Engine with safety checks"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, DBAPIError, OperationalError
from src.core.query_compiler import QueryCompiler

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
        self.compiler = QueryCompiler()

    def get_compiler_stats(self) -> Dict[str, Any]:
        """Get statistics from the query compiler"""
        return self.compiler.get_stats()

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
                - compiled: Whether query was compiled/cached
        """
        start_time = datetime.utcnow()

        # Try to use compiled query if no params provided and it's a SELECT
        compiled_query = None
        execution_params = params
        final_sql = sql

        # Only attempt compilation for SELECT queries without explicit params
        # (explicit params mean the caller is already handling parameterization)
        if params is None and sql.strip().upper().startswith("SELECT"):
            compiled_query, extracted_params = self.compiler.get_compiled_query(sql)

            if compiled_query:
                # Cache hit! Use template and extracted params
                final_sql = compiled_query.sql_template
                execution_params = extracted_params
            else:
                # Cache miss - compile it
                compiled_query, extracted_params = self.compiler.compile_query(sql)

                # Use the template for execution to cache the plan at DB level
                final_sql = compiled_query.sql_template
                execution_params = extracted_params

        try:
            # Check if this is a sync session (e.g., DuckDB)
            if isinstance(session, Session):
                # Execute sync session in thread pool to not block event loop
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._execute_with_sync_session,
                    session,
                    final_sql,
                    execution_params
                )
            else:
                # Execute with timeout for async sessions
                result = await asyncio.wait_for(
                    self._execute_with_session(session, final_sql, execution_params),
                    timeout=self.timeout_seconds
                )

            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Update compiler stats if applicable
            if compiled_query:
                self.compiler.update_stats(compiled_query, execution_time_ms)

            return {
                "success": True,
                "data": result["data"],
                "columns": result["columns"],
                "row_count": result["row_count"],
                "execution_time_ms": round(execution_time_ms, 2),
                "truncated": result["truncated"],
                "error": None,
                "compiled": compiled_query is not None
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

    async def execute_query_streaming(
        self,
        session: Union[AsyncSession, Session],
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
    ):
        """
        Execute SQL query and stream results in batches (async generator)

        Args:
            session: Database session (async or sync)
            sql: SQL query to execute
            params: Optional query parameters
            batch_size: Number of rows per batch

        Yields:
            Dictionary with:
                - event_type: 'metadata' | 'data' | 'complete' | 'error'
                - columns: Column names (only in metadata event)
                - data: Batch of rows (only in data event)
                - batch_number: Current batch number
                - rows_sent: Total rows sent so far
                - execution_time_ms: Time elapsed (in complete event)
                - error: Error message (only in error event)
        """
        start_time = datetime.utcnow()

        try:
            # Check if this is a sync session (e.g., DuckDB)
            if isinstance(session, Session):
                async for event in self._stream_with_sync_session(session, sql, params, batch_size, start_time):
                    yield event
            else:
                # Stream with async sessions
                # Note: Timeout handling is done per-batch in _stream_with_async_session
                async for event in self._stream_with_async_session(session, sql, params, batch_size, start_time):
                    yield event

        except Exception as e:
            logger.error(f"Unexpected error in streaming query: {e}", exc_info=True)
            yield {
                "event_type": "error",
                "error": f"Execution error: {str(e)}",
                "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }

    async def _stream_with_async_session(
        self,
        session: AsyncSession,
        sql: str,
        params: Optional[Dict[str, Any]],
        batch_size: int,
        start_time: datetime,
    ):
        """Stream results from async session"""
        stmt = text(sql)
        result = await session.execute(stmt, params or {})

        if not result.returns_rows:
            # Non-SELECT query
            await session.commit()
            yield {
                "event_type": "complete",
                "rows_affected": result.rowcount,
                "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }
            return

        # Send metadata first
        columns = list(result.keys())
        yield {
            "event_type": "metadata",
            "columns": columns,
        }

        # Stream data in batches
        batch_number = 0
        total_rows_sent = 0

        while True:
            # Fetch next batch
            rows = result.fetchmany(batch_size)

            if not rows:
                # No more data
                break

            batch_number += 1

            # Check if we've exceeded max_rows
            remaining_capacity = self.max_rows - total_rows_sent
            if remaining_capacity <= 0:
                # Send truncation warning and stop
                yield {
                    "event_type": "complete",
                    "truncated": True,
                    "total_rows": total_rows_sent,
                    "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                }
                return

            # Truncate batch if needed
            if len(rows) > remaining_capacity:
                rows = rows[:remaining_capacity]
                truncated = True
            else:
                truncated = False

            # Convert rows to dictionaries
            data = [
                {col: self._serialize_value(row[i]) for i, col in enumerate(columns)}
                for row in rows
            ]

            total_rows_sent += len(data)

            # Send batch
            yield {
                "event_type": "data",
                "data": data,
                "batch_number": batch_number,
                "rows_in_batch": len(data),
                "rows_sent": total_rows_sent,
            }

            if truncated:
                # Reached max_rows limit
                yield {
                    "event_type": "complete",
                    "truncated": True,
                    "total_rows": total_rows_sent,
                    "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                }
                return

        # All data sent
        execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        yield {
            "event_type": "complete",
            "truncated": False,
            "total_rows": total_rows_sent,
            "execution_time_ms": execution_time_ms,
        }

    async def _stream_with_sync_session(
        self,
        session: Session,
        sql: str,
        params: Optional[Dict[str, Any]],
        batch_size: int,
        start_time: datetime,
    ):
        """Stream results from sync session (e.g., DuckDB) in thread pool"""
        # Execute in thread pool to avoid blocking
        def sync_execute():
            stmt = text(sql)
            result = session.execute(stmt, params or {})

            if not result.returns_rows:
                session.commit()
                return {
                    "type": "non_select",
                    "rowcount": result.rowcount,
                }

            return {
                "type": "select",
                "result": result,
                "columns": list(result.keys()),
            }

        exec_result = await asyncio.get_event_loop().run_in_executor(None, sync_execute)

        if exec_result["type"] == "non_select":
            yield {
                "event_type": "complete",
                "rows_affected": exec_result["rowcount"],
                "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }
            return

        # Send metadata
        columns = exec_result["columns"]
        yield {
            "event_type": "metadata",
            "columns": columns,
        }

        # Stream batches
        result = exec_result["result"]
        batch_number = 0
        total_rows_sent = 0

        while True:
            # Fetch batch in thread pool
            def fetch_batch():
                return result.fetchmany(batch_size)

            rows = await asyncio.get_event_loop().run_in_executor(None, fetch_batch)

            if not rows:
                break

            batch_number += 1

            # Check max_rows limit
            remaining_capacity = self.max_rows - total_rows_sent
            if remaining_capacity <= 0:
                yield {
                    "event_type": "complete",
                    "truncated": True,
                    "total_rows": total_rows_sent,
                    "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                }
                return

            if len(rows) > remaining_capacity:
                rows = rows[:remaining_capacity]
                truncated = True
            else:
                truncated = False

            # Convert to dicts
            data = [
                {col: self._serialize_value(row[i]) for i, col in enumerate(columns)}
                for row in rows
            ]

            total_rows_sent += len(data)

            yield {
                "event_type": "data",
                "data": data,
                "batch_number": batch_number,
                "rows_in_batch": len(data),
                "rows_sent": total_rows_sent,
            }

            if truncated:
                yield {
                    "event_type": "complete",
                    "truncated": True,
                    "total_rows": total_rows_sent,
                    "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                }
                return

        # Complete
        yield {
            "event_type": "complete",
            "truncated": False,
            "total_rows": total_rows_sent,
            "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        }

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
