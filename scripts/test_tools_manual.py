#!/usr/bin/env python
"""
Manual test script for Tool-Using Agent tools.

Run with: python scripts/test_tools_manual.py

Requires:
- Backend running (or standalone mode with database connection)
- A database connection configured
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_via_api():
    """Test tools via REST API (requires backend running)"""
    import httpx

    base_url = "http://localhost:8000/api"

    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("Testing Tools API")
        print("=" * 60)

        # 1. List all tools
        print("\n1. GET /api/tools - List all tools")
        print("-" * 40)
        try:
            resp = await client.get(f"{base_url}/tools")
            if resp.status_code == 200:
                tools = resp.json()
                print(f"   Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']} ({tool['category']}): {tool['description'][:50]}...")
            else:
                print(f"   Error: {resp.status_code} - {resp.text}")
        except httpx.ConnectError:
            print("   ERROR: Cannot connect to backend. Is it running?")
            print("   Start with: python -m uvicorn src.main:app --reload")
            return False

        # 2. Filter by category
        print("\n2. GET /api/tools?category=schema - Schema tools only")
        print("-" * 40)
        resp = await client.get(f"{base_url}/tools?category=schema")
        if resp.status_code == 200:
            tools = resp.json()
            print(f"   Found {len(tools)} schema tools:")
            for tool in tools:
                print(f"   - {tool['name']}")

        # 3. Get tool stats
        print("\n3. GET /api/tools/stats - Execution statistics")
        print("-" * 40)
        resp = await client.get(f"{base_url}/tools/stats")
        if resp.status_code == 200:
            stats = resp.json()
            print(f"   Total tools: {stats['total_tools']}")
            print(f"   Total executions: {stats['total_executions']}")
            print(f"   Overall success rate: {stats['overall_success_rate']:.1%}")

        # 4. Get prompt format
        print("\n4. GET /api/tools/prompt - LLM prompt format")
        print("-" * 40)
        resp = await client.get(f"{base_url}/tools/prompt")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Tool count: {data['tool_count']}")
            print(f"   Prompt preview (first 200 chars):")
            print(f"   {data['prompt'][:200]}...")

        print("\n" + "=" * 60)
        print("API Tests Complete!")
        print("=" * 60)
        return True


async def test_tools_directly():
    """Test tools directly without API (standalone mode)"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    from src.tools import get_tool_registry, get_all_tools
    from src.core.schema_inspector import SchemaInspector

    print("=" * 60)
    print("Testing Tools Directly (Standalone Mode)")
    print("=" * 60)

    # Check if sample database exists
    sample_db = "sample_ecommerce.db"
    if not os.path.exists(sample_db):
        print(f"\nSample database not found at {sample_db}")
        print("Create it with: python scripts/create_sample_db.py")
        return False

    # Create async engine for sample database
    engine = create_async_engine(f"sqlite+aiosqlite:///{sample_db}")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create schema inspector
        inspector = SchemaInspector()
        schema = await inspector.get_full_schema(session)

        print(f"\nConnected to sample database with {len(schema.get('tables', []))} tables")

        # Get registry and test tools
        registry = get_tool_registry()
        all_tools = get_all_tools()

        print(f"Testing {len(all_tools)} tools:\n")

        # Test 1: search_schema
        print("1. search_schema('customer')")
        print("-" * 40)
        result = await registry.execute_tool(
            "search_schema",
            session=session,
            schema_inspector=inspector,
            connection_id=1,
            keyword="customer"
        )
        if result.success:
            print(f"   Found: {result.data}")
        else:
            print(f"   Error: {result.error}")

        # Test 2: get_table_info
        print("\n2. get_table_info('customers')")
        print("-" * 40)
        result = await registry.execute_tool(
            "get_table_info",
            session=session,
            schema_inspector=inspector,
            connection_id=1,
            table_name="customers"
        )
        if result.success:
            info = result.data
            print(f"   Table: {info.get('table_name')}")
            print(f"   Columns: {len(info.get('columns', []))}")
            print(f"   Primary key: {info.get('primary_key')}")
        else:
            print(f"   Error: {result.error}")

        # Test 3: find_columns
        print("\n3. find_columns('id')")
        print("-" * 40)
        result = await registry.execute_tool(
            "find_columns",
            session=session,
            schema_inspector=inspector,
            connection_id=1,
            column_name="id"
        )
        if result.success:
            found_in = result.data.get("found_in", [])
            print(f"   Found {len(found_in)} columns containing 'id'")
            for col in found_in[:5]:  # Show first 5
                print(f"   - {col['table']}.{col['column']}")
        else:
            print(f"   Error: {result.error}")

        # Test 4: get_column_values (the most useful tool!)
        print("\n4. get_column_values('customers', 'state') - CRITICAL for value formats!")
        print("-" * 40)
        result = await registry.execute_tool(
            "get_column_values",
            session=session,
            schema_inspector=inspector,
            connection_id=1,
            table_name="customers",
            column_name="state"
        )
        if result.success:
            values = result.data.get("distinct_values", [])
            print(f"   Found {len(values)} distinct values:")
            print(f"   {values[:10]}{'...' if len(values) > 10 else ''}")
            print(f"   (This tells agent: use 'CA' not 'California')")
        else:
            print(f"   Error: {result.error}")

        # Test 5: validate_sql
        print("\n5. validate_sql - Check for typos")
        print("-" * 40)
        test_sql = "SELECT * FROM customerz WHERE stat = 'CA'"
        result = await registry.execute_tool(
            "validate_sql",
            session=session,
            schema_inspector=inspector,
            connection_id=1,
            sql=test_sql
        )
        if result.success:
            data = result.data
            print(f"   SQL: {test_sql}")
            print(f"   Valid: {data.get('is_valid')}")
            if data.get("issues"):
                print(f"   Issues: {data.get('issues')}")
            if data.get("suggestions"):
                print(f"   Suggestions: {data.get('suggestions')}")
        else:
            print(f"   Error: {result.error}")

        print("\n" + "=" * 60)
        print("Direct Tool Tests Complete!")
        print("=" * 60)

    await engine.dispose()
    return True


async def main():
    print("\nTool-Using Agent Manual Test Script")
    print("=" * 60)

    # Try API first
    print("\nAttempting API tests (requires backend running)...\n")
    api_success = await test_via_api()

    if not api_success:
        print("\n\nFalling back to direct tool testing...\n")
        await test_tools_directly()
    else:
        # Also run direct tests for more detail
        print("\n\nRunning direct tool tests for detailed output...\n")
        await test_tools_directly()


if __name__ == "__main__":
    asyncio.run(main())
