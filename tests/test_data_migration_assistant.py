"""Tests for Data Migration Assistant (Phase 20.4)"""

import pytest
from src.migration.data_migration_assistant import (
    DataMigrationAssistant,
    DataMigrationPlan,
    TableDataMigration,
    ColumnMapping,
)
from src.migration.schema_comparator import (
    SchemaDiff, TableDiff, ColumnDiff, ConstraintDiff,
)
from src.llm.dialect_registry import DatabaseDialect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_diff(table_diffs=None) -> SchemaDiff:
    return SchemaDiff(
        table_diffs=table_diffs or [],
        total_breaking_changes=0,
        total_safe_changes=0,
        overall_risk="low",
        diff_summary="test",
    )


# ---------------------------------------------------------------------------
# Column mapping from schemas
# ---------------------------------------------------------------------------

class TestDataMigrationFromSchemas:
    def setup_method(self):
        self.assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL)

    def test_only_modified_tables(self):
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="new_t", diff_type="added"),
            TableDiff(table_name="old_t", diff_type="removed"),
        ])
        plan = self.assistant.generate_plan(diff)
        assert plan.total_tables_with_data == 0

    def test_direct_mapping(self):
        """Columns with same type get direct pass-through."""
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="name", diff_type="nullability_changed",
                               source_state={"name": "name", "type": "TEXT", "nullable": True},
                               target_state={"name": "name", "type": "TEXT", "nullable": False}),
                ],
            ),
        ])
        source_schema = {"tables": {"users": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "TEXT", "nullable": True},
        ]}}}
        target_schema = {"tables": {"users": {"columns": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "TEXT", "nullable": False},
        ]}}}

        plan = self.assistant.generate_plan(diff, source_schema, target_schema)
        assert plan.total_tables_with_data == 1
        migration = plan.table_migrations[0]
        # Both columns should be direct mappings
        assert len(migration.column_mappings) == 2
        assert all(m.source_col is not None for m in migration.column_mappings)

    def test_type_changed_adds_cast(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"name": "val", "type": "INTEGER"},
                               target_state={"name": "val", "type": "TEXT"}),
                ],
            ),
        ])
        source_schema = {"tables": {"t": {"columns": [
            {"name": "val", "type": "INTEGER"},
        ]}}}
        target_schema = {"tables": {"t": {"columns": [
            {"name": "val", "type": "TEXT"},
        ]}}}

        plan = self.assistant.generate_plan(diff, source_schema, target_schema)
        migration = plan.table_migrations[0]
        cast_mapping = next(m for m in migration.column_mappings if m.target_col == "val")
        assert "CAST" in cast_mapping.transform_expression

    def test_new_column_with_default(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="new_col", diff_type="added",
                               target_state={"name": "new_col", "type": "TEXT", "nullable": True, "default": "hello"}),
                ],
            ),
        ])
        source_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER"},
        ]}}}
        target_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER"},
            {"name": "new_col", "type": "TEXT", "nullable": True, "default": "hello"},
        ]}}}

        plan = self.assistant.generate_plan(diff, source_schema, target_schema)
        migration = plan.table_migrations[0]
        new_mapping = next(m for m in migration.column_mappings if m.target_col == "new_col")
        assert new_mapping.source_col is None
        assert "'hello'" in new_mapping.transform_expression

    def test_new_not_null_column_no_default_warning(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="required", diff_type="added",
                               target_state={"name": "required", "type": "TEXT", "nullable": False}),
                ],
            ),
        ])
        source_schema = {"tables": {"t": {"columns": [{"name": "id", "type": "INTEGER"}]}}}
        target_schema = {"tables": {"t": {"columns": [
            {"name": "id", "type": "INTEGER"},
            {"name": "required", "type": "TEXT", "nullable": False},
        ]}}}

        plan = self.assistant.generate_plan(diff, source_schema, target_schema)
        migration = plan.table_migrations[0]
        assert any("NOT NULL" in w for w in migration.warnings)


# ---------------------------------------------------------------------------
# Column mapping from diffs only
# ---------------------------------------------------------------------------

class TestDataMigrationFromDiffs:
    def setup_method(self):
        self.assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL)

    def test_added_column_nullable(self):
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
        plan = self.assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        new_mapping = next(m for m in migration.column_mappings if m.target_col == "new_col")
        assert "NULL" in new_mapping.transform_expression

    def test_removed_column_skipped(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="old_col", diff_type="removed",
                               source_state={"name": "old_col", "type": "TEXT"}),
                    ColumnDiff(table_name="t", column_name="kept_col", diff_type="nullability_changed",
                               source_state={"type": "TEXT"}, target_state={"type": "TEXT"}),
                ],
            ),
        ])
        plan = self.assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        col_names = [m.target_col for m in migration.column_mappings]
        assert "old_col" not in col_names

    def test_type_changed_adds_cast(self):
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="val", diff_type="type_changed",
                               source_state={"type": "INTEGER"},
                               target_state={"name": "val", "type": "BIGINT"}),
                ],
            ),
        ])
        plan = self.assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        m = migration.column_mappings[0]
        assert "CAST" in m.transform_expression
        assert "BIGINT" in m.transform_expression


# ---------------------------------------------------------------------------
# SQL generation
# ---------------------------------------------------------------------------

class TestSQLGeneration:
    def test_insert_sql_uses_staging_table(self):
        """INSERT should target a staging table, not the source table."""
        assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="name", diff_type="nullability_changed",
                               source_state={"type": "TEXT"}, target_state={"type": "TEXT"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert migration.source_table == "users"
        assert migration.target_table == "users__new"
        assert '"users__new"' in migration.insert_sql
        assert 'FROM "users"' in migration.insert_sql

    def test_batched_sql(self):
        assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL, batch_size=500)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="a", diff_type="default_changed",
                               source_state={"type": "TEXT"}, target_state={"type": "TEXT"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert "LIMIT 500" in migration.batched_insert_sql
        assert "OFFSET" in migration.batched_insert_sql
        # PostgreSQL uses ctid for ordering
        assert "ctid" in migration.batched_insert_sql
        # Should reference staging table for INSERT and source for SELECT
        assert '"t__new"' in migration.batched_insert_sql
        assert 'FROM "t"' in migration.batched_insert_sql

    def test_batched_sql_includes_loop_comment(self):
        """Batched SQL should include a comment explaining the loop pattern."""
        assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL, batch_size=1000)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="a", diff_type="default_changed",
                               source_state={"type": "TEXT"}, target_state={"type": "TEXT"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        # Comment should mention incrementing OFFSET and batch size
        assert "OFFSET" in migration.batched_insert_sql
        assert "1000" in migration.batched_insert_sql
        assert "-- Batch template" in migration.batched_insert_sql

    def test_count_verify_compares_source_and_staging(self):
        """Verify SQL should compare source table vs staging table counts."""
        assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="a", diff_type="default_changed",
                               source_state={"type": "TEXT"}, target_state={"type": "TEXT"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert "COUNT(*)" in migration.count_verify_sql
        assert '"t"' in migration.count_verify_sql
        assert '"t__new"' in migration.count_verify_sql


# ---------------------------------------------------------------------------
# MySQL quoting
# ---------------------------------------------------------------------------

class TestMySQLQuoting:
    def test_backtick_quoting(self):
        assistant = DataMigrationAssistant(DatabaseDialect.MYSQL)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="orders",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="orders", column_name="total", diff_type="default_changed",
                               source_state={"type": "DECIMAL"}, target_state={"type": "DECIMAL"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert "`orders__new`" in migration.insert_sql
        assert "`total`" in migration.insert_sql
        assert "FROM `orders`" in migration.insert_sql


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestDataMigrationSerialization:
    def test_plan_to_dict(self):
        plan = DataMigrationPlan(
            project_id=1,
            table_migrations=[
                TableDataMigration(
                    source_table="t",
                    target_table="t",
                    column_mappings=[ColumnMapping(source_col="a", target_col="a", transform_expression='"a"')],
                    insert_sql="INSERT ...",
                ),
            ],
            batch_size=1000,
            recommended_order=["t"],
            total_tables_with_data=1,
        )
        d = plan.to_dict()
        assert d["project_id"] == 1
        assert len(d["table_migrations"]) == 1
        assert d["table_migrations"][0]["column_mappings"][0]["source_col"] == "a"

    def test_format_default(self):
        assistant = DataMigrationAssistant(DatabaseDialect.POSTGRESQL)
        assert assistant._format_default(None) == "NULL"
        assert assistant._format_default(True) == "TRUE"
        assert assistant._format_default(False) == "FALSE"
        assert assistant._format_default(42) == "42"
        assert assistant._format_default("hello") == "'hello'"


# ---------------------------------------------------------------------------
# Oracle batch offset correctness
# ---------------------------------------------------------------------------

class TestOracleBatchOffset:
    def test_oracle_batch_has_offset(self):
        """Oracle batch template must use OFFSET to avoid infinite loop."""
        assistant = DataMigrationAssistant(DatabaseDialect.ORACLE, batch_size=500)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="a", diff_type="default_changed",
                               source_state={"type": "NUMBER"}, target_state={"type": "NUMBER"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert "OFFSET" in migration.batched_insert_sql
        assert "FETCH NEXT 500 ROWS ONLY" in migration.batched_insert_sql
        assert "ORDER BY ROWID" in migration.batched_insert_sql

    def test_oracle_insert_uses_double_quotes(self):
        assistant = DataMigrationAssistant(DatabaseDialect.ORACLE)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="orders",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="orders", column_name="total", diff_type="default_changed",
                               source_state={"type": "NUMBER"}, target_state={"type": "NUMBER"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert '"orders__new"' in migration.insert_sql
        assert '"total"' in migration.insert_sql


# ---------------------------------------------------------------------------
# MSSQL batch
# ---------------------------------------------------------------------------

class TestMSSQLBatch:
    def test_mssql_batch_has_offset_fetch(self):
        assistant = DataMigrationAssistant(DatabaseDialect.MSSQL, batch_size=1000)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="t",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="t", column_name="a", diff_type="default_changed",
                               source_state={"type": "INT"}, target_state={"type": "INT"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert "OFFSET" in migration.batched_insert_sql
        assert "FETCH NEXT 1000 ROWS ONLY" in migration.batched_insert_sql

    def test_mssql_bracket_quoting(self):
        assistant = DataMigrationAssistant(DatabaseDialect.MSSQL)
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="orders",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="orders", column_name="total", diff_type="default_changed",
                               source_state={"type": "INT"}, target_state={"type": "INT"}),
                ],
            ),
        ])
        plan = assistant.generate_plan(diff)
        migration = plan.table_migrations[0]
        assert "[orders__new]" in migration.insert_sql
        assert "[total]" in migration.insert_sql
