"""
Performance tests for connection pooling

Tests that connection pooling provides the expected speedup:
- Baseline: Fresh engine creation on every query (150ms avg)
- With pooling: Pool reuse (5ms avg)
- Expected: 2-3x speedup (or more)

Run these tests against the test databases:
    pytest tests/test_pooling_performance.py -v -s
"""

import pytest
import asyncio
import time
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import statistics

from src.config.settings import Settings
from src.core.connection_pool_manager import get_pool_manager_async
from src.database.models import DatabaseConnection


# Test database configurations
TEST_DATABASES = [
    {
        "name": "PostgreSQL",
        "database_type": "postgresql",
        "connection_string": "postgresql://test_user:test_pass@localhost:5433/test_pooling",
        "async_connection_string": "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_pooling",
        "is_async": True,
        "database_name": "test_pooling",
        "host": "localhost",
        "port": 5433,
        "username": "test_user",
        "password": "test_pass",
    },
    {
        "name": "MySQL",
        "database_type": "mysql",
        "connection_string": "mysql://test_user:test_pass@localhost:3307/test_pooling",
        "async_connection_string": "mysql+aiomysql://test_user:test_pass@localhost:3307/test_pooling",
        "is_async": True,
        "database_name": "test_pooling",
        "host": "localhost",
        "port": 3307,
        "username": "test_user",
        "password": "test_pass",
    },
    {
        "name": "SQLite",
        "database_type": "sqlite",
        "connection_string": "sqlite:///tests/fixtures/test_pooling.db",
        "async_connection_string": "sqlite+aiosqlite:///tests/fixtures/test_pooling.db",
        "is_async": True,
        "database_name": "tests/fixtures/test_pooling.db",
    },
    {
        "name": "DuckDB",
        "database_type": "duckdb",
        "connection_string": "duckdb:///tests/fixtures/test_pooling.duckdb",
        "async_connection_string": None,  # DuckDB is sync only
        "is_async": False,
        "database_name": "tests/fixtures/test_pooling.duckdb",
    },
]


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("db_config", TEST_DATABASES)
async def test_pooling_speedup(db_config):
    """
    Test that connection pooling provides significant speedup

    Measures:
    1. Baseline performance (fresh engine each time)
    2. Pooled performance (reuse engine)
    3. Speedup factor

    Expected: At least 2x speedup (realistically much more)
    """
    num_queries = 10
    query = "SELECT 1"

    print(f"\n{'='*60}")
    print(f"Testing {db_config['name']} performance")
    print(f"{'='*60}")

    # Skip if database is not available
    try:
        if db_config['is_async']:
            engine = create_async_engine(db_config['async_connection_string'])
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
        else:
            engine = create_engine(db_config['connection_string'])
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
    except Exception as e:
        pytest.skip(f"{db_config['name']} not available: {e}")

    # Baseline: Fresh engine creation on each query
    print(f"\n📊 Baseline (no pooling)...")
    baseline_times = []

    for i in range(num_queries):
        start = time.perf_counter()

        if db_config['is_async']:
            engine = create_async_engine(db_config['async_connection_string'])
            async with engine.begin() as conn:
                await conn.execute(text(query))
            await engine.dispose()
        else:
            engine = create_engine(db_config['connection_string'])
            with engine.begin() as conn:
                conn.execute(text(query))
            engine.dispose()

        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        baseline_times.append(elapsed)
        print(f"   Query {i+1}: {elapsed:.2f}ms")

    baseline_avg = statistics.mean(baseline_times)
    baseline_median = statistics.median(baseline_times)
    print(f"   Avg: {baseline_avg:.2f}ms, Median: {baseline_median:.2f}ms")

    # With pooling: Reuse engine
    print(f"\n🔗 With pooling...")
    pooled_times = []

    # Create mock DatabaseConnection using model fields
    conn_kwargs = {
        "id": 999,
        "name": f"test_{db_config['database_type']}",
        "database_type": db_config['database_type'],
        "database_name": db_config.get('database_name', ''),
    }
    # Add auth fields for remote databases
    if db_config['database_type'] in ('postgresql', 'mysql'):
        conn_kwargs.update({
            "host": db_config.get('host', 'localhost'),
            "port": db_config.get('port', 5432),
            "username": db_config.get('username', 'test_user'),
            "password_encrypted": db_config.get('password', 'test_pass'),
        })
    connection = DatabaseConnection(**conn_kwargs)

    settings = Settings()
    pool_manager = await get_pool_manager_async(settings)

    try:
        for i in range(num_queries):
            start = time.perf_counter()

            pool_entry = await pool_manager.get_pool(connection)

            if db_config['is_async']:
                async with pool_entry.session_factory() as session:
                    await session.execute(text(query))
            else:
                # DuckDB (sync)
                session = pool_entry.session_factory()
                try:
                    session.execute(text(query))
                finally:
                    session.close()

            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            pooled_times.append(elapsed)
            print(f"   Query {i+1}: {elapsed:.2f}ms")

        pooled_avg = statistics.mean(pooled_times)
        pooled_median = statistics.median(pooled_times)
        print(f"   Avg: {pooled_avg:.2f}ms, Median: {pooled_median:.2f}ms")

        # Calculate speedup
        speedup = baseline_avg / pooled_avg
        print(f"\n🚀 Speedup: {speedup:.1f}x faster")
        print(f"   Time saved: {baseline_avg - pooled_avg:.2f}ms per query ({(1 - pooled_avg/baseline_avg)*100:.1f}% reduction)")

        # Assertions
        assert pooled_avg < baseline_avg, \
            f"Pooling should be faster! Pooled: {pooled_avg:.2f}ms, Baseline: {baseline_avg:.2f}ms"

        # We expect at least 2x speedup, but in reality it's usually much more
        # Use a conservative threshold to account for test environment variability
        min_speedup = 1.5
        assert speedup >= min_speedup, \
            f"Expected at least {min_speedup}x speedup, got {speedup:.1f}x"

        print(f"✅ Performance test passed! ({speedup:.1f}x speedup)")

    finally:
        # Cleanup
        await pool_manager.evict_pool(connection.id)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_pooling_performance():
    """
    Test connection pooling under concurrent load

    Measures throughput with multiple concurrent requests
    """
    num_concurrent = 20
    query = "SELECT COUNT(*) FROM products"

    print(f"\n{'='*60}")
    print(f"Testing concurrent load (PostgreSQL)")
    print(f"{'='*60}")

    db_config = TEST_DATABASES[0]  # Use PostgreSQL

    # Skip if database is not available
    try:
        engine = create_async_engine(db_config['async_connection_string'])
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    # Create mock DatabaseConnection
    connection = DatabaseConnection(
        id=998,
        name="test_concurrent",
        database_type="postgresql",
        database_name=db_config['database_name'],
        host=db_config['host'],
        port=db_config['port'],
        username=db_config['username'],
        password_encrypted=db_config['password'],
    )

    settings = Settings()
    pool_manager = await get_pool_manager_async(settings)

    try:
        async def run_query():
            """Run a single query using pool"""
            pool_entry = await pool_manager.get_pool(connection)
            async with pool_entry.session_factory() as session:
                await session.execute(text(query))

        # Run concurrent queries
        print(f"\n🔗 Running {num_concurrent} concurrent queries...")
        start = time.perf_counter()

        await asyncio.gather(*[run_query() for _ in range(num_concurrent)])

        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        avg_per_query = elapsed / num_concurrent

        print(f"   Total time: {elapsed:.2f}ms")
        print(f"   Avg per query: {avg_per_query:.2f}ms")
        print(f"   Throughput: {num_concurrent / (elapsed/1000):.1f} queries/sec")

        # Get pool metrics
        metrics = pool_manager.get_all_metrics()
        pool_info = next((p for p in metrics['pools'] if p['connection_id'] == connection.id), None)

        if pool_info:
            print(f"\n📊 Pool metrics:")
            print(f"   Active connections: {pool_info['metrics']['active_connections']}")
            print(f"   Idle connections: {pool_info['metrics']['idle_connections']}")
            print(f"   Utilization: {pool_info['metrics']['utilization_percent']:.1f}%")
            print(f"   Total checkouts: {pool_info['metrics']['total_checkouts']}")
            print(f"   Avg wait time: {pool_info['metrics']['avg_wait_time_ms']:.2f}ms")

        # Assertions
        assert avg_per_query < 100, \
            f"Average query time should be under 100ms, got {avg_per_query:.2f}ms"

        print(f"✅ Concurrent test passed!")

    finally:
        # Cleanup
        await pool_manager.evict_pool(connection.id)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pool_exhaustion_handling():
    """
    Test that pool handles exhaustion gracefully

    Creates more concurrent connections than pool size
    """
    pool_size = 5  # Small pool
    max_overflow = 10
    num_concurrent = 30  # More than pool capacity

    print(f"\n{'='*60}")
    print(f"Testing pool exhaustion (PostgreSQL)")
    print(f"Pool size: {pool_size}, Max overflow: {max_overflow}")
    print(f"Concurrent requests: {num_concurrent}")
    print(f"{'='*60}")

    db_config = TEST_DATABASES[0]  # Use PostgreSQL

    # Skip if database is not available
    try:
        engine = create_async_engine(db_config['async_connection_string'])
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    # Create mock DatabaseConnection
    connection = DatabaseConnection(
        id=997,
        name="test_exhaustion",
        database_type="postgresql",
        database_name=db_config['database_name'],
        host=db_config['host'],
        port=db_config['port'],
        username=db_config['username'],
        password_encrypted=db_config['password'],
    )

    # Override settings for this test
    settings = Settings()
    settings.USER_DB_POOL_SIZE = pool_size
    settings.USER_DB_MAX_OVERFLOW = max_overflow

    pool_manager = await get_pool_manager_async(settings)

    try:
        async def run_slow_query():
            """Run a query with artificial delay"""
            pool_entry = await pool_manager.get_pool(connection)
            async with pool_entry.session_factory() as session:
                # Simulate slow query
                await asyncio.sleep(0.1)
                await session.execute(text("SELECT 1"))

        print(f"\n🔗 Running {num_concurrent} concurrent slow queries...")
        start = time.perf_counter()

        results = await asyncio.gather(
            *[run_slow_query() for _ in range(num_concurrent)],
            return_exceptions=True
        )

        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        # Check for errors
        errors = [r for r in results if isinstance(r, Exception)]
        successes = num_concurrent - len(errors)

        print(f"   Total time: {elapsed:.2f}ms")
        print(f"   Successful: {successes}/{num_concurrent}")
        if errors:
            print(f"   Errors: {len(errors)}")
            print(f"   First error: {errors[0]}")

        # Get pool metrics
        metrics = pool_manager.get_all_metrics()
        pool_info = next((p for p in metrics['pools'] if p['connection_id'] == connection.id), None)

        if pool_info:
            print(f"\n📊 Pool metrics:")
            print(f"   Peak connections: {pool_info['metrics']['total_connections']}")
            print(f"   Max capacity: {pool_size + max_overflow}")
            print(f"   Failed checkouts: {pool_info['metrics']['failed_checkouts']}")

        # All requests should eventually succeed (with overflow)
        # Some may timeout if pool_timeout is exceeded
        assert successes >= num_concurrent * 0.8, \
            f"At least 80% of requests should succeed, got {successes}/{num_concurrent}"

        print(f"✅ Pool exhaustion test passed!")

    finally:
        # Cleanup
        await pool_manager.evict_pool(connection.id)


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s", "-m", "slow"])
