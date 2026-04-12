"""Tests for DML Validator (Phase 18)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.database.models import ConnectionWritePermission, DatabaseConnection
from src.dml.dml_validator import DMLValidator
from src.dml.models import ChangeType, CellChangeSchema, RowChangeSchema


def _make_connection(
    id=1, database_type="postgresql", owner_id=None, is_deleted=False
):
    conn = MagicMock(spec=DatabaseConnection)
    conn.id = id
    conn.database_type = database_type
    conn.owner_id = owner_id
    conn.is_deleted = is_deleted
    return conn


def _make_permission(**kwargs):
    defaults = {
        "connection_id": 1,
        "allow_insert": True,
        "allow_update": True,
        "allow_delete": True,
        "require_where_clause": True,
        "max_rows_per_operation": 100,
        "allowed_tables": None,
    }
    defaults.update(kwargs)
    perm = MagicMock(spec=ConnectionWritePermission)
    for k, v in defaults.items():
        setattr(perm, k, v)
    return perm


def _make_settings(**kwargs):
    defaults = {"ALLOW_WRITE_OPERATIONS": True}
    defaults.update(kwargs)
    s = MagicMock(spec=Settings)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_db(connection=None, permission=None):
    db = AsyncMock(spec=AsyncSession)

    # Always provide a result for the connection query
    conn_result = MagicMock()
    conn_result.scalar_one_or_none.return_value = connection
    results = [conn_result]

    # Only provide permission result if connection is found
    if connection is not None:
        perm_result = MagicMock()
        perm_result.scalar_one_or_none.return_value = permission
        results.append(perm_result)

    db.execute.side_effect = results
    return db


def _simple_update():
    return RowChangeSchema(
        change_type=ChangeType.UPDATE,
        table_name="users",
        primary_key={"id": 1},
        changes=[CellChangeSchema(column="name", old_value="old", new_value="new")],
    )


class TestDMLValidatorGlobalSettings:
    @pytest.mark.asyncio
    async def test_rejects_when_writes_disabled(self):
        settings = _make_settings(ALLOW_WRITE_OPERATIONS=False)
        db = AsyncMock(spec=AsyncSession)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], settings
        )
        assert not is_valid
        assert "disabled globally" in error


class TestDMLValidatorConnectionAccess:
    @pytest.mark.asyncio
    async def test_rejects_missing_connection(self):
        db = _mock_db(connection=None)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 999, [_simple_update()], _make_settings()
        )
        assert not is_valid
        assert "not found" in error

    @pytest.mark.asyncio
    async def test_rejects_no_write_permissions(self):
        """Ownership is enforced by the API layer; the validator checks
        write-permission records next."""
        conn = _make_connection(owner_id=5)
        db = _mock_db(connection=conn)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings(), user_id=99
        )
        assert not is_valid
        assert "write permissions" in error.lower()

    @pytest.mark.asyncio
    async def test_nosql_passes_with_permissions(self):
        conn = _make_connection(database_type="mongodb")
        perm = _make_permission()
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings()
        )
        assert is_valid
        assert error is None


class TestDMLValidatorPermissions:
    @pytest.mark.asyncio
    async def test_rejects_no_permission_record(self):
        conn = _make_connection()
        db = _mock_db(connection=conn, permission=None)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings()
        )
        assert not is_valid
        assert "not been configured" in error

    @pytest.mark.asyncio
    async def test_rejects_insert_when_not_allowed(self):
        conn = _make_connection()
        perm = _make_permission(allow_insert=False)
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        change = RowChangeSchema(
            change_type=ChangeType.INSERT,
            table_name="users",
            new_row_data={"name": "test"},
        )
        is_valid, error = await validator.validate(
            db, 1, [change], _make_settings()
        )
        assert not is_valid
        assert "INSERT" in error

    @pytest.mark.asyncio
    async def test_rejects_update_when_not_allowed(self):
        conn = _make_connection()
        perm = _make_permission(allow_update=False)
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings()
        )
        assert not is_valid
        assert "UPDATE" in error

    @pytest.mark.asyncio
    async def test_rejects_table_not_in_whitelist(self):
        conn = _make_connection()
        perm = _make_permission(allowed_tables=["products", "orders"])
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings()
        )
        assert not is_valid
        assert "allowed tables" in error

    @pytest.mark.asyncio
    async def test_allows_table_in_whitelist(self):
        conn = _make_connection()
        perm = _make_permission(allowed_tables=["users", "orders"])
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings()
        )
        assert is_valid


class TestDMLValidatorSafety:
    @pytest.mark.asyncio
    async def test_rejects_update_without_pk(self):
        """UPDATE without primary key is always rejected, regardless of require_where_clause."""
        conn = _make_connection()
        perm = _make_permission(require_where_clause=False)
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        change = RowChangeSchema(
            change_type=ChangeType.UPDATE,
            table_name="users",
            primary_key={},
            changes=[CellChangeSchema(column="name", old_value="a", new_value="b")],
        )
        is_valid, error = await validator.validate(
            db, 1, [change], _make_settings()
        )
        assert not is_valid
        assert "primary key" in error

    @pytest.mark.asyncio
    async def test_rejects_too_many_operations(self):
        conn = _make_connection()
        perm = _make_permission(max_rows_per_operation=2)
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": f"user{i}"},
            )
            for i in range(3)
        ]
        is_valid, error = await validator.validate(
            db, 1, changes, _make_settings()
        )
        assert not is_valid
        assert "Too many" in error

    @pytest.mark.asyncio
    async def test_rejects_unsafe_table_name(self):
        conn = _make_connection()
        perm = _make_permission()
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        change = RowChangeSchema(
            change_type=ChangeType.INSERT,
            table_name="drop_table; --",
            new_row_data={"a": 1},
        )
        is_valid, error = await validator.validate(
            db, 1, [change], _make_settings()
        )
        assert not is_valid
        assert "Invalid table name" in error

    @pytest.mark.asyncio
    async def test_empty_changes_is_valid(self):
        db = AsyncMock(spec=AsyncSession)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [], _make_settings()
        )
        assert is_valid
        assert error is None


class TestDMLValidatorSuccess:
    @pytest.mark.asyncio
    async def test_valid_update_passes(self):
        conn = _make_connection()
        perm = _make_permission()
        db = _mock_db(connection=conn, permission=perm)
        validator = DMLValidator()
        is_valid, error = await validator.validate(
            db, 1, [_simple_update()], _make_settings()
        )
        assert is_valid
        assert error is None
