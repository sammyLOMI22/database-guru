"""Column semantic type detection for improved SQL generation.

This module detects the semantic type of database columns based on:
- Column name patterns (state, status, created_at, etc.)
- SQL data types (VARCHAR(2), INTEGER, TIMESTAMP, etc.)
- Sample values (2-letter codes, dates, enums)

This helps distinguish between:
- Location columns (state, city, country) → use location codes
- Categorical columns (status, type) → use exact enum values
- Temporal columns (date, timestamp) → use date functions
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, Set

logger = logging.getLogger(__name__)


class ColumnSemanticType(Enum):
    """Semantic types for database columns."""
    CATEGORICAL = "categorical"      # status, type, category (enum-like values)
    LOCATION = "location"            # state, city, country, region
    TEMPORAL = "temporal"            # date, timestamp, datetime
    NUMERIC = "numeric"              # price, count, amount, quantity
    IDENTIFIER = "identifier"        # id, code, key, uuid
    TEXT = "text"                    # name, description, notes
    BOOLEAN = "boolean"              # is_active, has_feature, enabled
    UNKNOWN = "unknown"


@dataclass
class ColumnSemantics:
    """Semantic information about a column.

    Attributes:
        semantic_type: Primary semantic type of the column
        location_subtype: For LOCATION type: "us_state", "city", "country", etc.
        value_format: Format hint: "code" (CA), "full_name" (California), etc.
        sample_values: Representative sample values
        cardinality: Distinct value count (if available)
        confidence: Confidence in the detection (0.0-1.0)
    """
    semantic_type: ColumnSemanticType
    location_subtype: Optional[str] = None
    value_format: Optional[str] = None
    sample_values: Optional[List[Any]] = None
    cardinality: Optional[int] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "semantic_type": self.semantic_type.value,
            "location_subtype": self.location_subtype,
            "value_format": self.value_format,
            "sample_values": self.sample_values,
            "cardinality": self.cardinality,
            "confidence": self.confidence,
        }


class ColumnSemanticsDetector:
    """Detects semantic type of columns based on name, type, and values.

    Usage:
        detector = ColumnSemanticsDetector()
        semantics = detector.detect("state", "VARCHAR(2)", ["CA", "NY", "TX"])
        print(semantics.semantic_type)  # ColumnSemanticType.LOCATION
        print(semantics.value_format)   # "code"
    """

    # US State 2-letter codes (for value-based detection)
    US_STATE_CODES: Set[str] = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    }

    # US State full names (for value-based detection)
    US_STATE_NAMES: Set[str] = {
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
        'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
        'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
        'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
        'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
        'new hampshire', 'new jersey', 'new mexico', 'new york',
        'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
        'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
        'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
        'west virginia', 'wisconsin', 'wyoming', 'district of columbia'
    }

    # Column name patterns for each semantic type
    NAME_PATTERNS = {
        ColumnSemanticType.LOCATION: [
            r'^state$', r'_state$', r'^state_',
            r'^city$', r'_city$', r'^city_',
            r'^country$', r'_country$', r'^country_',
            r'^region$', r'_region$',
            r'^zip', r'^postal', r'^address',
            r'^province$', r'_province$',
            r'^location$', r'_location$',
        ],
        ColumnSemanticType.CATEGORICAL: [
            r'^status$', r'_status$', r'^status_',
            r'^type$', r'_type$', r'^type_',
            r'^category$', r'_category$', r'^category_',
            r'^kind$', r'_kind$',
            r'^level$', r'_level$',
            r'^tier$', r'_tier$',
            r'^priority$', r'_priority$',
            r'^grade$', r'_grade$',
            r'^phase$', r'_phase$',
            r'^mode$', r'_mode$',
            r'^role$', r'_role$',
            r'^gender$', r'_gender$',
        ],
        ColumnSemanticType.TEMPORAL: [
            r'^date$', r'_date$', r'^date_',
            r'^time$', r'_time$', r'^time_',
            r'_at$',  # created_at, updated_at, deleted_at
            r'^timestamp', r'_timestamp$',
            r'^datetime', r'_datetime$',
            r'^created', r'^updated', r'^modified', r'^deleted',
            r'^start_', r'^end_', r'_start$', r'_end$',
            r'^expir', r'^due_',
        ],
        ColumnSemanticType.IDENTIFIER: [
            r'^id$', r'_id$', r'^id_',
            r'^uuid$', r'_uuid$',
            r'^key$', r'_key$',
            r'^code$', r'_code$',
            r'^sku$', r'^upc$', r'^ean$',
            r'^reference', r'^ref_',
        ],
        ColumnSemanticType.NUMERIC: [
            r'^price', r'_price$',
            r'^cost', r'_cost$',
            r'^amount', r'_amount$',
            r'^total', r'_total$',
            r'^count', r'_count$',
            r'^quantity', r'_quantity$', r'^qty',
            r'^rate', r'_rate$',
            r'^percent', r'_percent$', r'_pct$',
            r'^score', r'_score$',
            r'^weight', r'_weight$',
            r'^height', r'^width', r'^length',
            r'^age$', r'_age$',
            r'^balance', r'_balance$',
        ],
        ColumnSemanticType.TEXT: [
            r'^name$', r'_name$', r'^name_',
            r'^title$', r'_title$',
            r'^description', r'_description$', r'^desc$', r'_desc$',
            r'^comment', r'_comment$',
            r'^note', r'_note$',
            r'^message', r'_message$',
            r'^content', r'_content$',
            r'^email$', r'_email$',
            r'^phone', r'_phone$',
            r'^label$', r'_label$',
        ],
        ColumnSemanticType.BOOLEAN: [
            r'^is_', r'^has_', r'^can_', r'^should_',
            r'^enabled$', r'^disabled$',
            r'^active$', r'^inactive$',
            r'^visible$', r'^hidden$',
            r'^deleted$', r'^archived$',
            r'^verified$', r'^confirmed$',
            r'^public$', r'^private$',
            r'_flag$', r'^flag_',
        ],
    }

    # SQL type patterns
    TYPE_PATTERNS = {
        ColumnSemanticType.TEMPORAL: [
            r'date', r'time', r'timestamp', r'datetime',
        ],
        ColumnSemanticType.BOOLEAN: [
            r'^bool', r'^bit$', r'^tinyint\(1\)$',
        ],
        ColumnSemanticType.NUMERIC: [
            r'^int', r'^float', r'^double', r'^decimal', r'^numeric',
            r'^real', r'^money', r'^smallint', r'^bigint',
        ],
    }

    def detect(
        self,
        column_name: str,
        sql_type: str,
        sample_values: Optional[List[Any]] = None
    ) -> ColumnSemantics:
        """Detect the semantic type of a column.

        Args:
            column_name: Name of the column
            sql_type: SQL data type (e.g., "VARCHAR(2)", "INTEGER")
            sample_values: Optional list of sample values from the column

        Returns:
            ColumnSemantics with detected type and metadata
        """
        column_lower = column_name.lower()
        type_lower = sql_type.lower() if sql_type else ""

        # Track detection sources for confidence calculation
        name_match = None
        type_match = None
        value_match = None

        # 1. Check name patterns
        name_match = self._detect_from_name(column_lower)

        # 2. Check SQL type patterns
        type_match = self._detect_from_type(type_lower)

        # 3. Check sample values (most reliable for location detection)
        if sample_values:
            value_match = self._detect_from_values(sample_values, column_lower, type_lower)

        # 4. Resolve conflicts and calculate confidence
        return self._resolve_detection(
            column_lower, type_lower, sample_values,
            name_match, type_match, value_match
        )

    def _detect_from_name(self, column_lower: str) -> Optional[ColumnSemanticType]:
        """Detect type from column name patterns."""
        for sem_type, patterns in self.NAME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, column_lower):
                    logger.debug(f"Name pattern match: {column_lower} → {sem_type.value}")
                    return sem_type
        return None

    def _detect_from_type(self, type_lower: str) -> Optional[ColumnSemanticType]:
        """Detect type from SQL data type."""
        for sem_type, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, type_lower):
                    logger.debug(f"Type pattern match: {type_lower} → {sem_type.value}")
                    return sem_type
        return None

    def _detect_from_values(
        self,
        sample_values: List[Any],
        column_lower: str,
        type_lower: str
    ) -> Optional[tuple]:
        """Detect type from sample values. Returns (type, subtype, format, confidence)."""
        if not sample_values:
            return None

        # Filter out None/null values
        valid_values = [v for v in sample_values if v is not None]
        if not valid_values:
            return None

        # Check for US state codes
        if self._are_us_state_codes(valid_values):
            return (ColumnSemanticType.LOCATION, "us_state", "code", 0.95)

        # Check for US state full names
        if self._are_us_state_names(valid_values):
            return (ColumnSemanticType.LOCATION, "us_state", "full_name", 0.90)

        # Check for 2-letter uppercase codes (might be country codes)
        if self._are_two_letter_codes(valid_values):
            # If column name suggests location
            if any(kw in column_lower for kw in ['state', 'country', 'region', 'province']):
                return (ColumnSemanticType.LOCATION, "unknown", "code", 0.85)

        # Check for enum-like categorical values (low cardinality string values)
        if self._looks_categorical(valid_values, type_lower):
            return (ColumnSemanticType.CATEGORICAL, None, None, 0.70)

        return None

    def _are_us_state_codes(self, values: List[Any]) -> bool:
        """Check if values look like US state 2-letter codes."""
        str_values = [str(v).upper().strip() for v in values if v]
        if not str_values:
            return False

        # At least 50% should be valid state codes
        matches = sum(1 for v in str_values if v in self.US_STATE_CODES)
        return matches / len(str_values) >= 0.5

    def _are_us_state_names(self, values: List[Any]) -> bool:
        """Check if values look like US state full names."""
        str_values = [str(v).lower().strip() for v in values if v]
        if not str_values:
            return False

        # At least 50% should be valid state names
        matches = sum(1 for v in str_values if v in self.US_STATE_NAMES)
        return matches / len(str_values) >= 0.5

    def _are_two_letter_codes(self, values: List[Any]) -> bool:
        """Check if all values are 2-letter uppercase codes."""
        str_values = [str(v).strip() for v in values if v]
        if not str_values:
            return False

        # All should be exactly 2 uppercase letters
        return all(
            len(v) == 2 and v.isalpha() and v.isupper()
            for v in str_values
        )

    def _looks_categorical(self, values: List[Any], type_lower: str) -> bool:
        """Check if values look like categorical/enum values."""
        # Must be string type
        if 'int' in type_lower or 'float' in type_lower or 'decimal' in type_lower:
            return False

        str_values = [str(v).strip() for v in values if v]
        if not str_values:
            return False

        # Low cardinality (< 20 unique values)
        unique_values = set(str_values)
        if len(unique_values) > 20:
            return False

        # Short values (typical for status/type columns)
        avg_length = sum(len(v) for v in unique_values) / len(unique_values)
        if avg_length > 50:
            return False

        return True

    def _resolve_detection(
        self,
        column_lower: str,
        type_lower: str,
        sample_values: Optional[List[Any]],
        name_match: Optional[ColumnSemanticType],
        type_match: Optional[ColumnSemanticType],
        value_match: Optional[tuple]
    ) -> ColumnSemantics:
        """Resolve conflicts between detection methods and return final result."""

        # Value-based detection is most reliable
        if value_match:
            sem_type, subtype, fmt, conf = value_match
            return ColumnSemantics(
                semantic_type=sem_type,
                location_subtype=subtype,
                value_format=fmt,
                sample_values=sample_values[:5] if sample_values else None,
                confidence=conf
            )

        # Name + type agreement = high confidence
        if name_match and type_match and name_match == type_match:
            return ColumnSemantics(
                semantic_type=name_match,
                confidence=0.85,
                sample_values=sample_values[:5] if sample_values else None,
            )

        # Name match takes precedence
        if name_match:
            # Special handling for location columns
            if name_match == ColumnSemanticType.LOCATION:
                # Infer format from SQL type
                if 'varchar(2)' in type_lower or 'char(2)' in type_lower:
                    return ColumnSemantics(
                        semantic_type=name_match,
                        location_subtype=self._infer_location_subtype(column_lower),
                        value_format="code",
                        confidence=0.80,
                        sample_values=sample_values[:5] if sample_values else None,
                    )
                else:
                    return ColumnSemantics(
                        semantic_type=name_match,
                        location_subtype=self._infer_location_subtype(column_lower),
                        value_format="full_name",
                        confidence=0.75,
                        sample_values=sample_values[:5] if sample_values else None,
                    )

            return ColumnSemantics(
                semantic_type=name_match,
                confidence=0.70,
                sample_values=sample_values[:5] if sample_values else None,
            )

        # Type match only
        if type_match:
            return ColumnSemantics(
                semantic_type=type_match,
                confidence=0.60,
                sample_values=sample_values[:5] if sample_values else None,
            )

        # Unknown
        return ColumnSemantics(
            semantic_type=ColumnSemanticType.UNKNOWN,
            confidence=0.0,
            sample_values=sample_values[:5] if sample_values else None,
        )

    def _infer_location_subtype(self, column_lower: str) -> Optional[str]:
        """Infer location subtype from column name."""
        if 'state' in column_lower:
            return "us_state"
        if 'city' in column_lower:
            return "city"
        if 'country' in column_lower:
            return "country"
        if 'province' in column_lower:
            return "province"
        if 'region' in column_lower:
            return "region"
        if 'zip' in column_lower or 'postal' in column_lower:
            return "postal_code"
        return None


# Convenience function
def detect_column_semantics(
    column_name: str,
    sql_type: str,
    sample_values: Optional[List[Any]] = None
) -> ColumnSemantics:
    """Detect semantic type of a column.

    Args:
        column_name: Name of the column
        sql_type: SQL data type
        sample_values: Optional sample values

    Returns:
        ColumnSemantics with detected type
    """
    detector = ColumnSemanticsDetector()
    return detector.detect(column_name, sql_type, sample_values)
