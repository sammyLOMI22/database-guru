"""Tests for Phase 19.1: Small Model Narrative Optimization (tiered prompts)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.prompt_optimizer import ModelSize, get_model_size_for_model
from src.llm.prompts.narrative_tiers import (
    get_narrative_prompt,
    NARRATIVE_PROMPT_COMPACT,
    NARRATIVE_PROMPT_STANDARD,
    NARRATIVE_PROMPT_ENHANCED,
    MULTI_DB_PROMPT_COMPACT,
    MULTI_DB_PROMPT_STANDARD,
    MULTI_DB_PROMPT_ENHANCED,
    NARRATIVE_TOKEN_BUDGETS,
    MAX_SAMPLE_ROWS_BY_TIER,
    MAX_INSIGHTS_BY_TIER,
)
from src.llm.result_narrator import ResultNarrator


# =============================================================================
# Tier Detection Tests
# =============================================================================

class TestModelTierDetection:
    """Test model size detection for narrative tier selection."""

    def test_small_model_phi3(self):
        assert get_model_size_for_model("phi3") == ModelSize.SMALL

    def test_small_model_gemma_2b(self):
        assert get_model_size_for_model("gemma:2b") == ModelSize.SMALL

    def test_medium_model_llama_8b(self):
        assert get_model_size_for_model("llama3.1:8b") == ModelSize.MEDIUM

    def test_medium_model_mistral_7b(self):
        assert get_model_size_for_model("mistral:7b") == ModelSize.MEDIUM

    def test_large_model_qwen_32b(self):
        assert get_model_size_for_model("qwen2.5-coder:32b") == ModelSize.LARGE

    def test_large_model_llama_70b(self):
        assert get_model_size_for_model("llama3:70b") == ModelSize.LARGE

    def test_unknown_model_defaults_medium(self):
        assert get_model_size_for_model("") == ModelSize.MEDIUM

    def test_none_model_defaults_medium(self):
        """ResultNarrator with model=None should default to MEDIUM."""
        narrator = ResultNarrator(ollama_client=MagicMock(), model=None)
        assert narrator._get_model_tier() == ModelSize.MEDIUM


# =============================================================================
# Prompt Selection Tests
# =============================================================================

class TestPromptSelection:
    """Test that the correct prompt template is selected per tier."""

    def test_single_db_small_gets_compact(self):
        prompt = get_narrative_prompt(ModelSize.SMALL, multi_db=False)
        assert prompt == NARRATIVE_PROMPT_COMPACT
        assert len(prompt) < len(NARRATIVE_PROMPT_STANDARD)

    def test_single_db_medium_gets_standard(self):
        prompt = get_narrative_prompt(ModelSize.MEDIUM, multi_db=False)
        assert prompt == NARRATIVE_PROMPT_STANDARD

    def test_single_db_large_gets_enhanced(self):
        prompt = get_narrative_prompt(ModelSize.LARGE, multi_db=False)
        assert prompt == NARRATIVE_PROMPT_ENHANCED
        # Enhanced prompt is different from standard (focus on depth/quality)
        assert "senior data analyst" in prompt
        assert prompt != NARRATIVE_PROMPT_STANDARD

    def test_multi_db_small_gets_compact(self):
        prompt = get_narrative_prompt(ModelSize.SMALL, multi_db=True)
        assert prompt == MULTI_DB_PROMPT_COMPACT

    def test_multi_db_medium_gets_standard(self):
        prompt = get_narrative_prompt(ModelSize.MEDIUM, multi_db=True)
        assert prompt == MULTI_DB_PROMPT_STANDARD

    def test_multi_db_large_gets_enhanced(self):
        prompt = get_narrative_prompt(ModelSize.LARGE, multi_db=True)
        assert prompt == MULTI_DB_PROMPT_ENHANCED

    def test_compact_prompt_has_json_format(self):
        """Compact prompt should still request JSON output."""
        assert "JSON" in NARRATIVE_PROMPT_COMPACT
        assert "summary" in NARRATIVE_PROMPT_COMPACT

    def test_enhanced_prompt_mentions_quality(self):
        """Enhanced prompt should mention data quality."""
        assert "quality" in NARRATIVE_PROMPT_ENHANCED.lower()


# =============================================================================
# Statistics Compression Tests
# =============================================================================

class TestStatisticsCompression:
    """Test statistics compression by model tier."""

    def setup_method(self):
        self.narrator = ResultNarrator(ollama_client=MagicMock(), model="phi3")
        self.sample_stats = {
            "row_count": 100,
            "revenue": {
                "type": "numeric", "min": 10, "max": 1000,
                "avg": 250.5, "sum": 25050, "count": 100,
                "null_count": 0, "median": 200, "stdev": 150.3,
            },
            "cost": {
                "type": "numeric", "min": 5, "max": 500,
                "avg": 125.0, "sum": 12500, "count": 100,
                "null_count": 2, "median": 100, "stdev": 80.1,
            },
            "profit": {
                "type": "numeric", "min": 1, "max": 800,
                "avg": 125.5, "sum": 12550, "count": 100,
                "null_count": 0, "median": 100, "stdev": 120.0,
            },
            "extra_col": {
                "type": "numeric", "min": 0, "max": 10,
                "avg": 5, "sum": 500, "count": 100,
                "null_count": 0,
            },
            "category": {
                "type": "string", "unique_count": 5,
                "total_count": 100, "most_common": "A",
            },
        }

    def test_compact_limits_to_3_numeric_cols(self):
        """Compact compression should include at most 3 numeric columns."""
        result = self.narrator._format_essential_stats(self.sample_stats)
        parsed = json.loads(result)
        # row_count + at most 3 numeric columns
        numeric_keys = [k for k in parsed if k != "row_count"]
        assert len(numeric_keys) <= 3

    def test_compact_only_count_avg_min_max(self):
        """Compact stats should only have count, avg, min, max."""
        result = self.narrator._format_essential_stats(self.sample_stats)
        parsed = json.loads(result)
        for key in parsed:
            if key == "row_count":
                continue
            col_stats = parsed[key]
            assert "count" in col_stats
            assert "avg" in col_stats
            # Should NOT have stdev, median, sum in compact
            assert "stdev" not in col_stats
            assert "median" not in col_stats
            assert "sum" not in col_stats

    def test_compact_excludes_string_columns(self):
        """Compact stats should not include string column details."""
        result = self.narrator._format_essential_stats(self.sample_stats)
        parsed = json.loads(result)
        assert "category" not in parsed

    def test_standard_preserves_all(self):
        """Standard compression should preserve all statistics."""
        narrator = ResultNarrator(ollama_client=MagicMock(), model="mistral:7b")
        result = narrator._compress_statistics(self.sample_stats, ModelSize.MEDIUM)
        parsed = json.loads(result)
        assert "category" in parsed
        assert "revenue" in parsed
        assert "stdev" in parsed["revenue"]

    def test_enhanced_adds_range_and_cv(self):
        """Enhanced stats should add range and coefficient of variation."""
        narrator = ResultNarrator(ollama_client=MagicMock(), model="qwen2.5:32b")
        result = narrator._format_enhanced_stats(self.sample_stats)
        parsed = json.loads(result)
        assert "range" in parsed["revenue"]
        assert "cv" in parsed["revenue"]
        expected_range = 1000 - 10
        assert parsed["revenue"]["range"] == expected_range

    def test_empty_stats_handled(self):
        """Compression should handle empty statistics gracefully."""
        result = self.narrator._compress_statistics({}, ModelSize.SMALL)
        parsed = json.loads(result)
        assert parsed.get("row_count", 0) == 0


# =============================================================================
# Build Prompt Integration Tests
# =============================================================================

class TestBuildPromptIntegration:
    """Test that _build_prompt uses tier selection correctly."""

    def test_small_model_uses_compact_template(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="phi3:mini")
        results = [{"name": "A", "value": 100}, {"name": "B", "value": 200}]
        stats = {"row_count": 2, "value": {"type": "numeric", "min": 100, "max": 200, "avg": 150, "count": 2, "null_count": 0}}

        prompt = narrator._build_prompt("what values?", "SELECT *", results, stats, 2, 10.0)
        # Compact template is shorter and has "Data analyst." prefix
        assert "Data analyst." in prompt

    def test_medium_model_uses_standard_template(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="mistral:7b")
        results = [{"name": "A", "value": 100}, {"name": "B", "value": 200}]
        stats = {"row_count": 2}

        prompt = narrator._build_prompt("what values?", "SELECT *", results, stats, 2, 10.0)
        assert "compelling story" in prompt

    def test_large_model_uses_enhanced_template(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="qwen2.5:32b")
        results = [{"name": "A", "value": 100}, {"name": "B", "value": 200}]
        stats = {"row_count": 2}

        prompt = narrator._build_prompt("what values?", "SELECT *", results, stats, 2, 10.0)
        assert "senior data analyst" in prompt

    def test_sample_rows_limited_by_tier(self):
        """Small model should limit sample rows to MAX_SAMPLE_ROWS_BY_TIER[SMALL]."""
        narrator = ResultNarrator(ollama_client=MagicMock(), model="phi3")
        # Create 10 rows
        results = [{"name": f"Item{i}", "value": i * 100} for i in range(10)]
        stats = {"row_count": 10}

        prompt = narrator._build_prompt("list items", "SELECT *", results, stats, 10, 5.0)
        max_rows = MAX_SAMPLE_ROWS_BY_TIER[ModelSize.SMALL]
        # Count how many "Item" entries appear in the prompt
        item_count = prompt.count("Item")
        assert item_count <= max_rows

    def test_multi_db_small_uses_compact(self):
        narrator = ResultNarrator(ollama_client=MagicMock(), model="phi3")
        results = [
            {"_source_database": "db1", "name": "A", "value": 100},
            {"_source_database": "db2", "name": "B", "value": 200},
        ]
        stats = {"row_count": 2}

        prompt = narrator._build_multi_database_prompt(
            "compare", "SELECT *", results, stats, 2, 10.0, ["db1", "db2"]
        )
        assert "Data analyst comparing databases" in prompt


# =============================================================================
# Token Budget Tests
# =============================================================================

class TestTokenBudgets:
    """Test token budget configuration."""

    def test_small_budget_is_smallest(self):
        assert NARRATIVE_TOKEN_BUDGETS[ModelSize.SMALL] < NARRATIVE_TOKEN_BUDGETS[ModelSize.MEDIUM]

    def test_medium_budget_is_middle(self):
        assert NARRATIVE_TOKEN_BUDGETS[ModelSize.SMALL] < NARRATIVE_TOKEN_BUDGETS[ModelSize.MEDIUM]
        assert NARRATIVE_TOKEN_BUDGETS[ModelSize.MEDIUM] < NARRATIVE_TOKEN_BUDGETS[ModelSize.LARGE]

    def test_max_insights_increases_with_tier(self):
        assert MAX_INSIGHTS_BY_TIER[ModelSize.SMALL] < MAX_INSIGHTS_BY_TIER[ModelSize.MEDIUM]
        assert MAX_INSIGHTS_BY_TIER[ModelSize.MEDIUM] < MAX_INSIGHTS_BY_TIER[ModelSize.LARGE]

    def test_max_sample_rows_increases_with_tier(self):
        assert MAX_SAMPLE_ROWS_BY_TIER[ModelSize.SMALL] < MAX_SAMPLE_ROWS_BY_TIER[ModelSize.MEDIUM]
        assert MAX_SAMPLE_ROWS_BY_TIER[ModelSize.MEDIUM] < MAX_SAMPLE_ROWS_BY_TIER[ModelSize.LARGE]
