"""Redis handler - orchestrates the full NL-to-Redis-command query flow."""
import logging
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
                error_classifier=classify_error,
                model=model,
                db=db,
                query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"Redis handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)
