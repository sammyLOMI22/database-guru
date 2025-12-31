"""Tests for Query Intent Classifier.

Tests the pre-generation semantic understanding components:
- QueryIntentClassifier for intent classification
- Entity extraction (tables, columns, locations)
- Schema validation and IMPOSSIBLE query detection
"""
import pytest
from src.llm.query_intent_classifier import (
    QueryIntentClassifier,
    QueryIntent,
    QueryIntentResult,
    ExtractedEntity,
)


@pytest.fixture
def sample_schema():
    """Sample schema with common e-commerce tables."""
    return {
        "tables": {
            "products": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "price", "type": "DECIMAL"},
                    {"name": "category_id", "type": "INTEGER"},
                    {"name": "status", "type": "VARCHAR", "sample_values": ["active", "inactive"]},
                ]
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "customer_id", "type": "INTEGER"},
                    {"name": "state", "type": "VARCHAR(2)", "sample_values": ["CA", "NY", "TX"]},
                    {"name": "total", "type": "DECIMAL"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "foreign_keys": [
                    {"column": "customer_id", "references": {"table": "customers", "column": "id"}}
                ]
            },
            "categories": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                ]
            },
        },
        "relationships": [
            {"from_table": "products", "from_column": "category_id", "to_table": "categories", "to_column": "id"},
        ]
    }


@pytest.fixture
def simple_schema():
    """Simple schema without location columns."""
    return {
        "tables": {
            "items": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "quantity", "type": "INTEGER"},
                ]
            },
        }
    }


class TestIntentClassification:
    """Test intent classification patterns."""

    def test_lookup_intent_show_all(self, sample_schema):
        """Test LOOKUP intent for 'show all' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all products")
        assert result.intent == QueryIntent.LOOKUP
        assert result.confidence >= 0.5

    def test_lookup_intent_list(self, sample_schema):
        """Test LOOKUP intent for 'list' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("List all orders")
        assert result.intent == QueryIntent.LOOKUP

    def test_lookup_intent_get(self, sample_schema):
        """Test LOOKUP intent for 'get' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Get all categories")
        assert result.intent == QueryIntent.LOOKUP

    def test_aggregation_intent_count(self, sample_schema):
        """Test AGGREGATION intent for count queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("How many orders are there?")
        assert result.intent == QueryIntent.AGGREGATION
        assert "COUNT" in result.aggregations

    def test_aggregation_intent_total(self, sample_schema):
        """Test AGGREGATION intent for total/sum queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("What is the total revenue from orders?")
        assert result.intent == QueryIntent.AGGREGATION
        assert "SUM" in result.aggregations

    def test_aggregation_intent_average(self, sample_schema):
        """Test AGGREGATION intent for average queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("What is the average order total?")
        assert result.intent == QueryIntent.AGGREGATION
        assert "AVG" in result.aggregations

    def test_comparison_intent_less_than(self, sample_schema):
        """Test COMPARISON intent for less than queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Products under $50")
        assert result.intent == QueryIntent.COMPARISON
        assert any(f["operator"] == "<" for f in result.filters)

    def test_comparison_intent_greater_than(self, sample_schema):
        """Test COMPARISON intent for greater than queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Orders over $100")
        assert result.intent == QueryIntent.COMPARISON
        assert any(f["operator"] == ">" for f in result.filters)

    def test_comparison_intent_between(self, sample_schema):
        """Test COMPARISON intent for between queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Products between 10 and 50 dollars")
        assert result.intent == QueryIntent.COMPARISON
        assert any(f["operator"] == "BETWEEN" for f in result.filters)

    def test_relationship_intent_with(self, sample_schema):
        """Test RELATIONSHIP intent for 'with their' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show orders with their products")
        assert result.intent == QueryIntent.RELATIONSHIP

    def test_relationship_intent_join(self, sample_schema):
        """Test RELATIONSHIP intent for explicit join queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Products joined with categories")
        assert result.intent == QueryIntent.RELATIONSHIP

    def test_temporal_intent_last_week(self, sample_schema):
        """Test TEMPORAL intent for time-based queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Orders from last week")
        assert result.intent == QueryIntent.TEMPORAL

    def test_temporal_intent_this_month(self, sample_schema):
        """Test TEMPORAL intent for 'this month' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show orders from this month")
        assert result.intent == QueryIntent.TEMPORAL

    def test_ranking_intent_top_n(self, sample_schema):
        """Test RANKING intent for 'top N' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Top 10 products by price")
        assert result.intent == QueryIntent.RANKING

    def test_ranking_intent_highest(self, sample_schema):
        """Test RANKING intent for 'highest' queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show the highest priced products")
        assert result.intent == QueryIntent.RANKING


class TestImpossibleQueries:
    """Test CANNOT_ANSWER detection for impossible queries."""

    def test_missing_table_detected(self, sample_schema):
        """Test that missing table is detected."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all customers")  # No customers table
        assert result.intent == QueryIntent.IMPOSSIBLE
        assert not result.can_answer()
        assert "customers" in result.impossible_reason.lower()

    def test_valid_table_passes(self, sample_schema):
        """Test that valid table passes validation."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all products")
        assert result.can_answer()
        assert "products" in result.required_tables

    def test_missing_location_column(self, simple_schema):
        """Test that location query fails without location column."""
        classifier = QueryIntentClassifier(simple_schema)
        result = classifier.classify("Items from California")
        assert not result.can_answer()
        # Location entity detected but no column to satisfy it

    def test_location_with_state_column(self, sample_schema):
        """Test that location query passes with state column."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Orders from California")
        assert result.can_answer()  # orders table has 'state' column


class TestEntityExtraction:
    """Test entity extraction from questions."""

    def test_table_entity_extraction(self, sample_schema):
        """Test extraction of table references."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all products")

        table_entities = [e for e in result.extracted_entities if e.entity_type == "table"]
        assert any(e.schema_match == "products" for e in table_entities)

    def test_location_entity_extraction(self, sample_schema):
        """Test extraction of location references."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Orders from California")

        location_entities = [e for e in result.extracted_entities if e.entity_type == "location"]
        assert len(location_entities) >= 1
        assert location_entities[0].normalized_value == "CA"

    def test_value_entity_extraction(self, sample_schema):
        """Test extraction of numeric values."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Products under $50")

        value_entities = [e for e in result.extracted_entities if e.entity_type == "value"]
        assert any(e.normalized_value == 50.0 for e in value_entities)


class TestFuzzyMatching:
    """Test fuzzy matching for table/column names."""

    def test_singular_to_plural_match(self, sample_schema):
        """Test singular form matches plural table."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all product")  # singular
        assert "products" in result.required_tables

    def test_plural_to_singular_match(self):
        """Test plural form matches singular table."""
        schema = {"tables": {"item": {"columns": [{"name": "id", "type": "INTEGER"}]}}}
        classifier = QueryIntentClassifier(schema)
        result = classifier.classify("Show all items")  # plural
        assert "item" in result.required_tables

    def test_typo_fuzzy_match(self, sample_schema):
        """Test that typos are fuzzy matched to correct table."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all prducts")  # typo
        # Fuzzy matching should correct "prducts" -> "products"
        assert "products" in result.required_tables
        assert result.can_answer()

    def test_severe_typo_suggestion(self, sample_schema):
        """Test that severe typos get suggestions when fuzzy match fails."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all prdcts")  # severe typo (missing 'ou')
        # If fuzzy match fails (threshold 0.7), should get suggestions
        if not result.can_answer():
            assert any("products" in s.lower() for s in result.suggestions)


class TestQueryIntentResult:
    """Test QueryIntentResult dataclass methods."""

    def test_can_answer_true(self, sample_schema):
        """Test can_answer returns True for valid queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all products")
        assert result.can_answer() is True

    def test_can_answer_false(self, sample_schema):
        """Test can_answer returns False for impossible queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all users")  # No users table
        assert result.can_answer() is False

    def test_to_dict_format(self, sample_schema):
        """Test to_dict returns expected format."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all products")
        result_dict = result.to_dict()

        assert "intent" in result_dict
        assert "confidence" in result_dict
        assert "extracted_entities" in result_dict
        assert "required_tables" in result_dict
        assert "can_answer" in result_dict
        assert isinstance(result_dict["required_tables"], list)


class TestAggregationExtraction:
    """Test aggregation function extraction."""

    def test_count_extraction(self, sample_schema):
        """Test COUNT extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Count all products")
        assert "COUNT" in result.aggregations

    def test_sum_extraction(self, sample_schema):
        """Test SUM extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Total revenue from orders")
        assert "SUM" in result.aggregations

    def test_avg_extraction(self, sample_schema):
        """Test AVG extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Average price of products")
        assert "AVG" in result.aggregations

    def test_max_extraction(self, sample_schema):
        """Test MAX extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Maximum order total")
        assert "MAX" in result.aggregations

    def test_min_extraction(self, sample_schema):
        """Test MIN extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Minimum product price")
        assert "MIN" in result.aggregations

    def test_multiple_aggregations(self, sample_schema):
        """Test multiple aggregation extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show count and total of orders")
        assert "COUNT" in result.aggregations
        assert "SUM" in result.aggregations


class TestFilterExtraction:
    """Test filter condition extraction."""

    def test_numeric_less_than(self, sample_schema):
        """Test numeric less than filter."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Products under $50")
        filters = [f for f in result.filters if f["operator"] == "<"]
        assert len(filters) >= 1
        assert filters[0]["value"] == 50.0

    def test_numeric_greater_than(self, sample_schema):
        """Test numeric greater than filter."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Orders over 100")
        filters = [f for f in result.filters if f["operator"] == ">"]
        assert len(filters) >= 1
        assert filters[0]["value"] == 100.0

    def test_between_filter(self, sample_schema):
        """Test BETWEEN filter extraction."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Products between 10 and 50")
        filters = [f for f in result.filters if f["operator"] == "BETWEEN"]
        assert len(filters) >= 1
        assert filters[0]["value"] == (10.0, 50.0)


class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_high_confidence_clear_intent(self, sample_schema):
        """Test high confidence for clear intent."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("How many products are there?")
        # Clear aggregation intent should have high confidence
        assert result.confidence >= 0.7

    def test_moderate_confidence_ambiguous(self, sample_schema):
        """Test moderate confidence for ambiguous queries."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("products")  # Very short, ambiguous
        # Ambiguous should have lower confidence
        assert result.confidence <= 0.7

    def test_impossible_high_confidence(self, sample_schema):
        """Test IMPOSSIBLE intent has high confidence."""
        classifier = QueryIntentClassifier(sample_schema)
        result = classifier.classify("Show all users")  # No users table
        assert result.intent == QueryIntent.IMPOSSIBLE
        assert result.confidence >= 0.8  # Should be confident it's impossible
