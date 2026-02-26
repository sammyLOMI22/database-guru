"""Tests for Migration Planner (Phase 20.2)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.migration.migration_planner import MigrationPlanner, MigrationPlan, MigrationStep
from src.migration.schema_comparator import (
    SchemaDiff, TableDiff, ColumnDiff, ConstraintDiff,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_diff(
    table_diffs=None,
    overall_risk="low",
    breaking=0,
    safe=0,
    summary="test",
) -> SchemaDiff:
    return SchemaDiff(
        table_diffs=table_diffs or [],
        total_breaking_changes=breaking,
        total_safe_changes=safe,
        overall_risk=overall_risk,
        diff_summary=summary,
    )


def _simple_diff() -> SchemaDiff:
    """A diff with one added, one modified, and one removed table."""
    return _make_diff(
        table_diffs=[
            TableDiff(table_name="new_table", diff_type="added"),
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(
                        table_name="users",
                        column_name="email",
                        diff_type="added",
                        target_state={"name": "email", "type": "VARCHAR(255)", "nullable": True},
                        risk_level="low",
                    ),
                ],
            ),
            TableDiff(table_name="old_table", diff_type="removed"),
        ],
        overall_risk="critical",
        breaking=1,
        safe=2,
        summary="1 table added, 1 table removed, 1 table modified",
    )


# ---------------------------------------------------------------------------
# Deterministic plan generation
# ---------------------------------------------------------------------------

class TestMigrationPlannerDeterministic:
    @pytest.mark.asyncio
    async def test_empty_diff(self):
        planner = MigrationPlanner()
        plan = await planner.plan(1, _make_diff())

        assert plan.project_id == 1
        # pre_check + verify = 2 steps minimum
        assert len(plan.steps) >= 2
        assert plan.steps[0].action == "pre_check"
        assert plan.steps[-1].action == "verify"

    @pytest.mark.asyncio
    async def test_simple_diff_steps(self):
        planner = MigrationPlanner()
        diff = _simple_diff()
        plan = await planner.plan(1, diff)

        actions = [s.action for s in plan.steps]
        assert "pre_check" in actions
        assert "backup" in actions  # Critical risk triggers backup
        assert "verify" in actions
        assert actions.count("ddl") >= 3  # add table + add column + drop table

    @pytest.mark.asyncio
    async def test_added_table_step(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="orders", diff_type="added"),
        ])
        plan = await planner.plan(1, diff)

        ddl_steps = [s for s in plan.steps if s.action == "ddl"]
        assert len(ddl_steps) == 1
        assert "Create table" in ddl_steps[0].description
        assert ddl_steps[0].risk_level == "low"

    @pytest.mark.asyncio
    async def test_removed_table_step(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="legacy", diff_type="removed"),
        ], overall_risk="critical")
        plan = await planner.plan(1, diff)

        ddl_steps = [s for s in plan.steps if s.action == "ddl"]
        assert len(ddl_steps) == 1
        assert ddl_steps[0].risk_level == "critical"
        assert ddl_steps[0].is_reversible is False
        assert any("DATA LOSS" in w for w in ddl_steps[0].warnings)

    @pytest.mark.asyncio
    async def test_modified_table_steps(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="users",
                diff_type="modified",
                column_diffs=[
                    ColumnDiff(table_name="users", column_name="a", diff_type="added",
                               target_state={"type": "TEXT"}, risk_level="low"),
                    ColumnDiff(table_name="users", column_name="b", diff_type="removed",
                               source_state={"type": "TEXT"}, is_breaking=True, risk_level="critical"),
                ],
            ),
        ], overall_risk="critical")
        plan = await planner.plan(1, diff)

        ddl_steps = [s for s in plan.steps if s.action == "ddl"]
        assert len(ddl_steps) == 2  # one per column change

    @pytest.mark.asyncio
    async def test_backup_triggered_by_critical_risk(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="t", diff_type="removed"),
        ], overall_risk="critical")
        plan = await planner.plan(1, diff)
        assert any(s.action == "backup" for s in plan.steps)

    @pytest.mark.asyncio
    async def test_no_backup_for_low_risk(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="t", diff_type="added"),
        ])
        plan = await planner.plan(1, diff)
        assert not any(s.action == "backup" for s in plan.steps)


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_no_fk_deps(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="b", diff_type="added"),
            TableDiff(table_name="a", diff_type="added"),
        ])
        order = planner._topological_sort_tables(diff)
        # Should be alphabetical when no deps
        assert order == ["a", "b"]

    def test_with_fk_deps(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(
                table_name="orders",
                diff_type="modified",
                constraint_diffs=[
                    ConstraintDiff(
                        table_name="orders",
                        constraint_type="foreign_key",
                        diff_type="added",
                        target_state=("user_id", "users", "id"),
                    ),
                ],
            ),
            TableDiff(table_name="users", diff_type="modified"),
        ])
        order = planner._topological_sort_tables(diff)
        assert order.index("users") < order.index("orders")


# ---------------------------------------------------------------------------
# Complexity & downtime
# ---------------------------------------------------------------------------

class TestComplexityAssessment:
    @pytest.mark.asyncio
    async def test_simple(self):
        planner = MigrationPlanner()
        diff = _make_diff(table_diffs=[
            TableDiff(table_name="t", diff_type="added"),
        ])
        plan = await planner.plan(1, diff)
        assert plan.overall_complexity == "simple"

    @pytest.mark.asyncio
    async def test_critical_is_high_risk(self):
        planner = MigrationPlanner()
        diff = _make_diff(
            table_diffs=[TableDiff(table_name="t", diff_type="removed")],
            overall_risk="critical",
        )
        plan = await planner.plan(1, diff)
        assert plan.overall_complexity == "high-risk"

    @pytest.mark.asyncio
    async def test_maintenance_window_for_high_risk(self):
        planner = MigrationPlanner()
        diff = _make_diff(
            table_diffs=[TableDiff(table_name="t", diff_type="removed")],
            overall_risk="high",
        )
        plan = await planner.plan(1, diff)
        assert plan.recommended_maintenance_window is True

    @pytest.mark.asyncio
    async def test_rollback_strategy_critical(self):
        planner = MigrationPlanner()
        diff = _make_diff(
            table_diffs=[TableDiff(table_name="t", diff_type="removed")],
            overall_risk="critical",
        )
        plan = await planner.plan(1, diff)
        assert "backup" in plan.rollback_strategy.lower()


# ---------------------------------------------------------------------------
# LLM enrichment
# ---------------------------------------------------------------------------

class TestLLMEnrichment:
    @pytest.mark.asyncio
    async def test_llm_failure_falls_back(self):
        """If LLM fails, plan should still be complete with deterministic values."""
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(side_effect=Exception("LLM down"))

        planner = MigrationPlanner(ollama_client=mock_client, model="test-model")
        diff = _simple_diff()
        plan = await planner.plan(1, diff)

        # Plan should still work with deterministic fallback
        assert len(plan.steps) > 0
        # All LLM calls raised exceptions — no enrichment was applied,
        # so llm_used must be False
        assert plan.llm_used is False
        # Deterministic values should still be present
        assert plan.overall_complexity == "high-risk"
        assert len(plan.pre_migration_checklist) > 0

    @pytest.mark.asyncio
    async def test_no_client_skips_llm(self):
        planner = MigrationPlanner(ollama_client=None)
        diff = _simple_diff()
        plan = await planner.plan(1, diff)
        assert plan.llm_used is False


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestPlanSerialization:
    @pytest.mark.asyncio
    async def test_to_dict(self):
        planner = MigrationPlanner()
        diff = _simple_diff()
        plan = await planner.plan(1, diff)

        d = plan.to_dict()
        assert d["project_id"] == 1
        assert isinstance(d["steps"], list)
        assert "pre_migration_checklist" in d
        assert "post_migration_checklist" in d
        assert "generated_at" in d

    def test_step_to_dict(self):
        step = MigrationStep(step_number=1, action="ddl", description="test")
        d = step.to_dict()
        assert d["step_number"] == 1
        assert d["action"] == "ddl"
