"""Tests for Schema Comparator (Phase 20.1)"""

import pytest
from src.migration.schema_comparator import (
    SchemaComparator,
    SchemaDiff,
    TableDiff,
    ColumnDiff,
    ConstraintDiff,
    ViewDiff,
    SequenceDiff,
    CheckConstraintDiff,
    RoutineDiff,
    TriggerDiff,
    EnumDiff,
    _normalize_type,
    _extract_base_type,
    _extract_length,
    _is_type_narrowing,
    _max_risk,
)


# ---------------------------------------------------------------------------
# Type normalization helpers
# ---------------------------------------------------------------------------

class TestNormalizeType:
    def test_empty(self):
        assert _normalize_type("") == ""
        assert _normalize_type(None) == ""

    def test_case_insensitive(self):
        assert _normalize_type("VARCHAR(255)") == "varchar(255)"
        assert _normalize_type("INTEGER") == "integer"

    def test_synonyms(self):
        assert _normalize_type("CHARACTER VARYING") == "varchar"
        assert _normalize_type("int4") == "integer"
        assert _normalize_type("int8") == "bigint"
        assert _normalize_type("bool") == "boolean"
        assert _normalize_type("serial") == "integer"
        assert _normalize_type("bigserial") == "bigint"
        assert _normalize_type("timestamptz") == "timestamp with time zone"

    def test_preserves_params(self):
        assert _normalize_type("varchar(100)") == "varchar(100)"
        assert _normalize_type("numeric(10,2)") == "numeric(10,2)"


class TestExtractBaseType:
    def test_no_params(self):
        assert _extract_base_type("integer") == "integer"

    def test_with_params(self):
        assert _extract_base_type("varchar(255)") == "varchar"
        assert _extract_base_type("numeric(10,2)") == "numeric"


class TestExtractLength:
    def test_no_params(self):
        assert _extract_length("integer") is None

    def test_simple(self):
        assert _extract_length("varchar(255)") == 255

    def test_precision_scale(self):
        assert _extract_length("numeric(10,2)") == 10

    def test_invalid(self):
        assert _extract_length("varchar(abc)") is None


class TestIsTypeNarrowing:
    def test_same_type_wider(self):
        assert not _is_type_narrowing("varchar(100)", "varchar(255)")

    def test_same_type_narrower(self):
        assert _is_type_narrowing("varchar(255)", "varchar(100)")

    def test_integer_to_bigint(self):
        assert not _is_type_narrowing("integer", "bigint")

    def test_bigint_to_integer(self):
        assert _is_type_narrowing("bigint", "integer")

    def test_text_to_integer(self):
        assert _is_type_narrowing("text", "integer")

    def test_unknown_types(self):
        # Unknown types default to non-narrowing (avoids false high-risk alerts)
        assert not _is_type_narrowing("custom_type", "other_type")


# ---------------------------------------------------------------------------
# Risk helper
# ---------------------------------------------------------------------------

class TestMaxRisk:
    def test_empty(self):
        assert _max_risk([]) == "low"

    def test_single(self):
        assert _max_risk(["high"]) == "high"

    def test_mixed(self):
        assert _max_risk(["low", "medium", "high"]) == "high"

    def test_critical_wins(self):
        assert _max_risk(["low", "critical", "medium"]) == "critical"


# ---------------------------------------------------------------------------
# SchemaComparator
# ---------------------------------------------------------------------------

class TestSchemaComparator:
    def setup_method(self):
        self.comp = SchemaComparator()

    def _schema(self, tables: dict) -> dict:
        return {"tables": tables, "relationships": [], "summary": {}}

    def test_identical_schemas(self):
        schema = self._schema({
            "users": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": [],
            }
        })
        diff = self.comp.compare(schema, schema)
        assert len(diff.table_diffs) == 0
        assert diff.overall_risk == "none"
        assert diff.diff_summary == "No differences found"

    def test_table_added(self):
        source = self._schema({})
        target = self._schema({
            "orders": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "total", "type": "NUMERIC(10,2)", "nullable": True},
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        assert len(diff.table_diffs) == 1
        td = diff.table_diffs[0]
        assert td.table_name == "orders"
        assert td.diff_type == "added"
        assert td.risk_level == "low"
        assert len(td.column_diffs) == 2

    def test_table_removed(self):
        source = self._schema({
            "legacy": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({})
        diff = self.comp.compare(source, target)
        assert len(diff.table_diffs) == 1
        td = diff.table_diffs[0]
        assert td.diff_type == "removed"
        assert td.risk_level == "critical"
        assert diff.overall_risk == "critical"
        assert diff.total_breaking_changes >= 1

    def test_column_added(self):
        source = self._schema({
            "users": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "users": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "email", "type": "VARCHAR(255)", "nullable": True},
                ],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        assert len(diff.table_diffs) == 1
        td = diff.table_diffs[0]
        assert td.diff_type == "modified"
        assert len(td.column_diffs) == 1
        cd = td.column_diffs[0]
        assert cd.diff_type == "added"
        assert cd.column_name == "email"
        assert cd.risk_level == "low"

    def test_not_null_column_added_without_default(self):
        source = self._schema({
            "users": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "users": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "name", "type": "VARCHAR(100)", "nullable": False},
                ],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.risk_level == "medium"

    def test_column_removed(self):
        source = self._schema({
            "users": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "legacy_col", "type": "TEXT", "nullable": True},
                ],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "users": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.diff_type == "removed"
        assert cd.is_breaking is True
        assert cd.risk_level == "critical"

    def test_type_changed_widening(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "INTEGER", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "BIGINT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.diff_type == "type_changed"
        assert cd.is_breaking is False
        assert cd.risk_level == "low"

    def test_type_changed_narrowing(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "BIGINT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "SMALLINT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.diff_type == "type_changed"
        assert cd.is_breaking is True
        assert cd.risk_level == "high"

    def test_nullability_changed_to_not_null(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.diff_type == "nullability_changed"
        assert cd.is_breaking is True
        assert cd.risk_level == "high"

    def test_nullability_changed_to_nullable(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.is_breaking is False
        assert cd.risk_level == "low"

    def test_default_changed(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": True, "default": "old"}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": True, "default": "new"}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cd = diff.table_diffs[0].column_diffs[0]
        assert cd.diff_type == "default_changed"
        assert cd.risk_level == "low"

    def test_pk_changed(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": ["id"],
                "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": ["id", "name"],
                "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cds = diff.table_diffs[0].constraint_diffs
        assert len(cds) == 1
        assert cds[0].constraint_type == "primary_key"
        assert cds[0].risk_level == "critical"

    def test_fk_added(self):
        source = self._schema({
            "orders": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "orders": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [],
                "foreign_keys": [{"column": "user_id", "referred_table": "users", "referred_column": "id"}],
                "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        cds = diff.table_diffs[0].constraint_diffs
        assert any(cd.constraint_type == "foreign_key" and cd.diff_type == "added" for cd in cds)

    def test_index_added_removed(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "a", "type": "TEXT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [],
                "indexes": [{"name": "idx_old", "columns": ["a"], "unique": False}],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "a", "type": "TEXT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [],
                "indexes": [{"name": "idx_new", "columns": ["a"], "unique": True}],
            }
        })
        diff = self.comp.compare(source, target)
        cds = diff.table_diffs[0].constraint_diffs
        assert any(cd.diff_type == "added" for cd in cds)
        assert any(cd.diff_type == "removed" for cd in cds)

    def test_empty_diff(self):
        source = self._schema({})
        target = self._schema({})
        diff = self.comp.compare(source, target)
        assert diff.table_diffs == []
        assert diff.overall_risk == "none"

    def test_summary_text(self):
        source = self._schema({
            "a": {"columns": [], "primary_keys": [], "foreign_keys": [], "indexes": []},
        })
        target = self._schema({
            "a": {"columns": [], "primary_keys": [], "foreign_keys": [], "indexes": []},
            "b": {"columns": [], "primary_keys": [], "foreign_keys": [], "indexes": []},
        })
        diff = self.comp.compare(source, target)
        assert "1 table added" in diff.diff_summary

    def test_to_dict(self):
        schema = self._schema({
            "t": {
                "columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(schema, self._schema({}))
        d = diff.to_dict()
        assert "table_diffs" in d
        assert "overall_risk" in d
        assert isinstance(d["table_diffs"], list)

    def test_connection_ids_and_fingerprints(self):
        schema = self._schema({})
        diff = self.comp.compare(
            schema, schema,
            source_connection_id=1,
            target_connection_id=2,
            source_fingerprint="abc",
            target_fingerprint="def",
        )
        assert diff.source_connection_id == 1
        assert diff.target_connection_id == 2
        assert diff.source_fingerprint == "abc"
        assert diff.target_fingerprint == "def"

    def test_synonym_normalization_prevents_false_positive(self):
        """CHARACTER VARYING and varchar should not produce a type_changed diff."""
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "CHARACTER VARYING", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "varchar", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        assert len(diff.table_diffs) == 0

    def test_none_default_not_false_positive(self):
        """None vs None defaults should not produce a diff (str(None) fix)."""
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": True, "default": None}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "TEXT", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        # Both defaults are None, should have no diff
        assert len(diff.table_diffs) == 0


# ---------------------------------------------------------------------------
# Extended object diffs (views, sequences, enums, routines, triggers, checks)
# ---------------------------------------------------------------------------

class TestExtendedObjectDiffs:
    def setup_method(self):
        self.comp = SchemaComparator()

    def _schema(self, tables=None, **kwargs):
        s = {"tables": tables or {}, "relationships": [], "summary": {}}
        s.update(kwargs)
        return s

    # --- Views ---

    def test_view_added(self):
        source = self._schema()
        target = self._schema(views=[{"name": "v_test", "definition": "SELECT 1"}])
        diff = self.comp.compare(source, target)
        assert len(diff.view_diffs) == 1
        assert diff.view_diffs[0].view_name == "v_test"
        assert diff.view_diffs[0].diff_type == "added"

    def test_view_removed(self):
        source = self._schema(views=[{"name": "v_old", "definition": "SELECT 1"}])
        target = self._schema()
        diff = self.comp.compare(source, target)
        assert len(diff.view_diffs) == 1
        assert diff.view_diffs[0].diff_type == "removed"

    def test_view_modified(self):
        source = self._schema(views=[{"name": "v1", "definition": "SELECT 1"}])
        target = self._schema(views=[{"name": "v1", "definition": "SELECT 2"}])
        diff = self.comp.compare(source, target)
        assert len(diff.view_diffs) == 1
        assert diff.view_diffs[0].diff_type == "modified"

    def test_view_unchanged(self):
        source = self._schema(views=[{"name": "v1", "definition": "SELECT 1"}])
        target = self._schema(views=[{"name": "v1", "definition": "SELECT 1"}])
        diff = self.comp.compare(source, target)
        assert len(diff.view_diffs) == 0

    # --- Sequences ---

    def test_sequence_added(self):
        source = self._schema()
        target = self._schema(sequences=[{"name": "seq_id", "increment": 1}])
        diff = self.comp.compare(source, target)
        assert len(diff.sequence_diffs) == 1
        assert diff.sequence_diffs[0].diff_type == "added"

    def test_sequence_removed(self):
        source = self._schema(sequences=[{"name": "seq_old"}])
        target = self._schema()
        diff = self.comp.compare(source, target)
        assert len(diff.sequence_diffs) == 1
        assert diff.sequence_diffs[0].diff_type == "removed"

    # --- Enums ---

    def test_enum_added(self):
        source = self._schema()
        target = self._schema(enums=[{"name": "status", "values": ["a", "b"]}])
        diff = self.comp.compare(source, target)
        assert len(diff.enum_diffs) == 1
        assert diff.enum_diffs[0].diff_type == "added"

    def test_enum_values_modified(self):
        source = self._schema(enums=[{"name": "status", "values": ["a", "b"]}])
        target = self._schema(enums=[{"name": "status", "values": ["a", "b", "c"]}])
        diff = self.comp.compare(source, target)
        assert len(diff.enum_diffs) == 1
        assert diff.enum_diffs[0].diff_type == "modified"

    def test_enum_unchanged(self):
        source = self._schema(enums=[{"name": "status", "values": ["a", "b"]}])
        target = self._schema(enums=[{"name": "status", "values": ["a", "b"]}])
        diff = self.comp.compare(source, target)
        assert len(diff.enum_diffs) == 0

    # --- Routines ---

    def test_routine_added(self):
        source = self._schema()
        target = self._schema(routines=[{"name": "my_func", "type": "function", "definition": "CREATE..."}])
        diff = self.comp.compare(source, target)
        assert len(diff.routine_diffs) == 1
        assert diff.routine_diffs[0].diff_type == "added"

    def test_routine_removed(self):
        source = self._schema(routines=[{"name": "old_proc", "type": "procedure", "definition": "..."}])
        target = self._schema()
        diff = self.comp.compare(source, target)
        assert len(diff.routine_diffs) == 1
        assert diff.routine_diffs[0].diff_type == "removed"

    # --- Triggers ---

    def test_trigger_added(self):
        source = self._schema()
        target = self._schema(triggers=[{"name": "trg_test", "table_name": "t", "definition": "..."}])
        diff = self.comp.compare(source, target)
        assert len(diff.trigger_diffs) == 1
        assert diff.trigger_diffs[0].diff_type == "added"

    # --- Check constraints ---

    def test_check_constraint_added(self):
        source = self._schema()
        target = self._schema(check_constraints=[
            {"table_name": "t", "constraint_name": "ck_pos", "definition": "val > 0"}
        ])
        diff = self.comp.compare(source, target)
        assert len(diff.check_constraint_diffs) == 1
        assert diff.check_constraint_diffs[0].diff_type == "added"

    def test_check_constraint_removed(self):
        source = self._schema(check_constraints=[
            {"table_name": "t", "constraint_name": "ck_old", "definition": "val > 0"}
        ])
        target = self._schema()
        diff = self.comp.compare(source, target)
        assert len(diff.check_constraint_diffs) == 1
        assert diff.check_constraint_diffs[0].diff_type == "removed"


# ---------------------------------------------------------------------------
# SchemaDiff.from_dict() round-trip
# ---------------------------------------------------------------------------

class TestSchemaDiffRoundTrip:
    def setup_method(self):
        self.comp = SchemaComparator()

    def _schema(self, tables=None, **kwargs):
        s = {"tables": tables or {}, "relationships": [], "summary": {}}
        s.update(kwargs)
        return s

    def test_table_diff_round_trip(self):
        source = self._schema({
            "t": {
                "columns": [{"name": "val", "type": "INTEGER", "nullable": True}],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })
        target = self._schema({
            "t": {
                "columns": [
                    {"name": "val", "type": "BIGINT", "nullable": False},
                    {"name": "new_col", "type": "TEXT", "nullable": True},
                ],
                "primary_keys": ["val"],
                "foreign_keys": [], "indexes": [],
            }
        })
        diff = self.comp.compare(source, target)
        d = diff.to_dict()
        restored = SchemaDiff.from_dict(d)

        assert restored.overall_risk == diff.overall_risk
        assert restored.total_breaking_changes == diff.total_breaking_changes
        assert len(restored.table_diffs) == len(diff.table_diffs)
        assert restored.table_diffs[0].table_name == diff.table_diffs[0].table_name
        assert len(restored.table_diffs[0].column_diffs) == len(diff.table_diffs[0].column_diffs)
        assert len(restored.table_diffs[0].constraint_diffs) == len(diff.table_diffs[0].constraint_diffs)

    def test_extended_diffs_round_trip(self):
        source = self._schema(
            views=[{"name": "v1", "definition": "SELECT 1"}],
            enums=[{"name": "e1", "values": ["a"]}],
            sequences=[{"name": "s1"}],
            routines=[{"name": "r1", "type": "function", "definition": "..."}],
            triggers=[{"name": "t1", "table_name": "t", "definition": "..."}],
            check_constraints=[{"table_name": "t", "constraint_name": "ck1", "definition": "x > 0"}],
        )
        target = self._schema()
        diff = self.comp.compare(source, target)
        d = diff.to_dict()
        restored = SchemaDiff.from_dict(d)

        assert len(restored.view_diffs) == len(diff.view_diffs)
        assert len(restored.enum_diffs) == len(diff.enum_diffs)
        assert len(restored.sequence_diffs) == len(diff.sequence_diffs)
        assert len(restored.routine_diffs) == len(diff.routine_diffs)
        assert len(restored.trigger_diffs) == len(diff.trigger_diffs)
        assert len(restored.check_constraint_diffs) == len(diff.check_constraint_diffs)

    def test_from_dict_preserves_risk_level(self):
        """risk_level should survive round-trip (not be recomputed to default)."""
        diff = SchemaDiff(
            table_diffs=[
                TableDiff(
                    table_name="t",
                    diff_type="removed",
                    column_diffs=[
                        ColumnDiff(table_name="t", column_name="id", diff_type="removed",
                                   source_state={"name": "id", "type": "INT"},
                                   is_breaking=True, risk_level="critical"),
                    ],
                    risk_level="critical",
                )
            ],
            total_breaking_changes=1,
            overall_risk="critical",
        )
        d = diff.to_dict()
        restored = SchemaDiff.from_dict(d)
        assert restored.table_diffs[0].risk_level == "critical"
        assert restored.overall_risk == "critical"

    def test_empty_diff_round_trip(self):
        diff = SchemaDiff(diff_summary="No differences found", overall_risk="none")
        d = diff.to_dict()
        restored = SchemaDiff.from_dict(d)
        assert restored.overall_risk == "none"
        assert len(restored.table_diffs) == 0
