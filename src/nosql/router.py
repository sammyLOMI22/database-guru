"""NoSQL Query Router - central dispatch for NoSQL database queries.

Provides the branch point that query.py and multi_db_handler.py use to route
NoSQL connections away from the SQL pipeline.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.nosql.base import NoSQLSchemaInspector, SCHEMA_TTL_SECONDS

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


async def get_nosql_inspector(
    connection: DatabaseConnection,
) -> Tuple[NoSQLSchemaInspector, Any]:
    """Get the appropriate schema inspector for a NoSQL connection.

    Returns (inspector, native_client) — caller can use inspector.get_schema()
    and inspector.format_schema_for_llm().
    """
    db_type = connection.database_type.lower()

    if db_type == "mongodb":
        from src.nosql.mongodb.client_pool import MongoClientPool
        from src.nosql.mongodb.schema_inspector import MongoSchemaInspector
        pool = await MongoClientPool.get_instance()
        _, mongo_db = await pool.get_client(connection)
        return MongoSchemaInspector(mongo_db), mongo_db
    elif db_type == "redis":
        from src.nosql.redis.client_pool import RedisClientPool
        from src.nosql.redis.schema_inspector import RedisSchemaInspector
        pool = await RedisClientPool.get_instance()
        client = await pool.get_client(connection)
        return RedisSchemaInspector(client), client
    elif db_type == "cassandra":
        from src.nosql.cassandra.client_pool import CassandraClientPool
        from src.nosql.cassandra.schema_inspector import CassandraSchemaInspector
        pool = await CassandraClientPool.get_instance()
        session = await pool.get_session(connection)
        keyspace = connection.database_name or "system"
        return CassandraSchemaInspector(session, keyspace), session
    elif db_type == "dynamodb":
        from src.nosql.dynamodb.client_pool import DynamoDBClientPool
        from src.nosql.dynamodb.schema_inspector import DynamoDBSchemaInspector
        pool = await DynamoDBClientPool.get_instance()
        boto_session, region = pool.get_session(connection)
        return DynamoDBSchemaInspector(boto_session, region), boto_session
    elif db_type == "elasticsearch":
        from src.nosql.elasticsearch.client_pool import ElasticsearchClientPool
        from src.nosql.elasticsearch.schema_inspector import ElasticsearchSchemaInspector
        pool = await ElasticsearchClientPool.get_instance()
        client = await pool.get_client(connection)
        return ElasticsearchSchemaInspector(client), client
    else:
        raise ValueError(f"Unknown NoSQL type: {db_type}")


async def get_cached_or_fresh_schema(
    connection: DatabaseConnection,
    inspector: NoSQLSchemaInspector,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Return schema from cache (TTL-based) or inspect fresh.

    Shared by handlers (via NoSQLHandler._get_schema) and
    multi_db_handler._introspect_nosql_database.
    """
    cached = connection.schema_cache
    if cached and isinstance(cached, dict) and cached.get("tables"):
        updated_at = connection.schema_updated_at
        if updated_at:
            age_seconds = (datetime.utcnow() - updated_at).total_seconds()
            if age_seconds < SCHEMA_TTL_SECONDS:
                return cached

    # Fresh inspection
    schema_dict = await inspector.get_schema()

    # Persist to DatabaseConnection.schema_cache
    if db:
        try:
            connection.schema_cache = schema_dict
            connection.schema_updated_at = datetime.utcnow()
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to cache NoSQL schema: {e}")

    return schema_dict


async def evict_nosql_pool(connection_id: int, database_type: str) -> None:
    """Evict a connection from its NoSQL client pool (called on connection delete)."""
    db_type = database_type.lower()
    if db_type not in NOSQL_TYPES:
        return

    try:
        if db_type == "mongodb":
            from src.nosql.mongodb.client_pool import MongoClientPool
            pool = await MongoClientPool.get_instance()
            await pool.evict(connection_id)
        elif db_type == "redis":
            from src.nosql.redis.client_pool import RedisClientPool
            pool = await RedisClientPool.get_instance()
            await pool.evict(connection_id)
        elif db_type == "cassandra":
            from src.nosql.cassandra.client_pool import CassandraClientPool
            pool = await CassandraClientPool.get_instance()
            await pool.evict(connection_id)
        elif db_type == "dynamodb":
            from src.nosql.dynamodb.client_pool import DynamoDBClientPool
            pool = await DynamoDBClientPool.get_instance()
            await pool.evict(connection_id)
        elif db_type == "elasticsearch":
            from src.nosql.elasticsearch.client_pool import ElasticsearchClientPool
            pool = await ElasticsearchClientPool.get_instance()
            await pool.evict(connection_id)
    except Exception as e:
        logger.warning(f"Failed to evict NoSQL pool for connection {connection_id}: {e}")
