"""Test script for Database Guru API"""
import asyncio
import httpx


BASE_URL = "http://localhost:8000"


async def test_api():
    """Test the Database Guru API endpoints"""
    print("🧪 Testing Database Guru API\n")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        # Test 1: Health Check
        print("\n1️⃣  Testing Health Check")
        print("-" * 70)
        response = await client.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Overall Status: {data['status']}")
        print(f"Services:")
        for service, status in data['services'].items():
            emoji = "✅" if status else "❌"
            print(f"  {emoji} {service}: {status}")

        # Test 2: Root Endpoint
        print("\n2️⃣  Testing Root Endpoint")
        print("-" * 70)
        response = await client.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        # Test 3: Process Natural Language Query
        print("\n3️⃣  Testing Query Processing")
        print("-" * 70)
        query_data = {
            "question": "Show me all customers from California",
            "database_type": "postgresql",
            "use_cache": True,
        }
        print(f"Question: {query_data['question']}")

        response = await client.post(f"{BASE_URL}/api/query/", json=query_data)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Query ID: {data['query_id']}")
            print(f"Generated SQL: {data['sql']}")
            print(f"Valid: {data['is_valid']}")
            print(f"Read-only: {data['is_read_only']}")
            print(f"Cached: {data['cached']}")
            if data['warnings']:
                print(f"Warnings: {data['warnings']}")
        else:
            print(f"Error: {response.text}")

        # Test 4: Query Again (Should be cached)
        print("\n4️⃣  Testing Cache (Same Query)")
        print("-" * 70)
        response = await client.post(f"{BASE_URL}/api/query/", json=query_data)
        if response.status_code == 200:
            data = response.json()
            print(f"Cached: {data['cached']} (should be True)")
            print(f"SQL: {data['sql'][:60]}...")

        # Test 5: Different Query
        print("\n5️⃣  Testing Different Query")
        print("-" * 70)
        query_data2 = {
            "question": "What are the top 5 products by price?",
            "database_type": "postgresql",
        }
        print(f"Question: {query_data2['question']}")

        response = await client.post(f"{BASE_URL}/api/query/", json=query_data2)
        if response.status_code == 200:
            data = response.json()
            print(f"Generated SQL: {data['sql']}")

        # Test 6: Query History
        print("\n6️⃣  Testing Query History")
        print("-" * 70)
        response = await client.get(f"{BASE_URL}/api/query/history?limit=5")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            history = response.json()
            print(f"Found {len(history)} queries in history")
            for i, item in enumerate(history[:3], 1):
                print(f"  {i}. {item['natural_language_query'][:50]}...")

        # Test 7: Statistics
        print("\n7️⃣  Testing Statistics")
        print("-" * 70)
        response = await client.get(f"{BASE_URL}/api/query/stats")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"Total Queries: {stats['total_queries']}")
            print(f"Avg Execution Time: {stats['average_execution_time_ms']} ms")

        # Test 8: SQL Explanation
        print("\n8️⃣  Testing SQL Explanation")
        print("-" * 70)
        explain_data = {
            "sql": "SELECT * FROM customers WHERE state = 'CA' ORDER BY created_at DESC LIMIT 10"
        }
        response = await client.post(f"{BASE_URL}/api/query/explain", json=explain_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Explanation: {data['explanation'][:150]}...")

        # Test 9: Rate Limiting Headers
        print("\n9️⃣  Testing Rate Limit Headers")
        print("-" * 70)
        response = await client.get(f"{BASE_URL}/api/query/history")
        print(f"X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit')}")
        print(f"X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining')}")

    print("\n" + "=" * 70)
    print("✨ API Testing Complete!")
    print("=" * 70)


if __name__ == "__main__":
    print("\n🧙‍♂️ Database Guru API Test Suite\n")
    print("Make sure the API is running: python src/main.py\n")

    try:
        asyncio.run(test_api())
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the server is running: python src/main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
