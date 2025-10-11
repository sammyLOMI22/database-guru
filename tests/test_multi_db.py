"""Test script for multi-database query functionality"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api"


async def test_multi_database_queries():
    """Test multi-database query functionality"""
    print("="*60)
    print("Testing Multi-Database Query Functionality")
    print("="*60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: List existing connections
        print("\n1. Listing existing database connections...")
        response = await client.get(f"{BASE_URL}/connections/")
        if response.status_code == 200:
            data = response.json()
            connections = data.get("connections", [])
            print(f"   Found {len(connections)} connection(s):")
            for conn in connections:
                print(f"   - {conn['name']} (ID: {conn['id']}, Type: {conn['database_type']})")
        else:
            print(f"   Error: {response.status_code}")
            return

        if len(connections) < 1:
            print("   ⚠️  Need at least one database connection. Please set up a connection first.")
            return

        # Step 2: Create a chat session with multiple connections
        print("\n2. Creating a chat session with database connections...")
        connection_ids = [conn["id"] for conn in connections[:2]]  # Use first 2 connections
        session_data = {
            "name": "Multi-DB Test Session",
            "connection_ids": connection_ids,
        }

        response = await client.post(f"{BASE_URL}/chat/sessions", json=session_data)
        if response.status_code == 201:
            session = response.json()
            session_id = session["id"]
            print(f"   ✅ Created chat session: {session['name']} (ID: {session_id})")
            print(f"   Active connections: {len(session['connections'])}")
            for conn in session["connections"]:
                print(f"     - {conn['name']} ({conn['database_type']})")
        else:
            print(f"   Error: {response.status_code} - {response.text}")
            return

        # Step 3: Test single database query via chat session
        print("\n3. Testing single database query...")
        query_request = {
            "question": "Show me all products with their prices",
            "chat_session_id": session_id,
            "allow_write": False,
            "use_cache": False,
        }

        response = await client.post(f"{BASE_URL}/multi-query/", json=query_request)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Query successful!")
            print(f"   Databases queried: {result['total_databases_queried']}")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Execution time: {result['total_execution_time_ms']}ms")

            for db_result in result["database_results"]:
                print(f"\n   Database: {db_result['connection_name']}")
                print(f"   SQL: {db_result['sql']}")
                print(f"   Success: {db_result['success']}")
                if db_result['success']:
                    print(f"   Rows: {db_result['row_count']}")
                    if db_result['results'] and len(db_result['results']) > 0:
                        print(f"   Sample result: {json.dumps(db_result['results'][0], indent=2)}")
                else:
                    print(f"   Error: {db_result.get('error')}")
        else:
            print(f"   Error: {response.status_code} - {response.text}")

        # Step 4: Test multi-database comparison query
        if len(connection_ids) > 1:
            print("\n4. Testing multi-database comparison query...")
            query_request = {
                "question": "Compare the total number of records in each database",
                "chat_session_id": session_id,
                "allow_write": False,
                "use_cache": False,
            }

            response = await client.post(f"{BASE_URL}/multi-query/", json=query_request)
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Multi-database query successful!")
                print(f"   Databases queried: {result['total_databases_queried']}")
                print(f"   Total execution time: {result['total_execution_time_ms']}ms")

                for db_result in result["database_results"]:
                    print(f"\n   Database: {db_result['connection_name']}")
                    print(f"   SQL: {db_result['sql']}")
                    print(f"   Success: {db_result['success']}")
                    if db_result['success']:
                        print(f"   Rows: {db_result['row_count']}")
            else:
                print(f"   Error: {response.status_code} - {response.text}")

        # Step 5: View chat history
        print("\n5. Viewing chat history...")
        response = await client.get(f"{BASE_URL}/chat/sessions/{session_id}/messages")
        if response.status_code == 200:
            messages = response.json()
            print(f"   ✅ Found {len(messages)} message(s) in chat:")
            for msg in messages:
                print(f"\n   [{msg['role'].upper()}] {msg['content'][:100]}...")
                if msg.get('databases_used'):
                    print(f"   Databases used: {json.dumps(msg['databases_used'], indent=2)}")
        else:
            print(f"   Error: {response.status_code}")

        # Step 6: Query with explicit connection IDs (bypass chat session)
        print("\n6. Testing direct query with explicit connection IDs...")
        query_request = {
            "question": "List all tables in the database",
            "connection_ids": [connections[0]["id"]],
            "allow_write": False,
            "use_cache": False,
        }

        response = await client.post(f"{BASE_URL}/multi-query/", json=query_request)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Direct query successful!")
            print(f"   Databases queried: {result['total_databases_queried']}")
            for db_result in result["database_results"]:
                print(f"   Database: {db_result['connection_name']}")
                print(f"   SQL: {db_result['sql'][:100]}...")
        else:
            print(f"   Error: {response.status_code}")

        print("\n" + "="*60)
        print("✅ Multi-Database Tests Complete!")
        print("="*60)


async def main():
    """Main test runner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║     Multi-Database Query Testing                         ║
║                                                           ║
║  This script tests:                                      ║
║  - Chat session creation with multiple DB connections    ║
║  - Single database queries via chat context              ║
║  - Multi-database comparison queries                     ║
║  - Chat history tracking                                 ║
║  - Direct queries with explicit connection IDs           ║
╚══════════════════════════════════════════════════════════╝
    """)

    try:
        await test_multi_database_queries()
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to the server.")
        print("   Make sure the Database Guru server is running on http://localhost:8000")
        print("   Run: python -m src.main")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
