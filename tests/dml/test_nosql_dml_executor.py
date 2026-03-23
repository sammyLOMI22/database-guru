"""Tests for NoSQL DML Executor (mocked dispatch functions)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.dml.models import ChangeType, DMLStatement, ExecutionResult
from src.dml import nosql_dml_executor
from src.dml.nosql_dml_executor import NoSQLDMLExecutor, _execute_mongodb, _execute_redis, _execute_cassandra, _execute_dynamodb, _execute_elasticsearch


def _make_stmt(
    change_type: ChangeType = ChangeType.INSERT,
    table_name: str = "users",
    display: str = "db.users.insertOne(...)",
    native_op: dict = None,
) -> DMLStatement:
    return DMLStatement(
        display_sql=display,
        parameterized_sql="",
        change_type=change_type,
        table_name=table_name,
        native_operation=native_op or {"method": "insert_one", "collection": table_name, "document": {"x": 1}},
    )


def _make_connection(db_type: str = "mongodb", conn_id: int = 1):
    conn = MagicMock()
    conn.id = conn_id
    conn.name = "test-conn"
    conn.database_type = db_type
    conn.host = "localhost"
    conn.port = 27017
    conn.username = "user"
    conn.password_encrypted = "pass"
    conn.database_name = "testdb"
    conn.owner_id = None
    return conn


@pytest.fixture
def metadata_db():
    return AsyncMock(spec=AsyncSession)


def _patch_executor(db_type: str, return_value=1, side_effect=None):
    """Patch a specific DB executor in the _EXECUTORS registry."""
    mock_fn = AsyncMock(return_value=return_value, side_effect=side_effect)
    return patch.dict(nosql_dml_executor._EXECUTORS, {db_type: mock_fn}), mock_fn


# ── Core dispatch tests ────────────────────────────────────────────


class TestDispatch:
    @pytest.mark.asyncio
    async def test_mongodb_dispatch(self, metadata_db):
        stmt = _make_stmt(native_op={"method": "insert_one", "collection": "users", "document": {"name": "Alice"}})
        p, mock_fn = _patch_executor("mongodb")
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("mongodb"), [stmt], metadata_db)
        assert result.success is True
        assert result.rows_affected == 1
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_dispatch(self, metadata_db):
        stmt = _make_stmt(
            table_name="user:1", display="HSET user:1 name Alice",
            native_op={"command": "HSET", "key": "user:1", "mapping": {"name": "Alice"}},
        )
        p, mock_fn = _patch_executor("redis")
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("redis"), [stmt], metadata_db)
        assert result.success is True
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_cassandra_dispatch(self, metadata_db):
        stmt = _make_stmt(
            display="INSERT INTO users (id) VALUES (1)",
            native_op={"cql": "INSERT INTO users (id) VALUES (%s)", "params": [1]},
        )
        p, _ = _patch_executor("cassandra")
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("cassandra"), [stmt], metadata_db)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dynamodb_dispatch(self, metadata_db):
        stmt = _make_stmt(
            display='INSERT INTO "Users" VALUE ...',
            native_op={"partiql": 'INSERT INTO "Users" VALUE {\'pk\': \'u1\'}'},
        )
        p, _ = _patch_executor("dynamodb")
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("dynamodb"), [stmt], metadata_db)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_elasticsearch_dispatch(self, metadata_db):
        stmt = _make_stmt(
            display="POST /users/_doc",
            native_op={"method": "index", "index": "users", "body": {"name": "Alice"}},
        )
        p, _ = _patch_executor("elasticsearch")
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("elasticsearch"), [stmt], metadata_db)
        assert result.success is True


# ── Error handling ─────────────────────────────────────────────────


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_statements(self, metadata_db):
        result = await NoSQLDMLExecutor().execute(_make_connection("mongodb"), [], metadata_db)
        assert result.success is True
        assert result.rows_affected == 0

    @pytest.mark.asyncio
    async def test_unsupported_db_type(self, metadata_db):
        result = await NoSQLDMLExecutor().execute(_make_connection("neo4j"), [_make_stmt()], metadata_db)
        assert result.success is False
        assert "Unsupported" in result.error_message

    @pytest.mark.asyncio
    async def test_execution_error_returns_failure(self, metadata_db):
        p, _ = _patch_executor("mongodb", side_effect=ConnectionError("cannot connect"))
        with p:
            result = await NoSQLDMLExecutor().execute(
                _make_connection("mongodb"), [_make_stmt()], metadata_db,
                user_id=1, username="test",
            )
        assert result.success is False
        assert "cannot connect" in result.error_message

    @pytest.mark.asyncio
    async def test_multiple_statements_row_count(self, metadata_db):
        stmts = [_make_stmt() for _ in range(3)]
        p, _ = _patch_executor("mongodb", return_value=3)
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("mongodb"), stmts, metadata_db)
        assert result.success is True
        assert result.rows_affected == 3


# ── Audit logging ──────────────────────────────────────────────────


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_success_audit_logged(self, metadata_db):
        p, _ = _patch_executor("mongodb")
        with p, patch.object(nosql_dml_executor, "log_action", new_callable=AsyncMock) as mock_log:
            result = await NoSQLDMLExecutor().execute(
                _make_connection("mongodb"), [_make_stmt()], metadata_db,
                user_id=1, username="test", ip_address="127.0.0.1",
            )
        assert result.success is True
        mock_log.assert_called_once()
        kwargs = mock_log.call_args.kwargs
        assert kwargs["action"] == "dml_execute"
        assert kwargs["user_id"] == 1

    @pytest.mark.asyncio
    async def test_failure_audit_logged(self, metadata_db):
        p, _ = _patch_executor("mongodb", side_effect=RuntimeError("boom"))
        with p, patch.object(nosql_dml_executor, "log_action", new_callable=AsyncMock) as mock_log:
            result = await NoSQLDMLExecutor().execute(
                _make_connection("mongodb"), [_make_stmt()], metadata_db,
                user_id=1, username="test",
            )
        assert result.success is False
        mock_log.assert_called_once()
        kwargs = mock_log.call_args.kwargs
        assert kwargs["action"] == "dml_failed"

    @pytest.mark.asyncio
    async def test_display_sql_in_result(self, metadata_db):
        stmt = _make_stmt(display="db.users.insertOne({name: 'Alice'})")
        p, _ = _patch_executor("mongodb")
        with p:
            result = await NoSQLDMLExecutor().execute(_make_connection("mongodb"), [stmt], metadata_db)
        assert "insertOne" in result.executed_sql


# ── Import smoke test ─────────────────────────────────────────────


class TestExecutorImports:
    """Verify all per-DB executor functions are importable and callable."""

    def test_all_executors_are_async_callables(self):
        import asyncio
        for fn in [_execute_mongodb, _execute_redis, _execute_cassandra, _execute_dynamodb, _execute_elasticsearch]:
            assert callable(fn)
            assert asyncio.iscoroutinefunction(fn)

    def test_registry_matches_exports(self):
        assert set(nosql_dml_executor._EXECUTORS.keys()) == {
            "mongodb", "redis", "cassandra", "dynamodb", "elasticsearch",
        }


# ── _get_nosql_table_info tests ───────────────────────────────────


class TestGetNoSQLTableInfo:
    """Test the _get_nosql_table_info helper from the DML endpoint module."""

    @pytest.mark.asyncio
    async def test_mongodb_table_info_from_schema(self):
        from src.api.endpoints.dml import _get_nosql_table_info

        mock_inspector = AsyncMock()
        mock_inspector.get_schema.return_value = {
            "tables": {
                "users": {
                    "name": "string",
                    "_id": "ObjectId",
                    "email": "string",
                }
            }
        }
        conn = _make_connection("mongodb")
        with patch("src.nosql.router.get_nosql_inspector", new_callable=AsyncMock, return_value=(mock_inspector, None)):
            result = await _get_nosql_table_info(conn, "users")

        assert result.table_name == "users"
        assert "_id" in result.primary_key_columns
        assert len(result.columns) == 3
        # _id should be marked as PK
        id_col = next(c for c in result.columns if c.name == "_id")
        assert id_col.is_primary_key is True

    @pytest.mark.asyncio
    async def test_dynamodb_extracts_key_columns(self):
        from src.api.endpoints.dml import _get_nosql_table_info

        mock_inspector = AsyncMock()
        mock_inspector.get_schema.return_value = {
            "tables": {
                "Orders": {
                    "order_id": {"type": "S", "key_type": "HASH"},
                    "sort_key": {"type": "S", "key_type": "RANGE"},
                    "amount": {"type": "N"},
                }
            }
        }
        conn = _make_connection("dynamodb")
        with patch("src.nosql.router.get_nosql_inspector", new_callable=AsyncMock, return_value=(mock_inspector, None)):
            result = await _get_nosql_table_info(conn, "Orders")

        assert set(result.primary_key_columns) == {"order_id", "sort_key"}

    @pytest.mark.asyncio
    async def test_cassandra_extracts_partition_keys(self):
        from src.api.endpoints.dml import _get_nosql_table_info

        mock_inspector = AsyncMock()
        mock_inspector.get_schema.return_value = {
            "tables": {
                "events": {
                    "event_id": {"type": "uuid", "kind": "partition_key"},
                    "ts": {"type": "timestamp", "kind": "clustering"},
                    "data": {"type": "text"},
                }
            }
        }
        conn = _make_connection("cassandra")
        with patch("src.nosql.router.get_nosql_inspector", new_callable=AsyncMock, return_value=(mock_inspector, None)):
            result = await _get_nosql_table_info(conn, "events")

        assert set(result.primary_key_columns) == {"event_id", "ts"}

    @pytest.mark.asyncio
    async def test_missing_table_returns_minimal_info(self):
        from src.api.endpoints.dml import _get_nosql_table_info

        mock_inspector = AsyncMock()
        mock_inspector.get_schema.return_value = {"tables": {}}
        conn = _make_connection("mongodb")
        with patch("src.nosql.router.get_nosql_inspector", new_callable=AsyncMock, return_value=(mock_inspector, None)):
            result = await _get_nosql_table_info(conn, "nonexistent")

        # Should return minimal info with _id as default PK
        assert len(result.columns) == 1
        assert result.columns[0].name == "_id"
        assert result.columns[0].is_primary_key is True

    @pytest.mark.asyncio
    async def test_redis_uses_key_as_pk(self):
        from src.api.endpoints.dml import _get_nosql_table_info

        mock_inspector = AsyncMock()
        mock_inspector.get_schema.return_value = {
            "tables": {
                "user:1": {"name": "string", "age": "string"}
            }
        }
        conn = _make_connection("redis")
        with patch("src.nosql.router.get_nosql_inspector", new_callable=AsyncMock, return_value=(mock_inspector, None)):
            result = await _get_nosql_table_info(conn, "user:1")

        assert "key" in result.primary_key_columns
