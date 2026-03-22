"""NoSQL DML executor — runs native write operations against NoSQL databases.

Uses the existing client pools from src/nosql/ for each database type.
Supports per-DB transaction semantics where available.
"""
import asyncio
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.audit import log_action
from src.database.models import DatabaseConnection
from src.dml.models import DMLStatement, ExecutionResult

logger = logging.getLogger(__name__)


class NoSQLDMLExecutor:
    """Execute NoSQL DML statements using the appropriate client pool."""

    async def execute(
        self,
        connection: DatabaseConnection,
        statements: List[DMLStatement],
        metadata_db: AsyncSession,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute NoSQL DML statements with per-DB transaction handling."""
        if not statements:
            return ExecutionResult(success=True, rows_affected=0)

        display_sql = "\n".join(s.display_sql for s in statements)
        db_type = connection.database_type

        try:
            dispatch = _EXECUTORS.get(db_type)
            if not dispatch:
                raise ValueError(f"Unsupported NoSQL type for DML execution: {db_type}")

            total = await dispatch(connection, statements)

            # Audit log each statement on success
            for stmt in statements:
                await log_action(
                    metadata_db,
                    action="dml_execute",
                    resource_type="connection",
                    resource_id=str(connection.id),
                    user_id=user_id,
                    username=username,
                    details={
                        "change_type": stmt.change_type.value,
                        "table_name": stmt.table_name,
                        "sql": stmt.display_sql,
                        "connection_name": connection.name,
                        "database_type": db_type,
                    },
                    ip_address=ip_address,
                )

            return ExecutionResult(
                success=True,
                rows_affected=total,
                executed_sql=display_sql,
            )

        except Exception as e:
            logger.error(f"NoSQL DML execution failed on {connection.name}: {e}")

            await log_action(
                metadata_db,
                action="dml_failed",
                resource_type="connection",
                resource_id=str(connection.id),
                user_id=user_id,
                username=username,
                details={
                    "sql": display_sql,
                    "error": str(e),
                    "connection_name": connection.name,
                    "database_type": db_type,
                },
                ip_address=ip_address,
            )

            return ExecutionResult(
                success=False,
                rows_affected=0,
                error_message=str(e),
                executed_sql=display_sql,
            )


# ── MongoDB ─────────────────────────────────────────────────────────


async def _execute_mongodb(
    connection: DatabaseConnection, statements: List[DMLStatement]
) -> int:
    from src.nosql.mongodb.client_pool import MongoClientPool

    pool = await MongoClientPool.get_instance()
    client, db = await pool.get_client(connection)

    total = 0
    async with await client.start_session() as session:
        async with session.start_transaction():
            for stmt in statements:
                op = stmt.native_operation or {}
                method = op.get("method")
                collection = db[op["collection"]]

                if method == "insert_one":
                    doc = _mongo_convert_id(op["document"])
                    await collection.insert_one(doc, session=session)
                    total += 1
                elif method == "update_one":
                    filt = _mongo_convert_id(op["filter"])
                    result = await collection.update_one(
                        filt, op["update"], session=session
                    )
                    total += result.modified_count
                elif method == "delete_one":
                    filt = _mongo_convert_id(op["filter"])
                    result = await collection.delete_one(filt, session=session)
                    total += result.deleted_count
                else:
                    raise ValueError(f"Unknown MongoDB DML method: {method}")

    return total


def _mongo_convert_id(d: dict) -> dict:
    """Convert string _id to ObjectId if it looks like one (24-hex-char string)."""
    import re

    if "_id" in d and isinstance(d["_id"], str) and re.fullmatch(r"[0-9a-fA-F]{24}", d["_id"]):
        from bson import ObjectId

        d = dict(d)
        d["_id"] = ObjectId(d["_id"])
    return d


# ── Cassandra ──────────────────────────────────────────────────────


async def _execute_cassandra(
    connection: DatabaseConnection, statements: List[DMLStatement]
) -> int:
    from src.nosql.cassandra.client_pool import CassandraClientPool

    pool = await CassandraClientPool.get_instance()
    session = await pool.get_session(connection)

    loop = asyncio.get_running_loop()

    def _run_batch():
        from cassandra.query import BatchStatement, ConsistencyLevel

        batch = BatchStatement(consistency_level=ConsistencyLevel.LOCAL_QUORUM)
        for stmt in statements:
            op = stmt.native_operation or {}
            cql = op["cql"]
            params = op.get("params", [])
            prepared = session.prepare(cql)
            batch.add(prepared, params)
        session.execute(batch)
        return len(statements)

    return await loop.run_in_executor(None, _run_batch)


# ── DynamoDB ───────────────────────────────────────────────────────


async def _execute_dynamodb(
    connection: DatabaseConnection, statements: List[DMLStatement]
) -> int:
    from src.nosql.dynamodb.client_pool import DynamoDBClientPool

    pool = await DynamoDBClientPool.get_instance()
    boto_session, region = pool.get_session(connection)

    total = 0
    async with boto_session.client("dynamodb", region_name=region) as client:
        for stmt in statements:
            op = stmt.native_operation or {}
            partiql = op["partiql"]
            resp = await client.execute_statement(Statement=partiql)
            # DynamoDB doesn't return affected count for writes, count 1 per statement
            total += 1

    return total


# ── Elasticsearch ──────────────────────────────────────────────────


async def _execute_elasticsearch(
    connection: DatabaseConnection, statements: List[DMLStatement]
) -> int:
    from src.nosql.elasticsearch.client_pool import ElasticsearchClientPool

    pool = await ElasticsearchClientPool.get_instance()
    es_client = await pool.get_client(connection)

    total = 0
    for stmt in statements:
        op = stmt.native_operation or {}
        method = op.get("method")

        if method == "index":
            kwargs = {"index": op["index"], "document": op["body"]}
            if op.get("id"):
                kwargs["id"] = op["id"]
            await es_client.index(**kwargs)
            total += 1
        elif method == "update":
            await es_client.update(
                index=op["index"], id=op["id"], body=op["body"]
            )
            total += 1
        elif method == "delete":
            await es_client.delete(index=op["index"], id=op["id"])
            total += 1
        else:
            raise ValueError(f"Unknown Elasticsearch DML method: {method}")

    return total


# ── Redis ──────────────────────────────────────────────────────────


async def _execute_redis(
    connection: DatabaseConnection, statements: List[DMLStatement]
) -> int:
    from src.nosql.redis.client_pool import RedisClientPool

    pool = await RedisClientPool.get_instance()
    redis_client = await pool.get_client(connection)

    total = 0
    pipe = redis_client.pipeline(transaction=True)

    for stmt in statements:
        op = stmt.native_operation or {}
        command = op.get("command")

        if command == "HSET":
            pipe.hset(op["key"], mapping=op["mapping"])
            total += 1
        elif command == "HDEL":
            pipe.hdel(op["key"], *op["fields"])
            total += 1
        elif command == "DEL":
            pipe.delete(op["key"])
            total += 1
        else:
            raise ValueError(f"Unknown Redis DML command: {command}")

    await pipe.execute()
    return total


# ── Registry ───────────────────────────────────────────────────────

_EXECUTORS = {
    "mongodb": _execute_mongodb,
    "cassandra": _execute_cassandra,
    "dynamodb": _execute_dynamodb,
    "elasticsearch": _execute_elasticsearch,
    "redis": _execute_redis,
}
