"""Tests for NoSQL router and result formatter."""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.router import is_nosql, execute_nosql_query
from src.nosql.result_formatter import normalize_nosql_result, _serialize_value


# ── is_nosql ─────────────────────────────────────────────────────────────

class TestIsNoSQL:
    def test_mongodb(self):
        assert is_nosql("mongodb") is True

    def test_redis(self):
        assert is_nosql("redis") is True

    def test_cassandra(self):
        assert is_nosql("cassandra") is True

    def test_dynamodb(self):
        assert is_nosql("dynamodb") is True

    def test_elasticsearch(self):
        assert is_nosql("elasticsearch") is True

    def test_case_insensitive(self):
        assert is_nosql("MongoDB") is True
        assert is_nosql("REDIS") is True

    def test_sql_types_return_false(self):
        assert is_nosql("postgresql") is False
        assert is_nosql("mysql") is False
        assert is_nosql("sqlite") is False
        assert is_nosql("duckdb") is False
        assert is_nosql("mssql") is False
        assert is_nosql("oracle") is False

    def test_unknown_type(self):
        assert is_nosql("neo4j") is False


# ── normalize_nosql_result ───────────────────────────────────────────────

class TestNormalizeNoSQLResult:
    def test_success_shape(self):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = normalize_nosql_result(data=data, execution_time_ms=12.34)

        assert result["success"] is True
        assert result["error"] is None
        assert result["row_count"] == 2
        assert result["execution_time_ms"] == 12.34
        assert result["truncated"] is False
        assert result["compiled"] is False
        assert set(result["columns"]) == {"age", "name"}
        assert len(result["data"]) == 2

    def test_error_shape(self):
        result = normalize_nosql_result(
            data=[], execution_time_ms=5.0, error="Connection refused"
        )
        assert result["success"] is False
        assert result["error"] == "Connection refused"
        assert result["row_count"] == 0
        assert result["data"] == []
        assert result["columns"] == []

    def test_truncation(self):
        data = [{"x": i} for i in range(150)]
        result = normalize_nosql_result(data=data, execution_time_ms=1.0, max_rows=100)
        assert result["truncated"] is True
        assert result["row_count"] == 100

    def test_no_truncation_when_under_limit(self):
        data = [{"x": i} for i in range(50)]
        result = normalize_nosql_result(data=data, execution_time_ms=1.0, max_rows=100)
        assert result["truncated"] is False
        assert result["row_count"] == 50

    def test_empty_data(self):
        result = normalize_nosql_result(data=[], execution_time_ms=0.5)
        assert result["success"] is True
        assert result["row_count"] == 0
        assert result["columns"] == []

    def test_columns_union_of_all_keys(self):
        data = [{"a": 1}, {"b": 2}, {"a": 3, "c": 4}]
        result = normalize_nosql_result(data=data, execution_time_ms=1.0)
        assert sorted(result["columns"]) == ["a", "b", "c"]

    def test_scalar_result(self):
        data = [42]
        result = normalize_nosql_result(data=data, execution_time_ms=1.0)
        assert result["data"] == [{"value": 42}]
        assert "value" in result["columns"]


# ── _serialize_value ─────────────────────────────────────────────────────

class TestSerializeValue:
    def test_none(self):
        assert _serialize_value(None) is None

    def test_datetime(self):
        dt = datetime(2026, 1, 15, 10, 30, 0)
        assert _serialize_value(dt) == "2026-01-15T10:30:00"

    def test_bytes_utf8(self):
        assert _serialize_value(b"hello") == "hello"

    def test_bytes_binary(self):
        val = _serialize_value(b"\x80\x81\x82")
        assert val.startswith("<binary")

    def test_decimal(self):
        assert _serialize_value(Decimal("3.14")) == 3.14

    def test_nested_dict(self):
        data = {"a": datetime(2026, 1, 1), "b": Decimal("2.5")}
        result = _serialize_value(data)
        assert result["a"] == "2026-01-01T00:00:00"
        assert result["b"] == 2.5

    def test_list(self):
        data = [Decimal("1.0"), None, "text"]
        result = _serialize_value(data)
        assert result == [1.0, None, "text"]

    def test_passthrough(self):
        assert _serialize_value("hello") == "hello"
        assert _serialize_value(42) == 42
        assert _serialize_value(3.14) == 3.14


# ── execute_nosql_query routing ──────────────────────────────────────────

class TestExecuteNoSQLQuery:
    @pytest.mark.asyncio
    async def test_routes_to_mongodb(self):
        conn = MagicMock()
        conn.database_type = "mongodb"

        mock_handler = AsyncMock()
        mock_handler.handle.return_value = {"success": True, "data": []}

        with patch(
            "src.nosql.mongodb.handler.MongoDBHandler",
            return_value=mock_handler,
        ):
            result = await execute_nosql_query(
                question="find all users", connection=conn,
            )

        assert result["success"] is True
        mock_handler.handle.assert_called_once()
        call_kwargs = mock_handler.handle.call_args[1]
        assert call_kwargs["question"] == "find all users"
        assert call_kwargs["connection"] is conn

    @pytest.mark.asyncio
    async def test_routes_to_redis(self):
        conn = MagicMock()
        conn.database_type = "redis"

        mock_handler = AsyncMock()
        mock_handler.handle.return_value = {"success": True, "data": []}

        with patch(
            "src.nosql.redis.handler.RedisHandler",
            return_value=mock_handler,
        ):
            result = await execute_nosql_query(
                question="get all keys", connection=conn,
            )

        assert result["success"] is True
        mock_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_to_cassandra(self):
        conn = MagicMock()
        conn.database_type = "cassandra"

        mock_handler = AsyncMock()
        mock_handler.handle.return_value = {"success": True, "data": []}

        with patch(
            "src.nosql.cassandra.handler.CassandraHandler",
            return_value=mock_handler,
        ):
            result = await execute_nosql_query(
                question="query users", connection=conn,
            )

        assert result["success"] is True
        mock_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_to_dynamodb(self):
        conn = MagicMock()
        conn.database_type = "dynamodb"

        mock_handler = AsyncMock()
        mock_handler.handle.return_value = {"success": True, "data": []}

        with patch(
            "src.nosql.dynamodb.handler.DynamoDBHandler",
            return_value=mock_handler,
        ):
            result = await execute_nosql_query(
                question="list items", connection=conn,
            )

        assert result["success"] is True
        mock_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_to_elasticsearch(self):
        conn = MagicMock()
        conn.database_type = "elasticsearch"

        mock_handler = AsyncMock()
        mock_handler.handle.return_value = {"success": True, "data": []}

        with patch(
            "src.nosql.elasticsearch.handler.ElasticsearchHandler",
            return_value=mock_handler,
        ):
            result = await execute_nosql_query(
                question="search logs", connection=conn,
            )

        assert result["success"] is True
        mock_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_type_raises(self):
        conn = MagicMock()
        conn.database_type = "neo4j"

        with pytest.raises(ValueError, match="Unknown NoSQL database type"):
            await execute_nosql_query(
                question="test", connection=conn,
            )
