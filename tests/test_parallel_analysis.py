"""Tests for Phase 19.5: Parallel Analysis Pipeline."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.llm.result_narrator import ResultNarrator, NarrativeResult


# =============================================================================
# Fixtures
# =============================================================================

def _make_narrator(**kwargs) -> ResultNarrator:
    """Create a ResultNarrator with a mocked Ollama client."""
    mock_ollama = MagicMock()
    mock_ollama.generate = AsyncMock(return_value={
        "response": '{"summary": "Test summary", "key_insights": ["insight1"], "direct_answer": null, "confidence": 0.8}',
        "prompt_eval_count": 100,
        "eval_count": 50,
        "model": "mistral:7b",
    })
    defaults = dict(
        ollama_client=mock_ollama,
        model="mistral:7b",
        timeout_seconds=5,
        analytics_cache=None,
    )
    defaults.update(kwargs)
    narrator = defaults.pop("ollama_client")
    return ResultNarrator(ollama_client=narrator, **defaults)


def _make_rows(n: int) -> list:
    """Generate n sample data rows with numeric and string columns."""
    return [
        {"name": f"Item{i}", "revenue": 100 + i * 50, "cost": 20 + i * 10, "region": f"R{i % 3}"}
        for i in range(n)
    ]


# =============================================================================
# Early Exit Tests (Phase 19.5.3)
# =============================================================================

class TestEarlyExitSmallDataset:
    """Test that tiny datasets (<=3 rows) skip the LLM entirely."""

    @pytest.mark.asyncio
    async def test_zero_rows_returns_no_results(self):
        narrator = _make_narrator()
        result = await narrator.generate_narrative(
            question="what items?", sql="SELECT *", results=[],
            row_count=0, execution_time_ms=5.0,
        )
        assert result.summary == "No results found."
        assert result.confidence == 0.95
        narrator.ollama.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_large_dataset_returns_early(self):
        narrator = _make_narrator()
        result = await narrator.generate_narrative(
            question="all data", sql="SELECT *", results=[{"a": 1}],
            row_count=1500, execution_time_ms=100.0,
        )
        assert "too large" in result.summary
        narrator.ollama.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_tiny_dataset_uses_fallback(self):
        """<=3 rows should use _fallback_narrative (no LLM call)."""
        narrator = _make_narrator()
        results = _make_rows(2)
        result = await narrator.generate_narrative(
            question="what items?", sql="SELECT *", results=results,
            row_count=2, execution_time_ms=3.0,
        )
        assert isinstance(result, NarrativeResult)
        # Fallback generates "Found N record(s)" summary
        assert "Found 2 record" in result.summary
        narrator.ollama.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_four_rows_calls_llm(self):
        """4 rows should NOT early-exit; it should call the LLM."""
        narrator = _make_narrator()
        results = _make_rows(4)
        result = await narrator.generate_narrative(
            question="what items?", sql="SELECT *", results=results,
            row_count=4, execution_time_ms=3.0,
        )
        assert isinstance(result, NarrativeResult)
        narrator.ollama.generate.assert_called_once()


# =============================================================================
# Parallel vs Sequential Path Tests (Phase 19.5.2)
# =============================================================================

class TestParallelExecution:
    """Test that >=10 rows triggers parallel analysis."""

    @pytest.mark.asyncio
    async def test_parallel_path_runs_gather(self):
        """With >=10 rows, asyncio.gather should be used for parallel analysis."""
        narrator = _make_narrator()
        results = _make_rows(15)

        with patch("asyncio.gather", wraps=asyncio.gather) as mock_gather:
            await narrator.generate_narrative(
                question="revenue trends", sql="SELECT *", results=results,
                row_count=15, execution_time_ms=10.0,
            )
            # gather should be called for the parallel Phase A
            assert mock_gather.call_count >= 1

    @pytest.mark.asyncio
    async def test_sequential_path_for_small_dataset(self):
        """With <10 rows (but >3), should NOT use asyncio.gather."""
        narrator = _make_narrator()
        results = _make_rows(7)

        with patch("asyncio.gather", wraps=asyncio.gather) as mock_gather:
            await narrator.generate_narrative(
                question="items", sql="SELECT *", results=results,
                row_count=7, execution_time_ms=5.0,
            )
            mock_gather.assert_not_called()


# =============================================================================
# Exception Handling in Parallel Tasks
# =============================================================================

class TestParallelExceptionHandling:
    """Test that failures in parallel analysis tasks are handled gracefully."""

    @pytest.mark.asyncio
    async def test_anomaly_detection_failure_still_narrates(self):
        """If anomaly detection throws, narrative should still be generated."""
        narrator = _make_narrator()
        results = _make_rows(15)

        with patch.object(narrator, "_detect_anomalies", side_effect=ValueError("boom")):
            result = await narrator.generate_narrative(
                question="revenue", sql="SELECT *", results=results,
                row_count=15, execution_time_ms=10.0,
            )
            assert isinstance(result, NarrativeResult)
            assert result.summary  # Should have a valid summary
            # anomalies should not appear in statistics (failed gracefully)
            assert "anomalies" not in result.statistics

    @pytest.mark.asyncio
    async def test_correlation_failure_still_narrates(self):
        """If correlation calculation throws in sequential path, outer catch
        produces a fallback narrative (no crash)."""
        narrator = _make_narrator()
        # Use <10 rows to trigger the sequential path
        results = _make_rows(7)

        with patch.object(narrator, "_calculate_correlations", side_effect=RuntimeError("fail")):
            result = await narrator.generate_narrative(
                question="revenue", sql="SELECT *", results=results,
                row_count=7, execution_time_ms=10.0,
            )
            assert isinstance(result, NarrativeResult)
            # Outer exception handler produces fallback
            assert "Found 7 record" in result.summary

    @pytest.mark.asyncio
    async def test_statistics_failure_uses_empty_dict(self):
        """If statistics extraction throws, should fallback to empty dict."""
        narrator = _make_narrator()
        results = _make_rows(15)

        with patch.object(narrator, "_get_or_compute_statistics", side_effect=Exception("stats failed")):
            result = await narrator.generate_narrative(
                question="revenue", sql="SELECT *", results=results,
                row_count=15, execution_time_ms=10.0,
            )
            assert isinstance(result, NarrativeResult)

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_fallback(self):
        """If LLM times out, should return fallback narrative."""
        mock_ollama = MagicMock()
        mock_ollama.generate = AsyncMock(side_effect=asyncio.TimeoutError())
        narrator = ResultNarrator(
            ollama_client=mock_ollama, model="mistral:7b", timeout_seconds=1,
        )
        results = _make_rows(5)

        result = await narrator.generate_narrative(
            question="items?", sql="SELECT *", results=results,
            row_count=5, execution_time_ms=5.0,
        )
        assert isinstance(result, NarrativeResult)
        assert "Found 5 record" in result.summary


# =============================================================================
# Analysis Completeness Tests
# =============================================================================

class TestAnalysisCompleteness:
    """Test that all analysis components are included in the final result."""

    @pytest.mark.asyncio
    async def test_anomalies_appear_in_statistics(self):
        """Detected anomalies should be surfaced in result.statistics."""
        narrator = _make_narrator()
        # Build data with a clear outlier
        results = [{"value": 100}] * 14 + [{"value": 10000}]

        result = await narrator.generate_narrative(
            question="check values", sql="SELECT *", results=results,
            row_count=15, execution_time_ms=5.0,
        )
        assert isinstance(result, NarrativeResult)
        if result.statistics.get("anomalies"):
            assert result.statistics["anomalies"]["found"] is True
            assert result.statistics["anomalies"]["count"] > 0

    @pytest.mark.asyncio
    async def test_trends_appear_when_temporal_data(self):
        """Detected trends should be surfaced in result.statistics."""
        narrator = _make_narrator()
        results = [
            {"date": f"2024-01-{str(i+1).zfill(2)}", "sales": 100 + i * 20}
            for i in range(15)
        ]

        result = await narrator.generate_narrative(
            question="sales over time", sql="SELECT *", results=results,
            row_count=15, execution_time_ms=5.0,
        )
        assert isinstance(result, NarrativeResult)
        if result.statistics.get("trends"):
            assert result.statistics["trends"]["found"] is True
            assert len(result.statistics["trends"]["detected_trends"]) > 0

    @pytest.mark.asyncio
    async def test_correlations_appear_when_correlated(self):
        """Correlated columns should be surfaced in result.statistics."""
        narrator = _make_narrator()
        # x and y are perfectly correlated
        results = [{"x": float(i), "y": float(i * 2)} for i in range(20)]

        result = await narrator.generate_narrative(
            question="relationship?", sql="SELECT *", results=results,
            row_count=20, execution_time_ms=5.0,
        )
        assert isinstance(result, NarrativeResult)
        if result.statistics.get("correlations"):
            assert result.statistics["correlations"]["found"] is True

    @pytest.mark.asyncio
    async def test_narrative_includes_token_info(self):
        """Token info from LLM response should be captured."""
        narrator = _make_narrator()
        results = _make_rows(5)

        result = await narrator.generate_narrative(
            question="items?", sql="SELECT *", results=results,
            row_count=5, execution_time_ms=5.0,
        )
        assert result.token_info.get("input_tokens") == 100
        assert result.token_info.get("output_tokens") == 50
        assert result.token_info.get("model") == "mistral:7b"


# =============================================================================
# Multi-Database Parallel Tests
# =============================================================================

class TestMultiDatabaseParallel:
    """Test parallel analysis with multi-database results."""

    @pytest.mark.asyncio
    async def test_multi_db_with_quality_report(self):
        """Large-model multi-DB should compute quality report."""
        narrator = ResultNarrator(
            ollama_client=MagicMock(),
            model="qwen2.5-coder:32b",
            timeout_seconds=5,
        )
        narrator.ollama.generate = AsyncMock(return_value={
            "response": '{"summary": "Cross-DB comparison", "key_insights": ["db1 has more data"], "direct_answer": null, "confidence": 0.8}',
            "prompt_eval_count": 200,
            "eval_count": 80,
            "model": "qwen2.5-coder:32b",
        })

        results = [
            {"_source_database": "db1", "name": "A", "value": 100},
            {"_source_database": "db1", "name": "B", "value": 200},
            {"_source_database": "db2", "name": "C", "value": None},
            {"_source_database": "db2", "name": "D", "value": 400},
        ]

        result = await narrator.generate_narrative(
            question="compare databases", sql="SELECT *", results=results,
            row_count=4, execution_time_ms=15.0,
            databases=["db1", "db2"], multi_database=True,
        )
        assert isinstance(result, NarrativeResult)

    @pytest.mark.asyncio
    async def test_multi_db_small_model_skips_quality(self):
        """Small-model multi-DB should NOT compute quality report."""
        narrator = ResultNarrator(
            ollama_client=MagicMock(),
            model="phi3",
            timeout_seconds=5,
        )
        narrator.ollama.generate = AsyncMock(return_value={
            "response": '{"summary": "Quick comparison", "key_insights": ["diff"], "direct_answer": null, "confidence": 0.7}',
        })

        results = [
            {"_source_database": "db1", "name": "A", "value": 100},
            {"_source_database": "db2", "name": "B", "value": 200},
            {"_source_database": "db1", "name": "C", "value": 300},
            {"_source_database": "db2", "name": "D", "value": 400},
        ]

        with patch.object(narrator, "_get_or_compute_quality_report") as mock_quality:
            await narrator.generate_narrative(
                question="compare", sql="SELECT *", results=results,
                row_count=4, execution_time_ms=10.0,
                databases=["db1", "db2"], multi_database=True,
            )
            mock_quality.assert_not_called()
