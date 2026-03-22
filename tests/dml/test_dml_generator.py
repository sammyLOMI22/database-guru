"""Tests for DML Generator (Phase 18)."""
import pytest
from src.dml.dml_generator import DMLGenerator
from src.dml.models import ChangeType, CellChangeSchema, RowChangeSchema


class TestDMLGeneratorInsert:
    def test_basic_insert(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "Alice", "email": "alice@example.com"},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert stmt.change_type == ChangeType.INSERT
        assert stmt.table_name == "users"
        assert '"users"' in stmt.display_sql
        assert '"name"' in stmt.display_sql
        assert "'Alice'" in stmt.display_sql
        assert ":p" in stmt.parameterized_sql
        assert stmt.params["p1"] == "Alice"
        assert stmt.params["p2"] == "alice@example.com"

    def test_insert_with_null(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "Bob", "bio": None},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert "NULL" in stmts[0].display_sql
        assert stmts[0].params["p2"] is None

    def test_insert_with_numeric(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="products",
                new_row_data={"price": 19.99, "quantity": 5},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert "19.99" in stmts[0].display_sql
        assert stmts[0].params["p1"] == 19.99

    def test_insert_no_data_returns_none(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data=None,
            )
        ]
        stmts = gen.generate_statements(changes)
        assert len(stmts) == 0


class TestDMLGeneratorUpdate:
    def test_basic_update(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={"id": 1},
                changes=[
                    CellChangeSchema(column="email", old_value="old@ex.com", new_value="new@ex.com")
                ],
            )
        ]
        stmts = gen.generate_statements(changes)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert "UPDATE" in stmt.display_sql
        assert '"email"' in stmt.display_sql
        assert "'new@ex.com'" in stmt.display_sql
        assert "WHERE" in stmt.display_sql
        assert '"id" = 1' in stmt.display_sql
        # Parameterized version
        assert ":p1" in stmt.parameterized_sql  # SET value
        assert ":p2" in stmt.parameterized_sql  # WHERE value

    def test_update_multiple_columns(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={"id": 5},
                changes=[
                    CellChangeSchema(column="name", old_value="Old", new_value="New"),
                    CellChangeSchema(column="status", old_value="active", new_value="inactive"),
                ],
            )
        ]
        stmts = gen.generate_statements(changes)
        stmt = stmts[0]
        assert '"name"' in stmt.display_sql
        assert '"status"' in stmt.display_sql
        assert stmt.params["p1"] == "New"
        assert stmt.params["p2"] == "inactive"

    def test_update_no_changes_returns_none(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={"id": 1},
                changes=[],
            )
        ]
        stmts = gen.generate_statements(changes)
        assert len(stmts) == 0


class TestDMLGeneratorDelete:
    def test_basic_delete(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="users",
                primary_key={"id": 42},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert "DELETE FROM" in stmt.display_sql
        assert '"users"' in stmt.display_sql
        assert '"id" = 42' in stmt.display_sql

    def test_delete_composite_pk(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="order_items",
                primary_key={"order_id": 10, "item_id": 3},
            )
        ]
        stmts = gen.generate_statements(changes)
        stmt = stmts[0]
        assert "AND" in stmt.display_sql
        assert '"order_id"' in stmt.display_sql
        assert '"item_id"' in stmt.display_sql


class TestDMLGeneratorOrdering:
    def test_deletes_before_updates_before_inserts(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="t",
                new_row_data={"a": 1},
            ),
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="t",
                primary_key={"id": 1},
            ),
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="t",
                primary_key={"id": 2},
                changes=[CellChangeSchema(column="a", old_value=1, new_value=2)],
            ),
        ]
        stmts = gen.generate_statements(changes)
        assert stmts[0].change_type == ChangeType.DELETE
        assert stmts[1].change_type == ChangeType.UPDATE
        assert stmts[2].change_type == ChangeType.INSERT


class TestDMLGeneratorDialects:
    def test_mysql_backtick_quoting(self):
        gen = DMLGenerator(dialect="mysql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "test"},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert "`users`" in stmts[0].display_sql
        assert "`name`" in stmts[0].display_sql

    def test_mssql_bracket_quoting(self):
        gen = DMLGenerator(dialect="mssql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "test"},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert "[users]" in stmts[0].display_sql
        assert "[name]" in stmts[0].display_sql

    def test_sqlite_double_quote(self):
        gen = DMLGenerator(dialect="sqlite")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "test"},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert '"users"' in stmts[0].display_sql


class TestDMLGeneratorPreviewScript:
    def test_preview_with_transaction(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "test"},
            )
        ]
        script = gen.generate_preview_script(changes, wrap_in_transaction=True)
        assert "BEGIN;" in script
        assert "COMMIT;" in script
        assert "INSERT INTO" in script

    def test_preview_without_transaction(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "test"},
            )
        ]
        script = gen.generate_preview_script(changes, wrap_in_transaction=False)
        assert "BEGIN;" not in script
        assert "COMMIT;" not in script

    def test_mssql_begin_transaction(self):
        gen = DMLGenerator(dialect="mssql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="t",
                new_row_data={"a": 1},
            )
        ]
        script = gen.generate_preview_script(changes, wrap_in_transaction=True)
        assert "BEGIN TRANSACTION;" in script


class TestDMLGeneratorSafety:
    def test_rejects_unsafe_table_name(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users; DROP TABLE users--",
                new_row_data={"name": "evil"},
            )
        ]
        with pytest.raises(ValueError, match="Unsafe identifier"):
            gen.generate_statements(changes)

    def test_rejects_unsafe_column_name(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name; DROP TABLE users": "evil"},
            )
        ]
        with pytest.raises(ValueError, match="Unsafe identifier"):
            gen.generate_statements(changes)

    def test_sql_injection_in_values_is_parameterized(self):
        gen = DMLGenerator(dialect="postgresql")
        evil_value = "'; DROP TABLE users; --"
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": evil_value},
            )
        ]
        stmts = gen.generate_statements(changes)
        # Display SQL should escape quotes
        assert "'';" in stmts[0].display_sql
        # Parameterized SQL should use placeholder
        assert ":p1" in stmts[0].parameterized_sql
        assert stmts[0].params["p1"] == evil_value

    def test_boolean_values(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="flags",
                new_row_data={"is_active": True, "is_deleted": False},
            )
        ]
        stmts = gen.generate_statements(changes)
        assert "TRUE" in stmts[0].display_sql
        assert "FALSE" in stmts[0].display_sql


class TestDMLGeneratorEmptyPKGuards:
    """Verify generator raises on empty primary_key for UPDATE/DELETE."""

    def test_update_without_pk_raises(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={},
                changes=[CellChangeSchema(column="name", old_value="a", new_value="b")],
            )
        ]
        with pytest.raises(ValueError, match="primary key"):
            gen.generate_statements(changes)

    def test_delete_without_pk_raises(self):
        gen = DMLGenerator(dialect="postgresql")
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="users",
                primary_key={},
            )
        ]
        with pytest.raises(ValueError, match="primary key"):
            gen.generate_statements(changes)
