"""Tests for Redis NoSQL support."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.redis.error_classifier import classify_error
from src.llm.self_correcting_agent import ErrorType


# ── Redis error classifier ───────────────────────────────────────────────

class TestRedisErrorClassifier:
    def test_unknown_command(self):
        error_type, _ = classify_error("ERR unknown command 'BADCMD'")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_wrong_arguments(self):
        error_type, _ = classify_error("ERR wrong number of arguments for 'GET' command")
        assert error_type == ErrorType.SYNTAX_ERROR

    def test_wrongtype(self):
        error_type, _ = classify_error("WRONGTYPE Operation against a key holding the wrong kind of value")
        assert error_type == ErrorType.TYPE_MISMATCH

    def test_permission(self):
        error_type, _ = classify_error("NOAUTH Authentication required")
        assert error_type == ErrorType.PERMISSION_DENIED

    def test_timeout(self):
        error_type, _ = classify_error("Connection timed out")
        assert error_type == ErrorType.TIMEOUT

    def test_unknown(self):
        error_type, _ = classify_error("some redis error")
        assert error_type == ErrorType.UNKNOWN


# ── Redis command generator ──────────────────────────────────────────────

class TestRedisCommandGenerator:
    def setup_method(self):
        from src.nosql.redis.command_generator import RedisCommandGenerator
        self.gen = RedisCommandGenerator(MagicMock())

    def test_parse_single_command(self):
        response = json.dumps({
            "command": "GET", "args": ["user:123"],
            "data_type": "string", "is_write": False,
        })
        result = self.gen._parse_response(response)
        assert result.command == "GET"
        assert result.args == ["user:123"]

    def test_parse_json_in_code_block(self):
        response = '```json\n{"command": "KEYS", "args": ["user:*"]}\n```'
        result = self.gen._parse_response(response)
        assert result.command == "KEYS"

    def test_parse_hash_command(self):
        response = json.dumps({
            "command": "hgetall", "args": ["user:1"],
            "data_type": "hash",
        })
        result = self.gen._parse_response(response)
        assert result.command == "HGETALL"  # uppercased
        assert result.args == ["user:1"]

    def test_display_string(self):
        from src.nosql.redis.command_generator import RedisCommand
        cmd = RedisCommand(command="HGETALL", args=["user:123"])
        s = self.gen.query_to_display_string(cmd)
        assert "HGETALL" in s
        assert "user:123" in s

    @pytest.mark.asyncio
    async def test_generate_calls_ollama(self):
        from src.nosql.redis.command_generator import RedisCommandGenerator
        ollama = AsyncMock()
        ollama.generate.return_value = json.dumps({
            "command": "GET", "args": ["key1"],
        })
        gen = RedisCommandGenerator(ollama)
        result = await gen.generate(question="get key1", schema="Redis keys")
        assert result.command == "GET"
        ollama.generate.assert_called_once()


# ── Redis query executor ─────────────────────────────────────────────────

class TestRedisQueryExecutor:
    @pytest.mark.asyncio
    async def test_execute_get(self):
        from src.nosql.redis.command_generator import RedisCommand
        from src.nosql.redis.query_executor import RedisQueryExecutor

        mock_client = AsyncMock()
        mock_client.execute_command.return_value = "hello_world"

        executor = RedisQueryExecutor(client=mock_client)
        cmd = RedisCommand(command="GET", args=["mykey"])
        result = await executor.execute(cmd)

        assert result["success"] is True
        assert result["row_count"] >= 1

    @pytest.mark.asyncio
    async def test_execute_hash_result(self):
        from src.nosql.redis.command_generator import RedisCommand
        from src.nosql.redis.query_executor import RedisQueryExecutor

        mock_client = AsyncMock()
        mock_client.execute_command.return_value = {b"name": b"Alice", b"age": b"30"}

        executor = RedisQueryExecutor(client=mock_client)
        cmd = RedisCommand(command="HGETALL", args=["user:1"])
        result = await executor.execute(cmd)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_error(self):
        from src.nosql.redis.command_generator import RedisCommand
        from src.nosql.redis.query_executor import RedisQueryExecutor

        mock_client = AsyncMock()
        mock_client.execute_command.side_effect = Exception("Connection lost")

        executor = RedisQueryExecutor(client=mock_client)
        cmd = RedisCommand(command="GET", args=["key"])
        result = await executor.execute(cmd)

        assert result["success"] is False
        assert "Connection lost" in result["error"]


# ── Redis handler ────────────────────────────────────────────────────────

class TestRedisHandler:
    @pytest.mark.asyncio
    async def test_handler_error_result(self):
        from src.nosql.redis.handler import RedisHandler

        conn = MagicMock()
        conn.name = "test_redis"
        conn.database_type = "redis"

        with patch("src.nosql.redis.handler.RedisClientPool.get_instance", side_effect=Exception("Refused")):
            handler = RedisHandler()
            result = await handler.handle(question="get key", connection=conn)

        assert result["success"] is False
        assert "Refused" in result["error"]
