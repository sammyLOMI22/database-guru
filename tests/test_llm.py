"""Test script for LLM layer"""
import asyncio
from src.config.settings import Settings
from src.llm import OllamaClient, SQLGenerator, get_ollama_client


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


async def test_ollama_connection():
    """Test basic Ollama connectivity"""
    print("🧪 Testing Ollama Connection...\n")

    settings = Settings()
    client = get_ollama_client(settings)

    # Connect
    print("📡 Connecting to Ollama...")
    await client.connect()

    # Health check
    print("💚 Running health check...")
    is_healthy = await client.health_check()
    print(f"  ✓ Health check: {'PASSED' if is_healthy else 'FAILED'}\n")

    # List models
    print("📦 Available models:")
    models = await client.list_models()
    for model in models:
        print(f"  • {model}")
    print()

    # Test simple generation
    print("🤖 Testing text generation...")
    response = await client.generate(
        prompt="What is SQL?",
        temperature=0.7,
    )
    print(f"  Response: {response[:100]}...\n")

    await client.disconnect()
    print("✨ Connection test complete!")


async def test_sql_generation():
    """Test SQL generation from natural language"""
    print("\n" + "=" * 60)
    print("🧙‍♂️ Testing SQL Generation")
    print("=" * 60 + "\n")

    settings = Settings()
    generator = SQLGenerator(settings)

    # Initialize
    print("🚀 Initializing SQL generator...")
    await generator.initialize()
    print("  ✅ Ready!\n")

    # Test queries
    test_questions = [
        "Show me all customers from California",
        "What are the top 5 products by price?",
        "How many orders were placed last month?",
        "Find customers who have spent more than $1000",
        "List all products that are out of stock",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'─' * 60}")
        print(f"Question {i}: {question}")
        print('─' * 60)

        result = await generator.generate_sql(
            question=question,
            schema=SAMPLE_SCHEMA,
            database_type="postgresql",
            allow_write=False,
        )

        print(f"✓ SQL: {result['sql']}")
        print(f"✓ Valid: {result['is_valid']}")
        print(f"✓ Read-only: {result['is_read_only']}")

        if result['warnings']:
            print(f"⚠️  Warnings: {', '.join(result['warnings'])}")

    # Test dangerous query detection
    print(f"\n{'=' * 60}")
    print("🛡️  Testing Security Validation")
    print('=' * 60 + "\n")

    dangerous_question = "Delete all customers from the database"
    result = await generator.generate_sql(
        question=dangerous_question,
        schema=SAMPLE_SCHEMA,
        database_type="postgresql",
        allow_write=False,
    )

    print(f"Question: {dangerous_question}")
    print(f"Generated SQL: {result['sql']}")
    print(f"Read-only: {result['is_read_only']}")
    print(f"Warnings: {result['warnings']}")

    # Disconnect
    await generator.ollama.disconnect()

    print("\n✨ SQL generation test complete!")


async def test_sql_explanation():
    """Test SQL explanation feature"""
    print("\n" + "=" * 60)
    print("📖 Testing SQL Explanation")
    print("=" * 60 + "\n")

    settings = Settings()
    generator = SQLGenerator(settings)
    await generator.initialize()

    sample_sql = """
    SELECT c.name, c.email, SUM(o.total_amount) as total_spent
    FROM customers c
    JOIN orders o ON c.id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.id, c.name, c.email
    HAVING SUM(o.total_amount) > 1000
    ORDER BY total_spent DESC
    LIMIT 10
    """

    print(f"SQL Query:\n{sample_sql}\n")
    print("Generating explanation...\n")

    explanation = await generator.explain_sql(
        sql=sample_sql,
        schema=SAMPLE_SCHEMA,
    )

    print(f"Explanation:\n{explanation}\n")

    await generator.ollama.disconnect()
    print("✨ Explanation test complete!")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_ollama_connection())
    asyncio.run(test_sql_generation())
    asyncio.run(test_sql_explanation())
