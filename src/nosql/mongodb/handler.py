"""MongoDB handler - orchestrates the full NL-to-MQL query flow.

This is the main entry point called by the NoSQL router for MongoDB queries.
It manages: client lifecycle, schema caching, MQL generation, execution,
and self-correction retries.
"""
import logging
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
                error_classifier=classify_error,
                model=model,
                db=db,
                query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"MongoDB handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)
