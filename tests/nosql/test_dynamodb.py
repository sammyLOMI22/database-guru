"""Tests for DynamoDB NoSQL support."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.dynamodb.error_classifier import classify_error
from src.llm.self_correcting_agent import ErrorType


# ── DynamoDB error classifier ────────────────────────────────────────────

class TestDynamoDBErrorClassifier:
    def test_table_not_found(self):
        error_type, _ = classify_error("ResourceNotFoundException: Requested resource not found: Table: missing_table not found")
        assert error_type == ErrorType.TABLE_NOT_FOUND

    def test_validation_key(self):
        error_type, _ = classify_error("ValidationException: One or more parameter values were invalid: Missing the key id")
        assert error_type == ErrorType.COLUMN_NOT_FOUND

    def test_validation_general(self):
        error_type, _ = classify_error("ValidationException: Invalid ProjectionExpression")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_partiql_syntax(self):
        error_type, _ = classify_error("PartiQL syntax error near 'SELCT'")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_access_denied(self):
        error_type, _ = classify_error("AccessDeniedException: User is not authorized")
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_timeout(self):
        error_type, _ = classify_error("Request timed out")
        assert error_type == ErrorType.TIMEOUT

    def test_unknown(self):
        error_type, _ = classify_error("some dynamo error")
        assert error_type == ErrorType.UNKNOWN


# ── PartiQL generator ────────────────────────────────────────────────────

class TestPartiQLGenerator:
    def setup_method(self):
        from src.nosql.dynamodb.partiql_generator import PartiQLGenerator
        self.gen = PartiQLGenerator(MagicMock())

    def test_extract_raw_partiql(self):
        response = 'SELECT * FROM "users" WHERE status = \'active\''
        result = self.gen._extract_partiql(response)
        assert "SELECT * FROM" in result

    def test_extract_from_code_block(self):
        response = '```sql\nSELECT id, name FROM "orders"\n```'
        result = self.gen._extract_partiql(response)
        assert "SELECT id, name FROM" in result

    def test_extract_strips_explanation(self):
        response = 'SELECT * FROM "users"\nThis query gets all users'
        result = self.gen._extract_partiql(response)
        assert "This query" not in result
        assert "SELECT" in result

    def test_display_string(self):
        query = 'SELECT * FROM "users"'
        assert self.gen.query_to_display_string(query) == 'SELECT * FROM "users"'

    @pytest.mark.asyncio
    async def test_generate(self):
        from src.nosql.dynamodb.partiql_generator import PartiQLGenerator
        ollama = AsyncMock()
        ollama.generate.return_value = 'SELECT * FROM "users"'
        gen = PartiQLGenerator(ollama)
        result = await gen.generate(question="show users", schema="DynamoDB tables")
        assert "SELECT" in result


# ── DynamoDB handler ─────────────────────────────────────────────────────

class TestDynamoDBHandler:
    @pytest.mark.asyncio
    async def test_handler_error_result(self):
        from src.nosql.dynamodb.handler import DynamoDBHandler

        conn = MagicMock()
        conn.name = "test_dynamo"
        conn.database_type = "dynamodb"
        conn.username = "AKIA_FAKE"
        conn.host = "us-east-1"

        with patch("src.nosql.dynamodb.handler.DynamoDBClientPool.get_instance", side_effect=Exception("No credentials")):
            handler = DynamoDBHandler()
            result = await handler.handle(question="show tables", connection=conn)

        assert result["success"] is False
        assert "No credentials" in result["error"]
