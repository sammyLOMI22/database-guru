"""
Tests for Impact Advisor (Phase 12.2)

Tests the LLM-powered impact analysis with migration plans and SQL patches.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.lineage.impact_advisor import (
    ImpactAdvisor,
    ImpactAdvice,
    RiskExplanation,
    MigrationPlan,
    MigrationStep,
    SQLPatch,
    ChangeType,
    get_impact_advisor,
)
from src.lineage.impact_analyzer import (
    ImpactAnalysis,
    ImpactedQuery,
    RiskLevel,
)


@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def sample_impact_analysis():
    """Create a sample impact analysis."""
    return ImpactAnalysis(
        changed_object="orders.customer_id",
        object_type="column",
        impacted_queries=[
            ImpactedQuery(
                query_id=1,
                natural_language_query="Show all orders with customer names",
                generated_sql="SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
                impact_type="join",
                risk_level="medium",
            ),
            ImpactedQuery(
                query_id=2,
                natural_language_query="Count orders per customer",
                generated_sql="SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id",
                impact_type="group",
                risk_level="low",
            ),
        ],
        total_affected=2,
        risk_level="medium",
        risk_counts={"low": 1, "medium": 1, "high": 0},
        summary="Medium risk: 2 queries reference orders.customer_id.",
    )


@pytest.fixture
def advisor(mock_ollama_client):
    """Create an ImpactAdvisor with mock client."""
    return ImpactAdvisor(
        ollama_client=mock_ollama_client,
        timeout_seconds=5.0,
    )


class TestRiskExplanation:
    """Tests for RiskExplanation dataclass."""

    def test_risk_explanation_to_dict(self):
        """Test risk explanation serialization."""
        explanation = RiskExplanation(
            risk_level="medium",
            summary="Moderate impact on reporting queries",
            detailed_explanation="This change affects 5 queries used in reporting.",
            affected_areas=["reporting", "analytics"],
            recommendations=["Test in staging first"],
            confidence=0.85,
        )

        result = explanation.to_dict()

        assert result["risk_level"] == "medium"
        assert result["confidence"] == 0.85
        assert "reporting" in result["affected_areas"]


class TestMigrationPlan:
    """Tests for MigrationPlan dataclass."""

    def test_migration_plan_defaults(self):
        """Test migration plan has proper defaults."""
        plan = MigrationPlan(
            change_type="rename_column",
            target_object="orders.customer_id",
        )

        assert plan.change_type == "rename_column"
        assert plan.steps == []
        assert plan.estimated_downtime == "none"
        assert plan.rollback_possible is True
        assert plan.generated_at is not None

    def test_migration_plan_with_steps(self):
        """Test migration plan with steps."""
        plan = MigrationPlan(
            change_type="rename_column",
            target_object="orders.customer_id",
            new_value="cust_id",
            steps=[
                MigrationStep(
                    step_number=1,
                    action="backup",
                    description="Create backup",
                ),
                MigrationStep(
                    step_number=2,
                    action="alter_table",
                    description="Rename column",
                    sql="ALTER TABLE orders RENAME COLUMN customer_id TO cust_id",
                ),
            ],
        )

        assert len(plan.steps) == 2
        assert plan.steps[0].action == "backup"
        assert plan.steps[1].sql is not None


class TestSQLPatch:
    """Tests for SQLPatch dataclass."""

    def test_sql_patch_to_dict(self):
        """Test SQL patch serialization."""
        patch = SQLPatch(
            query_id=1,
            original_sql="SELECT customer_id FROM orders",
            patched_sql="SELECT cust_id FROM orders",
            change_description="Renamed customer_id to cust_id",
            confidence=0.95,
            requires_review=False,
        )

        result = patch.to_dict()

        assert result["query_id"] == 1
        assert result["confidence"] == 0.95
        assert "cust_id" in result["patched_sql"]


class TestImpactAdvisor:
    """Tests for ImpactAdvisor class."""

    @pytest.mark.asyncio
    async def test_explain_risk_success(self, advisor, mock_ollama_client, sample_impact_analysis):
        """Test successful risk explanation generation."""
        mock_ollama_client.generate.return_value = json.dumps({
            "risk_level": "medium",
            "summary": "Moderate risk due to JOIN dependencies",
            "detailed_explanation": "The customer_id column is used in JOIN operations.",
            "affected_areas": ["reporting", "ETL"],
            "recommendations": ["Update JOIN conditions in affected queries"],
            "confidence": 0.85,
        })

        explanation = await advisor.explain_risk(
            sample_impact_analysis,
            change_type="rename_column",
            new_value="cust_id",
        )

        assert explanation.risk_level == "medium"
        assert explanation.confidence > 0.5
        assert len(explanation.recommendations) > 0

    @pytest.mark.asyncio
    async def test_explain_risk_fallback(self, advisor, mock_ollama_client, sample_impact_analysis):
        """Test fallback on LLM error."""
        mock_ollama_client.generate.side_effect = Exception("LLM failed")

        explanation = await advisor.explain_risk(
            sample_impact_analysis,
            change_type="rename_column",
        )

        # Should return fallback
        assert explanation is not None
        assert explanation.confidence == 0.4  # Fallback confidence

    @pytest.mark.asyncio
    async def test_generate_migration_plan_success(self, advisor, mock_ollama_client, sample_impact_analysis):
        """Test successful migration plan generation."""
        mock_ollama_client.generate.return_value = json.dumps({
            "estimated_downtime": "minimal",
            "rollback_possible": True,
            "warnings": ["Backup before proceeding"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "backup",
                    "description": "Create table backup",
                    "reversible": True,
                    "risk_level": "low",
                },
                {
                    "step_number": 2,
                    "action": "alter_table",
                    "description": "Rename column",
                    "sql": "ALTER TABLE orders RENAME COLUMN customer_id TO cust_id",
                    "reversible": True,
                    "risk_level": "medium",
                },
            ],
        })

        plan = await advisor.generate_migration_plan(
            sample_impact_analysis,
            change_type="rename_column",
            new_value="cust_id",
        )

        assert plan.estimated_downtime == "minimal"
        assert len(plan.steps) == 2
        assert plan.steps[0].action == "backup"

    @pytest.mark.asyncio
    async def test_generate_migration_plan_fallback(self, advisor, mock_ollama_client, sample_impact_analysis):
        """Test fallback migration plan on LLM error."""
        mock_ollama_client.generate.side_effect = Exception("LLM failed")

        plan = await advisor.generate_migration_plan(
            sample_impact_analysis,
            change_type="rename_column",
            new_value="cust_id",
        )

        # Should return fallback plan
        assert plan is not None
        assert len(plan.steps) > 0
        assert "Basic" in plan.warnings[0] or len(plan.steps) >= 3

    @pytest.mark.asyncio
    async def test_generate_sql_patches_success(self, advisor, mock_ollama_client, sample_impact_analysis):
        """Test successful SQL patch generation."""
        mock_ollama_client.generate.return_value = json.dumps({
            "patches": [
                {
                    "query_id": 1,
                    "original_sql": "SELECT customer_id FROM orders",
                    "patched_sql": "SELECT cust_id FROM orders",
                    "change_description": "Renamed customer_id to cust_id",
                    "confidence": 0.95,
                    "requires_review": False,
                },
            ],
        })

        patches = await advisor.generate_sql_patches(
            sample_impact_analysis.impacted_queries[:1],
            change_type="rename_column",
            old_value="customer_id",
            new_value="cust_id",
        )

        assert len(patches) == 1
        assert patches[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_generate_sql_patches_empty_on_error(self, advisor, mock_ollama_client, sample_impact_analysis):
        """Test empty patches on LLM error."""
        mock_ollama_client.generate.side_effect = Exception("LLM failed")

        patches = await advisor.generate_sql_patches(
            sample_impact_analysis.impacted_queries,
            change_type="rename_column",
            old_value="customer_id",
            new_value="cust_id",
        )

        assert patches == []


class TestFallbackNarratives:
    """Tests for fallback behavior."""

    def test_fallback_risk_no_affected_queries(self, advisor):
        """Test fallback for impact with no affected queries."""
        empty_impact = ImpactAnalysis(
            changed_object="unused_table",
            object_type="table",
            total_affected=0,
            risk_level="low",
        )

        explanation = advisor._fallback_risk_explanation(empty_impact)

        assert "No queries" in explanation.summary or "no" in explanation.summary.lower()
        assert explanation.risk_level == "low"

    def test_fallback_risk_with_affected_queries(self, advisor, sample_impact_analysis):
        """Test fallback for impact with affected queries."""
        explanation = advisor._fallback_risk_explanation(sample_impact_analysis)

        assert explanation.risk_level == "medium"
        assert "2" in explanation.summary or "queries" in explanation.summary.lower()

    def test_fallback_migration_rename_column(self, advisor):
        """Test fallback migration plan for rename column."""
        plan = advisor._fallback_migration_plan(
            change_type="rename_column",
            target_object="orders.customer_id",
            new_value="cust_id",
        )

        assert len(plan.steps) >= 4
        assert any("backup" in s.action for s in plan.steps)
        assert any("alter" in s.action.lower() for s in plan.steps)

    def test_fallback_migration_drop_column(self, advisor):
        """Test fallback migration plan for drop column (irreversible)."""
        plan = advisor._fallback_migration_plan(
            change_type="drop_column",
            target_object="orders.old_column",
            new_value=None,
        )

        assert plan.rollback_possible is False
        assert any(s.risk_level == "high" for s in plan.steps)


class TestJsonExtraction:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_simple_json(self, advisor):
        """Test extraction of simple JSON."""
        text = '{"key": "value"}'
        result = advisor._extract_json_object(text)
        assert result == '{"key": "value"}'

    def test_extract_json_with_prefix(self, advisor):
        """Test extraction with text prefix."""
        text = 'Here is the analysis:\n{"summary": "test"}'
        result = advisor._extract_json_object(text)
        assert result is not None
        assert json.loads(result)["summary"] == "test"

    def test_extract_nested_json(self, advisor):
        """Test extraction of nested JSON."""
        text = '{"outer": {"inner": "value"}}'
        result = advisor._extract_json_object(text)
        assert result == '{"outer": {"inner": "value"}}'

    def test_extract_no_json(self, advisor):
        """Test returns None when no JSON found."""
        text = "This is just plain text"
        result = advisor._extract_json_object(text)
        assert result is None


class TestChangeTypes:
    """Tests for ChangeType enum."""

    def test_change_types_exist(self):
        """Test all expected change types exist."""
        assert ChangeType.RENAME_COLUMN.value == "rename_column"
        assert ChangeType.RENAME_TABLE.value == "rename_table"
        assert ChangeType.DROP_COLUMN.value == "drop_column"
        assert ChangeType.DROP_TABLE.value == "drop_table"
        assert ChangeType.CHANGE_TYPE.value == "change_type"


class TestGetImpactAdvisor:
    """Tests for get_impact_advisor factory function."""

    @pytest.mark.asyncio
    async def test_get_advisor_without_db(self):
        """Test getting advisor without database session."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            advisor = await get_impact_advisor()

            assert advisor is not None
            assert advisor.client == mock_client

    @pytest.mark.asyncio
    async def test_get_advisor_with_model_override(self):
        """Test getting advisor with model override."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            advisor = await get_impact_advisor(model="custom-model")

            assert advisor.model == "custom-model"


class TestIntegration:
    """Integration tests with mocked database."""

    @pytest.mark.asyncio
    async def test_analyze_with_recommendations_mock_db(self, advisor, mock_ollama_client):
        """Test full analysis with mocked database."""
        # Mock the impact analyzer
        with patch.object(advisor.impact_analyzer, 'analyze_column_impact') as mock_analyze:
            mock_analyze.return_value = ImpactAnalysis(
                changed_object="orders.customer_id",
                object_type="column",
                impacted_queries=[
                    ImpactedQuery(
                        query_id=1,
                        natural_language_query="Get orders",
                        generated_sql="SELECT * FROM orders WHERE customer_id = 1",
                        impact_type="filter",
                        risk_level="medium",
                    ),
                ],
                total_affected=1,
                risk_level="medium",
                risk_counts={"low": 0, "medium": 1, "high": 0},
                summary="1 query affected",
            )

            # Mock LLM responses
            mock_ollama_client.generate.return_value = json.dumps({
                "risk_level": "medium",
                "summary": "Medium risk change",
                "detailed_explanation": "Details here",
                "affected_areas": ["queries"],
                "recommendations": ["Test first"],
                "confidence": 0.8,
            })

            advice = await advisor.analyze_with_recommendations(
                db=MagicMock(),  # Mock db
                change_type="rename_column",
                table_name="orders",
                column_name="customer_id",
                new_value="cust_id",
                include_patches=False,  # Skip patches for this test
            )

            assert advice is not None
            assert advice.impact.total_affected == 1
            assert advice.risk_explanation is not None or advice.llm_used is False
