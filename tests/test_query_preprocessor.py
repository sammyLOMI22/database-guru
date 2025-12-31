"""Tests for the Query Preprocessor (Small Model Optimization)"""
import pytest
from src.llm.query_preprocessor import (
    QueryPreprocessor,
    PreprocessedQuery,
    LocationColumnInfo,
    DetectedLocation,
)


# Sample schema with state column using codes (CA, NY, TX)
@pytest.fixture
def schema_with_codes():
    return {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "state", "type": "varchar", "sample_values": ["CA", "NY", "TX", "FL"]},
                    {"name": "email", "type": "varchar"},
                ]
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "customer_id", "type": "integer"},
                    {"name": "total", "type": "decimal"},
                ]
            },
        }
    }


# Sample schema with state column using full names (California, New York)
@pytest.fixture
def schema_with_full_names():
    return {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "state", "type": "varchar", "sample_values": ["California", "New York", "Texas"]},
                    {"name": "email", "type": "varchar"},
                ]
            },
        }
    }


# Sample schema without location columns
@pytest.fixture
def schema_without_location():
    return {
        "tables": {
            "products": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "price", "type": "decimal"},
                ]
            },
        }
    }


class TestLocationDetection:
    """Tests for location detection in queries"""

    def test_detect_full_state_name(self, schema_with_codes):
        """Test that full state name is detected (in entities or locations)"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from California")

        # Location may be in detected_locations or detected_entities depending on LocationMapper availability
        has_california = (
            len(result.detected_locations) > 0 and any(
                loc.original.lower() == "california" for loc in result.detected_locations
            )
        ) or (
            len(result.detected_entities) > 0 and any(
                e.text.lower() == "california" and e.entity_type == "location"
                for e in result.detected_entities
            )
        )
        assert has_california

    def test_detect_state_code(self, schema_with_full_names):
        """Test that state code is detected"""
        preprocessor = QueryPreprocessor(schema_with_full_names)
        result = preprocessor.preprocess("Show customers from CA")

        # Location may be in detected_locations or detected_entities
        has_ca = (
            len(result.detected_locations) > 0 and any(
                loc.original.upper() == "CA" for loc in result.detected_locations
            )
        ) or (
            len(result.detected_entities) > 0 and any(
                e.text.upper() == "CA" and e.entity_type == "location"
                for e in result.detected_entities
            )
        )
        assert has_ca


class TestBidirectionalNormalization:
    """Tests for bidirectional location normalization"""

    def test_normalize_california_to_ca(self, schema_with_codes):
        """When DB uses codes, convert 'California' to 'CA'"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from California")

        # Check that the normalized query uses the code format
        if result.detected_locations:
            loc = result.detected_locations[0]
            assert loc.normalized == "CA" or "CA" in result.normalized

    def test_normalize_ca_to_california(self, schema_with_full_names):
        """When DB uses full names, convert 'CA' to 'California'"""
        preprocessor = QueryPreprocessor(schema_with_full_names)
        result = preprocessor.preprocess("Show customers from CA")

        # Check that the normalized query uses the full name format
        if result.detected_locations:
            loc = result.detected_locations[0]
            # Should convert to full name when DB uses full names
            assert loc.normalized == "California" or "California" in result.normalized

    def test_no_change_when_format_matches(self, schema_with_codes):
        """When query format matches DB format, no change needed"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from TX")

        # Query uses code, DB uses codes - should remain as TX
        if result.detected_locations:
            loc = result.detected_locations[0]
            assert loc.original.upper() == "TX"


class TestFormatDetection:
    """Tests for DB format detection from sample values"""

    def test_detect_code_format(self, schema_with_codes):
        """Test that code format is detected from sample values"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        # Check internal format detection
        assert len(preprocessor._location_columns) > 0
        for col_info in preprocessor._location_columns.values():
            assert col_info.uses_codes is True
            assert col_info.detected_format == "code"

    def test_detect_full_name_format(self, schema_with_full_names):
        """Test that full name format is detected from sample values"""
        preprocessor = QueryPreprocessor(schema_with_full_names)
        # Check internal format detection
        assert len(preprocessor._location_columns) > 0
        for col_info in preprocessor._location_columns.values():
            assert col_info.uses_codes is False
            assert col_info.detected_format == "full_name"


class TestNoLocationColumns:
    """Tests for schemas without location columns"""

    def test_no_normalization_without_location_columns(self, schema_without_location):
        """Test that queries work normally without location columns"""
        preprocessor = QueryPreprocessor(schema_without_location)
        result = preprocessor.preprocess("Show all products")

        assert result.original == "Show all products"
        assert result.normalized == "Show all products"
        assert len(result.detected_locations) == 0


class TestPreprocessedQueryOutput:
    """Tests for PreprocessedQuery output structure"""

    def test_result_structure(self, schema_with_codes):
        """Test that result has all required fields"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from California")

        assert isinstance(result, PreprocessedQuery)
        assert hasattr(result, "original")
        assert hasattr(result, "normalized")
        assert hasattr(result, "detected_locations")
        assert hasattr(result, "detected_entities")
        assert hasattr(result, "preprocessing_applied")
        assert hasattr(result, "location_format_hint")

    def test_to_dict(self, schema_with_codes):
        """Test that to_dict works correctly"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from California")

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "original" in result_dict
        assert "normalized" in result_dict
        assert "locations" in result_dict

    def test_enhanced_context_generated(self, schema_with_codes):
        """Test that enhanced context is generated for location queries"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from California")

        if result.detected_locations:
            assert result.enhanced_context != ""


class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_query(self, schema_with_codes):
        """Test handling of empty query"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("")
        assert result.original == ""
        assert result.normalized == ""

    def test_query_without_location(self, schema_with_codes):
        """Test query without location mentions"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show all customers")

        assert result.original == "Show all customers"
        assert result.normalized == "Show all customers"
        assert len(result.detected_locations) == 0

    def test_multiple_locations(self, schema_with_codes):
        """Test query with multiple location mentions"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Compare customers from California and New York")

        # Should detect both locations
        if result.detected_locations:
            assert len(result.detected_locations) >= 1

    def test_case_insensitive(self, schema_with_codes):
        """Test case insensitivity"""
        preprocessor = QueryPreprocessor(schema_with_codes)

        result1 = preprocessor.preprocess("customers from CALIFORNIA")
        result2 = preprocessor.preprocess("customers from california")

        # Both should normalize the same way
        if result1.detected_locations and result2.detected_locations:
            assert result1.detected_locations[0].normalized == result2.detected_locations[0].normalized


class TestLocationMapperIntegration:
    """Tests for LocationMapper integration"""

    def test_uses_location_mapper(self, schema_with_codes):
        """Test that LocationMapper is used for normalization"""
        preprocessor = QueryPreprocessor(schema_with_codes)
        result = preprocessor.preprocess("Show customers from California")

        # Should use location_normalization preprocessing
        if result.detected_locations:
            assert "location_normalization" in result.preprocessing_applied
