"""Tests for MongoDB NoSQL support.

Covers: MQL generation parsing, executor routing, write blocking,
error classification, handler retry loop, result shape contract.
"""
import json
import pytest
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.mongodb.mql_generator import (
    MQLGenerator, MQLQuery, MQLOperationType, SYSTEM_PROMPT,
)
from src.nosql.mongodb.error_classifier import classify_error
from src.llm.self_correcting_agent import ErrorType


# ── MQLQuery dataclass ───────────────────────────────────────────────────

class TestMQLQuery:
    def test_find_is_not_write(self):
        q = MQLQuery(operation=MQLOperationType.FIND, collection="users")
        assert q.is_write is False

    def test_aggregate_is_not_write(self):
        q = MQLQuery(operation=MQLOperationType.AGGREGATE, collection="users")
        assert q.is_write is False

    def test_insert_is_write(self):
        q = MQLQuery(operation=MQLOperationType.INSERT, collection="users")
        assert q.is_write is True

    def test_update_is_write(self):
        q = MQLQuery(operation=MQLOperationType.UPDATE, collection="users")
        assert q.is_write is True

    def test_delete_is_write(self):
        q = MQLQuery(operation=MQLOperationType.DELETE, collection="users")
        assert q.is_write is True


# ── MQL generation parsing ──────────────────────────────────────────────

class TestMQLGeneratorParsing:
    def setup_method(self):
        self.ollama = MagicMock()
        self.gen = MQLGenerator(self.ollama)

    def test_parse_direct_json(self):
        response = json.dumps({
            "operation": "find",
            "collection": "users",
            "query": {"status": "active"},
            "projection": {"name": 1},
            "sort": {"created_at": -1},
            "limit": 10,
        })
        result = self.gen._parse_response(response)
        assert isinstance(result, MQLQuery)
        assert result.operation == MQLOperationType.FIND
        assert result.collection == "users"
        assert result.query == {"status": "active"}
        assert result.limit == 10

    def test_parse_json_in_code_block(self):
        response = '```json\n{"operation": "count", "collection": "orders", "query": {}}\n```'
        result = self.gen._parse_response(response)
        assert result.operation == MQLOperationType.COUNT
        assert result.collection == "orders"

    def test_parse_json_surrounded_by_text(self):
        response = 'Here is the query:\n{"operation": "find", "collection": "products", "query": {"price": {"$gt": 100}}}\nThis will find expensive products.'
        result = self.gen._parse_response(response)
        assert result.operation == MQLOperationType.FIND
        assert result.collection == "products"

    def test_parse_unknown_operation_defaults_to_find(self):
        response = json.dumps({"operation": "mapReduce", "collection": "logs"})
        result = self.gen._parse_response(response)
        assert result.operation == MQLOperationType.FIND

    def test_parse_invalid_json_raises(self):
        with pytest.raises(ValueError, match="No JSON found"):
            self.gen._parse_response("This is not JSON at all")

    def test_parse_aggregate_with_pipeline(self):
        response = json.dumps({
            "operation": "aggregate",
            "collection": "sales",
            "pipeline": [
                {"$match": {"year": 2026}},
                {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
            ],
        })
        result = self.gen._parse_response(response)
        assert result.operation == MQLOperationType.AGGREGATE
        assert len(result.pipeline) == 2


# ── MQLGenerator display strings ────────────────────────────────────────

class TestMQLDisplayString:
    def setup_method(self):
        self.gen = MQLGenerator(MagicMock())

    def test_find_display(self):
        q = MQLQuery(
            operation=MQLOperationType.FIND,
            collection="users",
            query={"active": True},
        )
        s = self.gen.query_to_display_string(q)
        assert s.startswith("db.users.find(")
        assert "active" in s

    def test_find_with_sort_limit(self):
        q = MQLQuery(
            operation=MQLOperationType.FIND,
            collection="users",
            query={},
            sort={"name": 1},
            limit=10,
        )
        s = self.gen.query_to_display_string(q)
        assert ".sort(" in s
        assert ".limit(10)" in s

    def test_aggregate_display(self):
        q = MQLQuery(
            operation=MQLOperationType.AGGREGATE,
            collection="orders",
            pipeline=[{"$group": {"_id": "$status"}}],
        )
        s = self.gen.query_to_display_string(q)
        assert s.startswith("db.orders.aggregate(")

    def test_count_display(self):
        q = MQLQuery(
            operation=MQLOperationType.COUNT,
            collection="items",
            query={"type": "book"},
        )
        s = self.gen.query_to_display_string(q)
        assert "countDocuments" in s

    def test_distinct_display(self):
        q = MQLQuery(
            operation=MQLOperationType.DISTINCT,
            collection="events",
            projection={"field": "category"},
        )
        s = self.gen.query_to_display_string(q)
        assert "distinct" in s
        assert "category" in s


# ── MQLGenerator generate ───────────────────────────────────────────────

class TestMQLGeneratorGenerate:
    @pytest.mark.asyncio
    async def test_generate_calls_ollama(self):
        ollama = AsyncMock()
        ollama.generate.return_value = json.dumps({
            "operation": "find",
            "collection": "users",
            "query": {},
        })
        gen = MQLGenerator(ollama)
        result = await gen.generate(question="show all users", schema="DATABASE: MongoDB")
        assert isinstance(result, MQLQuery)
        assert result.collection == "users"
        ollama.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_error_context(self):
        ollama = AsyncMock()
        ollama.generate.return_value = json.dumps({
            "operation": "find",
            "collection": "users",
            "query": {"status": "active"},
        })
        gen = MQLGenerator(ollama)
        result = await gen.generate_with_error_context(
            question="show active users",
            schema="DATABASE: MongoDB",
            previous_query="db.user.find({})",
            error_message="collection 'user' not found",
        )
        assert result.collection == "users"
        call_args = ollama.generate.call_args
        assert "PREVIOUS ATTEMPT FAILED" in call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")


# ── MongoDB error classifier ────────────────────────────────────────────

class TestMongoErrorClassifier:
    def test_field_not_found(self):
        error_type, hint = classify_error("path 'nonexistent' doesn't exist in document")
        assert error_type == ErrorType.COLUMN_NOT_FOUND
        assert "nonexistent" in hint

    def test_collection_not_found(self):
        error_type, hint = classify_error("collection 'missing_coll' not found")
        assert error_type == ErrorType.TABLE_NOT_FOUND

    def test_syntax_error(self):
        error_type, hint = classify_error("unknown operator: $badop")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_type_mismatch(self):
        error_type, hint = classify_error("can't convert from string to int")
        assert error_type == ErrorType.TYPE_MISMATCH

    def test_permission_denied(self):
        error_type, hint = classify_error("not authorized on admin to execute command")
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_timeout(self):
        error_type, hint = classify_error("operation timed out")
        assert error_type == ErrorType.TIMEOUT

    def test_unknown(self):
        error_type, hint = classify_error("some random error")
        assert error_type == ErrorType.UNKNOWN


# ── MongoDB query executor ───────────────────────────────────────────────

class TestMongoQueryExecutor:
    def setup_method(self):
        # We can't import MongoQueryExecutor without motor installed,
        # so we test the core logic via mocks
        pass

    @pytest.mark.asyncio
    async def test_write_blocked(self):
        from src.nosql.mongodb.query_executor import MongoQueryExecutor

        mock_db = MagicMock()
        executor = MongoQueryExecutor(database=mock_db, allow_write=False)
        query = MQLQuery(operation=MQLOperationType.INSERT, collection="users")

        result = await executor.execute(query)
        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_collection_error(self):
        from src.nosql.mongodb.query_executor import MongoQueryExecutor

        mock_db = MagicMock()
        executor = MongoQueryExecutor(database=mock_db)
        query = MQLQuery(operation=MQLOperationType.FIND, collection="")

        result = await executor.execute(query)
        assert result["success"] is False
        assert "No collection" in result["error"]

    @pytest.mark.asyncio
    async def test_find_executes(self):
        from src.nosql.mongodb.query_executor import MongoQueryExecutor

        # Motor's find() is sync (returns cursor), but to_list() is async
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": "1", "name": "Alice"},
            {"_id": "2", "name": "Bob"},
        ])
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        executor = MongoQueryExecutor(database=mock_db, max_documents=100)
        query = MQLQuery(
            operation=MQLOperationType.FIND,
            collection="users",
            query={"active": True},
        )

        result = await executor.execute(query)
        assert result["success"] is True
        assert result["row_count"] == 2
        mock_collection.find.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_executes(self):
        from src.nosql.mongodb.query_executor import MongoQueryExecutor

        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 42

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        executor = MongoQueryExecutor(database=mock_db)
        query = MQLQuery(
            operation=MQLOperationType.COUNT,
            collection="users",
            query={},
        )

        result = await executor.execute(query)
        assert result["success"] is True
        assert result["data"][0]["count"] == 42

    @pytest.mark.asyncio
    async def test_aggregate_adds_limit(self):
        from src.nosql.mongodb.query_executor import MongoQueryExecutor

        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [{"_id": "group1", "total": 100}]

        mock_collection = MagicMock()
        mock_collection.aggregate.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        executor = MongoQueryExecutor(database=mock_db, max_documents=500)
        pipeline = [{"$group": {"_id": "$status", "total": {"$sum": 1}}}]
        query = MQLQuery(
            operation=MQLOperationType.AGGREGATE,
            collection="orders",
            pipeline=pipeline,
        )

        result = await executor.execute(query)
        assert result["success"] is True
        # Verify $limit was appended
        call_args = mock_collection.aggregate.call_args[0][0]
        assert any("$limit" in stage for stage in call_args)


# ── MongoDB handler ──────────────────────────────────────────────────────

class TestMongoDBHandler:
    @pytest.mark.asyncio
    async def test_handler_returns_correct_shape(self):
        """Handler result must match generate_and_execute_with_retry() contract."""
        from src.nosql.mongodb.handler import MongoDBHandler

        mock_db = MagicMock()
        mock_mongo_db = MagicMock()

        # Mock the pool
        mock_pool = AsyncMock()
        mock_pool.get_client.return_value = (MagicMock(), mock_mongo_db)

        # Mock schema inspector
        mock_schema = {"tables": {"users": {"columns": [], "row_count": 10}}, "database_type": "mongodb"}

        # Mock ollama
        mock_ollama = AsyncMock()
        mock_ollama.client = True
        mock_ollama.generate.return_value = json.dumps({
            "operation": "find",
            "collection": "users",
            "query": {},
        })

        # Mock cursor for executor
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [{"_id": "1", "name": "Alice"}]

        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)

        conn = MagicMock()
        conn.name = "test_mongo"
        conn.database_type = "mongodb"
        conn.schema_cache = None

        with patch("src.nosql.mongodb.handler.MongoClientPool.get_instance", return_value=mock_pool), \
             patch("src.nosql.mongodb.handler.get_llm_client", return_value=mock_ollama), \
             patch("src.nosql.mongodb.handler.MongoSchemaInspector") as MockInspector:

            mock_inspector = AsyncMock()
            mock_inspector.get_schema.return_value = mock_schema
            mock_inspector.format_schema_for_llm.return_value = "DATABASE: MongoDB"
            MockInspector.return_value = mock_inspector

            handler = MongoDBHandler()
            result = await handler.handle(
                question="show all users",
                connection=conn,
                db=mock_db,
            )

        # Verify contract shape
        assert "success" in result
        assert "sql" in result
        assert "result" in result
        assert "attempts" in result
        assert "self_corrected" in result
        assert "total_attempts" in result
        assert "error" in result
        assert "agent_trace" in result
        assert "model_used" in result

    @pytest.mark.asyncio
    async def test_handler_error_returns_error_result(self):
        from src.nosql.mongodb.handler import MongoDBHandler

        conn = MagicMock()
        conn.name = "test_mongo"
        conn.database_type = "mongodb"

        with patch("src.nosql.mongodb.handler.MongoClientPool.get_instance", side_effect=Exception("Connection refused")):
            handler = MongoDBHandler()
            result = await handler.handle(question="test", connection=conn)

        assert result["success"] is False
        assert "Connection refused" in result["error"]
        assert result["agent_trace"] is not None
