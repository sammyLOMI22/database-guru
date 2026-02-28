"""Elasticsearch handler - orchestrates the full NL-to-Query-DSL flow."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.llm.ollama_client import get_ollama_client
from src.llm.self_correcting_agent import AgentTrace
from src.nosql.base import NoSQLHandler
from src.nosql.elasticsearch.client_pool import ElasticsearchClientPool
from src.nosql.elasticsearch.error_classifier import classify_error
from src.nosql.elasticsearch.query_dsl_generator import QueryDSLGenerator
from src.nosql.elasticsearch.query_executor import ElasticsearchQueryExecutor
from src.nosql.elasticsearch.schema_inspector import ElasticsearchSchemaInspector

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
SCHEMA_TTL_SECONDS = 1800


class ElasticsearchHandler(NoSQLHandler):
    """Full NL -> Query DSL -> execute -> retry handler for Elasticsearch."""

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
        trace = AgentTrace()
        trace.add_step("analysis", f"Elasticsearch query: {question[:80]}", metadata={
            "database_type": "elasticsearch",
            "connection_name": connection.name,
        })

        try:
            pool = await ElasticsearchClientPool.get_instance()
            es_client = await pool.get_client(connection)
            trace.add_step("execution", "Connected to Elasticsearch")

            inspector = ElasticsearchSchemaInspector(es_client)
            schema_dict = await self._get_schema(connection, inspector, db, trace)
            schema_str = inspector.format_schema_for_llm(schema_dict)

            ollama = get_ollama_client()
            if not ollama.client:
                await ollama.initialize()

            generator = QueryDSLGenerator(ollama)
            executor = ElasticsearchQueryExecutor(
                client=es_client,
                max_results=row_limit,
                timeout_seconds=30,
                allow_write=allow_write,
            )

            return await self._generate_and_execute_with_retry(
                question=question, schema_str=schema_str,
                generator=generator, executor=executor, trace=trace,
                model=model, db=db, query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"Elasticsearch handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)

    async def _get_schema(self, connection, inspector, db, trace):
        cached = connection.schema_cache
        if cached and isinstance(cached, dict) and cached.get("tables"):
            updated_at = connection.schema_updated_at
            if updated_at:
                age = (datetime.utcnow() - updated_at).total_seconds()
                if age < SCHEMA_TTL_SECONDS:
                    trace.add_step("analysis", f"Using cached schema ({int(age)}s old)")
                    return cached

        trace.add_step("analysis", "Inspecting Elasticsearch indices...")
        schema_dict = await inspector.get_schema()
        tables = schema_dict.get("tables", {})
        trace.add_step("analysis", f"Found {len(tables)} indices")

        if db:
            try:
                connection.schema_cache = schema_dict
                connection.schema_updated_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to cache Elasticsearch schema: {e}")

        return schema_dict

    async def _generate_and_execute_with_retry(
        self, question, schema_str, generator, executor, trace,
        model=None, db=None, query_history_id=None, chat_session_id=None,
    ):
        last_query_str = ""
        last_error = ""
        attempts = []

        for attempt_num in range(1, MAX_RETRIES + 1):
            trace.add_step("attempt_start", f"Attempt {attempt_num}/{MAX_RETRIES}")

            try:
                if attempt_num == 1:
                    query_dsl = await generator.generate(
                        question=question, schema=schema_str, model=model,
                        db=db, query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
                else:
                    query_dsl = await generator.generate_with_error_context(
                        question=question, schema=schema_str,
                        previous_query=last_query_str, error_message=last_error,
                        model=model, db=db, query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
            except Exception as e:
                trace.add_step("error", f"Generation failed: {e}")
                last_error = str(e)
                attempts.append({"attempt": attempt_num, "query": "", "error": str(e), "success": False})
                continue

            query_str = generator.query_to_display_string(query_dsl)
            last_query_str = query_str
            trace.add_step("generation", f"Generated Query DSL for index: {query_dsl.get('index', 'unknown')}")

            result = await executor.execute(query_dsl)

            if result["success"]:
                trace.add_step("success", f"Returned {result['row_count']} documents")
                attempts.append({"attempt": attempt_num, "query": query_str, "success": True})

                return {
                    "success": True, "sql": query_str, "result": result,
                    "attempts": attempts, "self_corrected": attempt_num > 1,
                    "total_attempts": attempt_num, "error": None,
                    "agent_trace": trace.to_dict(), "model_used": model or "default",
                    "query_plan": None, "verification_warnings": [],
                    "used_planning": False,
                }

            error_msg = result.get("error", "Unknown error")
            error_type, hint = classify_error(error_msg)
            last_error = f"{error_msg}\nHint: {hint}"
            trace.add_step("error", f"Failed: {error_msg[:100]}")
            attempts.append({"attempt": attempt_num, "query": query_str, "error": error_msg, "success": False})

        trace.add_step("error", f"All {MAX_RETRIES} attempts failed")
        return self._build_error_result(
            f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
            trace, sql=last_query_str, attempts=attempts,
        )

    def _build_error_result(self, error, trace, sql="", attempts=None):
        return {
            "success": False, "sql": sql, "result": None,
            "attempts": attempts or [], "self_corrected": False,
            "total_attempts": len(attempts) if attempts else 0,
            "error": error, "agent_trace": trace.to_dict(),
            "model_used": "default", "query_plan": None,
            "verification_warnings": [], "used_planning": False,
        }
