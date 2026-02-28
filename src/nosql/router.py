"""NoSQL Query Router - central dispatch for NoSQL database queries.

Provides the branch point that query.py and multi_db_handler.py use to route
NoSQL connections away from the SQL pipeline.
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection

logger = logging.getLogger(__name__)

NOSQL_TYPES = {"mongodb", "redis", "cassandra", "dynamodb", "elasticsearch"}


def is_nosql(database_type: str) -> bool:
    """Check whether a database type is NoSQL (routed via this module)."""
    return database_type.lower() in NOSQL_TYPES


async def execute_nosql_query(
    question: str,
    connection: DatabaseConnection,
    model: Optional[str] = None,
    allow_write: bool = False,
    row_limit: int = 1000,
    db: Optional[AsyncSession] = None,
    query_history_id: Optional[int] = None,
    chat_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a natural language query against a NoSQL database.

    This is the main entry point called by query.py and multi_db_handler.py
    when is_nosql() returns True. Returns a dict with the same shape as
    SelfCorrectingSQLAgent.generate_and_execute_with_retry().

    Args:
        question: Natural language question from the user
        connection: DatabaseConnection model with connection details
        model: Optional LLM model name override
        allow_write: Whether write operations are allowed
        row_limit: Maximum number of rows/documents to return
        db: SQLAlchemy async session for metadata database
        query_history_id: ID of the QueryHistory record for tracking
        chat_session_id: Chat session ID for context

    Returns:
        Dict matching generate_and_execute_with_retry() contract
    """
    db_type = connection.database_type.lower()

    if db_type == "mongodb":
        from src.nosql.mongodb.handler import MongoDBHandler

        handler = MongoDBHandler()
    elif db_type == "redis":
        from src.nosql.redis.handler import RedisHandler

        handler = RedisHandler()
    elif db_type == "cassandra":
        from src.nosql.cassandra.handler import CassandraHandler

        handler = CassandraHandler()
    elif db_type == "dynamodb":
        from src.nosql.dynamodb.handler import DynamoDBHandler

        handler = DynamoDBHandler()
    elif db_type == "elasticsearch":
        from src.nosql.elasticsearch.handler import ElasticsearchHandler

        handler = ElasticsearchHandler()
    else:
        raise ValueError(f"Unknown NoSQL database type: {db_type}")

    logger.info(f"Routing {db_type} query to NoSQL handler: {question[:80]}")

    return await handler.handle(
        question=question,
        connection=connection,
        model=model,
        allow_write=allow_write,
        row_limit=row_limit,
        db=db,
        query_history_id=query_history_id,
        chat_session_id=chat_session_id,
    )
