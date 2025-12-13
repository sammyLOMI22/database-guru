#!/usr/bin/env python3
"""
Debug tool to diagnose query generation issues
Helps understand why complex multi-table queries are generating incorrect SQL
"""
import asyncio
import json
import logging
from typing import Optional

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose_query(question: str, db_connection_string: str = "sqlite+aiosqlite:///./database_guru.db"):
    """
    Run a diagnostic on a specific query to understand the generation flow

    Args:
        question: The natural language question to test
        db_connection_string: Database connection string
    """
    print("\n" + "="*80)
    print("QUERY GENERATION DIAGNOSTIC")
    print("="*80)
    print(f"\nQuestion: {question}\n")

    try:
        from src.config.settings import Settings
        from src.database.connection import get_db_manager
        from src.core.schema_inspector import SchemaInspector
        from src.llm.sql_generator import SQLGenerator
        from src.llm.query_planning_agent import QueryPlanningAgent
        from src.llm.tool_using_agent import ToolUsingAgent
        from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        from src.database.models import Base

        # Initialize settings
        settings = Settings()
        settings.DATABASE_URL = db_connection_string

        print("✅ Imports successful\n")

        # Get database manager and create session
        db_manager = get_db_manager(settings)
        await db_manager.initialize_async()

        # Create a session for metadata operations
        async_session_maker = sessionmaker(
            db_manager.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Get schema
        print("📋 Retrieving schema...")
        schema_inspector = SchemaInspector()

        # Create a dummy user database session for schema introspection
        # (In real flow this would be the user's database)
        from src.core.user_db_connector import UserDatabaseConnector
        from sqlalchemy import select
        from src.database.models import DatabaseConnection

        # Get active connection from metadata DB
        async with async_session_maker() as db:
            result = await db.execute(
                select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            )
            active_conn = result.scalar_one_or_none()

            if not active_conn:
                print("❌ No active database connection found")
                print("   Please set up a connection first in the UI")
                return

            print(f"✅ Active connection: {active_conn.name} ({active_conn.database_type})\n")

            # Get schema from user's database
            async with UserDatabaseConnector.get_user_db_session(active_conn) as user_db:
                schema_data = await schema_inspector.get_schema(user_db, active_conn.database_type)
                schema_str = schema_inspector.format_schema_for_llm(schema_data)

                print(f"📊 Schema loaded: {len(schema_data['tables'])} tables")
                print(f"   Tables: {', '.join([t['name'] for t in schema_data['tables'][:10]])}")
                if len(schema_data['tables']) > 10:
                    print(f"   ... and {len(schema_data['tables']) - 10} more")
                print()

                # Initialize SQL generator
                print("🤖 Initializing SQL generator...")
                sql_generator = SQLGenerator(settings=settings)
                await sql_generator.initialize()
                print("✅ SQL generator initialized\n")

                # Step 1: Check Query Planning
                print("─" * 80)
                print("STEP 1: QUERY PLANNING")
                print("─" * 80)
                print(f"Checking if query planning will be used...\n")

                query_planning_agent = QueryPlanningAgent(
                    settings=settings,
                    ollama_client=sql_generator.ollama,
                    enable_planning=True
                )

                try:
                    plan_result = await query_planning_agent.plan_and_generate_sql(
                        question=question,
                        schema=schema_str,
                        database_type=active_conn.database_type,
                        sql_generator=sql_generator
                    )

                    if plan_result.get("used_planning"):
                        print("✅ Query Planning WAS USED")
                        plan = plan_result.get("plan")
                        print(f"   Complexity: {plan.complexity.value}")
                        print(f"   Confidence: {plan.confidence:.2f}")
                        print(f"   Tables: {[t.name for t in plan.tables_needed]}")
                        print(f"   Joins: {len(plan.joins_needed)}")
                        print(f"   Generated SQL: {plan_result.get('sql', '')[:100]}...\n")
                    else:
                        print("❌ Query Planning NOT USED (falls back to direct generation)\n")
                except Exception as e:
                    print(f"⚠️  Query Planning failed: {e}\n")

                # Step 2: Check Tool-Using Agent
                print("─" * 80)
                print("STEP 2: TOOL-USING AGENT")
                print("─" * 80)
                print(f"Checking if tools will be used for context enhancement...\n")

                tool_using_agent = ToolUsingAgent(
                    sql_generator=sql_generator,
                    max_tool_calls=3,
                    enable_auto_explore=True
                )

                try:
                    tool_result = await tool_using_agent.process(
                        question=question,
                        schema=schema_str,
                        database_type=active_conn.database_type,
                        session=user_db,
                        schema_inspector=schema_inspector,
                        connection_id=active_conn.id,
                        use_tools=True
                    )

                    if tool_result.success:
                        print("✅ Tool-Using Agent SUCCEEDED")
                        print(f"   Tools used: {', '.join(tool_result.tools_used)}")
                        print(f"   Confidence: {tool_result.confidence:.2f}")
                        if tool_result.enriched_context:
                            print(f"   Context added ({len(tool_result.enriched_context)} chars)")
                            print(f"   Context preview: {tool_result.enriched_context[:200]}...\n")
                    else:
                        print("❌ Tool-Using Agent FAILED")
                        print(f"   Error: {tool_result.error}\n")
                except Exception as e:
                    print(f"⚠️  Tool-Using Agent error: {e}\n")

                # Step 3: Direct SQL Generation
                print("─" * 80)
                print("STEP 3: DIRECT SQL GENERATION")
                print("─" * 80)
                print(f"Generating SQL directly...\n")

                try:
                    gen_result = await sql_generator.generate_sql(
                        question=question,
                        schema=schema_str,
                        database_type=active_conn.database_type
                    )

                    if gen_result.get("sql"):
                        print("✅ SQL Generated successfully")
                        sql = gen_result["sql"]
                        print(f"   SQL: {sql}\n")

                        # Step 4: Explain the generated SQL
                        print("─" * 80)
                        print("STEP 4: EXPLAIN PLAN (Query Compilation)")
                        print("─" * 80)
                        print(f"Getting execution plan for generated SQL...\n")

                        try:
                            from src.core.executor import SQLExecutor
                            executor = SQLExecutor()

                            # Try to get EXPLAIN output
                            explain_result = await executor.execute_query(
                                session=user_db,
                                sql=f"EXPLAIN {sql}",
                                database_type=active_conn.database_type
                            )

                            if explain_result.get("success"):
                                print("✅ EXPLAIN Plan retrieved:")
                                if isinstance(explain_result.get("data"), list):
                                    for row in explain_result["data"][:10]:
                                        print(f"   {row}")
                                print()
                            else:
                                print(f"⚠️  EXPLAIN failed: {explain_result.get('error')}\n")
                        except Exception as e:
                            print(f"⚠️  Could not get EXPLAIN: {e}\n")
                    else:
                        print(f"❌ SQL Generation failed: {gen_result.get('error')}\n")
                except Exception as e:
                    print(f"❌ SQL Generation error: {e}\n")
                    import traceback
                    traceback.print_exc()

        print("="*80)
        print("DIAGNOSTIC COMPLETE")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Fatal error during diagnostic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        # Default test questions
        print("Usage: python debug_query_flow.py \"Your question here\"")
        print("\nExample for multi-table query diagnosis:")
        print('  python debug_query_flow.py "Show me orders from customers in California with product details"')
        print("\nRunning default diagnostic...\n")
        question = "What products do we have?"

    asyncio.run(diagnose_query(question))
