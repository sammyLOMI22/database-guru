"""Tests for Phase 22.2: Explain Interpreter"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.guru.explain_analyzer import ExecutionPlan, PlanNode
from src.guru.explain_interpreter import (
    ExplainInterpreter,
    PerformanceInsights,
    Bottleneck,
    IndexSuggestion,
    QueryRewrite,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.generate = AsyncMock(return_value="")
    return client


@pytest.fixture
def mock_router():
    router = MagicMock()
    router.get_model_for_task.return_value = "llama3.2:latest"
    router.get_timeout_for_task.return_value = 25
    router.get_model_size.return_value = MagicMock()  # Will be patched per test
    return router


@pytest.fixture
def interpreter(mock_client, mock_router):
    return ExplainInterpreter(
        ollama_client=mock_client,
        model_router=mock_router,
        timeout_seconds=10.0,
    )


@pytest.fixture
def sample_pg_plan():
    """A sample PostgreSQL plan with a seq scan."""
    return ExecutionPlan(
        dialect="postgresql",
        sql="SELECT * FROM orders WHERE status='pending'",
        analyzed=False,
        root_node=PlanNode(
            node_type="Seq Scan",
            relation="orders",
            cost_total=1823.0,
            rows_estimated=10000,
        ),
        all_nodes=[
            PlanNode(
                node_type="Seq Scan",
                relation="orders",
                cost_total=1823.0,
                rows_estimated=10000,
                filter="(status = 'pending')",
            ),
        ],
        has_seq_scans=True,
        seq_scan_tables=["orders"],
        raw_plan=["Seq Scan on orders  (cost=0.00..1823.00 rows=10000 width=8)"],
        warnings=["Sequential scan on 'orders' with filter — consider adding an index on the filtered column"],
    )


@pytest.fixture
def sample_sqlite_plan():
    """A sample SQLite plan."""
    return ExecutionPlan(
        dialect="sqlite",
        sql="SELECT * FROM orders",
        analyzed=False,
        root_node=PlanNode(node_type="SCAN", relation="orders"),
        all_nodes=[PlanNode(node_type="SCAN", relation="orders")],
        has_seq_scans=True,
        seq_scan_tables=["orders"],
        raw_plan=["SCAN TABLE orders"],
        warnings=["Full table scan on 'orders' — consider adding an index"],
    )


@pytest.fixture
def valid_llm_response():
    return json.dumps({
        "summary": "The query performs a sequential scan on the orders table, reading all 10,000 rows.",
        "overall_severity": "warning",
        "bottlenecks": [
            {
                "node_type": "Seq Scan",
                "table_or_index": "orders",
                "severity": "high",
                "description": "Full table scan on orders table with filter on status column",
                "impact_estimate": "85% of total query cost",
            }
        ],
        "index_suggestions": [
            {
                "table": "orders",
                "columns": ["status"],
                "reason": "Filter on status column currently requires full table scan",
                "create_sql": "CREATE INDEX idx_orders_status ON orders(status)",
                "estimated_speedup": "10-50x for equality filter queries",
            }
        ],
        "query_rewrites": [],
        "general_recommendations": ["Add an index on orders.status"],
        "confidence": 0.85,
    })


# ============================================================================
# Core interpretation tests
# ============================================================================

class TestInterpret:
    @pytest.mark.asyncio
    async def test_parses_valid_json_response(self, interpreter, mock_client, sample_pg_plan, valid_llm_response):
        mock_client.generate.return_value = valid_llm_response

        result = await interpreter.interpret(sample_pg_plan)

        assert isinstance(result, PerformanceInsights)
        assert result.llm_used is True
        assert result.overall_severity == "warning"
        assert len(result.bottlenecks) == 1
        assert result.bottlenecks[0].node_type == "Seq Scan"
        assert result.bottlenecks[0].table_or_index == "orders"
        assert len(result.index_suggestions) == 1
        assert result.index_suggestions[0].create_sql == "CREATE INDEX idx_orders_status ON orders(status)"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_returns_fallback_on_timeout(self, interpreter, mock_client, sample_pg_plan):
        mock_client.generate = AsyncMock(side_effect=asyncio.TimeoutError())

        result = await interpreter.interpret(sample_pg_plan)

        assert isinstance(result, PerformanceInsights)
        assert result.llm_used is False
        assert result.confidence == 0.4
        assert len(result.bottlenecks) > 0  # Deterministic fallback should find seq scan

    @pytest.mark.asyncio
    async def test_returns_fallback_on_llm_error(self, interpreter, mock_client, sample_pg_plan):
        mock_client.generate = AsyncMock(side_effect=Exception("Connection refused"))

        result = await interpreter.interpret(sample_pg_plan)

        assert result.llm_used is False
        assert result.confidence == 0.4

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self, interpreter, mock_client, sample_pg_plan):
        mock_client.generate.return_value = "This is not JSON at all, just some text."

        result = await interpreter.interpret(sample_pg_plan)

        assert result.llm_used is False
        assert result.confidence == 0.4

    @pytest.mark.asyncio
    async def test_handles_partial_json(self, interpreter, mock_client, sample_pg_plan):
        mock_client.generate.return_value = '{"summary": "ok but missing other fields"}'

        result = await interpreter.interpret(sample_pg_plan)

        # Should parse successfully even with minimal JSON
        assert isinstance(result, PerformanceInsights)
        assert result.summary == "ok but missing other fields"

    @pytest.mark.asyncio
    async def test_handles_empty_summary(self, interpreter, mock_client, sample_pg_plan):
        mock_client.generate.return_value = '{"summary": "", "confidence": 0.5}'

        result = await interpreter.interpret(sample_pg_plan)

        # Empty summary triggers fallback
        assert result.llm_used is False


# ============================================================================
# SQLite deterministic analysis tests
# ============================================================================

class TestSQLiteDeterministic:
    @pytest.mark.asyncio
    async def test_sqlite_skips_llm(self, interpreter, mock_client, sample_sqlite_plan):
        result = await interpreter.interpret(sample_sqlite_plan)

        # LLM should NOT be called for SQLite
        mock_client.generate.assert_not_called()
        assert result.llm_used is False
        assert result.confidence == 0.6

    @pytest.mark.asyncio
    async def test_sqlite_detects_full_scan(self, interpreter, mock_client, sample_sqlite_plan):
        result = await interpreter.interpret(sample_sqlite_plan)

        assert len(result.bottlenecks) == 1
        assert result.bottlenecks[0].node_type == "Full Table Scan"
        assert result.bottlenecks[0].table_or_index == "orders"

    @pytest.mark.asyncio
    async def test_sqlite_temp_btree(self, interpreter, mock_client):
        plan = ExecutionPlan(
            dialect="sqlite",
            sql="SELECT * FROM orders ORDER BY created_at",
            analyzed=False,
            all_nodes=[
                PlanNode(node_type="SCAN", relation="orders"),
                PlanNode(node_type="TEMP B-TREE"),
            ],
            has_seq_scans=True,
            seq_scan_tables=["orders"],
            raw_plan=["SCAN TABLE orders", "USE TEMP B-TREE FOR ORDER BY"],
            warnings=[],
        )

        result = await interpreter.interpret(plan)

        assert any("Temp B-Tree" in b.node_type for b in result.bottlenecks)

    @pytest.mark.asyncio
    async def test_sqlite_no_issues(self, interpreter, mock_client):
        plan = ExecutionPlan(
            dialect="sqlite",
            sql="SELECT * FROM orders WHERE id=1",
            analyzed=False,
            all_nodes=[
                PlanNode(node_type="SEARCH", relation="orders", index_name="sqlite_autoindex_orders_1"),
            ],
            has_seq_scans=False,
            seq_scan_tables=[],
            raw_plan=["SEARCH TABLE orders USING INDEX sqlite_autoindex_orders_1"],
            warnings=[],
        )

        result = await interpreter.interpret(plan)

        assert result.overall_severity == "good"
        assert len(result.bottlenecks) == 0


# ============================================================================
# Fallback insights tests
# ============================================================================

class TestFallbackInsights:
    def test_fallback_with_seq_scans(self, interpreter, sample_pg_plan):
        result = interpreter._fallback_insights(sample_pg_plan)

        assert result.llm_used is False
        assert result.overall_severity == "warning"
        assert "orders" in result.summary

    def test_fallback_with_disk_spill(self, interpreter):
        plan = ExecutionPlan(
            dialect="postgresql",
            sql="SELECT * FROM orders ORDER BY x",
            analyzed=False,
            has_seq_scans=False,
            has_disk_spill=True,
            seq_scan_tables=[],
            warnings=["Disk spill detected"],
        )
        result = interpreter._fallback_insights(plan)

        assert result.overall_severity == "critical"
        assert "Disk spill" in result.summary or "work_mem" in result.summary

    def test_fallback_no_issues(self, interpreter):
        plan = ExecutionPlan(
            dialect="postgresql",
            sql="SELECT 1",
            analyzed=False,
            has_seq_scans=False,
            has_disk_spill=False,
            seq_scan_tables=[],
            warnings=[],
        )
        result = interpreter._fallback_insights(plan)

        assert result.overall_severity == "good"


# ============================================================================
# Prompt building tests
# ============================================================================

class TestPromptBuilding:
    def test_prompt_includes_plan(self, interpreter, sample_pg_plan):
        prompt = interpreter._build_prompt(sample_pg_plan)

        assert "Seq Scan on orders" in prompt
        assert "SELECT * FROM orders" in prompt

    def test_prompt_includes_warnings(self, interpreter, sample_pg_plan):
        prompt = interpreter._build_prompt(sample_pg_plan)

        assert "Sequential scan" in prompt or "index" in prompt

    def test_prompt_includes_schema_context(self, interpreter, sample_pg_plan):
        schema = {"orders": ["id", "status", "total", "created_at"]}
        prompt = interpreter._build_prompt(sample_pg_plan, schema_context=schema)

        assert "orders" in prompt
        assert "status" in prompt


# ============================================================================
# Prompt tier selection tests
# ============================================================================

class TestPromptTierSelection:
    def test_get_explain_prompt_small(self):
        from src.llm.prompt_optimizer import ModelSize
        from src.guru.prompts.explain_prompts import get_explain_prompt

        prompt = get_explain_prompt(ModelSize.SMALL)
        assert "Return JSON ONLY" in prompt
        # Compact prompt is shorter
        assert len(prompt) < 800

    def test_get_explain_prompt_medium(self):
        from src.llm.prompt_optimizer import ModelSize
        from src.guru.prompts.explain_prompts import get_explain_prompt

        prompt = get_explain_prompt(ModelSize.MEDIUM)
        assert "INSTRUCTIONS:" in prompt

    def test_get_explain_prompt_large(self):
        from src.llm.prompt_optimizer import ModelSize
        from src.guru.prompts.explain_prompts import get_explain_prompt

        prompt = get_explain_prompt(ModelSize.LARGE)
        assert "ANALYSIS REQUIREMENTS:" in prompt
        assert "work_mem" in prompt


# ============================================================================
# Serialization tests
# ============================================================================

class TestSerialization:
    def test_performance_insights_to_dict(self):
        insights = PerformanceInsights(
            summary="Test summary",
            overall_severity="warning",
            bottlenecks=[Bottleneck("Seq Scan", "orders", "high", "desc", "impact")],
            index_suggestions=[IndexSuggestion("orders", ["status"], "reason", "CREATE INDEX...", "10x")],
            confidence=0.8,
            llm_used=True,
        )
        d = insights.to_dict()

        assert d["summary"] == "Test summary"
        assert len(d["bottlenecks"]) == 1
        assert d["bottlenecks"][0]["node_type"] == "Seq Scan"
        assert len(d["index_suggestions"]) == 1
        assert d["llm_used"] is True

    def test_generated_at_auto_set(self):
        insights = PerformanceInsights(summary="test")
        assert insights.generated_at is not None
