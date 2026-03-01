"""Cassandra handler - orchestrates the full NL-to-CQL query flow."""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.llm.ollama_client import get_ollama_client
from src.llm.self_correcting_agent import AgentTrace
from src.nosql.base import NoSQLHandler
from src.nosql.cassandra.client_pool import CassandraClientPool
from src.nosql.cassandra.cql_generator import CQLGenerator
from src.nosql.cassandra.error_classifier import classify_error
from src.nosql.cassandra.query_executor import CassandraQueryExecutor
from src.nosql.cassandra.schema_inspector import CassandraSchemaInspector

logger = logging.getLogger(__name__)


class CassandraHandler(NoSQLHandler):
    """Full NL -> CQL -> execute -> retry handler for Cassandra."""

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
        trace.add_step("analysis", f"Cassandra query: {question[:80]}", metadata={
            "database_type": "cassandra",
            "connection_name": connection.name,
        })

        try:
            pool = await CassandraClientPool.get_instance()
            cass_session = await pool.get_session(connection)
            trace.add_step("execution", "Connected to Cassandra")

            keyspace = connection.database_name or "system"
            inspector = CassandraSchemaInspector(cass_session, keyspace)
            schema_dict = await self._get_schema(connection, inspector, db, trace)
            schema_str = inspector.format_schema_for_llm(schema_dict)

            ollama = get_ollama_client()
            if not ollama.client:
                await ollama.initialize()

            generator = CQLGenerator(ollama)
            executor = CassandraQueryExecutor(
                session=cass_session,
                max_rows=row_limit,
                timeout_seconds=30,
                allow_write=allow_write,
            )

            return await self._generate_and_execute_with_retry(
                question=question, schema_str=schema_str,
                generator=generator, executor=executor, trace=trace,
                error_classifier=classify_error, database_type="cassandra",
                model=model, db=db, query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"Cassandra handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)
