"""Query Preprocessor - Pre-processes natural language queries before LLM generation

This module integrates existing components to preprocess questions:
1. LocationMapper - Normalize location names bidirectionally (California ↔ CA)
2. QueryIntentClassifier - Extract entities and validate schema
3. Early validation - Detect impossible queries before wasting LLM calls

Key Feature: Bidirectional Location Normalization
- Detects what format the DATABASE uses (from sample values)
- Converts query to match database format:
  - If DB stores "CA": "California" → "CA"
  - If DB stores "California": "CA" → "California"
- Works for US states, cities, countries

Usage:
    preprocessor = QueryPreprocessor(schema_dict)
    result = preprocessor.preprocess("Show orders from California")
    # If DB uses 2-letter codes: result.normalized = "Show orders from CA"
    # If DB uses full names: result.normalized unchanged

Part of: Small Model Optimization Phase
"""
import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DetectedLocation:
    """A detected location in the query."""
    original: str  # Original text (e.g., "California")
    normalized: str  # Normalized value (e.g., "CA" or "California" depending on DB format)
    location_type: str = "us_state"  # Type: us_state, city, country
    column_name: Optional[str] = None  # Which column this applies to
    db_format: str = "unknown"  # What format the DB uses: code, full_name, unknown
    start_pos: int = 0  # Position in original query
    end_pos: int = 0  # End position in original query


@dataclass
class LocationColumnInfo:
    """Information about a location column in the schema."""
    table: str
    column: str
    location_type: str  # us_state, city, country
    sample_values: List[str] = field(default_factory=list)
    uses_codes: bool = False  # True if DB uses codes (CA), False if full names
    detected_format: str = "unknown"  # code, full_name, mixed


@dataclass
class DetectedEntity:
    """An entity detected in the query."""
    text: str  # Original text
    entity_type: str  # table, column, value, location
    matched_to: Optional[str] = None  # Schema element it matched to
    confidence: float = 1.0


@dataclass
class PreprocessedQuery:
    """Result of query preprocessing."""
    original: str  # Original question
    normalized: str  # Normalized question (locations converted to match DB format)
    detected_locations: List[DetectedLocation] = field(default_factory=list)
    detected_entities: List[DetectedEntity] = field(default_factory=list)
    detected_intent: Optional[str] = None  # lookup, aggregation, comparison, etc.
    required_tables: List[str] = field(default_factory=list)
    required_columns: List[str] = field(default_factory=list)
    schema_validation_passed: bool = True
    validation_warnings: List[str] = field(default_factory=list)
    enhanced_context: str = ""  # Additional context for LLM
    preprocessing_applied: List[str] = field(default_factory=list)  # What was done
    location_format_hint: str = ""  # Hint about DB format for LLM

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "original": self.original,
            "normalized": self.normalized,
            "locations": [{"original": l.original, "normalized": l.normalized, "format": l.db_format}
                         for l in self.detected_locations],
            "entities": [{"text": e.text, "type": e.entity_type, "matched": e.matched_to}
                        for e in self.detected_entities],
            "intent": self.detected_intent,
            "required_tables": self.required_tables,
            "required_columns": self.required_columns,
            "validation_passed": self.schema_validation_passed,
            "warnings": self.validation_warnings,
            "preprocessing": self.preprocessing_applied,
            "location_format_hint": self.location_format_hint,
        }


class QueryPreprocessor:
    """
    Pre-processes natural language queries before LLM generation.

    Key Features:
    1. Bidirectional Location Normalization:
       - Detects what format the DB uses from sample values
       - Converts query locations to match: CA↔California, NY↔New York
       - Works for cities, states, and countries

    2. Intent Classification:
       - Extracts entities and validates against schema
       - Detects impossible queries early

    3. Enhanced Context:
       - Provides hints for LLM about matched entities
       - Adds location format guidance
    """

    def __init__(self, schema_dict: Dict[str, Any]):
        """
        Initialize the preprocessor with schema information.

        Args:
            schema_dict: Parsed schema dictionary from SchemaInspector
                Should include sample_values for location columns if available
        """
        self.schema = schema_dict
        self.tables = set(schema_dict.get("tables", {}).keys())
        self._location_columns = self._analyze_location_columns()

    def _analyze_location_columns(self) -> Dict[str, LocationColumnInfo]:
        """Find and analyze location columns to detect their format."""
        location_cols = {}

        for table_name, table_info in self.schema.get("tables", {}).items():
            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                sample_values = col.get("sample_values", [])

                # Detect location type from column name or hints
                location_type = None
                if col.get("location_type"):
                    location_type = col.get("location_type")
                elif col_name in ("state", "st", "state_code", "province"):
                    location_type = "us_state"
                elif col_name in ("city", "city_name"):
                    location_type = "city"
                elif col_name in ("country", "country_code", "nation"):
                    location_type = "country"
                elif col_name in ("region", "area", "zone"):
                    location_type = "region"

                if location_type:
                    # Analyze sample values to detect format
                    uses_codes, detected_format = self._detect_location_format(
                        sample_values, location_type
                    )

                    key = f"{table_name}.{col_name}"
                    location_cols[key] = LocationColumnInfo(
                        table=table_name,
                        column=col_name,
                        location_type=location_type,
                        sample_values=sample_values[:10],  # Keep first 10
                        uses_codes=uses_codes,
                        detected_format=detected_format
                    )

                    logger.debug(
                        f"Location column {key}: type={location_type}, "
                        f"format={detected_format}, uses_codes={uses_codes}"
                    )

        return location_cols

    def _detect_location_format(
        self,
        sample_values: List[str],
        location_type: str
    ) -> Tuple[bool, str]:
        """
        Detect whether a column uses codes or full names.

        Returns:
            Tuple of (uses_codes: bool, format: str)
        """
        if not sample_values:
            return False, "unknown"

        # Filter to non-empty string values
        values = [str(v).strip() for v in sample_values if v]
        if not values:
            return False, "unknown"

        if location_type == "us_state":
            # Check if values look like 2-letter state codes
            code_count = sum(1 for v in values if len(v) == 2 and v.isupper())
            full_name_count = sum(1 for v in values if len(v) > 2)

            if code_count > full_name_count:
                return True, "code"
            elif full_name_count > code_count:
                return False, "full_name"
            else:
                return False, "mixed"

        elif location_type == "country":
            # Check for 2-letter country codes (ISO 3166-1 alpha-2)
            code_count = sum(1 for v in values if len(v) == 2 and v.isupper())
            three_code_count = sum(1 for v in values if len(v) == 3 and v.isupper())
            full_name_count = sum(1 for v in values if len(v) > 3)

            if code_count > 0:
                return True, "code"
            elif three_code_count > 0:
                return True, "iso3"
            elif full_name_count > 0:
                return False, "full_name"
            else:
                return False, "unknown"

        # For cities and other types, assume full names
        return False, "full_name"

    def preprocess(self, question: str) -> PreprocessedQuery:
        """
        Apply all preprocessing steps to the question.

        Args:
            question: Natural language question

        Returns:
            PreprocessedQuery with normalized question and extracted info
        """
        result = PreprocessedQuery(
            original=question,
            normalized=question
        )

        try:
            # Step 1: Detect and normalize locations (bidirectional based on DB format)
            self._apply_location_normalization(result)

            # Step 2: Extract entities and classify intent using QueryIntentClassifier
            self._apply_intent_classification(result)

            # Step 3: Validate schema requirements
            self._validate_schema_requirements(result)

            # Step 4: Build enhanced context
            self._build_enhanced_context(result)

            logger.info(
                f"Preprocessed query: {len(result.detected_locations)} locations, "
                f"{len(result.detected_entities)} entities, "
                f"intent={result.detected_intent}, "
                f"valid={result.schema_validation_passed}"
            )

        except Exception as e:
            logger.error(f"Error preprocessing query: {e}", exc_info=True)
            result.validation_warnings.append(f"Preprocessing error: {str(e)}")

        return result

    def _apply_location_normalization(self, result: PreprocessedQuery) -> None:
        """
        Apply bidirectional location normalization based on database format.

        - If DB uses codes (CA, NY): Convert full names to codes
        - If DB uses full names (California, New York): Convert codes to full names
        """
        try:
            from src.core.location_mapper import LocationMapper

            # Detect locations in the query
            locations = LocationMapper.detect_location_in_query(result.original)

            if not locations:
                return

            result.preprocessing_applied.append("location_normalization")
            normalized = result.original

            # Determine what format to use based on location columns
            target_format = self._get_target_location_format()

            for loc in locations:
                original_text = loc.get("original", "")
                loc_type = loc.get("type", "us_state")

                # Determine what to normalize to based on DB format
                normalized_value = self._normalize_location_for_db(
                    original_text, loc_type, target_format
                )

                if normalized_value and original_text.lower() != normalized_value.lower():
                    # Create DetectedLocation record
                    result.detected_locations.append(DetectedLocation(
                        original=original_text,
                        normalized=normalized_value,
                        location_type=loc_type,
                        db_format=target_format
                    ))

                    # Replace in normalized query (case-insensitive, whole word)
                    pattern = re.compile(r'\b' + re.escape(original_text) + r'\b', re.IGNORECASE)
                    normalized = pattern.sub(normalized_value, normalized)

                    logger.debug(
                        f"Normalized location: '{original_text}' → '{normalized_value}' "
                        f"(target format: {target_format})"
                    )

            result.normalized = normalized

            # Add format hint for LLM
            if result.detected_locations:
                if target_format == "code":
                    result.location_format_hint = "Database uses 2-letter state codes (CA, NY, TX)"
                elif target_format == "full_name":
                    result.location_format_hint = "Database uses full state names (California, New York)"

        except ImportError:
            logger.debug("LocationMapper not available")
        except Exception as e:
            logger.warning(f"Location normalization failed: {e}")

    def _get_target_location_format(self) -> str:
        """Determine what location format the database uses."""
        # Check all location columns and prefer the most common format
        code_count = 0
        full_name_count = 0

        for col_info in self._location_columns.values():
            if col_info.uses_codes:
                code_count += 1
            else:
                full_name_count += 1

        if code_count > full_name_count:
            return "code"
        elif full_name_count > code_count:
            return "full_name"
        else:
            # Default to code format (most common in databases)
            return "code"

    def _normalize_location_for_db(
        self,
        location: str,
        location_type: str,
        target_format: str
    ) -> Optional[str]:
        """
        Normalize a location to match the database format.

        Args:
            location: The location text from the query
            location_type: Type of location (us_state, city, country)
            target_format: Target format (code or full_name)

        Returns:
            Normalized location string, or None if can't normalize
        """
        from src.core.location_mapper import LocationMapper

        if location_type in ("us_state", "state"):  # Handle both formats from LocationMapper
            # Check if it's already in the target format
            location_upper = location.upper().strip()
            location_lower = location.lower().strip()

            # Is it a 2-letter code?
            is_code = len(location.strip()) == 2 and location_upper in LocationMapper.US_STATE_CODES

            if target_format == "code":
                if is_code:
                    return location_upper  # Already a code
                else:
                    # Convert full name to code
                    return LocationMapper.normalize_us_state(location)
            else:  # target_format == "full_name"
                if is_code:
                    # Convert code to full name
                    return LocationMapper.expand_state_code(location_upper)
                else:
                    # Already a full name, return title case
                    if location_lower in LocationMapper.US_STATES:
                        return location.title()
                    return location

        # For other location types (city, country), return as-is for now
        return location

    def _apply_intent_classification(self, result: PreprocessedQuery) -> None:
        """Apply QueryIntentClassifier to extract entities and intent."""
        try:
            from src.llm.query_intent_classifier import QueryIntentClassifier

            classifier = QueryIntentClassifier(self.schema)
            intent_result = classifier.classify(result.original)

            result.preprocessing_applied.append("intent_classification")

            # Store detected intent
            result.detected_intent = intent_result.intent.value if intent_result.intent else None

            # Store required tables/columns
            result.required_tables = list(intent_result.required_tables) if intent_result.required_tables else []
            result.required_columns = list(intent_result.required_columns) if intent_result.required_columns else []

            # Convert extracted entities
            for entity in intent_result.extracted_entities or []:
                result.detected_entities.append(DetectedEntity(
                    text=entity.original_text,
                    entity_type=entity.entity_type,
                    matched_to=entity.schema_match,
                    confidence=entity.confidence
                ))

        except ImportError:
            logger.debug("QueryIntentClassifier not available")
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")

    def _validate_schema_requirements(self, result: PreprocessedQuery) -> None:
        """Validate that required schema elements exist."""
        result.preprocessing_applied.append("schema_validation")

        # Check if required tables exist
        tables_lower = {t.lower() for t in self.tables}
        for table in result.required_tables:
            if table.lower() not in tables_lower:
                result.schema_validation_passed = False
                result.validation_warnings.append(
                    f"Table '{table}' not found in schema. "
                    f"Available tables: {', '.join(sorted(self.tables)[:5])}"
                )

        # Check for location column if locations detected
        if result.detected_locations and not self._location_columns:
            result.validation_warnings.append(
                "Location detected in query but no state/region/country column found in schema"
            )

    def _build_enhanced_context(self, result: PreprocessedQuery) -> None:
        """Build enhanced context string for LLM."""
        context_parts = []

        # Add location hints with format information
        if result.detected_locations:
            loc_hints = [f"'{l.original}' → '{l.normalized}'" for l in result.detected_locations]
            context_parts.append(f"LOCATION NORMALIZATION: {', '.join(loc_hints)}")

            # Add format hint
            if result.location_format_hint:
                context_parts.append(f"FORMAT: {result.location_format_hint}")

            # Add info about which tables have location columns
            if self._location_columns:
                for key, col_info in self._location_columns.items():
                    context_parts.append(
                        f"Location column: {col_info.table}.{col_info.column} "
                        f"(type: {col_info.location_type}, format: {col_info.detected_format})"
                    )
                    if col_info.sample_values:
                        context_parts.append(f"  Sample values: {', '.join(col_info.sample_values[:5])}")

        # Add detected intent
        if result.detected_intent:
            context_parts.append(f"QUERY TYPE: {result.detected_intent.upper()}")

        # Add matched entities
        matched = [e for e in result.detected_entities if e.matched_to]
        if matched:
            entity_hints = [f"'{e.text}' → {e.matched_to}" for e in matched]
            context_parts.append(f"MATCHED ENTITIES: {', '.join(entity_hints)}")

        result.enhanced_context = "\n".join(context_parts)


def preprocess_query(
    question: str,
    schema_dict: Dict[str, Any],
    enable_location_preprocessing: bool = True
) -> PreprocessedQuery:
    """
    Convenience function to preprocess a query.

    Args:
        question: Natural language question
        schema_dict: Schema dictionary from SchemaInspector
        enable_location_preprocessing: Whether to apply location normalization

    Returns:
        PreprocessedQuery with normalized question and extracted info
    """
    if not enable_location_preprocessing:
        return PreprocessedQuery(
            original=question,
            normalized=question,
            preprocessing_applied=["skipped"]
        )

    preprocessor = QueryPreprocessor(schema_dict)
    return preprocessor.preprocess(question)
