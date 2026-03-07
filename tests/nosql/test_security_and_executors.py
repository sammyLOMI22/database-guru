"""Tests for NoSQL security validations, executor edge cases, and router utilities.

Covers gaps identified in PR Review #3:
- CQL injection validation (M6/C-NEW-1)
- PartiQL injection validation (M12)
- Redis blocked command rejection (M12)
- Elasticsearch recursive script detection (M-NEW-1)
- DynamoDB pagination truncation (M7)
- Router evict_nosql_pool and get_cached_or_fresh_schema (M11)
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.nosql.cassandra.query_executor import CassandraQueryExecutor
from src.nosql.dynamodb.query_executor import DynamoDBQueryExecutor
from src.nosql.elasticsearch.query_executor import ElasticsearchQueryExecutor
from src.nosql.redis.query_executor import RedisQueryExecutor, ALLOWED_READ_COMMANDS
from src.nosql.redis.command_generator import RedisCommand
from src.nosql.router import evict_nosql_pool, get_cached_or_fresh_schema


# ── CQL Validation (Cassandra) ──────────────────────────────────────────

class TestCQLValidation:
    """Tests for CassandraQueryExecutor._validate_cql()."""

    def _make_executor(self):
        return CassandraQueryExecutor(session=MagicMock())

    def test_valid_select(self):
        ex = self._make_executor()
        assert ex._validate_cql("SELECT * FROM users") is None

    def test_valid_select_with_trailing_semicolon(self):
        ex = self._make_executor()
        assert ex._validate_cql("SELECT * FROM users;") is None

    def test_empty_query(self):
        ex = self._make_executor()
        assert ex._validate_cql("") == "Empty query"
        assert ex._validate_cql("   ") == "Empty query"

    def test_multi_statement_blocked(self):
        ex = self._make_executor()
        result = ex._validate_cql("SELECT * FROM users; DROP TABLE users")
        assert "Multi-statement" in result

    def test_semicolon_inside_string_allowed(self):
        ex = self._make_executor()
        result = ex._validate_cql("SELECT * FROM users WHERE name = 'foo;bar'")
        assert result is None

    def test_comment_prefixed_write_blocked(self):
        ex = self._make_executor()
        result = ex._validate_cql("/* comment */ DROP TABLE users")
        assert "Unsupported CQL statement type" in result

    def test_unsupported_statement_type(self):
        ex = self._make_executor()
        result = ex._validate_cql("TRUNCATE users")
        assert "Unsupported CQL statement type" in result

    def test_use_statement_allowed(self):
        ex = self._make_executor()
        assert ex._validate_cql("USE my_keyspace") is None

    @pytest.mark.asyncio
    async def test_write_blocked_without_allow_write(self):
        ex = self._make_executor()
        result = await ex.execute("INSERT INTO users (id) VALUES (1)")
        assert result["success"] is False
        assert "Write operation" in result["error"]

    @pytest.mark.asyncio
    async def test_write_blocked_with_comment_prefix(self):
        ex = self._make_executor()
        result = await ex.execute("/* bypass */ INSERT INTO users (id) VALUES (1)")
        assert result["success"] is False


# ── PartiQL Validation (DynamoDB) ────────────────────────────────────────

class TestPartiQLValidation:
    """Tests for DynamoDBQueryExecutor._validate_partiql()."""

    def _make_executor(self):
        return DynamoDBQueryExecutor(session=MagicMock(), region="us-east-1")

    def test_valid_select(self):
        ex = self._make_executor()
        assert ex._validate_partiql("SELECT * FROM Users") is None

    def test_empty_query(self):
        ex = self._make_executor()
        assert ex._validate_partiql("") == "Empty query"

    def test_multi_statement_blocked(self):
        ex = self._make_executor()
        result = ex._validate_partiql("SELECT * FROM Users; DELETE FROM Users")
        assert "Multi-statement" in result

    def test_semicolon_inside_string_allowed(self):
        ex = self._make_executor()
        result = ex._validate_partiql("SELECT * FROM Users WHERE name = 'a;b'")
        assert result is None

    def test_escaped_quotes_in_string(self):
        ex = self._make_executor()
        result = ex._validate_partiql("SELECT * FROM Users WHERE name = 'it''s'")
        assert result is None

    def test_unsupported_statement_type(self):
        ex = self._make_executor()
        result = ex._validate_partiql("DROP TABLE Users")
        assert "Unsupported PartiQL statement type" in result

    @pytest.mark.asyncio
    async def test_pagination_truncation_flag(self):
        """M7: Verify truncated flag is set when NextToken is present."""
        ex = self._make_executor()

        mock_client = AsyncMock()
        mock_client.execute_statement.return_value = {
            "Items": [{"id": {"S": "1"}, "name": {"S": "Alice"}}],
            "NextToken": "abc123",
        }
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)
        ex.session.client.return_value = mock_context

        result = await ex.execute("SELECT * FROM Users")
        assert result["success"] is True
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_no_truncation_without_next_token(self):
        ex = self._make_executor()

        mock_client = AsyncMock()
        mock_client.execute_statement.return_value = {
            "Items": [{"id": {"S": "1"}}],
        }
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)
        ex.session.client.return_value = mock_context

        result = await ex.execute("SELECT * FROM Users")
        assert result["success"] is True
        assert result["truncated"] is False


# ── Redis Blocked Commands ───────────────────────────────────────────────

class TestRedisBlockedCommands:
    """Tests for Redis command allowlist enforcement."""

    def _make_executor(self):
        import redis.asyncio as aioredis
        mock_client = MagicMock(spec=aioredis.Redis)
        return RedisQueryExecutor(client=mock_client)

    @pytest.mark.asyncio
    async def test_flushall_blocked(self):
        ex = self._make_executor()
        result = await ex.execute(RedisCommand(command="FLUSHALL", args=[]))
        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_config_blocked(self):
        ex = self._make_executor()
        result = await ex.execute(RedisCommand(command="CONFIG", args=["GET", "*"]))
        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_eval_blocked(self):
        ex = self._make_executor()
        result = await ex.execute(RedisCommand(command="EVAL", args=["return 1", "0"]))
        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_shutdown_blocked(self):
        ex = self._make_executor()
        result = await ex.execute(RedisCommand(command="SHUTDOWN", args=[]))
        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_debug_blocked(self):
        ex = self._make_executor()
        result = await ex.execute(RedisCommand(command="DEBUG", args=["SLEEP", "10"]))
        assert result["success"] is False
        assert "not allowed" in result["error"]

    def test_keys_not_in_allowlist(self):
        """M5: KEYS should have been removed from the allowlist."""
        assert "KEYS" not in ALLOWED_READ_COMMANDS

    @pytest.mark.asyncio
    async def test_keys_command_blocked(self):
        """M5: KEYS command should be blocked."""
        ex = self._make_executor()
        result = await ex.execute(RedisCommand(command="KEYS", args=["*"]))
        assert result["success"] is False
        assert "not allowed" in result["error"]


# ── Elasticsearch Script Detection ───────────────────────────────────────

class TestElasticsearchScriptDetection:
    """Tests for recursive script detection in ES query DSL."""

    def _make_executor(self):
        return ElasticsearchQueryExecutor(client=MagicMock())

    @pytest.mark.asyncio
    async def test_top_level_script_blocked(self):
        ex = self._make_executor()
        result = await ex.execute({"script": {"source": "ctx._source.count++"}})
        assert result["success"] is False
        assert "Script execution not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_nested_script_score_blocked(self):
        ex = self._make_executor()
        result = await ex.execute({
            "index": "logs",
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {"source": "_score * 2"},
                }
            }
        })
        assert result["success"] is False
        assert "Script execution not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_nested_scripted_metric_blocked(self):
        ex = self._make_executor()
        result = await ex.execute({
            "index": "logs",
            "aggs": {
                "my_agg": {
                    "scripted_metric": {
                        "init_script": "state.transactions = []",
                    }
                }
            }
        })
        assert result["success"] is False
        assert "Script execution not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_deeply_nested_script_blocked(self):
        ex = self._make_executor()
        result = await ex.execute({
            "index": "logs",
            "query": {
                "bool": {
                    "must": [
                        {"script_score": {"query": {"match_all": {}}, "script": {"source": "1"}}}
                    ]
                }
            }
        })
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_safe_query_allowed(self):
        """A normal query without scripts should pass the write check."""
        ex = self._make_executor()
        # Mock the client.search to avoid actual ES call
        mock_response = {"hits": {"hits": []}}
        ex.client.search = AsyncMock(return_value=mock_response)
        result = await ex.execute({
            "index": "logs",
            "query": {"match": {"message": "error"}}
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_top_level_update_blocked(self):
        ex = self._make_executor()
        result = await ex.execute({"update": {"_id": "1"}})
        assert result["success"] is False
        assert "Write operation not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_script_allowed_with_allow_write(self):
        ex = ElasticsearchQueryExecutor(client=MagicMock(), allow_write=True)
        ex.client.search = AsyncMock(return_value={"hits": {"hits": []}})
        result = await ex.execute({
            "index": "logs",
            "query": {"script_score": {"query": {"match_all": {}}, "script": {"source": "1"}}}
        })
        assert result["success"] is True


# ── Router Utilities ─────────────────────────────────────────────────────

class TestEvictNoSQLPool:
    """Tests for evict_nosql_pool."""

    @pytest.mark.asyncio
    async def test_sql_type_is_noop(self):
        """SQL types should return without doing anything."""
        await evict_nosql_pool(1, "postgresql")  # Should not raise

    @pytest.mark.asyncio
    async def test_mongodb_eviction(self):
        mock_pool = AsyncMock()
        with patch("src.nosql.mongodb.client_pool.MongoClientPool.get_instance", return_value=mock_pool):
            await evict_nosql_pool(42, "mongodb")
        mock_pool.evict.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_eviction_error_logged_not_raised(self):
        """Eviction errors should be caught, not propagated."""
        mock_pool = AsyncMock()
        mock_pool.evict.side_effect = RuntimeError("pool error")
        with patch("src.nosql.mongodb.client_pool.MongoClientPool.get_instance", return_value=mock_pool):
            await evict_nosql_pool(1, "mongodb")  # Should not raise


class TestGetCachedOrFreshSchema:
    """Tests for get_cached_or_fresh_schema."""

    @pytest.mark.asyncio
    async def test_returns_cached_schema_when_fresh(self):
        conn = MagicMock()
        conn.schema_cache = {"tables": {"users": {}}}
        conn.schema_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        inspector = AsyncMock()
        result = await get_cached_or_fresh_schema(conn, inspector)

        assert result == {"tables": {"users": {}}}
        inspector.get_schema.assert_not_called()

    @pytest.mark.asyncio
    async def test_inspects_when_cache_expired(self):
        conn = MagicMock()
        conn.schema_cache = {"tables": {"users": {}}}
        # Set updated_at to a very old time
        conn.schema_updated_at = datetime(2020, 1, 1)

        inspector = AsyncMock()
        inspector.get_schema.return_value = {"tables": {"orders": {}}}

        result = await get_cached_or_fresh_schema(conn, inspector, db=None)

        assert result == {"tables": {"orders": {}}}
        inspector.get_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_inspects_when_no_cache(self):
        conn = MagicMock()
        conn.schema_cache = None
        conn.schema_updated_at = None

        inspector = AsyncMock()
        inspector.get_schema.return_value = {"tables": {"t1": {}}}

        result = await get_cached_or_fresh_schema(conn, inspector)

        assert result == {"tables": {"t1": {}}}
        inspector.get_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_persists_schema_to_db(self):
        conn = MagicMock()
        conn.schema_cache = None
        conn.schema_updated_at = None

        inspector = AsyncMock()
        inspector.get_schema.return_value = {"tables": {"t1": {}}}

        db = AsyncMock()

        await get_cached_or_fresh_schema(conn, inspector, db=db)

        assert conn.schema_cache == {"tables": {"t1": {}}}
        db.commit.assert_called_once()
