"""Tests for BackupScriptGenerator (Phase 20)"""

import pytest
from src.migration.backup_script_generator import BackupScriptGenerator, BackupScripts
from src.llm.dialect_registry import DatabaseDialect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_schema(tables=None, **kwargs):
    schema = {"tables": tables or {}, "relationships": [], "summary": {}}
    schema.update(kwargs)
    return schema


def _table(columns, primary_keys=None, foreign_keys=None, indexes=None):
    return {
        "columns": columns,
        "primary_keys": primary_keys or [],
        "foreign_keys": foreign_keys or [],
        "indexes": indexes or [],
    }


# ---------------------------------------------------------------------------
# BackupScripts dataclass
# ---------------------------------------------------------------------------

class TestBackupScripts:
    def test_to_dict(self):
        bs = BackupScripts(connection_id=1, connection_name="test", dialect="postgresql")
        d = bs.to_dict()
        assert d["connection_id"] == 1
        assert d["connection_name"] == "test"
        assert "generated_at" in d

    def test_auto_timestamp(self):
        bs = BackupScripts()
        assert bs.generated_at != ""


# ---------------------------------------------------------------------------
# Empty schema
# ---------------------------------------------------------------------------

class TestEmptySchema:
    def test_empty_tables(self):
        gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)
        result = gen.generate(_simple_schema(), connection_name="test_db")
        assert result.table_count == 0
        assert any("No tables found" in w for w in result.warnings)
        assert "test_db" in result.backup_sql

    def test_table_with_no_columns_skipped(self):
        gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)
        schema = _simple_schema({"empty_t": _table([])})
        result = gen.generate(schema)
        assert "skipped" in result.backup_sql.lower()
        assert any("no columns" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

class TestPostgresBackup:
    def setup_method(self):
        self.gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)

    def test_create_table(self):
        schema = _simple_schema({
            "users": _table(
                [{"name": "id", "type": "INTEGER", "nullable": False},
                 {"name": "email", "type": "VARCHAR(255)", "nullable": True}],
                primary_keys=["id"],
            )
        })
        result = self.gen.generate(schema, connection_name="mydb")
        assert 'CREATE TABLE IF NOT EXISTS "users"' in result.backup_sql
        assert '"id" INTEGER NOT NULL' in result.backup_sql
        assert '"email" VARCHAR(255)' in result.backup_sql
        assert 'PRIMARY KEY ("id")' in result.backup_sql

    def test_restore_drops_table(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert 'DROP TABLE IF EXISTS "t"' in result.restore_sql

    def test_verify_uses_information_schema(self):
        schema = _simple_schema({"t": _table([{"name": "a", "type": "TEXT"}])})
        result = self.gen.generate(schema)
        assert "information_schema.columns" in result.verify_sql
        assert "expected: 1" in result.verify_sql

    def test_double_quote_escaping(self):
        schema = _simple_schema({
            'weird"name': _table([{"name": "id", "type": "INT", "nullable": False}])
        })
        result = self.gen.generate(schema)
        assert '"weird""name"' in result.backup_sql

    def test_foreign_key_in_ddl(self):
        schema = _simple_schema({
            "orders": _table(
                [{"name": "id", "type": "INT"}, {"name": "uid", "type": "INT"}],
                foreign_keys=[{"column": "uid", "referred_table": "users", "referred_column": "id"}],
            )
        })
        result = self.gen.generate(schema)
        assert 'FOREIGN KEY ("uid") REFERENCES "users" ("id")' in result.backup_sql

    def test_default_value(self):
        schema = _simple_schema({
            "t": _table([{"name": "val", "type": "INT", "nullable": True, "default": 42}])
        })
        result = self.gen.generate(schema)
        assert "DEFAULT 42" in result.backup_sql

    def test_index_generated(self):
        schema = _simple_schema({
            "t": _table(
                [{"name": "email", "type": "TEXT"}],
                indexes=[{"name": "idx_email", "columns": ["email"], "unique": True}],
            )
        })
        result = self.gen.generate(schema)
        assert "CREATE UNIQUE INDEX" in result.backup_sql
        assert '"email"' in result.backup_sql

    def test_pk_index_skipped(self):
        schema = _simple_schema({
            "t": _table(
                [{"name": "id", "type": "INT"}],
                primary_keys=["id"],
                indexes=[{"name": "pk_idx", "columns": ["id"], "unique": True}],
            )
        })
        result = self.gen.generate(schema)
        assert "CREATE UNIQUE INDEX" not in result.backup_sql


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------

class TestMySQLBackup:
    def setup_method(self):
        self.gen = BackupScriptGenerator(DatabaseDialect.MYSQL)

    def test_fk_checks_wrap(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "SET FOREIGN_KEY_CHECKS = 0" in result.backup_sql
        assert "SET FOREIGN_KEY_CHECKS = 1" in result.backup_sql
        assert "SET FOREIGN_KEY_CHECKS = 0" in result.restore_sql
        assert "SET FOREIGN_KEY_CHECKS = 1" in result.restore_sql

    def test_backtick_quoting(self):
        schema = _simple_schema({"orders": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "`orders`" in result.backup_sql
        assert "`id`" in result.backup_sql


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------

class TestSQLiteBackup:
    def setup_method(self):
        self.gen = BackupScriptGenerator(DatabaseDialect.SQLITE)

    def test_if_not_exists(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "CREATE TABLE IF NOT EXISTS" in result.backup_sql

    def test_verify_uses_pragma(self):
        schema = _simple_schema({"t": _table([{"name": "a", "type": "TEXT"}])})
        result = self.gen.generate(schema)
        assert "pragma_table_info" in result.verify_sql


# ---------------------------------------------------------------------------
# MSSQL
# ---------------------------------------------------------------------------

class TestMSSQLBackup:
    def setup_method(self):
        self.gen = BackupScriptGenerator(DatabaseDialect.MSSQL)

    def test_if_object_id_with_begin_end(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "IF OBJECT_ID" in result.backup_sql
        assert "BEGIN" in result.backup_sql
        assert "END" in result.backup_sql

    def test_bracket_quoting(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "[t]" in result.backup_sql
        assert "[id]" in result.backup_sql

    def test_bracket_escaping(self):
        schema = _simple_schema({"t]x": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "[t]]x]" in result.backup_sql

    def test_restore_uses_if_object_id(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "IF OBJECT_ID" in result.restore_sql
        assert "DROP TABLE" in result.restore_sql

    def test_sp_msforeachtable_in_backup(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "sp_MSforeachtable" in result.backup_sql

    def test_index_exists_guard(self):
        schema = _simple_schema({
            "t": _table(
                [{"name": "col", "type": "INT"}],
                indexes=[{"name": "idx_col", "columns": ["col"], "unique": False}],
            )
        })
        result = self.gen.generate(schema)
        assert "sys.indexes" in result.backup_sql


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------

class TestOracleBackup:
    def setup_method(self):
        self.gen = BackupScriptGenerator(DatabaseDialect.ORACLE)

    def test_no_if_not_exists_on_create_table(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        # Oracle CREATE TABLE should not have IF NOT EXISTS (only indexes may)
        assert 'CREATE TABLE IF NOT EXISTS' not in result.backup_sql
        assert 'CREATE TABLE "t"' in result.backup_sql

    def test_restore_uses_execute_immediate(self):
        schema = _simple_schema({"t": _table([{"name": "id", "type": "INT"}])})
        result = self.gen.generate(schema)
        assert "EXECUTE IMMEDIATE" in result.restore_sql
        assert "ORA-00942" in result.restore_sql

    def test_verify_uses_user_tab_columns(self):
        schema = _simple_schema({"t": _table([{"name": "a", "type": "TEXT"}])})
        result = self.gen.generate(schema)
        assert "user_tab_columns" in result.verify_sql


# ---------------------------------------------------------------------------
# Table ordering (FK-aware)
# ---------------------------------------------------------------------------

class TestTableOrdering:
    def test_parent_before_child_in_backup(self):
        """parent must be created before child."""
        gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)
        schema = _simple_schema({
            "child": _table(
                [{"name": "id", "type": "INT"}, {"name": "pid", "type": "INT"}],
                foreign_keys=[{"column": "pid", "referred_table": "parent", "referred_column": "id"}],
            ),
            "parent": _table([{"name": "id", "type": "INT"}]),
        })
        result = gen.generate(schema)
        parent_pos = result.backup_sql.index('"parent"')
        child_pos = result.backup_sql.index('"child"')
        assert parent_pos < child_pos

    def test_child_before_parent_in_restore(self):
        """child must be dropped before parent."""
        gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)
        schema = _simple_schema({
            "child": _table(
                [{"name": "id", "type": "INT"}, {"name": "pid", "type": "INT"}],
                foreign_keys=[{"column": "pid", "referred_table": "parent", "referred_column": "id"}],
            ),
            "parent": _table([{"name": "id", "type": "INT"}]),
        })
        result = gen.generate(schema)
        child_pos = result.restore_sql.index('"child"')
        parent_pos = result.restore_sql.index('"parent"')
        assert child_pos < parent_pos

    def test_circular_fk_handled(self):
        """Circular FKs should not crash — tables are appended at end."""
        gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)
        schema = _simple_schema({
            "a": _table(
                [{"name": "id", "type": "INT"}, {"name": "bid", "type": "INT"}],
                foreign_keys=[{"column": "bid", "referred_table": "b", "referred_column": "id"}],
            ),
            "b": _table(
                [{"name": "id", "type": "INT"}, {"name": "aid", "type": "INT"}],
                foreign_keys=[{"column": "aid", "referred_table": "a", "referred_column": "id"}],
            ),
        })
        result = gen.generate(schema)
        assert '"a"' in result.backup_sql
        assert '"b"' in result.backup_sql


# ---------------------------------------------------------------------------
# Extended objects
# ---------------------------------------------------------------------------

class TestExtendedObjectBackup:
    def setup_method(self):
        self.gen = BackupScriptGenerator(DatabaseDialect.POSTGRESQL)

    def test_enum_backup(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            enums=[{"name": "status_type", "values": ["active", "inactive"]}],
        )
        result = self.gen.generate(schema)
        assert "CREATE TYPE" in result.backup_sql
        assert "'active'" in result.backup_sql
        assert "DROP TYPE IF EXISTS" in result.restore_sql

    def test_view_backup(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            views=[{"name": "v_test", "definition": "SELECT 1"}],
        )
        result = self.gen.generate(schema)
        assert "CREATE VIEW" in result.backup_sql
        assert "SELECT 1" in result.backup_sql
        assert "DROP VIEW IF EXISTS" in result.restore_sql

    def test_view_without_definition_warns(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            views=[{"name": "v_broken"}],
        )
        result = self.gen.generate(schema)
        assert any("definition not available" in w for w in result.warnings)

    def test_sequence_backup(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            sequences=[{"name": "seq_id", "increment": 1, "start_value": 100}],
        )
        result = self.gen.generate(schema)
        assert "CREATE SEQUENCE" in result.backup_sql
        assert "START WITH 100" in result.backup_sql
        assert "DROP SEQUENCE IF EXISTS" in result.restore_sql

    def test_check_constraint_backup(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            check_constraints=[{"table_name": "t", "constraint_name": "ck_positive", "definition": "id > 0"}],
        )
        result = self.gen.generate(schema)
        assert "ADD CONSTRAINT" in result.backup_sql
        assert "id > 0" in result.backup_sql

    def test_routine_backup(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            routines=[{"name": "my_func", "type": "function", "definition": "CREATE FUNCTION my_func() RETURNS INT"}],
        )
        result = self.gen.generate(schema)
        assert "my_func" in result.backup_sql
        assert "DROP FUNCTION IF EXISTS" in result.restore_sql

    def test_trigger_backup(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            triggers=[{"name": "trg_test", "table_name": "t", "definition": "CREATE TRIGGER trg_test BEFORE INSERT ON t"}],
        )
        result = self.gen.generate(schema)
        assert "trg_test" in result.backup_sql
        assert "DROP TRIGGER IF EXISTS" in result.restore_sql

    def test_verify_views(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            views=[{"name": "v_test", "definition": "SELECT 1"}],
        )
        result = self.gen.generate(schema)
        assert "information_schema.views" in result.verify_sql

    def test_verify_sequences(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            sequences=[{"name": "seq_id"}],
        )
        result = self.gen.generate(schema)
        assert "pg_sequences" in result.verify_sql

    def test_verify_routines(self):
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            routines=[{"name": "my_func", "type": "function", "definition": "..."}],
        )
        result = self.gen.generate(schema)
        assert "information_schema.routines" in result.verify_sql


# ---------------------------------------------------------------------------
# Oracle extended object restore
# ---------------------------------------------------------------------------

class TestOracleExtendedRestore:
    def test_oracle_trigger_drop(self):
        gen = BackupScriptGenerator(DatabaseDialect.ORACLE)
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            triggers=[{"name": "trg_test", "table_name": "t", "definition": "..."}],
        )
        result = gen.generate(schema)
        assert "DROP TRIGGER" in result.restore_sql
        assert "EXCEPTION WHEN OTHERS THEN NULL" in result.restore_sql

    def test_oracle_routine_drop(self):
        gen = BackupScriptGenerator(DatabaseDialect.ORACLE)
        schema = _simple_schema(
            {"t": _table([{"name": "id", "type": "INT"}])},
            routines=[{"name": "my_proc", "type": "procedure", "definition": "..."}],
        )
        result = gen.generate(schema)
        assert "DROP PROCEDURE" in result.restore_sql
