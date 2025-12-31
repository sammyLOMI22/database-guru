"""Tests for SQL Semantic Validator (Phase 3)."""
import pytest
from dataclasses import dataclass, field
from typing import Set, Dict, List, Any
from enum import Enum

from src.llm.sql_semantic_validator import (
    SQLSemanticValidator,
    SemanticValidationResult,
    SemanticMismatchType,
    validate_sql_semantics,
)


# Mock QueryIntent enum (matches query_intent_classifier.py)
class MockQueryIntent(Enum):
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    RELATIONSHIP = "relationship"
    TEMPORAL = "temporal"
    RANKING = "ranking"
    IMPOSSIBLE = "impossible"


# Mock QueryIntentResult for testing
@dataclass
class MockQueryIntentResult:
    intent: MockQueryIntent
    confidence: float = 0.9
    required_tables: Set[str] = field(default_factory=set)
    required_values: Dict[str, Any] = field(default_factory=dict)

    def can_answer(self) -> bool:
        return self.intent != MockQueryIntent.IMPOSSIBLE


class TestAggregationValidation:
    """Test validation of aggregation intent queries."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_aggregation_with_count(self, validator):
        """COUNT query should pass aggregation validation."""
        sql = "SELECT COUNT(*) FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent, "How many products are there?")

        assert result.is_valid
        assert result.confidence >= 0.9

    def test_valid_aggregation_with_sum(self, validator):
        """SUM query should pass aggregation validation."""
        sql = "SELECT SUM(price) FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent, "What is the total price?")

        assert result.is_valid

    def test_valid_aggregation_with_avg(self, validator):
        """AVG query should pass aggregation validation."""
        sql = "SELECT AVG(price) FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_missing_aggregation(self, validator):
        """Query without aggregation should fail aggregation validation."""
        sql = "SELECT * FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent, "How many products?")

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.MISSING_AGGREGATION
        assert "COUNT" in "".join(result.suggestions)

    def test_aggregation_hint_from_question(self, validator):
        """Validator should suggest specific aggregation from question."""
        sql = "SELECT * FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        # "total" implies SUM
        result = validator.validate(sql, intent, "What is the total of sales?")

        assert not result.is_valid
        assert "SUM" in "".join(result.suggestions)


class TestComparisonValidation:
    """Test validation of comparison intent queries."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_comparison_with_where(self, validator):
        """Query with WHERE should pass comparison validation."""
        sql = "SELECT * FROM products WHERE price > 100"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.COMPARISON
        )

        result = validator.validate(sql, intent)

        assert result.is_valid
        assert result.confidence >= 0.85

    def test_missing_where_clause(self, validator):
        """Query without WHERE should fail comparison validation."""
        sql = "SELECT * FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.COMPARISON,
            required_values={"price": 100}
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.MISSING_WHERE
        assert "WHERE" in "".join(result.mismatch_details)

    def test_filter_value_missing(self, validator):
        """Query missing expected filter value should fail."""
        # Use a SQL that doesn't contain the expected column or value
        sql = "SELECT * FROM orders WHERE amount > 100"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.COMPARISON,
            required_values={"state": "CA"}
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert "state" in "".join(result.mismatch_details).lower()


class TestRelationshipValidation:
    """Test validation of relationship (JOIN) intent queries."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_join(self, validator):
        """Query with JOIN should pass relationship validation."""
        sql = "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RELATIONSHIP,
            required_tables={"orders", "customers"}
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_valid_left_join(self, validator):
        """Query with LEFT JOIN should pass."""
        sql = "SELECT * FROM orders LEFT JOIN products ON orders.product_id = products.id"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RELATIONSHIP
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_valid_implicit_join(self, validator):
        """Implicit join (comma-separated) should pass."""
        sql = "SELECT * FROM orders, customers WHERE orders.customer_id = customers.id"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RELATIONSHIP
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_missing_join(self, validator):
        """Single table query should fail relationship validation."""
        sql = "SELECT * FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RELATIONSHIP,
            required_tables={"orders", "customers"}
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.MISSING_JOIN


class TestRankingValidation:
    """Test validation of ranking intent queries."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_ranking(self, validator):
        """Query with ORDER BY and LIMIT should pass."""
        sql = "SELECT * FROM products ORDER BY price DESC LIMIT 10"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RANKING
        )

        result = validator.validate(sql, intent)

        assert result.is_valid
        assert result.confidence >= 0.9

    def test_missing_order_by(self, validator):
        """Query without ORDER BY should fail ranking validation."""
        sql = "SELECT * FROM products LIMIT 10"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RANKING
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.MISSING_ORDER_BY

    def test_missing_limit(self, validator):
        """Query without LIMIT should fail ranking validation."""
        sql = "SELECT * FROM products ORDER BY price DESC"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.RANKING
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.MISSING_LIMIT


class TestTemporalValidation:
    """Test validation of temporal intent queries."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_temporal(self, validator):
        """Query with date column and WHERE should pass."""
        sql = "SELECT * FROM orders WHERE created_at > '2024-01-01'"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.TEMPORAL
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_valid_temporal_order_date(self, validator):
        """Query referencing order_date should pass."""
        sql = "SELECT * FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31'"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.TEMPORAL
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_missing_date_column(self, validator):
        """Query without date column should fail."""
        sql = "SELECT * FROM products WHERE category = 'Electronics'"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.TEMPORAL
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.MISSING_DATE_FILTER


class TestLookupValidation:
    """Test validation of lookup intent queries."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_lookup(self, validator):
        """Simple SELECT should pass lookup validation."""
        sql = "SELECT * FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.LOOKUP,
            required_tables={"products"}
        )

        result = validator.validate(sql, intent)

        assert result.is_valid

    def test_missing_required_table(self, validator):
        """Query missing required table should fail."""
        sql = "SELECT * FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.LOOKUP,
            required_tables={"products"}
        )

        result = validator.validate(sql, intent)

        assert not result.is_valid
        assert result.mismatch_type == SemanticMismatchType.TABLE_NOT_REFERENCED


class TestTableReferenceValidation:
    """Test table reference validation."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_valid_table_references(self, validator):
        """All tables in SQL exist in schema."""
        sql = "SELECT * FROM products JOIN categories ON products.category_id = categories.id"
        available = {"products", "categories", "orders"}

        result = validator.validate_table_references(sql, available)

        assert result.is_valid
        assert result.confidence == 1.0

    def test_missing_table(self, validator):
        """Table not in schema should fail."""
        sql = "SELECT * FROM nonexistent_table"
        available = {"products", "categories"}

        result = validator.validate_table_references(sql, available)

        assert not result.is_valid
        assert "nonexistent_table" in "".join(result.mismatch_details)


class TestRegenerationHints:
    """Test regeneration hint generation."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_aggregation_hints(self, validator):
        """Missing aggregation should generate helpful hints."""
        sql = "SELECT * FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent, "How many orders?")
        hints = result.get_regeneration_hints()

        assert "missing_aggregation" in hints.lower()
        assert "count" in hints.lower()

    def test_valid_query_no_hints(self, validator):
        """Valid query should return empty hints."""
        sql = "SELECT COUNT(*) FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent)
        hints = result.get_regeneration_hints()

        assert hints == ""


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_validate_sql_semantics(self):
        """Test the module-level convenience function."""
        sql = "SELECT COUNT(*) FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validate_sql_semantics(sql, intent)

        assert result.is_valid


class TestImpossibleIntent:
    """Test handling of impossible intent."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_impossible_intent_passes(self, validator):
        """IMPOSSIBLE intent should always pass validation."""
        sql = "SELECT * FROM anything"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.IMPOSSIBLE
        )

        result = validator.validate(sql, intent)

        assert result.is_valid
        assert result.confidence == 1.0


class TestValidationTiming:
    """Test validation performance."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_validation_records_time(self, validator):
        """Validation should record execution time."""
        sql = "SELECT COUNT(*) FROM products"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent)

        assert result.validation_time_ms >= 0
        assert result.validation_time_ms < 100  # Should be fast (<100ms)


class TestToDictSerialization:
    """Test serialization of results."""

    @pytest.fixture
    def validator(self):
        return SQLSemanticValidator()

    def test_to_dict(self, validator):
        """Result should serialize to dictionary."""
        sql = "SELECT * FROM orders"
        intent = MockQueryIntentResult(
            intent=MockQueryIntent.AGGREGATION
        )

        result = validator.validate(sql, intent)
        d = result.to_dict()

        assert "is_valid" in d
        assert "confidence" in d
        assert "mismatch_type" in d
        assert "mismatch_details" in d
        assert "suggestions" in d
        assert "validation_time_ms" in d
