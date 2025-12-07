"""
Unit tests for ConnectionPoolManager

Tests verify:
- Pool creation and reuse
- Pool isolation by connection_id
- Concurrent access and thread safety
- Idle pool cleanup
- Max age eviction
- MongoDB handling
- Metrics tracking
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.core.connection_pool_manager import (
    ConnectionPoolManager,
    PoolEntry,
    PoolMetrics,
    HealthStatus,
    get_pool_manager_async,
)
from src.database.models import DatabaseConnection
from src.config.settings import Settings


@pytest.fixture
def test_settings():
    """Create test settings with shorter timeouts for faster tests"""
    return Settings(
        ENABLE_CONNECTION_POOLING=True,
        USER_DB_POOL_SIZE=5,
        USER_DB_MAX_OVERFLOW=10,
        USER_DB_POOL_RECYCLE=3600,
        USER_DB_POOL_TIMEOUT=30,
        POOL_IDLE_CLEANUP_INTERVAL=1,  # 1 second for testing
        POOL_MAX_IDLE_TIME=2,  # 2 seconds for testing
        POOL_MAX_AGE=5,  # 5 seconds for testing
        POOL_PRE_PING=True,
    )


@pytest.fixture
async def pool_manager(test_settings):
    """Create a fresh ConnectionPoolManager instance for each test"""
    # Reset singleton
    ConnectionPoolManager._instance = None

    manager = ConnectionPoolManager(test_settings)
    await manager.initialize()

    yield manager

    # Cleanup
    await manager.close_all_pools()


@pytest.fixture
def mock_postgresql_connection():
    """Mock PostgreSQL connection"""
    return DatabaseConnection(
        id=1,
        name="test_postgres",
        database_type="postgresql",
        database_name="testdb",
        host="localhost",
        port=5432,
        username="testuser",
        password_encrypted="testpass",
    )


@pytest.fixture
def mock_sqlite_connection():
    """Mock SQLite connection"""
    return DatabaseConnection(
        id=2,
        name="test_sqlite",
        database_type="sqlite",
        database_name=":memory:",
    )


@pytest.fixture
def mock_duckdb_connection():
    """Mock DuckDB connection"""
    return DatabaseConnection(
        id=3,
        name="test_duckdb",
        database_type="duckdb",
        database_name=":memory:",
    )


@pytest.fixture
def mock_mongodb_connection():
    """Mock MongoDB connection"""
    return DatabaseConnection(
        id=4,
        name="test_mongodb",
        database_type="mongodb",
        database_name="testdb",
        host="localhost",
        port=27017,
    )


class TestConnectionPoolManager:
    """Test ConnectionPoolManager singleton and pool lifecycle"""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, test_settings):
        """Test that get_pool_manager_async returns same instance"""
        # Reset singleton
        ConnectionPoolManager._instance = None

        manager1 = await get_pool_manager_async(test_settings)
        manager2 = await get_pool_manager_async(test_settings)

        assert manager1 is manager2

        # Cleanup
        await manager1.close_all_pools()

    @pytest.mark.asyncio
    async def test_pool_creation_sqlite(self, pool_manager, mock_sqlite_connection):
        """Test pool creation for SQLite database"""
        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            pool_entry = await pool_manager.get_pool(mock_sqlite_connection)

            assert pool_entry is not None
            assert pool_entry.connection_id == mock_sqlite_connection.id
            assert pool_entry.database_type == mock_sqlite_connection.database_type
            assert pool_entry.connection_name == mock_sqlite_connection.name
            assert pool_entry.metrics.total_checkouts == 1
            assert pool_entry.metrics.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_pool_creation_duckdb(self, pool_manager, mock_duckdb_connection):
        """Test pool creation for DuckDB (sync engine)"""
        with patch('src.core.connection_pool_manager.create_engine') as mock_engine:
            mock_sync_engine = MagicMock()
            mock_sync_engine.pool.size.return_value = 5
            mock_sync_engine.pool.overflow.return_value = 10
            mock_engine.return_value = mock_sync_engine

            pool_entry = await pool_manager.get_pool(mock_duckdb_connection)

            assert pool_entry is not None
            assert pool_entry.connection_id == mock_duckdb_connection.id
            assert pool_entry.database_type == "duckdb"
            assert pool_entry.connection_name == mock_duckdb_connection.name
            assert pool_entry.metrics.total_checkouts == 1

    @pytest.mark.asyncio
    async def test_pool_reuse(self, pool_manager, mock_sqlite_connection):
        """Test that same pool is reused for same connection"""
        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            # First call creates pool
            pool1 = await pool_manager.get_pool(mock_sqlite_connection)
            initial_checkouts = pool1.metrics.total_checkouts

            # Second call reuses pool
            pool2 = await pool_manager.get_pool(mock_sqlite_connection)

            assert pool1 is pool2
            assert pool2.metrics.total_checkouts == initial_checkouts + 1

            # Engine should only be created once
            assert mock_engine.call_count == 1

    @pytest.mark.asyncio
    async def test_pool_isolation_by_connection_id(self, pool_manager):
        """Test that different connections get separate pools"""
        conn1 = DatabaseConnection(
            id=1, name="db1", database_type="sqlite", database_name=":memory:"
        )
        conn2 = DatabaseConnection(
            id=2, name="db2", database_type="sqlite", database_name=":memory:"
        )

        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            pool1 = await pool_manager.get_pool(conn1)
            pool2 = await pool_manager.get_pool(conn2)

            assert pool1 is not pool2
            assert pool1.connection_id == 1
            assert pool2.connection_id == 2

            # Two separate engines created
            assert mock_engine.call_count == 2

    @pytest.mark.asyncio
    async def test_mongodb_not_implemented(self, pool_manager, mock_mongodb_connection):
        """Test that MongoDB raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await pool_manager.get_pool(mock_mongodb_connection)

        assert "MongoDB" in str(exc_info.value)
        assert "PostgreSQL, MySQL, SQLite, DuckDB" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pooling_disabled_raises_error(self, mock_sqlite_connection):
        """Test that pooling disabled raises RuntimeError"""
        disabled_settings = Settings(ENABLE_CONNECTION_POOLING=False)
        manager = ConnectionPoolManager(disabled_settings)
        await manager.initialize()

        with pytest.raises(RuntimeError) as exc_info:
            await manager.get_pool(mock_sqlite_connection)

        assert "Connection pooling is disabled" in str(exc_info.value)

        await manager.close_all_pools()

    @pytest.mark.asyncio
    async def test_manual_pool_eviction(self, pool_manager, mock_sqlite_connection):
        """Test manual pool eviction by connection_id"""
        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_async_engine = AsyncMock()
            mock_engine.return_value = mock_async_engine

            # Create pool
            await pool_manager.get_pool(mock_sqlite_connection)

            # Verify pool exists
            key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)
            assert key in pool_manager._pools

            # Evict pool
            await pool_manager.evict_pool(mock_sqlite_connection.id)

            # Verify pool removed
            assert key not in pool_manager._pools

            # Verify engine.dispose() was called
            mock_async_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_pool_access(self, pool_manager, mock_sqlite_connection):
        """Test concurrent access to same pool (thread safety)"""
        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            # Concurrently request same pool 10 times
            tasks = [pool_manager.get_pool(mock_sqlite_connection) for _ in range(10)]
            pools = await asyncio.gather(*tasks)

            # All should return same pool
            first_pool = pools[0]
            assert all(pool is first_pool for pool in pools)

            # Engine created only once (thread-safe singleton behavior)
            assert mock_engine.call_count == 1

            # Checkouts should be 10
            assert first_pool.metrics.total_checkouts == 10

    @pytest.mark.asyncio
    async def test_idle_pool_cleanup(self, test_settings, mock_sqlite_connection):
        """Test that idle pools are cleaned up after timeout"""
        # Use very short timeout for testing
        test_settings.POOL_MAX_IDLE_TIME = 1  # 1 second

        manager = ConnectionPoolManager(test_settings)
        await manager.initialize()

        try:
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
                mock_async_engine = AsyncMock()
                mock_engine.return_value = mock_async_engine

                # Create pool
                pool_entry = await manager.get_pool(mock_sqlite_connection)
                key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)

                # Pool should exist
                assert key in manager._pools

                # Manually trigger last_used update to be old
                pool_entry.metrics.last_used = datetime.now() - timedelta(seconds=2)

                # Run cleanup
                await manager._cleanup_idle_pools()

                # Pool should be evicted
                assert key not in manager._pools

                # Engine.dispose() should be called
                mock_async_engine.dispose.assert_called_once()
        finally:
            await manager.close_all_pools()

    @pytest.mark.asyncio
    async def test_max_age_eviction(self, test_settings, mock_sqlite_connection):
        """Test that pools are evicted after max age"""
        # Use very short max age for testing
        test_settings.POOL_MAX_AGE = 1  # 1 second

        manager = ConnectionPoolManager(test_settings)
        await manager.initialize()

        try:
            with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
                mock_async_engine = AsyncMock()
                mock_engine.return_value = mock_async_engine

                # Create pool
                pool_entry = await manager.get_pool(mock_sqlite_connection)
                key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)

                # Manually set created_at to be old
                pool_entry.metrics.created_at = datetime.now() - timedelta(seconds=2)

                # Run cleanup
                await manager._cleanup_idle_pools()

                # Pool should be evicted due to age
                assert key not in manager._pools
        finally:
            await manager.close_all_pools()

    @pytest.mark.asyncio
    async def test_get_all_metrics(self, pool_manager):
        """Test metrics aggregation across all pools"""
        conn1 = DatabaseConnection(
            id=1, name="db1", database_type="sqlite", database_name=":memory:"
        )
        conn2 = DatabaseConnection(
            id=2, name="db2", database_type="sqlite", database_name=":memory:"
        )

        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            # Create two pools
            await pool_manager.get_pool(conn1)
            await pool_manager.get_pool(conn2)

            # Get metrics
            metrics = pool_manager.get_all_metrics()

            assert metrics["total_pools"] == 2
            assert len(metrics["pools"]) == 2
            assert "global_metrics" in metrics
            assert metrics["global_metrics"]["total_active_connections"] >= 0

            # Verify top-level fields in pool data
            pool_data = metrics["pools"][0]
            assert "connection_id" in pool_data
            assert "database_type" in pool_data
            assert "connection_name" in pool_data
            assert "age_seconds" in pool_data
            assert "created_at" in pool_data
            assert "last_used" in pool_data
            assert "metrics" in pool_data

            # Verify connection_name matches
            assert pool_data["connection_name"] in ["db1", "db2"]

    @pytest.mark.asyncio
    async def test_warm_pool(self, pool_manager, mock_sqlite_connection):
        """Test pre-warming a pool"""
        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            # Pre-warm pool
            await pool_manager.warm_pool(mock_sqlite_connection)

            # Pool should exist
            key = (mock_sqlite_connection.id, mock_sqlite_connection.database_type)
            assert key in pool_manager._pools

            # Engine created
            assert mock_engine.call_count == 1

    @pytest.mark.asyncio
    async def test_close_all_pools(self, test_settings):
        """Test graceful shutdown of all pools"""
        manager = ConnectionPoolManager(test_settings)
        await manager.initialize()

        conn1 = DatabaseConnection(
            id=1, name="db1", database_type="sqlite", database_name=":memory:"
        )
        conn2 = DatabaseConnection(
            id=2, name="db2", database_type="sqlite", database_name=":memory:"
        )

        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_async_engine = AsyncMock()
            mock_engine.return_value = mock_async_engine

            # Create two pools
            await manager.get_pool(conn1)
            await manager.get_pool(conn2)

            # Close all pools
            await manager.close_all_pools()

            # All pools should be removed
            assert len(manager._pools) == 0

            # Engine.dispose() should be called twice
            assert mock_async_engine.dispose.call_count == 2

    @pytest.mark.asyncio
    async def test_pool_metrics_tracking(self, pool_manager, mock_sqlite_connection):
        """Test that pool metrics are tracked correctly"""
        with patch('src.core.connection_pool_manager.create_async_engine') as mock_engine:
            mock_engine.return_value = AsyncMock()

            # Create pool
            pool1 = await pool_manager.get_pool(mock_sqlite_connection)
            initial_time = pool1.metrics.last_used

            # Wait a bit
            await asyncio.sleep(0.1)

            # Get pool again
            pool2 = await pool_manager.get_pool(mock_sqlite_connection)

            # Metrics should be updated
            assert pool2.metrics.last_used > initial_time
            assert pool2.metrics.total_checkouts == 2
            assert pool2.metrics.health_status == HealthStatus.HEALTHY


class TestPoolMetrics:
    """Test PoolMetrics dataclass methods"""

    def test_metrics_to_dict(self):
        """Test conversion of metrics to dictionary"""
        metrics = PoolMetrics(
            active_connections=5,
            idle_connections=3,
            total_capacity=10,
            total_checkouts=100,
            total_checkins=95,
            avg_wait_time_ms=5.2,
            max_wait_time_ms=15.8,
        )

        data = metrics.to_dict()

        assert data["active_connections"] == 5
        assert data["idle_connections"] == 3
        assert data["total_capacity"] == 10
        assert data["utilization_percent"] == 50.0  # 5/10 * 100
        assert data["total_checkouts"] == 100
        assert data["health_status"] == "healthy"
        assert "created_at" in data
        assert "last_used" in data

    def test_utilization_calculation(self):
        """Test utilization percentage calculation"""
        metrics = PoolMetrics(
            active_connections=7,
            total_capacity=10,
        )

        metrics.update_utilization()

        assert metrics.utilization_percent == 70.0

    def test_age_calculation(self):
        """Test age calculation"""
        metrics = PoolMetrics(
            created_at=datetime.now() - timedelta(seconds=60)
        )

        metrics.update_age()

        assert metrics.total_age_seconds >= 60
        assert metrics.total_age_seconds < 61
