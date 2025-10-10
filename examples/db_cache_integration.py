"""Example: Database + Cache Integration"""
import asyncio
from datetime import datetime
from src.config.settings import Settings
from src.database.connection import get_db_manager
from src.database.models import QueryHistory
from src.cache import get_redis_cache, cache_query_result


async def save_query_to_db(nl_query: str, sql: str, execution_time: float):
    """Save query to database"""
    settings = Settings()
    db_manager = get_db_manager(settings)

    if not db_manager.async_session_factory:
        await db_manager.initialize_async()

    async with db_manager.get_async_session() as session:
        query_record = QueryHistory(
            natural_language_query=nl_query,
            generated_sql=sql,
            executed=True,
            execution_time_ms=execution_time,
            database_type="postgresql",
            model_used="llama3",
        )
        session.add(query_record)
        await session.commit()
        print(f"  💾 Saved to database: Query #{query_record.id}")
        return query_record.id


@cache_query_result(ttl=1800)
async def process_query_with_cache(nl_query: str):
    """
    Process a natural language query with caching

    This simulates the full query pipeline:
    1. Check cache (via decorator)
    2. If miss, "generate SQL" and execute
    3. Save to database
    4. Return result (automatically cached)
    """
    print(f"  🔄 Processing query: '{nl_query}'")

    # Simulate SQL generation (this would use LLM in real implementation)
    await asyncio.sleep(0.5)  # Simulate LLM latency
    generated_sql = f"SELECT * FROM customers WHERE name LIKE '%{nl_query}%'"

    # Simulate query execution
    execution_time = 42.5  # ms

    # Save to database
    query_id = await save_query_to_db(nl_query, generated_sql, execution_time)

    # Return result
    result = {
        "query_id": query_id,
        "nl_query": nl_query,
        "sql": generated_sql,
        "execution_time_ms": execution_time,
        "timestamp": datetime.utcnow().isoformat(),
        "data": [
            {"id": 1, "name": "John Doe", "email": "john@example.com"},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
        ]
    }

    return result


async def main():
    """Demonstrate database + cache integration"""
    print("🧙‍♂️ Database Guru - DB + Cache Integration Example\n")

    settings = Settings()

    # Initialize database
    print("📊 Initializing database...")
    db_manager = get_db_manager(settings)
    await db_manager.initialize_async()
    await db_manager.create_tables_async()
    print("  ✅ Database ready\n")

    # Initialize cache
    print("💾 Initializing cache...")
    cache = get_redis_cache(settings)
    await cache.connect()
    print("  ✅ Cache ready\n")

    # Test query processing
    test_query = "show me all customers in California"

    print("=" * 60)
    print("🔍 First Query (Cache Miss - will process fully)")
    print("=" * 60)
    result1 = await process_query_with_cache(test_query)
    print(f"  ✓ Result: {len(result1['data'])} rows")
    print(f"  ✓ SQL: {result1['sql'][:50]}...")
    print()

    print("=" * 60)
    print("🔍 Second Query (Cache Hit - instant return)")
    print("=" * 60)
    result2 = await process_query_with_cache(test_query)
    print(f"  ✓ Result: {len(result2['data'])} rows (from cache!)")
    print(f"  ✓ Same query ID: {result1['query_id'] == result2['query_id']}")
    print()

    # Check cache stats
    print("=" * 60)
    print("📊 Cache Statistics")
    print("=" * 60)
    query_exists = await cache.exists(f"query:{hash(test_query)}")
    print(f"  ✓ Query cached: {query_exists}")
    print()

    # Cleanup
    print("🧹 Cleaning up...")
    await cache.clear_pattern("query:*")
    await cache.disconnect()
    await db_manager.close_async()

    print("\n✨ Integration example complete!")


if __name__ == "__main__":
    asyncio.run(main())
