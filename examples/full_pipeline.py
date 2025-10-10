"""Full Pipeline: Natural Language -> SQL -> Cached Results"""
import asyncio
from datetime import datetime
from src.config.settings import Settings
from src.database import get_db_manager
from src.database.models import QueryHistory
from src.cache import get_redis_cache, cache_query_result
from src.llm import SQLGenerator


# Sample database schema
SAMPLE_SCHEMA = """
Tables:
- customers (id, name, email, city, state, created_at)
- products (id, name, price, category, stock_quantity)
- orders (id, customer_id, order_date, total_amount, status)
- order_items (id, order_id, product_id, quantity, price)

Relationships:
- orders.customer_id -> customers.id
- order_items.order_id -> orders.id
- order_items.product_id -> products.id
"""


async def save_query_history(
    nl_query: str,
    sql: str,
    is_valid: bool,
    execution_time: float = 0,
):
    """Save query to database"""
    db_manager = get_db_manager()

    async with db_manager.get_async_session() as session:
        query_record = QueryHistory(
            natural_language_query=nl_query,
            generated_sql=sql,
            sql_validated=is_valid,
            executed=True,
            execution_time_ms=execution_time,
            database_type="postgresql",
            model_used="llama3",
        )
        session.add(query_record)
        await session.commit()

        return query_record.id


@cache_query_result(ttl=1800)
async def process_natural_language_query(
    question: str,
    schema: str = SAMPLE_SCHEMA,
) -> dict:
    """
    Complete pipeline: NL -> SQL -> Cache -> Results

    This function demonstrates the full Database Guru workflow:
    1. Check cache (via decorator) - if hit, return immediately
    2. If cache miss, generate SQL using LLM
    3. Validate SQL for safety
    4. Save to database history
    5. Return result (automatically cached by decorator)
    """
    print(f"  🔄 Processing: '{question}'")

    # Initialize SQL generator
    generator = SQLGenerator()
    await generator.initialize()

    # Generate SQL from natural language
    print(f"  🤖 Generating SQL...")
    result = await generator.generate_sql(
        question=question,
        schema=schema,
        database_type="postgresql",
        allow_write=False,
    )

    sql = result['sql']
    is_valid = result['is_valid']
    warnings = result['warnings']

    print(f"  ✓ SQL: {sql[:80]}...")

    if warnings:
        print(f"  ⚠️  Warnings: {', '.join(warnings)}")

    # Save to database history
    print(f"  💾 Saving to history...")
    query_id = await save_query_history(
        nl_query=question,
        sql=sql,
        is_valid=is_valid,
        execution_time=50.0,  # Simulated
    )

    # In a real implementation, we would execute the SQL here
    # For demo, we'll return mock data
    mock_results = [
        {"id": 1, "name": "John Doe", "value": 1250.50},
        {"id": 2, "name": "Jane Smith", "value": 2100.00},
    ]

    # Prepare response
    response = {
        "query_id": query_id,
        "question": question,
        "sql": sql,
        "is_valid": is_valid,
        "is_read_only": result['is_read_only'],
        "warnings": warnings,
        "results": mock_results,
        "row_count": len(mock_results),
        "timestamp": datetime.utcnow().isoformat(),
    }

    return response


async def main():
    """Demonstrate the full Database Guru pipeline"""
    print("=" * 70)
    print("🧙‍♂️  DATABASE GURU - FULL PIPELINE DEMONSTRATION")
    print("=" * 70)
    print()

    settings = Settings()

    # Initialize all services
    print("🚀 Initializing services...")
    print()

    # 1. Database
    print("  📊 Database...")
    db_manager = get_db_manager(settings)
    await db_manager.initialize_async()
    await db_manager.create_tables_async()
    print("     ✅ Connected")

    # 2. Cache
    print("  💾 Redis Cache...")
    cache = get_redis_cache(settings)
    await cache.connect()
    print("     ✅ Connected")

    # 3. LLM
    print("  🤖 Ollama LLM...")
    generator = SQLGenerator(settings)
    await generator.initialize()
    print("     ✅ Connected")
    print()

    # Test queries
    test_queries = [
        "Show me customers from California",
        "What are the top 5 most expensive products?",
        "How many orders were completed last month?",
    ]

    for i, question in enumerate(test_queries, 1):
        print("=" * 70)
        print(f"Query {i}: {question}")
        print("=" * 70)

        # First execution (cache miss)
        print("\n🔍 First execution (cache miss):")
        result1 = await process_natural_language_query(question)
        print(f"  ✓ Results: {result1['row_count']} rows")
        print(f"  ✓ Query ID: {result1['query_id']}")

        # Second execution (cache hit)
        print("\n🔍 Second execution (cache hit - should be instant):")
        result2 = await process_natural_language_query(question)
        print(f"  ✓ Results: {result2['row_count']} rows (from cache!)")
        print(f"  ✓ Same query: {result1['query_id'] == result2['query_id']}")
        print()

    # Show statistics
    print("=" * 70)
    print("📊 STATISTICS")
    print("=" * 70)

    # Database stats
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select, func
        from src.database.models import QueryHistory

        result = await session.execute(select(func.count(QueryHistory.id)))
        total_queries = result.scalar()
        print(f"  Total queries in history: {total_queries}")

    # Cache stats
    cache_keys = 0
    async for key in cache.redis.scan_iter(match="query:*"):
        cache_keys += 1
    print(f"  Cached queries: {cache_keys}")
    print()

    # Cleanup
    print("🧹 Cleaning up...")
    await cache.clear_pattern("query:*")
    await cache.disconnect()
    await db_manager.close_async()
    await generator.ollama.disconnect()

    print()
    print("=" * 70)
    print("✨ DEMONSTRATION COMPLETE!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Natural language to SQL conversion using LLM")
    print("  ✓ SQL validation and safety checks")
    print("  ✓ Query history tracking in PostgreSQL")
    print("  ✓ Automatic result caching in Redis")
    print("  ✓ Cache hit optimization (instant responses)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
