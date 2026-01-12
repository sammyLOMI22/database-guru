"""
Tests for Prompt Optimizer (Phase 2.2)

Tests the prompt optimization system including:
- Model size detection
- Token budget allocations
- Schema compression
- Example selection
- Model-specific templates
"""
import pytest
from src.llm.prompt_optimizer import (
    ModelSize,
    ModelFamily,
    PromptBudget,
    PromptOptimizer,
    OptimizedPrompt,
    PROMPT_BUDGETS,
    MODEL_TEMPLATES,
    COMPACT_SYSTEM_PROMPTS,
    KNOWN_MODEL_SIZES,
    get_model_size_for_model,
    get_model_family,
    get_prompt_optimizer,
    build_optimized_prompt,
    _count_tokens,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_schema():
    """Sample schema with multiple tables and relationships."""
    return {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "email", "type": "VARCHAR(255)"},
                    {"name": "state", "type": "VARCHAR(2)"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "foreign_keys": [],
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "customer_id", "type": "INTEGER"},
                    {"name": "total", "type": "DECIMAL(10,2)"},
                    {"name": "status", "type": "VARCHAR(20)"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "foreign_keys": [
                    {"column": "customer_id", "referred_table": "customers", "referred_column": "id"}
                ],
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "price", "type": "DECIMAL(10,2)"},
                    {"name": "category", "type": "VARCHAR(50)"},
                ],
                "foreign_keys": [],
            },
            "order_items": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "order_id", "type": "INTEGER"},
                    {"name": "product_id", "type": "INTEGER"},
                    {"name": "quantity", "type": "INTEGER"},
                    {"name": "unit_price", "type": "DECIMAL(10,2)"},
                ],
                "foreign_keys": [
                    {"column": "order_id", "referred_table": "orders", "referred_column": "id"},
                    {"column": "product_id", "referred_table": "products", "referred_column": "id"},
                ],
            },
            "categories": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "VARCHAR(50)"},
                    {"name": "description", "type": "TEXT"},
                ],
                "foreign_keys": [],
            },
        }
    }


@pytest.fixture
def sample_examples():
    """Sample few-shot examples for testing."""
    return [
        {"question": "count all customers", "sql": "SELECT COUNT(*) FROM customers"},
        {"question": "list all products", "sql": "SELECT * FROM products LIMIT 100"},
        {"question": "show orders by customer", "sql": "SELECT c.name, COUNT(o.id) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name"},
        {"question": "total revenue", "sql": "SELECT SUM(total) FROM orders"},
        {"question": "top 5 products by price", "sql": "SELECT * FROM products ORDER BY price DESC LIMIT 5"},
    ]


# =============================================================================
# MODEL SIZE DETECTION TESTS
# =============================================================================

class TestModelSizeDetection:
    """Test model size detection from model names."""

    def test_small_models_detected(self):
        """Small models (< 7B) should be detected correctly."""
        assert get_model_size_for_model("phi3") == ModelSize.SMALL
        assert get_model_size_for_model("phi-3:latest") == ModelSize.SMALL
        assert get_model_size_for_model("tinyllama") == ModelSize.SMALL
        assert get_model_size_for_model("gemma:2b") == ModelSize.SMALL
        assert get_model_size_for_model("qwen2.5:3b") == ModelSize.SMALL

    def test_medium_models_detected(self):
        """Medium models (7-13B) should be detected correctly."""
        assert get_model_size_for_model("llama3.2:latest") == ModelSize.MEDIUM
        assert get_model_size_for_model("llama3.1:8b") == ModelSize.MEDIUM
        assert get_model_size_for_model("mistral") == ModelSize.MEDIUM
        assert get_model_size_for_model("mistral:7b") == ModelSize.MEDIUM
        assert get_model_size_for_model("duckdb-nsql") == ModelSize.MEDIUM
        assert get_model_size_for_model("codellama:7b") == ModelSize.MEDIUM

    def test_large_models_detected(self):
        """Large models (13B+) should be detected correctly."""
        assert get_model_size_for_model("qwen2.5:32b") == ModelSize.LARGE
        assert get_model_size_for_model("llama3.1:70b") == ModelSize.LARGE
        assert get_model_size_for_model("gemma2:27b") == ModelSize.LARGE
        assert get_model_size_for_model("codellama:34b") == ModelSize.LARGE

    def test_unknown_model_defaults_to_medium(self):
        """Unknown models should default to MEDIUM."""
        assert get_model_size_for_model("unknown-model") == ModelSize.MEDIUM
        assert get_model_size_for_model("custom-model-v1") == ModelSize.MEDIUM

    def test_empty_model_defaults_to_medium(self):
        """Empty or None model names should default to MEDIUM."""
        assert get_model_size_for_model("") == ModelSize.MEDIUM
        assert get_model_size_for_model(None) == ModelSize.MEDIUM

    def test_size_indicator_detection(self):
        """Models with size indicators in name should be detected."""
        assert get_model_size_for_model("custom-model-3b") == ModelSize.SMALL
        assert get_model_size_for_model("my-model-7b") == ModelSize.MEDIUM
        assert get_model_size_for_model("big-model-70b") == ModelSize.LARGE


# =============================================================================
# MODEL FAMILY DETECTION TESTS
# =============================================================================

class TestModelFamilyDetection:
    """Test model family detection from model names."""

    def test_llama_family_detected(self):
        """Llama models should be detected."""
        assert get_model_family("llama3.2") == ModelFamily.LLAMA
        assert get_model_family("llama3.1:8b") == ModelFamily.LLAMA
        assert get_model_family("codellama:7b") == ModelFamily.LLAMA

    def test_qwen_family_detected(self):
        """Qwen models should be detected."""
        assert get_model_family("qwen2.5:7b") == ModelFamily.QWEN
        assert get_model_family("qwen2.5:32b") == ModelFamily.QWEN

    def test_gemma_family_detected(self):
        """Gemma models should be detected."""
        assert get_model_family("gemma:7b") == ModelFamily.GEMMA
        assert get_model_family("gemma2:9b") == ModelFamily.GEMMA

    def test_mistral_family_detected(self):
        """Mistral models should be detected."""
        assert get_model_family("mistral") == ModelFamily.MISTRAL
        assert get_model_family("mixtral:8x7b") == ModelFamily.MISTRAL

    def test_sql_specialized_models_detected(self):
        """SQL-specialized models should be detected."""
        assert get_model_family("duckdb-nsql") == ModelFamily.DUCKDB_NSQL
        assert get_model_family("sqlcoder:7b") == ModelFamily.SQLCODER

    def test_unknown_family_defaults_to_default(self):
        """Unknown models should default to DEFAULT family."""
        assert get_model_family("unknown-model") == ModelFamily.DEFAULT
        assert get_model_family("") == ModelFamily.DEFAULT
        assert get_model_family(None) == ModelFamily.DEFAULT


# =============================================================================
# PROMPT BUDGET TESTS
# =============================================================================

class TestPromptBudgets:
    """Test token budget allocations."""

    def test_all_sizes_have_budgets(self):
        """Ensure all model sizes have budget allocations."""
        for size in ModelSize:
            assert size in PROMPT_BUDGETS
            assert isinstance(PROMPT_BUDGETS[size], PromptBudget)

    def test_small_budget_has_no_examples(self):
        """Small models should have zero example budget (zero-shot)."""
        budget = PROMPT_BUDGETS[ModelSize.SMALL]
        assert budget.examples == 0
        assert budget.history == 0

    def test_budget_totals_are_correct(self):
        """Budget totals should match expected values."""
        assert PROMPT_BUDGETS[ModelSize.SMALL].total == 2000
        assert PROMPT_BUDGETS[ModelSize.MEDIUM].total == 4000
        assert PROMPT_BUDGETS[ModelSize.LARGE].total == 7000

    def test_budget_components_are_positive(self):
        """All budget components should be non-negative."""
        for size, budget in PROMPT_BUDGETS.items():
            assert budget.system_prompt >= 0
            assert budget.schema_context >= 0
            assert budget.examples >= 0
            assert budget.history >= 0
            assert budget.user_query >= 0
            assert budget.buffer >= 0

    def test_input_budget_excludes_buffer(self):
        """Input budget should exclude response buffer."""
        for size, budget in PROMPT_BUDGETS.items():
            assert budget.input_budget == budget.total - budget.buffer


# =============================================================================
# MODEL TEMPLATE TESTS
# =============================================================================

class TestModelTemplates:
    """Test model-specific prompt templates."""

    def test_all_families_have_templates(self):
        """Ensure all model families have templates."""
        for family in ModelFamily:
            assert family in MODEL_TEMPLATES

    def test_llama_template_markers(self):
        """Llama template should have correct markers."""
        template = MODEL_TEMPLATES[ModelFamily.LLAMA]
        assert "<|begin_of_text|>" in template.system_prefix
        assert "<|eot_id|>" in template.system_suffix
        assert template.uses_chat_format is True

    def test_qwen_template_markers(self):
        """Qwen template should have correct markers."""
        template = MODEL_TEMPLATES[ModelFamily.QWEN]
        assert "<|im_start|>" in template.system_prefix
        assert "<|im_end|>" in template.system_suffix

    def test_sql_specialized_templates_are_minimal(self):
        """SQL-specialized models should have minimal system prompts."""
        for family in [ModelFamily.DUCKDB_NSQL, ModelFamily.SQLCODER]:
            template = MODEL_TEMPLATES[family]
            assert template.uses_chat_format is False

    def test_default_template_is_minimal(self):
        """Default template should be minimal with no special markers."""
        template = MODEL_TEMPLATES[ModelFamily.DEFAULT]
        assert template.system_prefix == ""
        assert template.uses_chat_format is True


# =============================================================================
# COMPACT SYSTEM PROMPTS TESTS
# =============================================================================

class TestCompactSystemPrompts:
    """Test compact system prompts for different tasks and sizes."""

    def test_all_tasks_have_prompts(self):
        """Ensure all task types have prompts defined."""
        assert "sql_generation" in COMPACT_SYSTEM_PROMPTS
        assert "error_correction" in COMPACT_SYSTEM_PROMPTS
        assert "narratives" in COMPACT_SYSTEM_PROMPTS

    def test_all_sizes_have_prompts_for_sql(self):
        """SQL generation should have prompts for all sizes."""
        sql_prompts = COMPACT_SYSTEM_PROMPTS["sql_generation"]
        for size in ModelSize:
            assert size in sql_prompts

    def test_small_prompts_are_shorter(self):
        """Small model prompts should be shorter than large."""
        sql_prompts = COMPACT_SYSTEM_PROMPTS["sql_generation"]
        small_len = len(sql_prompts[ModelSize.SMALL])
        large_len = len(sql_prompts[ModelSize.LARGE])
        assert small_len < large_len

    def test_prompts_contain_dialect_placeholder(self):
        """Prompts should contain dialect placeholder for formatting."""
        sql_prompts = COMPACT_SYSTEM_PROMPTS["sql_generation"]
        for size, prompt in sql_prompts.items():
            assert "{dialect}" in prompt


# =============================================================================
# SCHEMA COMPRESSION TESTS
# =============================================================================

class TestSchemaCompression:
    """Test schema compression functionality."""

    def test_extracts_mentioned_tables(self, sample_schema):
        """Should extract tables directly mentioned in question."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        tables = optimizer._extract_table_mentions("show all customers", sample_schema)
        assert "customers" in tables

    def test_extracts_plural_mentions(self, sample_schema):
        """Should handle singular/plural variations."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        tables = optimizer._extract_table_mentions("show customer list", sample_schema)
        assert "customers" in tables

    def test_includes_related_tables(self, sample_schema):
        """Should include FK-related tables."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        mentioned = {"orders"}
        related = optimizer._get_related_tables(mentioned, sample_schema)
        # orders has FK to customers
        assert "customers" in related

    def test_compression_returns_tuple(self, sample_schema):
        """Compression should return (schema_str, included, excluded)."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        result = optimizer.compress_schema(sample_schema, "show all customers")
        assert isinstance(result, tuple)
        assert len(result) == 3
        compressed, included, excluded = result
        assert isinstance(compressed, str)
        assert isinstance(included, list)
        assert isinstance(excluded, list)

    def test_compression_excludes_irrelevant_tables(self, sample_schema):
        """Should exclude tables not relevant to question."""
        optimizer = PromptOptimizer(ModelSize.SMALL)
        compressed, included, excluded = optimizer.compress_schema(
            sample_schema, "show all customers"
        )
        # categories is not related to customers
        assert "categories" in excluded or "categories" not in included

    def test_compression_respects_budget(self, sample_schema):
        """Compressed schema should respect token budget."""
        optimizer = PromptOptimizer(ModelSize.SMALL)
        compressed, _, _ = optimizer.compress_schema(
            sample_schema, "show all customers", max_tokens=200
        )
        tokens = _count_tokens(compressed)
        assert tokens <= 200


# =============================================================================
# EXAMPLE SELECTION TESTS
# =============================================================================

class TestExampleSelection:
    """Test dynamic example selection."""

    def test_zero_shot_for_small_models(self, sample_examples):
        """Small models should get zero examples."""
        optimizer = PromptOptimizer(ModelSize.SMALL)
        examples = optimizer.select_examples("count customers", sample_examples)
        assert len(examples) == 0

    def test_selects_relevant_examples(self, sample_examples):
        """Should prefer examples similar to question."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        examples = optimizer.select_examples(
            "count all customers",
            sample_examples,
            max_tokens=500
        )
        # Should include the count example
        assert any("COUNT" in ex.get("sql", "") for ex in examples)

    def test_respects_token_budget(self, sample_examples):
        """Should not exceed token budget for examples."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        examples = optimizer.select_examples(
            "any question",
            sample_examples,
            max_tokens=100  # Very small budget
        )
        # Should limit examples due to budget
        total_tokens = sum(_count_tokens(f"{e['question']} {e['sql']}") for e in examples)
        assert total_tokens <= 100

    def test_empty_examples_returns_empty(self):
        """Empty example list should return empty."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        examples = optimizer.select_examples("any question", [])
        assert examples == []


# =============================================================================
# PROMPT OPTIMIZATION TESTS
# =============================================================================

class TestPromptOptimization:
    """Test end-to-end prompt optimization."""

    def test_optimization_returns_valid_result(self, sample_schema):
        """Optimization should return a complete OptimizedPrompt."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        result = optimizer.optimize_prompt(
            task="sql_generation",
            question="show all customers",
            schema_dict=sample_schema,
            database_type="postgresql",
        )
        assert isinstance(result, OptimizedPrompt)
        assert result.system_prompt
        assert result.user_prompt
        assert result.compressed_schema

    def test_optimization_includes_metrics(self, sample_schema):
        """Optimization should include metrics."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        result = optimizer.optimize_prompt(
            task="sql_generation",
            question="show all customers",
            schema_dict=sample_schema,
            database_type="postgresql",
        )
        assert "total_tokens" in result.metrics
        assert "schema_tokens" in result.metrics
        assert "model_size" in result.metrics

    def test_optimization_tracks_included_tables(self, sample_schema):
        """Should track which tables were included."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        result = optimizer.optimize_prompt(
            task="sql_generation",
            question="show all customers",
            schema_dict=sample_schema,
            database_type="postgresql",
        )
        assert len(result.tables_included) > 0
        assert "customers" in result.tables_included

    def test_small_model_produces_compact_prompt(self, sample_schema):
        """Small model should produce more compact prompt."""
        small_opt = PromptOptimizer(ModelSize.SMALL)
        large_opt = PromptOptimizer(ModelSize.LARGE)

        small_result = small_opt.optimize_prompt(
            task="sql_generation",
            question="show all customers",
            schema_dict=sample_schema,
            database_type="postgresql",
        )
        large_result = large_opt.optimize_prompt(
            task="sql_generation",
            question="show all customers",
            schema_dict=sample_schema,
            database_type="postgresql",
        )

        assert small_result.metrics["total_tokens"] < large_result.metrics["total_tokens"]


# =============================================================================
# TEMPLATE FORMATTING TESTS
# =============================================================================

class TestTemplateFormatting:
    """Test model-specific template formatting."""

    def test_format_with_llama_template(self):
        """Should format correctly with Llama template."""
        optimizer = PromptOptimizer(model_name="llama3.2")
        formatted = optimizer.format_with_template(
            system="You are a SQL expert",
            user="Generate SQL for: show customers"
        )
        assert "<|begin_of_text|>" in formatted
        assert "SQL expert" in formatted
        assert "show customers" in formatted

    def test_format_with_default_template(self):
        """Should format correctly with default template."""
        optimizer = PromptOptimizer(model_name="unknown-model")
        formatted = optimizer.format_with_template(
            system="System message",
            user="User message"
        )
        assert "System message" in formatted
        assert "User message" in formatted


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================

class TestFactoryFunctions:
    """Test factory and convenience functions."""

    def test_get_prompt_optimizer_with_model_name(self):
        """Should create optimizer with auto-detected settings."""
        optimizer = get_prompt_optimizer(model_name="llama3.2")
        assert optimizer.model_size == ModelSize.MEDIUM
        assert optimizer.model_family == ModelFamily.LLAMA

    def test_get_prompt_optimizer_with_explicit_size(self):
        """Should respect explicit size override."""
        optimizer = get_prompt_optimizer(model_size=ModelSize.SMALL)
        assert optimizer.model_size == ModelSize.SMALL

    def test_get_prompt_optimizer_defaults_to_medium(self):
        """Should default to medium without arguments."""
        optimizer = get_prompt_optimizer()
        assert optimizer.model_size == ModelSize.MEDIUM

    def test_build_optimized_prompt_convenience(self, sample_schema):
        """Convenience function should work end-to-end."""
        result = build_optimized_prompt(
            question="show all customers",
            schema_dict=sample_schema,
            database_type="postgresql",
            model_name="llama3.2",
        )
        assert isinstance(result, OptimizedPrompt)
        assert result.system_prompt
        assert result.compressed_schema


# =============================================================================
# TOKEN COUNTING TESTS
# =============================================================================

class TestTokenCounting:
    """Test token estimation."""

    def test_empty_string_returns_zero(self):
        """Empty string should return 0 tokens."""
        assert _count_tokens("") == 0
        assert _count_tokens(None) == 0

    def test_estimates_approximately_4_chars_per_token(self):
        """Should estimate ~4 characters per token."""
        text = "This is a test string with exactly forty chars."
        tokens = _count_tokens(text)
        # 48 chars / 4 = 12 tokens
        assert 10 <= tokens <= 14

    def test_longer_text_produces_more_tokens(self):
        """Longer text should produce more tokens."""
        short = "Hello"
        long = "Hello world, this is a much longer string"
        assert _count_tokens(short) < _count_tokens(long)


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_schema(self):
        """Should handle empty schema gracefully."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        compressed, included, excluded = optimizer.compress_schema({}, "any question")
        assert compressed == ""
        assert included == []
        assert excluded == []

    def test_schema_without_tables(self):
        """Should handle schema with no tables key."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        compressed, included, excluded = optimizer.compress_schema(
            {"name": "test_db"}, "any question"
        )
        assert compressed == ""
        assert included == []

    def test_question_with_no_table_matches(self, sample_schema):
        """Should handle question that doesn't match any tables."""
        optimizer = PromptOptimizer(ModelSize.MEDIUM)
        result = optimizer.optimize_prompt(
            task="sql_generation",
            question="what is the meaning of life",
            schema_dict=sample_schema,
            database_type="postgresql",
        )
        # Should still produce a valid result
        assert result.system_prompt
        assert result.compressed_schema
