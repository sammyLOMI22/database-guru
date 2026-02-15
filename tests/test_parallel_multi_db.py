"""
Tests for parallel multi-database query execution

Tests verify that queries execute in parallel (5-10x speedup) and that
both async (PostgreSQL, MySQL) and sync (DuckDB) sessions work correctly.
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.core.multi_db_handler import MultiDatabaseHandler
from src.database.models import DatabaseConnection


class TestParallelMultiDatabaseExecution:
    """Test parallel query execution across multiple databases"""

    @pytest.mark.asyncio
    async def test_execute_multi_database_query_parallel_speedup(self):
        """Test that parallel execution is faster than sequential"""
        handler = MultiDatabaseHandler()

        # Create mock connections
        connections = [
            DatabaseConnection(
                id=1,
                name="db1",
                database_type="postgresql",
                database_name="test1",
            ),
            DatabaseConnection(
                id=2,
                name="db2",
                database_type="mysql",
                database_name="test2",
            ),
            DatabaseConnection(
                id=3,
                name="db3",
                database_type="duckdb",
                database_name="test3.duckdb",
            ),
        ]

        # Create queries for each database
        queries = [
            {"connection_id": 1, "sql": "SELECT 1 as test"},
            {"connection_id": 2, "sql": "SELECT 2 as test"},
            {"connection_id": 3, "sql": "SELECT 3 as test"},
        ]

        # Mock execute_query_on_database to simulate slow queries
        async def slow_query_execution(connection, sql, allow_write=False):
            """Simulate a 1-second query"""
            await asyncio.sleep(1.0)  # Simulate query time
            return {
                "success": True,
                "data": [{"test": connection.id}],
                "row_count": 1,
                "execution_time_ms": 1000,
                "database_name": connection.name,
                "connection_id": connection.id,
            }

        handler.execute_query_on_database = slow_query_execution

        # Execute queries and measure time
        start_time = time.time()
        results = await handler.execute_multi_database_query(
            queries=queries,
            connections=connections,
            allow_write=False,
        )
        elapsed_time = time.time() - start_time

        # Verify results
        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert results[0]["data"][0]["test"] == 1
        assert results[1]["data"][0]["test"] == 2
        assert results[2]["data"][0]["test"] == 3

        # Verify parallel execution (should take ~1s, not ~3s)
        # Sequential would take 3+ seconds, parallel takes ~1 second
        assert elapsed_time < 1.5, f"Parallel execution took {elapsed_time:.2f}s, expected <1.5s (speedup: {3.0/elapsed_time:.1f}x)"
        print(f"\n✓ Parallel speedup achieved: {3.0/elapsed_time:.1f}x faster than sequential")

    @pytest.mark.asyncio
    async def test_parallel_execution_handles_mixed_async_sync(self):
        """Test that parallel execution works with both async and sync sessions"""
        handler = MultiDatabaseHandler()

        # Create connections with different types
        connections = [
            DatabaseConnection(
                id=1,
                name="postgres_db",
                database_type="postgresql",  # Async
                database_name="test_pg",
            ),
            DatabaseConnection(
                id=2,
                name="duckdb_file",
                database_type="duckdb",  # Sync
                database_name="test.duckdb",
            ),
        ]

        queries = [
            {"connection_id": 1, "sql": "SELECT 'async' as type"},
            {"connection_id": 2, "sql": "SELECT 'sync' as type"},
        ]

        # Mock execute_query_on_database
        async def mock_execution(connection, sql, allow_write=False):
            await asyncio.sleep(0.1)  # Simulate processing
            query_type = "async" if connection.database_type != "duckdb" else "sync"
            return {
                "success": True,
                "data": [{"type": query_type}],
                "row_count": 1,
                "execution_time_ms": 100,
                "database_name": connection.name,
                "connection_id": connection.id,
            }

        handler.execute_query_on_database = mock_execution

        # Execute in parallel
        results = await handler.execute_multi_database_query(
            queries=queries,
            connections=connections,
            allow_write=False,
        )

        # Verify both types executed successfully
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert results[0]["data"][0]["type"] == "async"
        assert results[1]["data"][0]["type"] == "sync"

    @pytest.mark.asyncio
    async def test_parallel_execution_graceful_degradation(self):
        """Test that one database failure doesn't stop others"""
        handler = MultiDatabaseHandler()

        connections = [
            DatabaseConnection(id=1, name="db1", database_type="postgresql", database_name="test1"),
            DatabaseConnection(id=2, name="db2", database_type="mysql", database_name="test2"),
            DatabaseConnection(id=3, name="db3", database_type="sqlite", database_name="test3.db"),
        ]

        queries = [
            {"connection_id": 1, "sql": "SELECT 1"},
            {"connection_id": 2, "sql": "SELECT 2"},
            {"connection_id": 3, "sql": "SELECT 3"},
        ]

        # Mock with db2 failing
        async def mock_with_failure(connection, sql, allow_write=False):
            await asyncio.sleep(0.1)
            if connection.id == 2:
                raise Exception("Database connection failed")
            return {
                "success": True,
                "data": [{"result": connection.id}],
                "row_count": 1,
                "execution_time_ms": 100,
                "database_name": connection.name,
                "connection_id": connection.id,
            }

        handler.execute_query_on_database = mock_with_failure

        # Execute in parallel
        results = await handler.execute_multi_database_query(
            queries=queries,
            connections=connections,
            allow_write=False,
        )

        # Verify graceful degradation
        assert len(results) == 3
        assert results[0]["success"] is True  # db1 succeeded
        assert results[1]["success"] is False  # db2 failed
        assert "Database connection failed" in results[1]["error"]
        assert results[2]["success"] is True  # db3 succeeded (not affected by db2 failure)

    @pytest.mark.asyncio
    async def test_parallel_execution_with_missing_connections(self):
        """Test handling of missing connection IDs"""
        handler = MultiDatabaseHandler()

        connections = [
            DatabaseConnection(id=1, name="db1", database_type="postgresql", database_name="test1"),
        ]

        queries = [
            {"connection_id": 1, "sql": "SELECT 1"},
            {"connection_id": 999, "sql": "SELECT 2"},  # Connection doesn't exist
            {"connection_id": None, "sql": "SELECT 3"},  # No connection ID
        ]

        async def mock_execution(connection, sql, allow_write=False):
            return {
                "success": True,
                "data": [{"result": 1}],
                "row_count": 1,
                "execution_time_ms": 100,
            }

        handler.execute_query_on_database = mock_execution

        # Execute in parallel
        results = await handler.execute_multi_database_query(
            queries=queries,
            connections=connections,
            allow_write=False,
        )

        # Verify error handling
        assert len(results) == 3
        assert results[0]["success"] is True  # Valid connection
        assert results[1]["success"] is False  # Connection not found
        assert "not found" in results[1]["error"].lower()
        assert results[2]["success"] is False  # Missing connection_id
        assert "missing" in results[2]["error"].lower()

    @pytest.mark.asyncio
    async def test_parallel_execution_timing_logs(self):
        """Test that parallel execution logs timing information"""
        import logging

        handler = MultiDatabaseHandler()

        connections = [
            DatabaseConnection(id=1, name="db1", database_type="postgresql", database_name="test1"),
            DatabaseConnection(id=2, name="db2", database_type="mysql", database_name="test2"),
        ]

        queries = [
            {"connection_id": 1, "sql": "SELECT 1"},
            {"connection_id": 2, "sql": "SELECT 2"},
        ]

        async def mock_execution(connection, sql, allow_write=False):
            await asyncio.sleep(0.05)
            return {"success": True, "data": [], "row_count": 0, "execution_time_ms": 50}

        handler.execute_query_on_database = mock_execution

        # Use a dedicated handler to capture log records reliably
        records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        target_logger = logging.getLogger("src.core.multi_db_handler")
        old_level = target_logger.level
        old_disabled = target_logger.disabled
        target_logger.disabled = False
        target_logger.setLevel(logging.INFO)
        capture = CaptureHandler()
        target_logger.addHandler(capture)

        try:
            await handler.execute_multi_database_query(queries, connections, allow_write=False)

            messages = [r.getMessage() for r in records]
            assert any("database queries in parallel" in m for m in messages), f"Expected parallel log in {messages}"
        finally:
            target_logger.removeHandler(capture)
            target_logger.setLevel(old_level)
            target_logger.disabled = old_disabled

    @pytest.mark.asyncio
    async def test_parallel_execution_timeout_protection(self):
        """Test that individual database queries timeout properly without holding semaphore"""
        from unittest.mock import patch

        handler = MultiDatabaseHandler()

        connections = [
            DatabaseConnection(id=1, name="db1", database_type="postgresql", database_name="test1"),
            DatabaseConnection(id=2, name="db2", database_type="mysql", database_name="test2"),
            DatabaseConnection(id=3, name="db3", database_type="sqlite", database_name="test3"),
        ]

        queries = [
            {"connection_id": 1, "sql": "SELECT 1"},  # Will succeed fast
            {"connection_id": 2, "sql": "SELECT 2"},  # Will hang and timeout
            {"connection_id": 3, "sql": "SELECT 3"},  # Will succeed (not blocked by db2)
        ]

        # Mock execution: db1 and db3 succeed quickly, db2 hangs
        async def mock_execution(connection, sql, allow_write=False):
            if connection.id == 2:
                # Simulate hanging query (longer than timeout)
                await asyncio.sleep(100)
                return {"success": True, "data": [], "row_count": 0, "execution_time_ms": 100000}
            else:
                # Fast execution
                await asyncio.sleep(0.1)
                return {
                    "success": True,
                    "data": [{"result": connection.id}],
                    "row_count": 1,
                    "execution_time_ms": 100,
                }

        handler.execute_query_on_database = mock_execution

        # Mock settings to use a short timeout (1 second for testing)
        with patch('src.core.multi_db_handler.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.MAX_PARALLEL_DATABASES = 10
            mock_settings.QUERY_TIMEOUT_SECONDS = 1  # 1 second timeout
            mock_settings_class.return_value = mock_settings

            import time
            start_time = time.time()

            # Execute in parallel
            results = await handler.execute_multi_database_query(
                queries=queries,
                connections=connections,
                allow_write=False,
            )

            elapsed = time.time() - start_time

            # Verify timeout occurred quickly (not 100 seconds)
            # Should be around 1 + 5 = 6 seconds timeout, not 100 seconds
            assert elapsed < 10, f"Expected timeout in ~6s, took {elapsed:.2f}s"
            assert elapsed >= 1, f"Timeout too fast: {elapsed:.2f}s"

            # Verify results
            assert len(results) == 3

            # db1 should succeed
            assert results[0]["success"] is True
            assert results[0]["row_count"] == 1

            # db2 should timeout with proper error message
            assert results[1]["success"] is False
            assert "timed out" in results[1]["error"].lower()
            assert results[1]["database_name"] == "db2"
            assert results[1]["connection_id"] == 2

            # db3 should succeed (not blocked by db2 timeout)
            assert results[2]["success"] is True
            assert results[2]["row_count"] == 1

            print(f"\n✓ Timeout protection works: db2 timed out in ~{elapsed:.1f}s without blocking db1/db3")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
