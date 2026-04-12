"""DynamoDB handler - orchestrates the full NL-to-PartiQL query flow."""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.llm import get_llm_client
from src.llm.self_correcting_agent import AgentTrace
from src.nosql.base import NoSQLHandler
from src.nosql.dynamodb.client_pool import DynamoDBClientPool
from src.nosql.dynamodb.error_classifier import classify_error
from src.nosql.dynamodb.partiql_generator import PartiQLGenerator
from src.nosql.dynamodb.query_executor import DynamoDBQueryExecutor
from src.nosql.dynamodb.schema_inspector import DynamoDBSchemaInspector

logger = logging.getLogger(__name__)


class DynamoDBHandler(NoSQLHandler):
    """Full NL -> PartiQL -> execute -> retry handler for DynamoDB."""

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
        trace.add_step("analysis", f"DynamoDB query: {question[:80]}", metadata={
            "database_type": "dynamodb",
            "connection_name": connection.name,
        })

        try:
            pool = await DynamoDBClientPool.get_instance()
            boto_session, region = pool.get_session(connection)
            trace.add_step("execution", f"Connected to DynamoDB ({region})")

            inspector = DynamoDBSchemaInspector(boto_session, region)
            schema_dict = await self._get_schema(connection, inspector, db, trace)
            schema_str = inspector.format_schema_for_llm(schema_dict)

            ollama = get_llm_client()
            if not ollama.client:
                await ollama.initialize()

            generator = PartiQLGenerator(ollama)
            executor = DynamoDBQueryExecutor(
                session=boto_session, region=region,
                max_rows=row_limit, timeout_seconds=30,
                allow_write=allow_write,
            )

            return await self._generate_and_execute_with_retry(
                question=question, schema_str=schema_str,
                generator=generator, executor=executor, trace=trace,
                error_classifier=classify_error, database_type="dynamodb",
                model=model, db=db, query_history_id=query_history_id,
                chat_session_id=chat_session_id,
            )

        except Exception as e:
            logger.error(f"DynamoDB handler error: {e}", exc_info=True)
            trace.add_step("error", f"Handler error: {e}")
            return self._build_error_result(str(e), trace)
