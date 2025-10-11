"""End-to-end test for Database Guru with real SQL execution"""
import asyncio
import httpx


BASE_URL = "http://localhost:8000"


async def test_end_to_end():
    """Test the complete Database Guru workflow"""
    print("=" * 80)
    print("🧙‍♂️ DATABASE GURU - END-TO-END TEST")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Health Check
        print("1️⃣  Health Check")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"Status: {data['status']}")
        for service, healthy in data['services'].items():
            emoji = "✅" if healthy else "❌"
            print(f"  {emoji} {service}")

        if data['status'] != 'healthy':
            print("\n❌ Services not healthy! Please check Docker services.")
            return
        print()

        # Test 2: Get Database Schema
        print("2️⃣  Database Schema Introspection")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/api/schema/")
        if response.status_code == 200:
            schema = response.json()
            print(f"✅ Tables: {schema['table_count']}")
            print(f"✅ Columns: {schema['column_count']}")
            print(f"✅ Relationships: {schema['relationship_count']}")
            print(f"   Cached: {schema.get('cached', False)}")

            print(f"\n   Tables found:")
            for table_name in schema['schema']['tables'].keys():
                col_count = len(schema['schema']['tables'][table_name]['columns'])
                print(f"     • {table_name} ({col_count} columns)")
        else:
            print(f"❌ Error: {response.text}")
            return
        print()

        # Test 3: Execute Natural Language Query
        print("3️⃣  Natural Language Query → SQL → Execution")
        print("-" * 80)

        test_queries = [
            "Show me all customers from California",
            "What are the top 5 most expensive products?",
            "How many completed orders are there?",
            "List all products in the Electronics category",
        ]

        for i, question in enumerate(test_queries, 1):
            print(f"\n📝 Query {i}: {question}")
            print("   " + "-" * 70)

            query_data = {
                "question": question,
                "database_type": "postgresql",
                "use_cache": False,  # Disable cache for testing
            }

            response = await client.post(f"{BASE_URL}/api/query/", json=query_data)

            if response.status_code == 200:
                result = response.json()

                print(f"   ✓ Query ID: {result['query_id']}")
                print(f"   ✓ Valid: {result['is_valid']}")
                print(f"   ✓ Read-only: {result['is_read_only']}")

                # Show generated SQL
                print(f"\n   📊 Generated SQL:")
                print(f"   {result['sql']}")

                # Show execution results
                if result.get('results') is not None:
                    print(f"\n   🎯 Results:")
                    print(f"      Rows returned: {result['row_count']}")
                    print(f"      Execution time: {result['execution_time_ms']:.2f}ms")

                    # Show first few results
                    if result['results']:
                        print(f"\n      First row:")
                        for key, value in list(result['results'][0].items())[:3]:
                            print(f"        • {key}: {value}")

                        if result['row_count'] > 1:
                            print(f"      ... and {result['row_count'] - 1} more rows")
                else:
                    print(f"\n   ⚠️  No results (query may have failed)")

                if result.get('warnings'):
                    print(f"\n   ⚠️  Warnings: {result['warnings']}")

            else:
                print(f"   ❌ Error: {response.text}")

        print()

        # Test 4: SQL Explanation
        print("4️⃣  SQL Explanation")
        print("-" * 80)
        explain_data = {
            "sql": "SELECT * FROM customers WHERE state = 'CA' ORDER BY created_at DESC"
        }
        response = await client.post(f"{BASE_URL}/api/query/explain", json=explain_data)

        if response.status_code == 200:
            result = response.json()
            print(f"SQL: {result['sql'][:60]}...")
            print(f"\nExplanation:")
            print(f"{result['explanation'][:200]}...")
        else:
            print(f"❌ Error: {response.text}")
        print()

        # Test 5: Query History
        print("5️⃣  Query History")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/api/query/history?limit=5")

        if response.status_code == 200:
            history = response.json()
            print(f"✅ Found {len(history)} recent queries\n")

            for i, item in enumerate(history[:3], 1):
                print(f"   {i}. {item['natural_language_query'][:50]}...")
                print(f"      SQL: {item['generated_sql'][:60]}...")
                print(f"      Executed: {item['executed']}, Valid: {item['sql_validated']}")
                if item.get('execution_time_ms'):
                    print(f"      Time: {item['execution_time_ms']:.2f}ms, Rows: {item.get('result_count', 0)}")
                print()
        else:
            print(f"❌ Error: {response.text}")

        # Test 6: Statistics
        print("6️⃣  Statistics")
        print("-" * 80)
        response = await client.get(f"{BASE_URL}/api/query/stats")

        if response.status_code == 200:
            stats = response.json()
            print(f"Total Queries: {stats['total_queries']}")
            if stats['average_execution_time_ms']:
                print(f"Average Execution Time: {stats['average_execution_time_ms']:.2f}ms")
        print()

    print("=" * 80)
    print("✨ END-TO-END TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🧙‍♂️ Database Guru End-to-End Test\n")
    print("Prerequisites:")
    print("  1. API is running (python src/main.py)")
    print("  2. Sample data is loaded (python scripts/load_sample_data.py)")
    print("  3. Ollama is running with llama3 model\n")

    try:
        asyncio.run(test_end_to_end())
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the server is running: python src/main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
