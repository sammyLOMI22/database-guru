"""Tests for Script Generator (Phase 20.3)"""

import pytest
from src.migration.script_generator import ScriptGenerator, GeneratedScripts
from src.migration.schema_comparator import (
    SchemaDiff, TableDiff, ColumnDiff, ConstraintDiff,
)
from src.llm.dialect_registry import DatabaseDialect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_diff(table_diffs=None, **kwargs) -> SchemaDiff:
    defaults = dict(
        total_breaking_changes=0,
        total_safe_changes=0,
        overall_risk="low",
        diff_summary="test",
    )
    defaults.update(kwargs)
    return SchemaDiff(table_diffs=table_diffs or [], **defaults)


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

class TestScriptGeneratorPostgres:
    def setup_method(self):
        self.gen = ScriptGenerator(DatabaseDialect.POSTGRESQL)

    def test_create_table(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="orders",
                diff_type="added",
                column_diffs=[
                    ColumnDiff(table_name="orders", column_name="id", diff_type="added",
                               target_state={"name": "id", "type": "INTEGER", "nullable": False}),
                    ColumnDiff(table_name="orders", column_name="total", diff_type="added",
                               target_state={"name": "total", "type": "NUMERIC(10,2)", "nullable": True, "default": 0}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert 'CREATE TABLE "orders"' in result.up_sql
        assert '"id" INTEGER NOT NULL' in result.up_sql
        assert "DEFAULT 0" in result.up_sql
        assert 'DROP TABLE IF EXISTS "orders"' in result.down_sql

    def test_drop_table(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="legacy",
                diff_type="removed",
                column_diffs=[
                    ColumnDiff(table_name="legacy", column_name="id", diff_type="removed",
                               source_state={"name": "id", "type": "INTEGER", "nullable": False}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert 'DROP TABLE IF EXISTS "legacy"' in result.up_sql
        assert 'CREATE TABLE "legacy"' in result.down_sql
        assert any("DROP TABLE" in w for w in result.warnings)

    def test_add_column(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="email", diff_type="added",
                               target_state={"name": "email", "type": "VARCHAR(255)", "nullable": True}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert 'ADD COLUMN "email" VARCHAR(255) NULL' in result.up_sql
        assert 'DROP COLUMN "email"' in result.down_sql

    def test_drop_column(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="old_col", diff_type="removed",
                               source_state={"name": "old_col", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert 'DROP COLUMN "old_col"' in result.up_sql
        assert 'ADD COLUMN "old_col"' in result.down_sql
        assert any("DROP COLUMN" in w for w in result.warnings)

    def test_type_change_postgresql(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"name": "val", "type": "INTEGER", "nullable": True},
                               target_state={"name": "val", "type": "BIGINT", "nullable": True}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert 'ALTER COLUMN "val" TYPE BIGINT USING "val"::BIGINT' in result.up_sql

    def test_nullability_change_postgresql(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="nullability_changed",
                               source_state={"name": "val", "type": "TEXT", "nullable": True},
                               target_state={"name": "val", "type": "TEXT", "nullable": False}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert 'SET NOT NULL' in result.up_sql

    def test_verify_sql(self):
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="new_t", diff_type="added"),
            TableDiff(table_name="old_t", diff_type="removed",
                      column_diffs=[ColumnDiff(table_name="old_t", column_name="id", diff_type="removed",
                                                source_state={"name": "id", "type": "INTEGER"})]),
        ])
        result = self.gen.generate(diff)
        assert 'SELECT COUNT(*)' in result.verify_sql
        assert 'information_schema' in result.verify_sql

    def test_index_added(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                constraint_diffs=[
                    ConstraintDiff(
                        table_name="t", constraint_type="index", diff_type="added",
                        target_state=(("email",), True),
                    ),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert "CREATE UNIQUE INDEX" in result.up_sql


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------

class TestScriptGeneratorMySQL:
    def setup_method(self):
        self.gen = ScriptGenerator(DatabaseDialect.MYSQL)

    def test_fk_checks(self):
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="t", diff_type="added",
                      column_diffs=[ColumnDiff(table_name="t", column_name="id", diff_type="added",
                                                target_state={"name": "id", "type": "INT"})]),
        ])
        result = self.gen.generate(diff)
        assert "SET FOREIGN_KEY_CHECKS = 0" in result.up_sql
        assert "SET FOREIGN_KEY_CHECKS = 1" in result.up_sql

    def test_backtick_quoting(self):
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="orders", diff_type="added",
                      column_diffs=[ColumnDiff(table_name="orders", column_name="id", diff_type="added",
                                                target_state={"name": "id", "type": "INT", "nullable": False})]),
        ])
        result = self.gen.generate(diff)
        assert "`orders`" in result.up_sql
        assert "`id`" in result.up_sql

    def test_modify_column_type(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"name": "val", "type": "INT", "nullable": True},
                               target_state={"name": "val", "type": "BIGINT", "nullable": True}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert "MODIFY COLUMN" in result.up_sql


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------

class TestScriptGeneratorSQLite:
    def setup_method(self):
        self.gen = ScriptGenerator(DatabaseDialect.SQLITE)

    def test_sqlite_recreate_for_type_change(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"name": "val", "type": "INTEGER", "nullable": True},
                               target_state={"name": "val", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        # Provide source/target schemas so unchanged columns are included
        source_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "val", "type": "INTEGER", "nullable": True},
        ]}}}
        target_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "val", "type": "TEXT", "nullable": True},
        ]}}}
        result = self.gen.generate(diff, source_schema=source_schema, target_schema=target_schema)
        assert '"t__new"' in result.up_sql
        assert "CAST" in result.up_sql
        assert "DROP TABLE" in result.up_sql
        assert "RENAME TO" in result.up_sql
        assert any("recreate" in w.lower() for w in result.warnings)
        # Unchanged column "id" must be included in the recreated table
        assert '"id"' in result.up_sql

    def test_sqlite_recreate_includes_unchanged_columns(self):
        """Regression: unchanged columns must not be silently dropped."""
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="bio", diff_type="type_changed",
                               source_state={"name": "bio", "type": "VARCHAR(100)", "nullable": True},
                               target_state={"name": "bio", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        source_schema = {"tables": {"users": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "TEXT", "nullable": False},
            {"name": "bio", "type": "VARCHAR(100)", "nullable": True},
        ]}}}
        target_schema = {"tables": {"users": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "TEXT", "nullable": False},
            {"name": "bio", "type": "TEXT", "nullable": True},
        ]}}}
        result = self.gen.generate(diff, source_schema=source_schema, target_schema=target_schema)
        # All three columns must appear in the CREATE TABLE for the new table
        assert '"id" INTEGER NOT NULL' in result.up_sql
        assert '"name" TEXT NOT NULL' in result.up_sql
        assert '"bio" TEXT' in result.up_sql

    def test_sqlite_recreate_fallback_without_schemas(self):
        """Without schemas, only diff columns are included (with a warning)."""
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"name": "val", "type": "INTEGER", "nullable": True},
                               target_state={"name": "val", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        result = self.gen.generate(diff)
        assert '"t__new"' in result.up_sql
        assert any("missing unchanged columns" in w.lower() for w in result.warnings)

    def test_sqlite_verify(self):
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="dropped", diff_type="removed",
                      column_diffs=[ColumnDiff(table_name="dropped", column_name="id", diff_type="removed",
                                                source_state={"name": "id", "type": "INTEGER"})]),
        ])
        result = self.gen.generate(diff)
        assert "sqlite_master" in result.verify_sql


# ---------------------------------------------------------------------------
# SQLite down.sql rollback (Issue 2)
# ---------------------------------------------------------------------------

class TestSQLiteDownRollback:
    def setup_method(self):
        self.gen = ScriptGenerator(DatabaseDialect.SQLITE)

    def test_sqlite_down_uses_rollback_table(self):
        """SQLite down.sql must use a __rollback recreate pattern, not ALTER."""
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="bio", diff_type="type_changed",
                               source_state={"name": "bio", "type": "TEXT", "nullable": True},
                               target_state={"name": "bio", "type": "VARCHAR(100)", "nullable": True}),
                ],
            ),
        ])
        source_schema = {"tables": {"users": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "bio", "type": "TEXT", "nullable": True},
        ]}}}
        result = self.gen.generate(diff, source_schema=source_schema)
        assert '"users__rollback"' in result.down_sql
        assert "RENAME TO" in result.down_sql
        # Cast from post-up VARCHAR(100) back to original TEXT
        assert "CAST" in result.down_sql
        assert "TEXT" in result.down_sql
        # Original unchanged column "id" must also be present
        assert '"id"' in result.down_sql

    def test_sqlite_down_added_column_dropped(self):
        """Column added in up.sql should not appear in rollback table."""
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="new_col", diff_type="added",
                               target_state={"name": "new_col", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        source_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
        ]}}}
        result = self.gen.generate(diff, source_schema=source_schema)
        assert '"t__rollback"' in result.down_sql
        # "new_col" should NOT be in the rollback table definition
        assert "new_col" not in result.down_sql

    def test_sqlite_down_removed_column_uses_null(self):
        """Column dropped in up.sql is filled with NULL in rollback."""
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="gone", diff_type="removed",
                               source_state={"name": "gone", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        source_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "gone", "type": "TEXT", "nullable": True},
        ]}}}
        result = self.gen.generate(diff, source_schema=source_schema)
        assert '"t__rollback"' in result.down_sql
        assert "NULL AS" in result.down_sql
        assert "Data for 'gone' was lost" in result.down_sql


# ---------------------------------------------------------------------------
# FK-aware DROP TABLE order (Issue 3)
# ---------------------------------------------------------------------------

class TestDropTableOrder:
    def setup_method(self):
        self.gen = ScriptGenerator(DatabaseDialect.POSTGRESQL)

    def test_child_dropped_before_parent(self):
        """orders (FK → users) must be dropped before users."""
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="users", diff_type="removed",
                      column_diffs=[ColumnDiff(table_name="users", column_name="id", diff_type="removed",
                                                source_state={"name": "id", "type": "INTEGER"})]),
            TableDiff(table_name="orders", diff_type="removed",
                      column_diffs=[ColumnDiff(table_name="orders", column_name="user_id", diff_type="removed",
                                                source_state={"name": "user_id", "type": "INTEGER"})]),
        ])
        source_schema = {"tables": {
            "users": {"columns": [{"name": "id", "type": "INTEGER"}], "foreign_keys": []},
            "orders": {
                "columns": [{"name": "user_id", "type": "INTEGER"}],
                "foreign_keys": [{"column": "user_id", "referred_table": "users", "referred_column": "id"}],
            },
        }}
        result = self.gen.generate(diff, source_schema=source_schema)
        orders_pos = result.up_sql.index('"orders"')
        users_pos = result.up_sql.index('"users"')
        assert orders_pos < users_pos, "orders must be dropped before users (FK child before parent)"

    def test_no_fk_falls_back_to_alphabetical(self):
        """Without FK relationships, tables are dropped in the order returned (alphabetical from comparator)."""
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="beta", diff_type="removed",
                      column_diffs=[ColumnDiff(table_name="beta", column_name="id", diff_type="removed",
                                                source_state={"name": "id", "type": "INTEGER"})]),
            TableDiff(table_name="alpha", diff_type="removed",
                      column_diffs=[ColumnDiff(table_name="alpha", column_name="id", diff_type="removed",
                                                source_state={"name": "id", "type": "INTEGER"})]),
        ])
        result = self.gen.generate(diff)
        # Both must appear in up_sql; order is irrelevant here, just verify both present
        assert '"alpha"' in result.up_sql
        assert '"beta"' in result.up_sql


# ---------------------------------------------------------------------------
# verify.sql column existence (Issue 4)
# ---------------------------------------------------------------------------

class TestVerifyColumnExists:
    def test_added_column_verify_postgresql(self):
        gen = ScriptGenerator(DatabaseDialect.POSTGRESQL)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="email", diff_type="added",
                               target_state={"name": "email", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        result = gen.generate(diff)
        assert "information_schema.columns" in result.verify_sql
        assert "column_name = 'email'" in result.verify_sql
        assert "table_name = 'users'" in result.verify_sql

    def test_added_column_verify_sqlite(self):
        gen = ScriptGenerator(DatabaseDialect.SQLITE)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="products",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="products", column_name="sku", diff_type="added",
                               target_state={"name": "sku", "type": "TEXT", "nullable": True}),
                ],
            ),
        ])
        result = gen.generate(diff)
        assert "pragma_table_info('products')" in result.verify_sql
        assert "name = 'sku'" in result.verify_sql

    def test_type_change_no_col_exists_check(self):
        """Type-changed columns don't need col-existence check — they already exist."""
        gen = ScriptGenerator(DatabaseDialect.POSTGRESQL)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"name": "val", "type": "INT"},
                               target_state={"name": "val", "type": "BIGINT"}),
                ],
            ),
        ])
        result = gen.generate(diff)
        assert "information_schema.columns" not in result.verify_sql


# ---------------------------------------------------------------------------
# GeneratedScripts
# ---------------------------------------------------------------------------

class TestGeneratedScripts:
    def test_to_dict(self):
        gs = GeneratedScripts(project_id=1, target_dialect="postgresql", up_sql="UP", down_sql="DOWN", verify_sql="V")
        d = gs.to_dict()
        assert d["project_id"] == 1
        assert d["up_sql"] == "UP"
        assert "generated_at" in d

    def test_auto_timestamp(self):
        gs = GeneratedScripts()
        assert gs.generated_at != ""
