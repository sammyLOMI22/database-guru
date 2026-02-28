"""MongoDB handler - orchestrates the full NL-to-MQL query flow.

This is the main entry point called by the NoSQL router for MongoDB queries.
It manages: client lifecycle, schema caching, MQL generation, execution,
and self-correction retries.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.llm.ollama_client import get_ollama_client
from src.llm.self_correcting_agent import AgentTrace
from src.nosql.base import NoSQLHandler
from src.nosql.mongodb.client_pool import MongoClientPool
from src.nosql.mongodb.error_classifier import classify_error
from src.nosql.mongodb.mql_generator import MQLGenerator
from src.nosql.mongodb.query_executor import MongoQueryExecutor
from src.nosql.mongodb.schema_inspector import MongoSchemaInspector

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
SCHEMA_TTL_SECONDS = 1800  # 30 minutes


class MongoDBHandler(NoSQLHandler):
    """Full NL → MQL → execute → retry handler for MongoDB."""

    async def handle(
        self,
        question: str,
        connection: DatabaseConnection,
        model: Optional[str] = None,
        allow_write: bool = False,
        row_limit: int = 1000,
        db: Optional[AsyncSession] = None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a natural language query against MongoDB.

        Returns dict matching generate_and_execute_with_retry() contract.
        """
        trace = AgentTrace()
        trace.add_step("analysis", f"MongoDB query: {question[:80]}", metadata={
            "database_type": "mongodb",
            "connection_name": connection.name,
        })

        try:
            # 1. Get motor client and database
            pool = await MongoClientPool.get_instance()
            client, mongo_db = await pool.get_client(connection)
            trace.add_step("execution", "Connected to MongoDB")

            # 2. Get or refresh schema
            schema_inspector = MongoSchemaInspector(mongo_db)
            schema_dict = await self._get_schema(
                connection, schema_inspector, db, trace
            )
            schema_str = schema_inspector.format_schema_for_llm(schema_dict)

            # 3. Initialize generator and executor
            ollama = get_ollama_client()
            if not ollama.client:
                await ollama.initialize()

            generator = MQLGenerator(ollama)
            executor = MongoQueryExecutor(
                database=mongo_db,
                max_documents=row_limit,
                timeout_seconds=30,
                allow_write=allow_write,
            )

            # 4. Generate and execute with retry loop
            return await self._generate_and_execute_with_retry(
                question=question,
                schema_str=schema_str,
                generator=generator,
                executor=executor,
                trace=trace,
                model=model,
                db=db,
                query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"MongoDB handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)

    async def _get_schema(
        self,
        connection: DatabaseConnection,
        inspector: MongoSchemaInspector,
        db: Optional[AsyncSession],
        trace: AgentTrace,
    ) -> Dict[str, Any]:
        """Get schema from cache or inspect fresh."""
        # Check if cached schema is still valid
        cached = connection.schema_cache
        if cached and isinstance(cached, dict) and cached.get("tables"):
            updated_at = connection.schema_updated_at
            if updated_at:
                age_seconds = (datetime.utcnow() - updated_at).total_seconds()
                if age_seconds < SCHEMA_TTL_SECONDS:
                    tables = cached.get("tables", {})
                    trace.add_step(
                        "analysis",
                        f"Using cached schema ({len(tables)} collections, {int(age_seconds)}s old)",
                    )
                    return cached

        # Fresh inspection
        trace.add_step("analysis", "Inspecting MongoDB collections...")
        schema_dict = await inspector.get_schema()
        tables = schema_dict.get("tables", {})
        trace.add_step(
            "analysis",
            f"Found {len(tables)} collections: {', '.join(list(tables.keys())[:10])}",
        )

        # Cache in DatabaseConnection.schema_cache
        if db:
            try:
                connection.schema_cache = schema_dict
                connection.schema_updated_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to cache MongoDB schema: {e}")

        return schema_dict

    async def _generate_and_execute_with_retry(
        self,
        question: str,
        schema_str: str,
        generator: MQLGenerator,
        executor: MongoQueryExecutor,
        trace: AgentTrace,
        model: Optional[str] = None,
        db=None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate MQL and execute with up to MAX_RETRIES attempts."""
        last_query_str = ""
        last_error = ""
        attempts = []

        for attempt_num in range(1, MAX_RETRIES + 1):
            trace.add_step(
                "attempt_start",
                f"Attempt {attempt_num}/{MAX_RETRIES}",
                metadata={"attempt": attempt_num},
            )

            # Generate MQL
            try:
                if attempt_num == 1:
                    mql_query = await generator.generate(
                        question=question,
                        schema=schema_str,
                        model=model,
                        db=db,
                        query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
                else:
                    mql_query = await generator.generate_with_error_context(
                        question=question,
                        schema=schema_str,
                        previous_query=last_query_str,
                        error_message=last_error,
                        model=model,
                        db=db,
                        query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
            except Exception as e:
                logger.warning(f"MQL generation failed (attempt {attempt_num}): {e}")
                trace.add_step("error", f"MQL generation failed: {e}")
                last_error = str(e)
                attempts.append({
                    "attempt": attempt_num,
                    "query": "",
                    "error": str(e),
                    "success": False,
                })
                continue

            query_str = generator.query_to_display_string(mql_query)
            last_query_str = query_str
            trace.add_step(
                "generation",
                f"Generated MQL: {query_str[:120]}",
                metadata={"operation": mql_query.operation.value, "collection": mql_query.collection},
            )

            # Execute
            result = await executor.execute(mql_query)

            if result["success"]:
                trace.add_step(
                    "success",
                    f"Query returned {result['row_count']} documents in {result['execution_time_ms']:.0f}ms",
                )
                attempts.append({
                    "attempt": attempt_num,
                    "query": query_str,
                    "success": True,
                    "row_count": result["row_count"],
                })

                return {
                    "success": True,
                    "sql": query_str,
                    "result": result,
                    "attempts": attempts,
                    "self_corrected": attempt_num > 1,
                    "total_attempts": attempt_num,
                    "error": None,
                    "agent_trace": trace.to_dict(),
                    "model_used": model or "default",
                    "query_plan": None,
                    "verification_warnings": [],
                    "used_planning": False,
                }

            # Query failed — classify error for retry
            error_msg = result.get("error", "Unknown error")
            error_type, hint = classify_error(error_msg)
            last_error = f"{error_msg}\nHint: {hint}"

            trace.add_step(
                "error",
                f"Query failed: {error_msg[:100]}",
                metadata={"error_type": error_type.value, "hint": hint},
            )
            attempts.append({
                "attempt": attempt_num,
                "query": query_str,
                "error": error_msg,
                "error_type": error_type.value,
                "success": False,
            })

        # All attempts exhausted
        trace.add_step("error", f"All {MAX_RETRIES} attempts failed")
        return self._build_error_result(
            f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
            trace,
            sql=last_query_str,
            attempts=attempts,
        )

    def _build_error_result(
        self,
        error: str,
        trace: AgentTrace,
        sql: str = "",
        attempts: list = None,
    ) -> Dict[str, Any]:
        """Build a standardized error result dict."""
        return {
            "success": False,
            "sql": sql,
            "result": None,
            "attempts": attempts or [],
            "self_corrected": False,
            "total_attempts": len(attempts) if attempts else 0,
            "error": error,
            "agent_trace": trace.to_dict(),
            "model_used": "default",
            "query_plan": None,
            "verification_warnings": [],
            "used_planning": False,
        }
