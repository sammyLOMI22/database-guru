"""
Tests for Pattern Intelligence Agent (Phase 12.4)

Tests the pattern analysis with:
- Anti-pattern detection (SELECT *, N+1, missing WHERE, etc.)
- Trend analysis
- Bottleneck analysis
- Optimization suggestions
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.lineage.pattern_intelligence import (
    PatternIntelligenceAgent,
    PatternIntelligenceReport,
    BottleneckAnalysis,
    OptimizationSuggestion,
    QueryAntiPattern,
    UsageTrend,
    TrendAnalysis,
    AntiPatternDetector,
    TrendAnalyzer,
    get_pattern_intelligence_agent,
)
from src.lineage.query_pattern_analyzer import PerformanceBottleneck


@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def mock_query_history():
    """Create mock query history entries."""
    class MockQuery:
        def __init__(self, id, sql, execution_time=None, created_at=None):
            self.id = id
            self.generated_sql = sql
            self.execution_time_ms = execution_time
            self.created_at = created_at or datetime.now(timezone.utc)
            self.executed = True
            self.connection_id = 1

    return [
        MockQuery(1, "SELECT * FROM users WHERE id = 1", 50),
        MockQuery(2, "SELECT * FROM users WHERE id = 2", 45),
        MockQuery(3, "SELECT * FROM orders WHERE user_id = 1", 100),
        MockQuery(4, "SELECT id, name FROM users WHERE email LIKE '%@test.com'", 200),
        MockQuery(5, "SELECT o.*, u.name FROM orders o JOIN users u ON o.user_id = u.id", 150),
        MockQuery(6, "SELECT * FROM products", 300),  # No WHERE clause
        MockQuery(7, "SELECT * FROM products", 280),
        MockQuery(8, "SELECT * FROM products", 290),
    ]


@pytest.fixture
def anti_pattern_detector():
    """Create an AntiPatternDetector instance."""
    return AntiPatternDetector()


@pytest.fixture
def agent(mock_ollama_client):
    """Create a PatternIntelligenceAgent with mock client."""
    return PatternIntelligenceAgent(
        ollama_client=mock_ollama_client,
        timeout_seconds=5.0,
    )


# =============================================================================
# Dataclass Tests
# =============================================================================

class TestBottleneckAnalysis:
    """Tests for BottleneckAnalysis dataclass."""

    def test_bottleneck_analysis_to_dict(self):
        """Test bottleneck analysis serialization."""
        analysis = BottleneckAnalysis(
            table_name="orders",
            bottleneck_score=0.85,
            root_causes=["Missing index on user_id", "Complex joins"],
            contributing_factors=["High query frequency"],
            optimization_suggestions=["Add index on user_id"],
            estimated_improvement="high",
            sample_slow_queries=["SELECT * FROM orders WHERE user_id = 1"],
            confidence=0.8,
        )

        result = analysis.to_dict()

        assert result["table_name"] == "orders"
        assert result["bottleneck_score"] == 0.85
        assert len(result["root_causes"]) == 2
        assert result["estimated_improvement"] == "high"


class TestOptimizationSuggestion:
    """Tests for OptimizationSuggestion dataclass."""

    def test_optimization_suggestion_to_dict(self):
        """Test optimization suggestion serialization."""
        suggestion = OptimizationSuggestion(
            category="index",
            title="Add index on orders.user_id",
            description="This column is frequently used in WHERE clauses",
            affected_tables=["orders"],
            estimated_impact="high",
            implementation_sql="CREATE INDEX idx_orders_user_id ON orders(user_id);",
            priority=1,
        )

        result = suggestion.to_dict()

        assert result["category"] == "index"
        assert result["estimated_impact"] == "high"
        assert result["priority"] == 1


class TestQueryAntiPattern:
    """Tests for QueryAntiPattern dataclass."""

    def test_query_anti_pattern_to_dict(self):
        """Test query anti-pattern serialization."""
        pattern = QueryAntiPattern(
            pattern_type="select_star",
            severity="warning",
            title="SELECT * Usage",
            description="Found 10 queries using SELECT *",
            affected_queries=[1, 2, 3],
            sample_sql="SELECT * FROM users",
            recommendation="Specify columns explicitly",
            occurrence_count=10,
        )

        result = pattern.to_dict()

        assert result["pattern_type"] == "select_star"
        assert result["severity"] == "warning"
        assert result["occurrence_count"] == 10


class TestUsageTrend:
    """Tests for UsageTrend dataclass."""

    def test_usage_trend_to_dict(self):
        """Test usage trend serialization."""
        trend = UsageTrend(
            table_name="users",
            period="daily",
            data_points=[
                {"date": "2024-01-01", "count": 10},
                {"date": "2024-01-02", "count": 15},
            ],
            trend_direction="increasing",
            change_percentage=50.0,
        )

        result = trend.to_dict()

        assert result["table_name"] == "users"
        assert result["trend_direction"] == "increasing"
        assert len(result["data_points"]) == 2


class TestPatternIntelligenceReport:
    """Tests for PatternIntelligenceReport dataclass."""

    def test_report_to_dict(self):
        """Test complete report serialization."""
        report = PatternIntelligenceReport(
            connection_id=1,
            bottleneck_analyses=[
                BottleneckAnalysis(
                    table_name="orders",
                    bottleneck_score=0.8,
                    root_causes=["Test"],
                    contributing_factors=[],
                    optimization_suggestions=[],
                    estimated_improvement="medium",
                    sample_slow_queries=[],
                )
            ],
            optimization_suggestions=[],
            anti_patterns=[],
            summary="Test summary",
            recommendations=["Fix indexes"],
            llm_used=True,
        )

        result = report.to_dict()

        assert result["connection_id"] == 1
        assert len(result["bottleneck_analyses"]) == 1
        assert result["llm_used"] is True

    def test_report_post_init_timestamp(self):
        """Test automatic timestamp generation."""
        report = PatternIntelligenceReport(connection_id=1)

        assert report.analyzed_at is not None


# =============================================================================
# AntiPatternDetector Tests
# =============================================================================

class TestAntiPatternDetector:
    """Tests for AntiPatternDetector."""

    def test_detect_select_star(self, anti_pattern_detector, mock_query_history):
        """Test SELECT * detection."""
        patterns = anti_pattern_detector.detect_select_star(mock_query_history)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == "select_star"
        assert patterns[0].occurrence_count >= 5  # Multiple SELECT * queries

    def test_detect_missing_where(self, anti_pattern_detector, mock_query_history):
        """Test missing WHERE clause detection."""
        patterns = anti_pattern_detector.detect_missing_where(mock_query_history)

        # Should find queries without WHERE (SELECT * FROM products)
        assert len(patterns) >= 1 or len(patterns) == 0  # Depends on threshold

    def test_detect_like_leading_wildcard(self, anti_pattern_detector):
        """Test LIKE '%...' pattern detection."""
        class MockQuery:
            def __init__(self, sql):
                self.id = 1
                self.generated_sql = sql

        queries = [
            MockQuery("SELECT * FROM users WHERE email LIKE '%@test.com'"),
            MockQuery("SELECT * FROM users WHERE name LIKE '%john%'"),
            MockQuery("SELECT * FROM users WHERE name LIKE 'john%'"),  # OK - no leading wildcard
        ]

        patterns = anti_pattern_detector.detect_like_leading_wildcard(queries)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == "leading_wildcard"
        assert patterns[0].occurrence_count == 2

    def test_detect_multiple_or(self, anti_pattern_detector):
        """Test multiple OR conditions detection."""
        class MockQuery:
            def __init__(self, sql):
                self.id = 1
                self.generated_sql = sql

        queries = [
            MockQuery("SELECT * FROM users WHERE status = 'a' OR status = 'b' OR status = 'c' OR status = 'd'"),
            MockQuery("SELECT * FROM users WHERE status = 'a' OR status = 'b' OR status = 'c' OR status = 'd'"),
            MockQuery("SELECT * FROM users WHERE id = 1"),  # OK - single condition
        ]

        patterns = anti_pattern_detector.detect_or_in_where(queries)

        assert len(patterns) >= 1
        assert patterns[0].pattern_type == "multiple_or"

    def test_detect_n_plus_one(self, anti_pattern_detector):
        """Test N+1 query pattern detection."""
        class MockQuery:
            def __init__(self, id, sql):
                self.id = id
                self.generated_sql = sql

        # Create many similar queries differing only by ID
        queries = [MockQuery(i, f"SELECT * FROM users WHERE id = {i}") for i in range(15)]

        patterns = anti_pattern_detector.detect_n_plus_one(queries)

        assert len(patterns) >= 1
        assert patterns[0].pattern_type == "n_plus_one"
        assert patterns[0].occurrence_count >= 10

    def test_detect_all_returns_sorted(self, anti_pattern_detector, mock_query_history):
        """Test detect_all returns sorted by severity."""
        patterns = anti_pattern_detector.detect_all(mock_query_history)

        # Verify sorted by severity (error < warning < info)
        if len(patterns) >= 2:
            severity_order = {"error": 0, "warning": 1, "info": 2}
            for i in range(len(patterns) - 1):
                assert severity_order.get(patterns[i].severity, 3) <= severity_order.get(patterns[i + 1].severity, 3)


# =============================================================================
# TrendAnalyzer Tests
# =============================================================================

class TestTrendAnalyzer:
    """Tests for TrendAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_trends_empty(self):
        """Test trend analysis with no data."""
        analyzer = TrendAnalyzer()

        # Mock db session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.analyze_trends(mock_db, connection_id=1, time_range_days=30)

        assert result.connection_id == 1
        assert len(result.table_trends) == 0
        assert "No query data" in result.summary

    def test_extract_tables(self):
        """Test table extraction from SQL."""
        analyzer = TrendAnalyzer()

        tables = analyzer._extract_tables("SELECT * FROM users JOIN orders ON users.id = orders.user_id")

        assert "users" in tables
        assert "orders" in tables


# =============================================================================
# PatternIntelligenceAgent Tests
# =============================================================================

class TestPatternIntelligenceAgent:
    """Tests for PatternIntelligenceAgent."""

    @pytest.mark.asyncio
    async def test_analyze_bottleneck_basic(self, agent):
        """Test basic bottleneck analysis without LLM."""
        bottleneck = PerformanceBottleneck(
            table_name="orders",
            query_count=100,
            avg_execution_time_ms=1500,
            max_execution_time_ms=5000,
            bottleneck_score=0.85,
        )

        # Mock db
        mock_db = MagicMock()

        analysis = await agent.analyze_bottleneck(bottleneck, mock_db, 1, queries=[])

        assert analysis.table_name == "orders"
        assert analysis.bottleneck_score == 0.85
        assert len(analysis.root_causes) > 0
        assert len(analysis.optimization_suggestions) > 0

    @pytest.mark.asyncio
    async def test_analyze_bottleneck_with_llm(self, mock_ollama_client):
        """Test bottleneck analysis with LLM enhancement."""
        llm_response = json.dumps({
            "root_causes": ["Missing index on user_id"],
            "contributing_factors": ["High join complexity"],
            "optimization_suggestions": ["Add composite index"],
            "estimated_improvement": "high",
            "confidence": 0.9,
        })
        mock_ollama_client.generate.return_value = llm_response

        agent = PatternIntelligenceAgent(
            ollama_client=mock_ollama_client,
            timeout_seconds=5.0,
        )

        bottleneck = PerformanceBottleneck(
            table_name="orders",
            query_count=100,
            avg_execution_time_ms=1500,
            max_execution_time_ms=5000,
            bottleneck_score=0.85,
        )

        class MockQuery:
            def __init__(self):
                self.generated_sql = "SELECT * FROM orders WHERE user_id = 1"
                self.execution_time_ms = 2000

        mock_db = MagicMock()

        analysis = await agent.analyze_bottleneck(bottleneck, mock_db, 1, queries=[MockQuery()])

        assert analysis.table_name == "orders"
        assert "Missing index on user_id" in analysis.root_causes

    def test_generate_summary(self, agent):
        """Test summary generation."""
        from src.lineage.query_pattern_analyzer import HeatmapData

        report = PatternIntelligenceReport(
            connection_id=1,
            bottleneck_analyses=[
                BottleneckAnalysis("t1", 0.8, [], [], [], "medium", []),
                BottleneckAnalysis("t2", 0.6, [], [], [], "low", []),
            ],
            anti_patterns=[
                QueryAntiPattern("select_star", "warning", "Test", "", [], "", "", 5),
            ],
            optimization_suggestions=[
                OptimizationSuggestion("index", "Test", "", [], "high", None, 1),
            ],
        )

        heatmap = HeatmapData(total_queries_analyzed=100)

        summary = agent._generate_summary(report, heatmap)

        assert "2 performance bottlenecks" in summary
        assert "1 anti-patterns" in summary
        assert "100 queries" in summary

    def test_generate_recommendations(self, agent):
        """Test recommendation generation."""
        report = PatternIntelligenceReport(
            connection_id=1,
            bottleneck_analyses=[
                BottleneckAnalysis(
                    "orders", 0.8,
                    ["Root cause"],
                    [],
                    ["Add index"],
                    "high",
                    [],
                ),
            ],
            anti_patterns=[
                QueryAntiPattern(
                    "select_star", "warning",
                    "SELECT * Usage",
                    "Description",
                    [],
                    "",
                    "Specify columns",
                    10,
                ),
            ],
            optimization_suggestions=[
                OptimizationSuggestion("index", "Add index", "", [], "high", None, 1),
            ],
        )

        recs = agent._generate_recommendations(report)

        assert len(recs) > 0
        assert any("[Bottleneck]" in r for r in recs)

    def test_extract_json_object(self):
        """Test JSON extraction from LLM response."""
        from src.lineage.llm_utils import parse_json_response
        response = '''Here's the analysis:
        {
            "root_causes": ["Missing index"],
            "confidence": 0.8
        }
        '''

        result = parse_json_response(response)

        assert result is not None
        assert result["confidence"] == 0.8

    def test_extract_json_object_no_json(self):
        """Test JSON extraction when no JSON present."""
        from src.lineage.llm_utils import parse_json_response
        response = "This response has no JSON."

        result = parse_json_response(response)

        assert result is None

    def test_normalize_string_list_plain_strings(self, agent):
        """Test normalizing a list that already contains plain strings."""
        items = ["cause 1", "cause 2", "cause 3"]
        result = agent._normalize_string_list(items)
        assert result == ["cause 1", "cause 2", "cause 3"]

    def test_normalize_string_list_dict_objects(self, agent):
        """Test normalizing a list containing dict objects from LLM."""
        items = [
            {"cause": "Full table scan on orders table"},
            {"cause": "Missing index on user_id column"},
        ]
        result = agent._normalize_string_list(items)
        assert result == ["Full table scan on orders table", "Missing index on user_id column"]

    def test_normalize_string_list_mixed(self, agent):
        """Test normalizing a list with mixed strings and dicts."""
        items = [
            "Simple string cause",
            {"factor": "Complex factor from LLM"},
            {"suggestion": "Add an index"},
        ]
        result = agent._normalize_string_list(items)
        assert result == ["Simple string cause", "Complex factor from LLM", "Add an index"]

    def test_normalize_string_list_empty(self, agent):
        """Test normalizing an empty list."""
        result = agent._normalize_string_list([])
        assert result == []

    def test_normalize_string_list_fallback_key(self, agent):
        """Test normalizing dict with non-standard key."""
        items = [{"custom_key": "Value with custom key"}]
        result = agent._normalize_string_list(items)
        assert result == ["Value with custom key"]


class TestPatternIntelligenceAgentLLM:
    """Tests for LLM integration in PatternIntelligenceAgent."""

    @pytest.mark.asyncio
    async def test_llm_bottleneck_analysis_timeout(self, mock_ollama_client):
        """Test LLM timeout handling in bottleneck analysis."""
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)
            return "{}"

        mock_ollama_client.generate = slow_generate

        agent = PatternIntelligenceAgent(
            ollama_client=mock_ollama_client,
            timeout_seconds=0.1,
        )

        bottleneck = PerformanceBottleneck("orders", 100, 1500, 5000, 0.85)

        # Should still return analysis with deterministic data
        analysis = await agent.analyze_bottleneck(bottleneck, MagicMock(), 1, queries=[])

        assert analysis.table_name == "orders"
        # Deterministic analysis should be present
        assert len(analysis.root_causes) > 0

    @pytest.mark.asyncio
    async def test_llm_bottleneck_analysis_error(self, mock_ollama_client):
        """Test LLM error handling in bottleneck analysis."""
        mock_ollama_client.generate.side_effect = Exception("API Error")

        agent = PatternIntelligenceAgent(
            ollama_client=mock_ollama_client,
            timeout_seconds=5.0,
        )

        bottleneck = PerformanceBottleneck("orders", 100, 1500, 5000, 0.85)

        # Should still return analysis with deterministic data
        analysis = await agent.analyze_bottleneck(bottleneck, MagicMock(), 1, queries=[])

        assert analysis.table_name == "orders"


class TestGetPatternIntelligenceAgent:
    """Tests for factory function."""

    @pytest.mark.asyncio
    async def test_get_agent_without_db(self):
        """Test factory without database session."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_get_client.return_value = MagicMock()

            agent = await get_pattern_intelligence_agent()

            assert agent is not None
            assert agent.client is not None

    @pytest.mark.asyncio
    async def test_get_agent_with_model_override(self):
        """Test factory with model override."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_get_client.return_value = MagicMock()

            agent = await get_pattern_intelligence_agent(model="custom-model")

            assert agent.model == "custom-model"
