"""MongoDB query executor - runs MQLQuery objects against motor database.

Handles find, aggregate, count, distinct operations with safety checks
and result normalization.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.nosql.mongodb.mql_generator import MQLQuery, MQLOperationType
from src.nosql.result_formatter import normalize_nosql_result

logger = logging.getLogger(__name__)


class MongoQueryExecutor:
    """Execute MongoDB queries safely with timeout and row limits."""

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        max_documents: int = 1000,
        timeout_seconds: int = 30,
        allow_write: bool = False,
    ):
        self.db = database
        self.max_documents = max_documents
        self.timeout_seconds = timeout_seconds
        self.allow_write = allow_write

    async def execute(self, query: MQLQuery) -> Dict[str, Any]:
        """Execute an MQLQuery and return a normalized result dict.

        Returns:
            Dict matching SQLExecutor.execute_query() contract.
        """
        # Safety check: block write operations unless explicitly allowed
        if query.is_write and not self.allow_write:
            return normalize_nosql_result(
                data=[],
                execution_time_ms=0,
                error=f"Write operation '{query.operation.value}' not allowed. Enable allow_write to permit modifications.",
            )

        if not query.collection:
            return normalize_nosql_result(
                data=[], execution_time_ms=0, error="No collection specified"
            )

        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._execute_query(query),
                timeout=self.timeout_seconds,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=result,
                execution_time_ms=elapsed_ms,
                max_rows=self.max_documents,
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=[],
                execution_time_ms=elapsed_ms,
                error=f"Query timed out after {self.timeout_seconds}s",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"MongoDB query error: {e}", exc_info=True)
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms, error=str(e)
            )

    async def _execute_query(self, query: MQLQuery) -> List[Dict]:
        """Route to the appropriate pymongo operation."""
        collection = self.db[query.collection]

        if query.operation == MQLOperationType.FIND:
            return await self._execute_find(collection, query)
        elif query.operation == MQLOperationType.FIND_ONE:
            return await self._execute_find_one(collection, query)
        elif query.operation == MQLOperationType.AGGREGATE:
            return await self._execute_aggregate(collection, query)
        elif query.operation == MQLOperationType.COUNT:
            return await self._execute_count(collection, query)
        elif query.operation == MQLOperationType.DISTINCT:
            return await self._execute_distinct(collection, query)
        else:
            raise ValueError(f"Unsupported operation: {query.operation}")

    async def _execute_find(self, collection, query: MQLQuery) -> List[Dict]:
        """Execute find query with cursor options."""
        cursor = collection.find(query.query, query.projection)

        if query.sort:
            cursor = cursor.sort(list(query.sort.items()))
        if query.skip:
            cursor = cursor.skip(query.skip)

        limit = min(query.limit or self.max_documents, self.max_documents)
        cursor = cursor.limit(limit)

        return await cursor.to_list(length=limit)

    async def _execute_find_one(self, collection, query: MQLQuery) -> List[Dict]:
        """Execute findOne query."""
        doc = await collection.find_one(query.query, query.projection)
        return [doc] if doc else []

    async def _execute_aggregate(self, collection, query: MQLQuery) -> List[Dict]:
        """Execute aggregation pipeline."""
        pipeline = query.pipeline or []

        # Add $limit if not present to prevent unbounded results
        has_limit = any("$limit" in stage for stage in pipeline)
        if not has_limit:
            pipeline.append({"$limit": self.max_documents})

        cursor = collection.aggregate(pipeline)
        return await cursor.to_list(length=self.max_documents)

    async def _execute_count(self, collection, query: MQLQuery) -> List[Dict]:
        """Execute count query."""
        count = await collection.count_documents(query.query)
        return [{"count": count}]

    async def _execute_distinct(self, collection, query: MQLQuery) -> List[Dict]:
        """Execute distinct query."""
        field_name = "_id"
        if query.projection and isinstance(query.projection, dict):
            field_name = query.projection.get("field", "_id")

        values = await collection.distinct(field_name, query.query)
        return [{"field": field_name, "distinct_values": values, "count": len(values)}]
