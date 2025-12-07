"""
Integration tests for pooled query execution

Tests verify that:
- Queries use connection pooling when enabled
- Multiple queries reuse the same pool
- Pool metrics are tracked correctly
- Query execution works correctly with pooling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.core.user_db_connector import UserDatabaseConnector
from src.core.connection_pool_manager import (
    ConnectionPoolManager,
    get_pool_manager_async,
)
from src.database.models import DatabaseConnection
from src.config.settings import Settings


@pytest.fixture
def test_settings():
    """Settings with pooling enabled"""
    return Settings(
        ENABLE_CONNECTION_POOLING=True,
        USER_DB_POOL_SIZE=5,
        USER_DB_MAX_OVERFLOW=10,
    )


@pytest.fixture
async def pool_manager(test_settings):
    """Create fresh pool manager for tests"""
    # Reset singleton
    ConnectionPoolManager._instance = None

    manager = ConnectionPoolManager(test_settings)
    await manager.initialize()

    yield manager

    # Cleanup
    await manager.close_all_pools()


@pytest.fixture
def mock_sqlite_connection():
    """Mock SQLite connection"""
    return DatabaseConnection(
        id=1,
        name="test_db",
        database_type="sqlite",
        database_name=":memory:",
    )


@pytest.fixture
def mock_postgresql_connection():
    """Mock PostgreSQL connection"""
    return DatabaseConnection(
        id=2,
        name="test_postgres",
        database_type="postgresql",
        database_name="testdb",
        host="localhost",
        port=5432,
        username="testuser",
        password_encrypted="testpass",
    )


class TestPooledQueryExecution:
    """Test query execution with connection pooling"""

    def _mock_pool_manager(self, pool_manager):
        """Helper to mock get_pool_manager_async to return test fixture"""
        async def mock_get_pool_manager(settings=None):
            return pool_manager
        return patch('src.core.user_db_connector.get_pool_manager_async', side_effect=mock_get_pool_manager)

    @pytest.mark.asyncio
    async def test_query_uses_connection_pool(self, pool_manager, mock_sqlite_connection):
        """Test that queries use the connection pool instead of creating fresh engines"""

        with self._mock_pool_manager(pool_manager):
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_create_engine:
                mock_async_engine = AsyncMock()
                mock_create_engine.return_value = mock_async_engine

                # Execute first query
                async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                    assert session is not None

                # Engine should be created once
                assert mock_create_engine.call_count == 1

                # Pool should exist
                key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)
                assert key in pool_manager._pools

                # Execute second query
                async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                    assert session is not None

                # Engine should NOT be created again (reused from pool)
                assert mock_create_engine.call_count == 1, "Engine should be reused from pool"

                # Pool metrics should be updated
                pool_entry = pool_manager._pools[key]
                assert pool_entry.metrics.total_checkouts == 2
                assert pool_entry.metrics.total_checkins == 2

    @pytest.mark.asyncio
    async def test_multiple_queries_share_pool(self, pool_manager, mock_sqlite_connection):
        """Test that multiple concurrent queries share the same pool"""

        with self._mock_pool_manager(pool_manager):
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_create_engine:
                mock_async_engine = AsyncMock()
                mock_create_engine.return_value = mock_async_engine

                # Execute 5 concurrent queries
                async def execute_query():
                    async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                        return session is not None

                results = await asyncio.gather(*[execute_query() for _ in range(5)])

                # All queries should succeed
                assert all(results)

                # Only one engine should be created (shared pool)
                assert mock_create_engine.call_count == 1

                # Pool metrics should show 5 checkouts
                key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)
                pool_entry = pool_manager._pools[key]
                assert pool_entry.metrics.total_checkouts == 5
                assert pool_entry.metrics.total_checkins == 5

    @pytest.mark.asyncio
    async def test_pool_metrics_tracking(self, pool_manager, mock_sqlite_connection):
        """Test that pool metrics are tracked correctly during query execution"""

        with self._mock_pool_manager(pool_manager):
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_create_engine:
                mock_async_engine = AsyncMock()
                mock_create_engine.return_value = mock_async_engine

                key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)

                # Execute query 1
                initial_time = datetime.now()
                async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                    pass

                pool_entry = pool_manager._pools[key]

                # Check metrics after first query
                assert pool_entry.metrics.total_checkouts == 1
                assert pool_entry.metrics.total_checkins == 1
                assert pool_entry.metrics.last_used >= initial_time

                # Wait a bit
                await asyncio.sleep(0.1)

                # Execute query 2
                async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                    pass

                # Check metrics updated
                assert pool_entry.metrics.total_checkouts == 2
                assert pool_entry.metrics.total_checkins == 2
                assert pool_entry.metrics.last_used > initial_time

    @pytest.mark.asyncio
    async def test_different_connections_get_separate_pools(self, pool_manager):
        """Test that different connections get separate pools"""

        conn1 = DatabaseConnection(
            id=1, name="db1", database_type="sqlite", database_name=":memory:"
        )
        conn2 = DatabaseConnection(
            id=2, name="db2", database_type="sqlite", database_name=":memory:"
        )

        with self._mock_pool_manager(pool_manager):
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_create_engine:
                mock_async_engine = AsyncMock()
                mock_create_engine.return_value = mock_async_engine

                # Execute query on conn1
                async with UserDatabaseConnector.get_user_db_session(conn1) as session:
                    pass

                # Execute query on conn2
                async with UserDatabaseConnector.get_user_db_session(conn2) as session:
                    pass

                # Two separate engines should be created
                assert mock_create_engine.call_count == 2

                # Two pools should exist
                assert len(pool_manager._pools) == 2

                key1 = (conn1.id, conn1.database_type)
                key2 = (conn2.id, conn2.database_type)

                assert key1 in pool_manager._pools
                assert key2 in pool_manager._pools

                # Each pool should have 1 checkout
                assert pool_manager._pools[key1].metrics.total_checkouts == 1
                assert pool_manager._pools[key2].metrics.total_checkouts == 1

    @pytest.mark.asyncio
    async def test_duckdb_sync_session_pooling(self, pool_manager):
        """Test that DuckDB (sync) sessions work with pooling"""

        duckdb_conn = DatabaseConnection(
            id=3,
            name="test_duckdb",
            database_type="duckdb",
            database_name=":memory:",
        )

        with self._mock_pool_manager(pool_manager):
            with patch('src.core.connection_pool_manager.create_engine') as mock_create_engine:
                mock_sync_engine = MagicMock()
                mock_sync_engine.pool.size.return_value = 5
                mock_sync_engine.pool.overflow.return_value = 10
                mock_create_engine.return_value = mock_sync_engine

                # Execute query
                async with UserDatabaseConnector.get_user_db_session(duckdb_conn) as session:
                    assert session is not None

                # Sync engine should be created
                assert mock_create_engine.call_count == 1

                # Pool should exist
                key = (duckdb_conn.id, duckdb_conn.database_type)
                assert key in pool_manager._pools

                # Metrics should be tracked
                pool_entry = pool_manager._pools[key]
                assert pool_entry.metrics.total_checkouts == 1
                assert pool_entry.metrics.total_checkins == 1

    @pytest.mark.asyncio
    async def test_pool_reuse_performance(self, pool_manager, mock_sqlite_connection):
        """Test that pool reuse is faster than creating fresh engines"""
        import time

        with self._mock_pool_manager(pool_manager):
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_create_engine:
                # Simulate slow engine creation
                def slow_create(*args, **kwargs):
                    import time
                    time.sleep(0.1)  # 100ms to create engine
                    return AsyncMock()

                mock_create_engine.side_effect = slow_create

                # First query (creates pool) - should be slow
                start_time = time.time()
                async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                    pass
                first_query_time = time.time() - start_time

                # Second query (reuses pool) - should be fast
                start_time = time.time()
                async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                    pass
                second_query_time = time.time() - start_time

                # First query should take at least 100ms (engine creation)
                assert first_query_time >= 0.1

                # Second query should be much faster (no engine creation)
                assert second_query_time < first_query_time
                assert second_query_time < 0.05  # Less than 50ms

                # Only one engine created
                assert mock_create_engine.call_count == 1

    @pytest.mark.asyncio
    async def test_pool_capacity_settings(self, mock_sqlite_connection):
        """Test that pool capacity is set from settings"""

        custom_settings = Settings(
            ENABLE_CONNECTION_POOLING=True,
            USER_DB_POOL_SIZE=15,
            USER_DB_MAX_OVERFLOW=25,
        )

        # Reset singleton
        ConnectionPoolManager._instance = None
        manager = ConnectionPoolManager(custom_settings)
        await manager.initialize()

        try:
            # Mock get_pool_manager_async to return our custom manager
            async def mock_get_pool_manager(settings=None):
                return manager

            with patch('src.core.user_db_connector.get_pool_manager_async', side_effect=mock_get_pool_manager):
                with patch('src.core.connection_pool_manager.create_async_engine') as mock_create_engine:
                    mock_async_engine = AsyncMock()
                    mock_create_engine.return_value = mock_async_engine

                    # Execute query
                    async with UserDatabaseConnector.get_user_db_session(mock_sqlite_connection) as session:
                        pass

                    # Check pool capacity set from settings
                    key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)
                    pool_entry = manager._pools[key]

                    # Total capacity = pool_size + max_overflow
                    expected_capacity = 15 + 25  # 40
                    assert pool_entry.metrics.total_capacity == expected_capacity

        finally:
            await manager.close_all_pools()

    @pytest.mark.asyncio
    async def test_pooling_disabled_fallback(self):
        """Test that queries raise error when pooling is disabled"""

        disabled_settings = Settings(
            ENABLE_CONNECTION_POOLING=False,
        )

        # This test verifies error handling when pooling is disabled
        # The UserDatabaseConnector should raise an error from pool_manager.get_pool()

        conn = DatabaseConnection(
            id=1,
            name="test_db",
            database_type="sqlite",
            database_name=":memory:",
        )

        # Reset singleton with disabled settings
        ConnectionPoolManager._instance = None
        disabled_manager = ConnectionPoolManager(disabled_settings)
        await disabled_manager.initialize()

        # Mock get_pool_manager_async to return disabled manager
        async def mock_get_pool_manager(settings=None):
            return disabled_manager

        try:
            with patch('src.core.user_db_connector.get_pool_manager_async', side_effect=mock_get_pool_manager):
                with pytest.raises(RuntimeError, match="Connection pooling is disabled"):
                    async with UserDatabaseConnector.get_user_db_session(conn) as session:
                        pass
        finally:
            await disabled_manager.close_all_pools()
