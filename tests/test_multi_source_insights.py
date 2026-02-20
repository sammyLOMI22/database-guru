"""Tests for Phase 19.3: Multi-Source Data Quality Insights."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.llm.result_narrator import (
    ResultNarrator,
    DataQualityMetrics,
    GapInsight,
    MultiSourceQualityReport,
)


# =============================================================================
# Data Quality Metrics Tests
# =============================================================================

class TestCalculateQualityMetrics:
    """Test per-database quality metric calculation."""

    def setup_method(self):
        self.narrator = ResultNarrator(ollama_client=MagicMock(), model="qwen2.5:32b")

    def test_empty_results(self):
        m = self.narrator._calculate_quality_metrics([], "db1")
        assert m.database == "db1"
        assert m.row_count == 0
        assert m.completeness == 1.0

    def test_null_rate_calculation(self):
        results = [
            {"name": "Alice", "score": 90},
            {"name": None, "score": 80},
            {"name": "Charlie", "score": None},
        ]
        m = self.narrator._calculate_quality_metrics(results, "testdb")
        assert m.row_count == 3
        assert m.null_rates["name"] == pytest.approx(1 / 3, rel=1e-2)
        assert m.null_rates["score"] == pytest.approx(1 / 3, rel=1e-2)

    def test_completeness_all_filled(self):
        results = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        m = self.narrator._calculate_quality_metrics(results, "db")
        assert m.completeness == 1.0

    def test_completeness_with_nulls(self):
        results = [
            {"a": 1, "b": None},
            {"a": None, "b": None},
        ]
        m = self.narrator._calculate_quality_metrics(results, "db")
        # 4 total cells, 3 nulls -> completeness = 0.25
        assert m.completeness == pytest.approx(0.25, rel=1e-2)

    def test_duplicate_detection(self):
        results = [
            {"name": "Alice", "value": 100},
            {"name": "Alice", "value": 100},
            {"name": "Bob", "value": 200},
        ]
        m = self.narrator._calculate_quality_metrics(results, "db")
        assert m.duplicate_rate == pytest.approx(1 / 3, rel=1e-2)

    def test_no_duplicates(self):
        results = [
            {"name": "Alice", "value": 100},
            {"name": "Bob", "value": 200},
        ]
        m = self.narrator._calculate_quality_metrics(results, "db")
        assert m.duplicate_rate == 0.0

    def test_freshness_detection(self):
        results = [
            {"date": "2025-01-01", "value": 10},
            {"date": "2025-06-15", "value": 20},
            {"date": "2025-03-10", "value": 30},
        ]
        m = self.narrator._calculate_quality_metrics(results, "db")
        assert m.freshness == "2025-06-15"

    def test_source_database_column_excluded(self):
        results = [
            {"_source_database": "db1", "name": "Alice"},
            {"_source_database": "db1", "name": "Bob"},
        ]
        m = self.narrator._calculate_quality_metrics(results, "db1")
        assert "_source_database" not in m.null_rates


# =============================================================================
# Gap Detection Tests
# =============================================================================

class TestGapDetection:
    """Test cross-database coverage gap detection."""

    def setup_method(self):
        self.narrator = ResultNarrator(ollama_client=MagicMock(), model="qwen2.5:32b")

    def test_no_gaps_when_all_dbs_have_data(self):
        db_results = {
            "db1": [{"col_a": 1, "col_b": 2}],
            "db2": [{"col_a": 3, "col_b": 4}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        assert len(report.gap_insights) == 0

    def test_gap_detected_when_column_all_null(self):
        db_results = {
            "db1": [{"col_a": 1, "col_b": 2}],
            "db2": [{"col_a": 3, "col_b": None}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        gaps = [g for g in report.gap_insights if g.column == "col_b"]
        assert len(gaps) == 1
        assert "db1" in gaps[0].present_in
        assert "db2" in gaps[0].missing_in

    def test_gap_multiple_dbs(self):
        db_results = {
            "db1": [{"x": 1, "y": 10}],
            "db2": [{"x": 2, "y": None}],
            "db3": [{"x": None, "y": 30}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        x_gaps = [g for g in report.gap_insights if g.column == "x"]
        y_gaps = [g for g in report.gap_insights if g.column == "y"]
        assert len(x_gaps) == 1
        assert "db3" in x_gaps[0].missing_in
        assert len(y_gaps) == 1
        assert "db2" in y_gaps[0].missing_in

    def test_empty_results_no_crash(self):
        db_results = {"db1": [], "db2": []}
        report = self.narrator._build_multi_source_quality_report(db_results)
        assert len(report.gap_insights) == 0


# =============================================================================
# Quality Report Tests
# =============================================================================

class TestMultiSourceQualityReport:
    """Test the full quality report generation."""

    def setup_method(self):
        self.narrator = ResultNarrator(ollama_client=MagicMock(), model="qwen2.5:32b")

    def test_freshest_db_detected(self):
        db_results = {
            "old_db": [{"date": "2024-01-01", "val": 1}],
            "new_db": [{"date": "2025-12-01", "val": 2}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        assert report.freshest_db == "new_db"

    def test_most_complete_db_detected(self):
        db_results = {
            "sparse_db": [{"a": None, "b": None}],
            "full_db": [{"a": 1, "b": 2}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        assert report.most_complete_db == "full_db"

    def test_format_summary_not_empty(self):
        db_results = {
            "db1": [{"x": 1}],
            "db2": [{"x": 2}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        summary = report.format_summary()
        assert "DATA QUALITY COMPARISON" in summary
        assert "db1" in summary
        assert "db2" in summary

    def test_format_summary_includes_gaps(self):
        db_results = {
            "db1": [{"x": 1, "y": 10}],
            "db2": [{"x": 2, "y": None}],
        }
        report = self.narrator._build_multi_source_quality_report(db_results)
        summary = report.format_summary()
        assert "Coverage gaps" in summary
        assert "'y'" in summary

    def test_format_summary_empty_when_no_metrics(self):
        report = MultiSourceQualityReport()
        assert report.format_summary() == ""


# =============================================================================
# Prompt Integration Tests
# =============================================================================

class TestQualityInPrompt:
    """Test that quality summary appears in enhanced multi-DB prompts."""

    def test_large_model_prompt_includes_quality(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="qwen2.5:32b")
        results = [
            {"_source_database": "db1", "name": "A", "value": 100},
            {"_source_database": "db2", "name": "B", "value": None},
        ]
        stats = {"row_count": 2}

        quality_text = "DATA QUALITY COMPARISON:\n  - db1: 1 rows, 100% complete"
        prompt = narrator._build_multi_database_prompt(
            "compare", "SELECT *", results, stats, 2, 10.0,
            ["db1", "db2"], quality_summary=quality_text,
        )
        assert "DATA QUALITY COMPARISON" in prompt

    def test_medium_model_prompt_no_quality(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="mistral:7b")
        results = [
            {"_source_database": "db1", "name": "A", "value": 100},
        ]
        stats = {"row_count": 1}

        prompt = narrator._build_multi_database_prompt(
            "query", "SELECT *", results, stats, 1, 5.0,
            ["db1"],
        )
        # Medium tier template doesn't have quality_summary placeholder
        assert "DATA QUALITY COMPARISON" not in prompt

    def test_small_model_prompt_no_quality(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="phi3")
        results = [
            {"_source_database": "db1", "name": "A", "value": 100},
        ]
        stats = {"row_count": 1}

        prompt = narrator._build_multi_database_prompt(
            "query", "SELECT *", results, stats, 1, 5.0,
            ["db1"],
        )
        assert "DATA QUALITY COMPARISON" not in prompt


# =============================================================================
# Cached Quality Report Tests
# =============================================================================

class TestCachedQualityReport:
    """Test caching of quality reports."""

    @pytest.mark.asyncio
    async def test_quality_report_cached_on_compute(self):
        mock_cache = MagicMock()
        mock_cache.get_patterns = AsyncMock(return_value=None)
        mock_cache.set_patterns = AsyncMock()

        narrator = ResultNarrator(
            ollama_client=MagicMock(), model="qwen2.5:32b",
            analytics_cache=mock_cache,
        )

        db_results = {
            "db1": [{"x": 1}],
            "db2": [{"x": 2}],
        }
        report = await narrator._get_or_compute_quality_report(db_results)
        assert isinstance(report, MultiSourceQualityReport)
        mock_cache.set_patterns.assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_report_returned_from_cache(self):
        cached_data = {
            "databases": ["db1", "db2"],
            "quality_metrics": [
                {"database": "db1", "row_count": 5, "null_rates": {},
                 "duplicate_rate": 0, "completeness": 1.0, "freshness": None},
            ],
            "gap_insights": [],
            "freshest_db": "db1",
            "most_complete_db": "db1",
        }
        mock_cache = MagicMock()
        mock_cache.get_patterns = AsyncMock(return_value=cached_data)

        narrator = ResultNarrator(
            ollama_client=MagicMock(), model="qwen2.5:32b",
            analytics_cache=mock_cache,
        )

        db_results = {"db1": [{"x": 1}]}
        report = await narrator._get_or_compute_quality_report(db_results)
        assert report.freshest_db == "db1"
        assert len(report.quality_metrics) == 1
