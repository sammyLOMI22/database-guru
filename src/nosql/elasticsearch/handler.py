"""Elasticsearch handler - orchestrates the full NL-to-Query-DSL flow."""
import logging
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
                error_classifier=classify_error,
                model=model, db=db, query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"Elasticsearch handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)
