"""Redis handler - orchestrates the full NL-to-Redis-command query flow."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.llm.ollama_client import get_ollama_client
from src.llm.self_correcting_agent import AgentTrace
from src.nosql.base import NoSQLHandler
from src.nosql.redis.client_pool import RedisClientPool
from src.nosql.redis.command_generator import RedisCommandGenerator
from src.nosql.redis.error_classifier import classify_error
from src.nosql.redis.query_executor import RedisQueryExecutor
from src.nosql.redis.schema_inspector import RedisSchemaInspector

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
SCHEMA_TTL_SECONDS = 1800


class RedisHandler(NoSQLHandler):
    """Full NL -> Redis command -> execute -> retry handler."""

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
        trace.add_step("analysis", f"Redis query: {question[:80]}", metadata={
            "database_type": "redis",
            "connection_name": connection.name,
        })

        try:
            # 1. Get Redis client
            pool = await RedisClientPool.get_instance()
            client = await pool.get_client(connection)
            trace.add_step("execution", "Connected to Redis")

            # 2. Get or refresh schema (key patterns)
            inspector = RedisSchemaInspector(client)
            schema_dict = await self._get_schema(connection, inspector, db, trace)
            schema_str = inspector.format_schema_for_llm(schema_dict)

            # 3. Initialize generator and executor
            ollama = get_ollama_client()
            if not ollama.client:
                await ollama.initialize()

            generator = RedisCommandGenerator(ollama)
            executor = RedisQueryExecutor(
                client=client,
                max_results=row_limit,
                timeout_seconds=30,
                allow_write=allow_write,
            )

            # 4. Generate and execute with retry
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
            logger.error(f"Redis handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)

    async def _get_schema(self, connection, inspector, db, trace):
        """Get schema from cache or inspect fresh."""
        cached = connection.schema_cache
        if cached and isinstance(cached, dict) and cached.get("tables"):
            updated_at = connection.schema_updated_at
            if updated_at:
                age = (datetime.utcnow() - updated_at).total_seconds()
                if age < SCHEMA_TTL_SECONDS:
                    trace.add_step("analysis", f"Using cached key patterns ({int(age)}s old)")
                    return cached

        trace.add_step("analysis", "Scanning Redis key patterns...")
        schema_dict = await inspector.get_schema()
        tables = schema_dict.get("tables", {})
        trace.add_step("analysis", f"Found {len(tables)} key patterns")

        if db:
            try:
                connection.schema_cache = schema_dict
                connection.schema_updated_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to cache Redis schema: {e}")

        return schema_dict

    async def _generate_and_execute_with_retry(
        self, question, schema_str, generator, executor, trace,
        model=None, db=None, query_history_id=None, chat_session_id=None,
    ):
        last_cmd_str = ""
        last_error = ""
        attempts = []

        for attempt_num in range(1, MAX_RETRIES + 1):
            trace.add_step("attempt_start", f"Attempt {attempt_num}/{MAX_RETRIES}")

            try:
                if attempt_num == 1:
                    redis_cmd = await generator.generate(
                        question=question, schema=schema_str, model=model,
                        db=db, query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
                else:
                    redis_cmd = await generator.generate_with_error_context(
                        question=question, schema=schema_str,
                        previous_command=last_cmd_str, error_message=last_error,
                        model=model, db=db, query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
            except Exception as e:
                trace.add_step("error", f"Command generation failed: {e}")
                last_error = str(e)
                attempts.append({"attempt": attempt_num, "query": "", "error": str(e), "success": False})
                continue

            cmd_str = generator.query_to_display_string(redis_cmd)
            last_cmd_str = cmd_str
            trace.add_step("generation", f"Generated: {cmd_str}")

            result = await executor.execute(redis_cmd)

            if result["success"]:
                trace.add_step("success", f"Returned {result['row_count']} results")
                attempts.append({"attempt": attempt_num, "query": cmd_str, "success": True})

                return {
                    "success": True,
                    "sql": cmd_str,
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

            error_msg = result.get("error", "Unknown error")
            error_type, hint = classify_error(error_msg)
            last_error = f"{error_msg}\nHint: {hint}"
            trace.add_step("error", f"Failed: {error_msg[:100]}")
            attempts.append({"attempt": attempt_num, "query": cmd_str, "error": error_msg, "success": False})

        trace.add_step("error", f"All {MAX_RETRIES} attempts failed")
        return self._build_error_result(
            f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
            trace, sql=last_cmd_str, attempts=attempts,
        )

    def _build_error_result(self, error, trace, sql="", attempts=None):
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
