"""Tests for column semantic type detection."""
import pytest
from src.core.column_semantics import (
    ColumnSemanticsDetector,
    ColumnSemanticType,
    ColumnSemantics,
    detect_column_semantics,
)


class TestColumnSemanticTypeDetection:
    """Test column semantic type detection from names, types, and values."""

    @pytest.fixture
    def detector(self):
        return ColumnSemanticsDetector()

    # ============== LOCATION DETECTION ==============

    def test_state_column_with_codes(self, detector):
        """State column with 2-letter codes should be detected as location."""
        result = detector.detect(
            "state", "VARCHAR(2)", ["CA", "NY", "TX"]
        )
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.location_subtype == "us_state"
        assert result.value_format == "code"
        assert result.confidence >= 0.9

    def test_state_column_with_full_names(self, detector):
        """State column with full names should be detected as location."""
        result = detector.detect(
            "state", "VARCHAR(50)", ["California", "New York", "Texas"]
        )
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.location_subtype == "us_state"
        assert result.value_format == "full_name"
        assert result.confidence >= 0.85

    def test_city_column(self, detector):
        """City column should be detected as location based on name pattern."""
        # Without known city values list, cities are detected from name pattern only
        result = detector.detect(
            "city", "VARCHAR(100)", None  # No sample values
        )
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.location_subtype == "city"
        assert result.confidence >= 0.70

    def test_country_column(self, detector):
        """Country column should be detected as location."""
        result = detector.detect(
            "country", "VARCHAR(2)", None  # Use name-based detection
        )
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.location_subtype == "country"

    def test_shipping_state_column(self, detector):
        """Column with 'state' in name should be detected as location."""
        result = detector.detect(
            "shipping_state", "CHAR(2)", ["CA", "NY"]
        )
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.location_subtype == "us_state"

    # ============== CATEGORICAL DETECTION ==============

    def test_status_column(self, detector):
        """Status column should be detected as categorical."""
        result = detector.detect(
            "status", "VARCHAR(20)", ["active", "inactive", "pending"]
        )
        assert result.semantic_type == ColumnSemanticType.CATEGORICAL
        assert result.confidence >= 0.70

    def test_type_column(self, detector):
        """Type column should be detected as categorical."""
        result = detector.detect(
            "product_type", "VARCHAR(50)", ["electronics", "clothing", "food"]
        )
        assert result.semantic_type == ColumnSemanticType.CATEGORICAL

    def test_category_column(self, detector):
        """Category column should be detected as categorical."""
        result = detector.detect(
            "category", "VARCHAR(100)", ["Books", "Movies", "Music"]
        )
        assert result.semantic_type == ColumnSemanticType.CATEGORICAL

    def test_priority_column(self, detector):
        """Priority column should be detected as categorical."""
        result = detector.detect(
            "priority", "VARCHAR(10)", ["high", "medium", "low"]
        )
        assert result.semantic_type == ColumnSemanticType.CATEGORICAL

    # ============== TEMPORAL DETECTION ==============

    def test_created_at_column(self, detector):
        """Timestamp columns should be detected as temporal."""
        result = detector.detect(
            "created_at", "TIMESTAMP", None
        )
        assert result.semantic_type == ColumnSemanticType.TEMPORAL

    def test_date_column(self, detector):
        """Date columns should be detected as temporal."""
        result = detector.detect(
            "order_date", "DATE", None
        )
        assert result.semantic_type == ColumnSemanticType.TEMPORAL

    def test_updated_column(self, detector):
        """Updated columns should be detected as temporal."""
        result = detector.detect(
            "updated_at", "DATETIME", None
        )
        assert result.semantic_type == ColumnSemanticType.TEMPORAL

    # ============== IDENTIFIER DETECTION ==============

    def test_id_column(self, detector):
        """ID columns should be detected as identifier."""
        result = detector.detect(
            "id", "INTEGER", None
        )
        assert result.semantic_type == ColumnSemanticType.IDENTIFIER

    def test_product_id_column(self, detector):
        """Product ID columns should be detected as identifier."""
        result = detector.detect(
            "product_id", "BIGINT", None
        )
        assert result.semantic_type == ColumnSemanticType.IDENTIFIER

    def test_uuid_column(self, detector):
        """UUID columns should be detected as identifier."""
        result = detector.detect(
            "uuid", "VARCHAR(36)", None
        )
        assert result.semantic_type == ColumnSemanticType.IDENTIFIER

    # ============== NUMERIC DETECTION ==============

    def test_price_column(self, detector):
        """Price columns should be detected as numeric."""
        result = detector.detect(
            "price", "DECIMAL(10,2)", None
        )
        assert result.semantic_type == ColumnSemanticType.NUMERIC

    def test_quantity_column(self, detector):
        """Quantity columns should be detected as numeric."""
        result = detector.detect(
            "quantity", "INTEGER", None
        )
        assert result.semantic_type == ColumnSemanticType.NUMERIC

    def test_amount_column(self, detector):
        """Amount columns should be detected as numeric."""
        result = detector.detect(
            "total_amount", "FLOAT", None
        )
        assert result.semantic_type == ColumnSemanticType.NUMERIC

    # ============== TEXT DETECTION ==============

    def test_name_column(self, detector):
        """Name columns should be detected as text."""
        result = detector.detect(
            "name", "VARCHAR(255)", None
        )
        assert result.semantic_type == ColumnSemanticType.TEXT

    def test_description_column(self, detector):
        """Description columns should be detected as text."""
        result = detector.detect(
            "description", "TEXT", None
        )
        assert result.semantic_type == ColumnSemanticType.TEXT

    # ============== BOOLEAN DETECTION ==============

    def test_is_active_column(self, detector):
        """Boolean columns should be detected."""
        result = detector.detect(
            "is_active", "BOOLEAN", None
        )
        assert result.semantic_type == ColumnSemanticType.BOOLEAN

    def test_has_feature_column(self, detector):
        """Columns starting with 'has_' should be detected as boolean."""
        result = detector.detect(
            "has_subscription", "BOOLEAN", None
        )
        assert result.semantic_type == ColumnSemanticType.BOOLEAN

    # ============== VALUE-BASED DETECTION ==============

    def test_values_override_name(self, detector):
        """Value-based detection should have higher confidence than name."""
        # Column named 'code' but values are US state codes
        result = detector.detect(
            "code", "CHAR(2)", ["CA", "NY", "TX", "FL"]
        )
        # Should detect as location based on values
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.value_format == "code"

    def test_mixed_values(self, detector):
        """Mixed values with some valid state codes should still detect location."""
        result = detector.detect(
            "state", "VARCHAR(10)", ["CA", "Unknown", "NY", "Other"]
        )
        # 50% valid codes (CA, NY) meets the threshold, still detected as location
        assert result.semantic_type == ColumnSemanticType.LOCATION
        assert result.confidence >= 0.90

    # ============== CONVENIENCE FUNCTION ==============

    def test_convenience_function(self):
        """Test the convenience function."""
        result = detect_column_semantics(
            "status", "VARCHAR(20)", ["active", "inactive"]
        )
        assert result.semantic_type == ColumnSemanticType.CATEGORICAL

    # ============== TO_DICT ==============

    def test_to_dict(self, detector):
        """Test serialization to dictionary."""
        result = detector.detect(
            "state", "VARCHAR(2)", ["CA", "NY"]
        )
        d = result.to_dict()
        assert "semantic_type" in d
        assert "location_subtype" in d
        assert "value_format" in d
        assert "confidence" in d
        assert d["semantic_type"] == "location"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def detector(self):
        return ColumnSemanticsDetector()

    def test_empty_sample_values(self, detector):
        """Empty sample values should still use name/type detection."""
        result = detector.detect(
            "state", "VARCHAR(2)", []
        )
        assert result.semantic_type == ColumnSemanticType.LOCATION

    def test_none_sample_values(self, detector):
        """None sample values should still use name/type detection."""
        result = detector.detect(
            "status", "VARCHAR(20)", None
        )
        assert result.semantic_type == ColumnSemanticType.CATEGORICAL

    def test_unknown_column(self, detector):
        """Unknown columns should return UNKNOWN type."""
        result = detector.detect(
            "xyz123", "VARCHAR(50)", None
        )
        assert result.semantic_type == ColumnSemanticType.UNKNOWN
        assert result.confidence == 0.0

    def test_case_insensitive_detection(self, detector):
        """Detection should be case-insensitive."""
        result1 = detector.detect("STATE", "VARCHAR(2)", ["CA"])
        result2 = detector.detect("state", "VARCHAR(2)", ["CA"])
        result3 = detector.detect("State", "VARCHAR(2)", ["CA"])

        assert result1.semantic_type == ColumnSemanticType.LOCATION
        assert result2.semantic_type == ColumnSemanticType.LOCATION
        assert result3.semantic_type == ColumnSemanticType.LOCATION
