"""Test schema value sampling feature"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.core.schema_inspector import SchemaInspector


async def test_sampling():
    """Test that schema sampling captures state values correctly"""
    print("🔍 Testing Schema Value Sampling\n")

    # Connect to sample database
    engine = create_async_engine(
        "sqlite+aiosqlite:///./sample_ecommerce.db",
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        inspector = SchemaInspector()

        # Get schema with samples
        print("📊 Introspecting schema with value sampling...")
        schema = await inspector.get_full_schema(session, include_samples=True)

        # Check if customers.state has samples
        customers_table = schema["tables"].get("customers", {})
        columns = customers_table.get("columns", [])

        state_column = None
        for col in columns:
            if col["name"] == "state":
                state_column = col
                break

        if state_column:
            print(f"\n✅ Found 'state' column in customers table")
            print(f"   Type: {state_column['type']}")

            if "sample_values" in state_column:
                samples = state_column["sample_values"]
                print(f"   Sample values: {samples}")

                # Check if samples are 2-letter codes
                if samples and all(len(str(s)) == 2 for s in samples):
                    print(f"   ✅ Detected 2-letter state codes format!")
                else:
                    print(f"   ⚠️  Sample values don't look like 2-letter codes")
            else:
                print(f"   ❌ No sample values found")
        else:
            print(f"\n❌ 'state' column not found in customers table")

        # Format schema for LLM
        print(f"\n📝 Formatted schema for LLM:")
        print("=" * 60)
        formatted = inspector.format_schema_for_llm(schema)
        # Just print the customers table section
        lines = formatted.split("\n")
        in_customers = False
        for line in lines:
            if "Table: customers" in line:
                in_customers = True
            elif in_customers and line.startswith("Table:"):
                break
            if in_customers:
                print(line)
        print("=" * 60)

        # Check status column too
        print(f"\n📊 Checking orders.status column...")
        orders_table = schema["tables"].get("orders", {})
        if orders_table:
            status_col = None
            for col in orders_table.get("columns", []):
                if col["name"] == "status":
                    status_col = col
                    break

            if status_col and "sample_values" in status_col:
                print(f"   Sample statuses: {status_col['sample_values']}")
                print(f"   ✅ LLM will see these are lowercase!")

    await engine.dispose()
    print(f"\n✅ Schema sampling test complete!")


if __name__ == "__main__":
    asyncio.run(test_sampling())
