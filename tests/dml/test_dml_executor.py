"""Tests for DML Executor (Phase 18)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.dml.dml_executor import DMLExecutor
from src.dml.models import ChangeType, DMLStatement


def _make_connection(id=1, name="test-db", database_type="postgresql"):
    conn = MagicMock(spec=DatabaseConnection)
    conn.id = id
    conn.name = name
    conn.database_type = database_type
    return conn


def _make_statement(
    change_type=ChangeType.UPDATE,
    table_name="users",
    display_sql="UPDATE users SET name = 'new' WHERE id = 1;",
    parameterized_sql="UPDATE users SET name = :p1 WHERE id = :p2",
    params=None,
):
    return DMLStatement(
        display_sql=display_sql,
        parameterized_sql=parameterized_sql,
        params=params or {"p1": "new", "p2": 1},
        change_type=change_type,
        table_name=table_name,
    )


class TestDMLExecutorSuccess:
    @pytest.mark.asyncio
    async def test_empty_statements_returns_success(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection()

        result = await executor.execute(connection, [], metadata_db)
        assert result.success
        assert result.rows_affected == 0

    @pytest.mark.asyncio
    async def test_executes_async_statements(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection(database_type="postgresql")

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        stmt = _make_statement()

        with patch(
            "src.dml.dml_executor.UserDatabaseConnector"
        ) as mock_connector:
            # Setup async context manager
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_session
            mock_connector.get_user_db_session.return_value = mock_cm

            result = await executor.execute(
                connection, [stmt], metadata_db, user_id=1, username="alice"
            )

        assert result.success
        assert result.rows_affected == 1
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_log_on_success(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection()
        stmt = _make_statement()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        with patch(
            "src.dml.dml_executor.UserDatabaseConnector"
        ) as mock_connector, patch(
            "src.dml.dml_executor.log_action"
        ) as mock_log:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_session
            mock_connector.get_user_db_session.return_value = mock_cm

            await executor.execute(
                connection, [stmt], metadata_db, user_id=1, username="alice"
            )

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        assert call_kwargs.kwargs["action"] == "dml_execute"
        assert call_kwargs.kwargs["user_id"] == 1


class TestDMLExecutorFailure:
    @pytest.mark.asyncio
    async def test_returns_error_on_execution_failure(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection()
        stmt = _make_statement()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = RuntimeError("constraint violation")

        with patch(
            "src.dml.dml_executor.UserDatabaseConnector"
        ) as mock_connector, patch(
            "src.dml.dml_executor.log_action"
        ) as mock_log:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_session
            mock_connector.get_user_db_session.return_value = mock_cm

            result = await executor.execute(
                connection, [stmt], metadata_db, user_id=1
            )

        assert not result.success
        assert "constraint violation" in result.error_message

        # Should log failure
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "dml_failed"


class TestDMLExecutorDelete:
    @pytest.mark.asyncio
    async def test_executes_delete_statement(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock(rowcount=3)
        mock_session.execute.return_value = mock_result

        stmt = _make_statement(
            change_type=ChangeType.DELETE,
            table_name="orders",
            display_sql='DELETE FROM "orders" WHERE "id" = 42;',
            parameterized_sql='DELETE FROM "orders" WHERE "id" = :p1',
            params={"p1": 42},
        )

        with patch(
            "src.dml.dml_executor.UserDatabaseConnector"
        ) as mock_connector, patch("src.dml.dml_executor.log_action") as mock_log:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_session
            mock_connector.get_user_db_session.return_value = mock_cm

            result = await executor.execute(
                connection, [stmt], metadata_db, user_id=1, username="alice"
            )

        assert result.success
        assert result.rows_affected == 3
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "dml_execute"
        assert mock_log.call_args.kwargs["details"]["change_type"] == "DELETE"


class TestDMLExecutorInsert:
    @pytest.mark.asyncio
    async def test_executes_insert_statement(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock(rowcount=1)
        mock_session.execute.return_value = mock_result

        stmt = _make_statement(
            change_type=ChangeType.INSERT,
            table_name="users",
            display_sql="INSERT INTO \"users\" (\"name\", \"email\") VALUES ('bob', 'bob@test.com');",
            parameterized_sql='INSERT INTO "users" ("name", "email") VALUES (:p1, :p2)',
            params={"p1": "bob", "p2": "bob@test.com"},
        )

        with patch(
            "src.dml.dml_executor.UserDatabaseConnector"
        ) as mock_connector, patch("src.dml.dml_executor.log_action") as mock_log:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_session
            mock_connector.get_user_db_session.return_value = mock_cm

            result = await executor.execute(
                connection, [stmt], metadata_db, user_id=2, username="bob"
            )

        assert result.success
        assert result.rows_affected == 1
        assert mock_log.call_args.kwargs["details"]["change_type"] == "INSERT"


class TestDMLExecutorMultipleStatements:
    @pytest.mark.asyncio
    async def test_multiple_statements_accumulate_rowcount(self):
        executor = DMLExecutor()
        metadata_db = AsyncMock(spec=AsyncSession)
        connection = _make_connection()

        mock_session = AsyncMock(spec=AsyncSession)
        result1 = MagicMock(rowcount=2)
        result2 = MagicMock(rowcount=3)
        mock_session.execute.side_effect = [result1, result2]

        stmts = [_make_statement(), _make_statement(change_type=ChangeType.INSERT)]

        with patch(
            "src.dml.dml_executor.UserDatabaseConnector"
        ) as mock_connector, patch("src.dml.dml_executor.log_action"):
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_session
            mock_connector.get_user_db_session.return_value = mock_cm

            result = await executor.execute(connection, stmts, metadata_db)

        assert result.success
        assert result.rows_affected == 5
