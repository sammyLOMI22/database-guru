#!/usr/bin/env python3
"""
Simplified diagnostic tool to test query generation flow
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def test_query():
    """Test a complex query generation"""
    print("\n" + "="*80)
    print("QUERY GENERATION TEST - STEP BY STEP")
    print("="*80 + "\n")

    question = "Show me orders from customers in California with product details"
    print(f"Question: {question}\n")

    try:
        # Step 1: Initialize LLM
        print("STEP 1: Initializing LLM...")
        from src.config.settings import Settings
        from src.llm.sql_generator import SQLGenerator

        settings = Settings()
        generator = SQLGenerator(settings=settings)
        await generator.initialize()
        print("✅ LLM initialized\n")

        # Step 2: Create a simple schema
        print("STEP 2: Creating test schema...")
        schema = """
Tables:
- customers: id (PK), name, state, email
- orders: id (PK), customer_id (FK), order_date, total
- order_items: id (PK), order_id (FK), product_id (FK), quantity, price
- products: id (PK), name, category, price

Relationships:
- customers.id -> orders.customer_id
- orders.id -> order_items.order_id
- products.id -> order_items.product_id
"""
        print("✅ Schema created\n")

        # Step 3: Test direct SQL generation (no query planning, no tool-using)
        print("STEP 3: Direct SQL Generation (no enhancements)...")
        result = await generator.generate_sql(
            question=question,
            schema=schema,
            database_type="sqlite"
        )

        if result.get("sql"):
            print("✅ SQL Generated:")
            print(f"   {result['sql']}\n")
        else:
            print(f"❌ Failed: {result.get('error')}\n")

        # Step 4: Test with Query Planning
        print("STEP 4: Testing Query Planning Agent...")
        try:
            from src.llm.query_planning_agent import QueryPlanningAgent

            planner = QueryPlanningAgent(
                settings=settings,
                ollama_client=generator.ollama
            )

            plan_result = await planner.plan_and_generate_sql(
                question=question,
                schema=schema,
                database_type="sqlite",
                sql_generator=generator
            )

            if plan_result.get("used_planning"):
                print("✅ Query Planning was used")
                print(f"   Complexity: {plan_result['plan'].complexity.value}")
                print(f"   Confidence: {plan_result['plan'].confidence:.2f}")
                print(f"   SQL from plan: {plan_result.get('sql', '')[:100]}...\n")
            else:
                print("❌ Query Planning not used (direct generation fallback)\n")
        except Exception as e:
            print(f"⚠️  Query Planning error: {e}\n")

        # Step 5: Compare performance
        print("STEP 5: Performance Analysis")
        print("   ⏱️  If queries are taking longer, it's likely due to:")
        print("      1. Query Planning analysis overhead (~200-500ms)")
        print("      2. Tool-Using Agent schema exploration (~300-800ms)")
        print("      3. Combined context enrichment (~500-1300ms)")
        print()
        print("   💡 These features improve ACCURACY but add LATENCY for complex queries")
        print()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query())
