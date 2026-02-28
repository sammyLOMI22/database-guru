"""Tests for Cassandra NoSQL support."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.cassandra.error_classifier import classify_error
from src.llm.self_correcting_agent import ErrorType


# ── Cassandra error classifier ───────────────────────────────────────────

class TestCassandraErrorClassifier:
    def test_table_not_found(self):
        error_type, _ = classify_error("unconfigured table my_keyspace.missing_table")
        assert error_type == ErrorType.TABLE_NOT_FOUND

    def test_column_not_found(self):
        error_type, _ = classify_error("Undefined column name bad_col")
        assert error_type == ErrorType.COLUMN_NOT_FOUND

    def test_syntax_error(self):
        error_type, _ = classify_error("SyntaxException: mismatched input 'SELCT'")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_allow_filtering(self):
        error_type, hint = classify_error("Cannot execute this query as it might involve data filtering")
        assert error_type == ErrorType.SYNTAX_ERROR
        assert "ALLOW FILTERING" in hint

    def test_type_mismatch(self):
        error_type, _ = classify_error("Type error: cannot assign text to int column")
        assert error_type == ErrorType.TYPE_MISMATCH

    def test_permission(self):
        error_type, _ = classify_error("Unauthorized: user has no permission")
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_timeout(self):
        error_type, _ = classify_error("OperationTimedOut: timeout")
        assert error_type == ErrorType.TIMEOUT

    def test_unknown(self):
        error_type, _ = classify_error("some cassandra error")
        assert error_type == ErrorType.UNKNOWN


# ── CQL generator ────────────────────────────────────────────────────────

class TestCQLGenerator:
    def setup_method(self):
        from src.nosql.cassandra.cql_generator import CQLGenerator
        self.gen = CQLGenerator(MagicMock())

    def test_extract_raw_cql(self):
        response = "SELECT count(*) FROM events WHERE type = 'click'"
        result = self.gen._extract_cql(response)
        assert "SELECT count(*)" in result

    def test_extract_from_code_block(self):
        response = '```cql\nSELECT name FROM users WHERE id = 1\n```'
        result = self.gen._extract_cql(response)
        assert "SELECT name FROM users" in result

    def test_extract_strips_explanation(self):
        response = "SELECT * FROM users LIMIT 100\nThis query gets all users"
        result = self.gen._extract_cql(response)
        assert "This query" not in result
        assert "SELECT" in result

    def test_extract_adds_semicolon(self):
        response = "SELECT * FROM users"
        result = self.gen._extract_cql(response)
        assert result.endswith(";")

    def test_display_string(self):
        assert self.gen.query_to_display_string("SELECT * FROM users;") == "SELECT * FROM users;"

    @pytest.mark.asyncio
    async def test_generate(self):
        from src.nosql.cassandra.cql_generator import CQLGenerator
        ollama = AsyncMock()
        ollama.generate.return_value = "SELECT * FROM users LIMIT 100"
        gen = CQLGenerator(ollama)
        result = await gen.generate(question="show users", schema="Cassandra schema")
        assert "SELECT" in result
        ollama.generate.assert_called_once()


# ── Cassandra handler ────────────────────────────────────────────────────

class TestCassandraHandler:
    @pytest.mark.asyncio
    async def test_handler_error_result(self):
        from src.nosql.cassandra.handler import CassandraHandler

        conn = MagicMock()
        conn.name = "test_cassandra"
        conn.database_type = "cassandra"

        with patch("src.nosql.cassandra.handler.CassandraClientPool.get_instance", side_effect=Exception("No hosts")):
            handler = CassandraHandler()
            result = await handler.handle(question="show tables", connection=conn)

        assert result["success"] is False
        assert "No hosts" in result["error"]
