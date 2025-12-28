"""Tests for Required Data Detector.

Tests the schema validation component that detects what data is needed
and validates against the schema before SQL generation.
"""
import pytest
from src.llm.required_data_detector import (
    RequiredDataDetector,
    RequiredDataResult,
    SchemaMatch,
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
                ]
            },
            "categories": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                ]
            },
        }
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


class TestTableDetection:
    """Test table reference detection."""

    def test_explicit_table_mention(self, sample_schema):
        """Test detection of explicit table mentions."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show all products")
        assert "products" in result.tables_required

    def test_multiple_tables(self, sample_schema):
        """Test detection of multiple table references."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show products and orders")
        assert "products" in result.tables_required
        assert "orders" in result.tables_required

    def test_missing_table_detected(self, sample_schema):
        """Test that missing tables are detected."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show all customers")  # No customers table
        assert not result.can_satisfy
        assert "customers" in result.missing_tables

    def test_from_clause_detection(self, sample_schema):
        """Test detection from 'from table' pattern."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Get data from orders")
        assert "orders" in result.tables_required


class TestLocationDetection:
    """Test location detection integration."""

    def test_location_with_state_column(self, sample_schema):
        """Test location detection when schema has state column."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Orders from California")
        assert len(result.locations_detected) > 0
        assert result.can_satisfy  # Has state column in orders

    def test_location_without_state_column(self, simple_schema):
        """Test location detection when schema lacks state column."""
        detector = RequiredDataDetector(simple_schema)
        result = detector.detect_required_data("Items from California")
        # Should flag as impossible - no location column
        assert not result.can_satisfy

    def test_state_code_normalization(self, sample_schema):
        """Test that state names are normalized to codes."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Orders from Texas")
        if result.locations_detected:
            # LocationMapper should normalize Texas to TX
            assert result.locations_detected[0].get("normalized") == "TX"


class TestValueExtraction:
    """Test filter value extraction."""

    def test_numeric_value_extraction(self, sample_schema):
        """Test extraction of numeric values."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Products under $50")
        assert "_numeric_values" in result.values_required
        assert 50.0 in result.values_required["_numeric_values"]

    def test_quoted_value_extraction(self, sample_schema):
        """Test extraction of quoted string values."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data('Products with status "active"')
        assert "_quoted_values" in result.values_required
        assert "active" in result.values_required["_quoted_values"]

    def test_multiple_values(self, sample_schema):
        """Test extraction of multiple values."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Products between 10 and 100")
        assert "_numeric_values" in result.values_required
        assert 10.0 in result.values_required["_numeric_values"]
        assert 100.0 in result.values_required["_numeric_values"]


class TestFuzzyMatching:
    """Test fuzzy matching for table/column names."""

    def test_exact_match(self, sample_schema):
        """Test exact table name match."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_table("products")
        assert match.matched
        assert match.match_type == "exact"
        assert match.matched_name == "products"

    def test_case_insensitive_match(self, sample_schema):
        """Test case-insensitive matching."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_table("PRODUCTS")
        assert match.matched
        assert match.matched_name == "products"

    def test_singular_plural_match(self, sample_schema):
        """Test singular matches plural."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_table("product")  # singular
        assert match.matched
        # "product" is singular, matches "products" (plural table)
        # match_type is "singular" because the input is singular form
        assert match.match_type == "singular"
        assert match.matched_name == "products"

    def test_fuzzy_match(self, sample_schema):
        """Test fuzzy matching for typos."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_table("prodcuts")  # typo
        assert match.matched
        assert match.match_type == "fuzzy"
        assert match.matched_name == "products"

    def test_no_match_suggestions(self, sample_schema):
        """Test suggestions when no match found."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_table("users")
        assert not match.matched
        # Should have suggestions
        assert len(match.suggestions) > 0


class TestColumnMatching:
    """Test column name matching."""

    def test_exact_column_match(self, sample_schema):
        """Test exact column match."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_column("price")
        assert match.matched
        assert match.matched_name == "price"

    def test_column_fuzzy_match(self, sample_schema):
        """Test fuzzy column matching."""
        detector = RequiredDataDetector(sample_schema)
        match = detector._match_column("pric")  # partial
        assert match.matched
        assert match.matched_name == "price"

    def test_find_tables_with_column(self, sample_schema):
        """Test finding tables that contain a column."""
        detector = RequiredDataDetector(sample_schema)
        tables = detector._find_tables_with_column("id")
        # All tables have 'id' column
        assert "products" in tables
        assert "orders" in tables
        assert "categories" in tables


class TestRequiredDataResult:
    """Test RequiredDataResult dataclass."""

    def test_can_satisfy_true(self, sample_schema):
        """Test can_satisfy is True for valid queries."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show all products")
        assert result.can_satisfy

    def test_can_satisfy_false(self, sample_schema):
        """Test can_satisfy is False for impossible queries."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show all customers")
        assert not result.can_satisfy

    def test_to_dict_format(self, sample_schema):
        """Test to_dict returns expected format."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show all products")
        result_dict = result.to_dict()

        assert "tables_required" in result_dict
        assert "columns_required" in result_dict
        assert "can_satisfy" in result_dict
        assert "suggestions" in result_dict
        assert isinstance(result_dict["tables_required"], list)

    def test_suggestions_for_missing_tables(self, sample_schema):
        """Test helpful suggestions are provided."""
        detector = RequiredDataDetector(sample_schema)
        result = detector.detect_required_data("Show all customers")
        # Should suggest available tables
        assert any("available tables" in s.lower() for s in result.suggestions)


class TestColumnSampleValues:
    """Test sample value retrieval."""

    def test_get_sample_values(self, sample_schema):
        """Test getting sample values for a column."""
        detector = RequiredDataDetector(sample_schema)
        samples = detector.get_sample_values("orders", "state")
        assert "CA" in samples
        assert "NY" in samples

    def test_get_sample_values_missing_column(self, sample_schema):
        """Test getting sample values for missing column."""
        detector = RequiredDataDetector(sample_schema)
        samples = detector.get_sample_values("products", "nonexistent")
        assert samples == []

    def test_get_column_info(self, sample_schema):
        """Test getting column metadata."""
        detector = RequiredDataDetector(sample_schema)
        info = detector.get_column_info("orders", "state")
        assert info is not None
        assert info["name"] == "state"
        assert "VARCHAR" in info["type"]


class TestEntityNameHeuristics:
    """Test entity name detection heuristics."""

    def test_stop_words_filtered(self, sample_schema):
        """Test that stop words are filtered out."""
        detector = RequiredDataDetector(sample_schema)
        # 'show' and 'all' should not be detected as tables
        result = detector.detect_required_data("show all the data")
        assert "show" not in [e.lower() for e in result.missing_tables]
        assert "all" not in [e.lower() for e in result.missing_tables]

    def test_short_words_filtered(self, sample_schema):
        """Test that very short words are not matched."""
        detector = RequiredDataDetector(sample_schema)
        # Very short words should not trigger missing table errors
        result = detector.detect_required_data("get it")
        assert "it" not in result.missing_tables

    def test_verb_endings_filtered(self, sample_schema):
        """Test words with verb endings are filtered."""
        detector = RequiredDataDetector(sample_schema)
        # Words ending in 'ing' should not be detected as tables
        assert not detector._looks_like_entity_name("showing")
        assert not detector._looks_like_entity_name("getting")
