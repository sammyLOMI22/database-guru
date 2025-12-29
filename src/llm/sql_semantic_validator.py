"""SQL Semantic Validation (Phase 3).

This module validates that generated SQL matches the detected user intent
BEFORE execution. This catches mismatches early and allows regeneration.

Key validations:
- AGGREGATION intent → SQL must have COUNT/SUM/AVG/etc.
- COMPARISON intent → SQL must have WHERE clause
- RELATIONSHIP intent → SQL must have JOIN
- RANKING intent → SQL must have ORDER BY + LIMIT
- TEMPORAL intent → SQL must reference date/time columns

Performance target: <20ms (regex-based, no LLM calls)
"""
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set

# Import centralized FuzzyMatcher (addresses PR review: code duplication)
try:
    from src.core.fuzzy_matcher import FuzzyMatcher
    FUZZY_MATCHER_AVAILABLE = True
except ImportError:
    FUZZY_MATCHER_AVAILABLE = False

logger = logging.getLogger(__name__)


class SemanticMismatchType(Enum):
    """Types of semantic mismatches between intent and SQL."""
    NO_MISMATCH = "no_mismatch"
    MISSING_AGGREGATION = "missing_aggregation"
    MISSING_JOIN = "missing_join"
    MISSING_WHERE = "missing_where"
    MISSING_ORDER_BY = "missing_order_by"
    MISSING_LIMIT = "missing_limit"
    MISSING_DATE_FILTER = "missing_date_filter"
    TABLE_NOT_REFERENCED = "table_not_referenced"
    COLUMN_NOT_REFERENCED = "column_not_referenced"
    LOCATION_NOT_MAPPED = "location_not_mapped"
    WRONG_AGGREGATION_TYPE = "wrong_aggregation_type"


@dataclass
class SemanticValidationResult:
    """Result of semantic validation.

    Attributes:
        is_valid: Whether the SQL matches the detected intent
        confidence: Confidence in the validation (0.0-1.0)
        mismatch_type: Type of mismatch (if any)
        mismatch_details: Detailed explanation of mismatches
        suggestions: Hints for regenerating better SQL
        validation_time_ms: Time taken to validate (for metrics)
    """
    is_valid: bool
    confidence: float
    mismatch_type: SemanticMismatchType = SemanticMismatchType.NO_MISMATCH
    mismatch_details: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0

    def get_regeneration_hints(self) -> str:
        """Get hints for regenerating better SQL.

        Returns:
            Formatted string with regeneration hints
        """
        if self.is_valid:
            return ""

        hints = [f"Validation failed: {self.mismatch_type.value}"]
        hints.extend(self.mismatch_details)

        if self.suggestions:
            hints.append("\nSuggestions for better SQL:")
            hints.extend(f"- {s}" for s in self.suggestions)

        return "\n".join(hints)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "mismatch_type": self.mismatch_type.value,
            "mismatch_details": self.mismatch_details,
            "suggestions": self.suggestions,
            "validation_time_ms": self.validation_time_ms,
        }


class SQLSemanticValidator:
    """Validates that generated SQL matches detected query intent.

    This validator uses fast regex-based pattern matching to check
    that the SQL structure aligns with the classified intent.

    Usage:
        validator = SQLSemanticValidator()
        result = validator.validate(sql, intent_result)
        if not result.is_valid:
            hints = result.get_regeneration_hints()
            # Use hints to regenerate SQL

    Note: Regex patterns are designed to be robust against various SQL formatting
    styles (addresses PR review: regex fragility). Key improvements:
    - Handle multiple whitespace/newlines with \\s+
    - Handle optional parentheses spacing like COUNT ( * )
    - Handle quoted identifiers and aliases
    """

    # SQL pattern matchers (robust to whitespace variations)
    # Addresses PR review: "COUNT ( * ) with spaces might fail"
    AGGREGATION_PATTERN = re.compile(
        r'\b(COUNT|SUM|AVG|MIN|MAX|TOTAL)\s*\(\s*',  # Allow spaces inside parens
        re.IGNORECASE | re.MULTILINE
    )

    # More robust JOIN detection with various whitespace
    JOIN_PATTERN = re.compile(
        r'\b(INNER\s+JOIN|LEFT\s+(OUTER\s+)?JOIN|RIGHT\s+(OUTER\s+)?JOIN|'
        r'FULL\s+(OUTER\s+)?JOIN|CROSS\s+JOIN|NATURAL\s+JOIN|JOIN)\b',
        re.IGNORECASE | re.MULTILINE
    )

    WHERE_PATTERN = re.compile(r'\bWHERE\s+', re.IGNORECASE | re.MULTILINE)

    # Handle multiline ORDER BY
    ORDER_BY_PATTERN = re.compile(r'\bORDER\s+BY\s+', re.IGNORECASE | re.MULTILINE)

    # Handle various LIMIT formats (including OFFSET)
    LIMIT_PATTERN = re.compile(
        r'\bLIMIT\s+\d+(\s+OFFSET\s+\d+)?',
        re.IGNORECASE | re.MULTILINE
    )

    GROUP_BY_PATTERN = re.compile(r'\bGROUP\s+BY\s+', re.IGNORECASE | re.MULTILINE)

    # Date/time column patterns (for temporal validation)
    # Extended to catch more date-related column naming patterns
    DATE_COLUMN_PATTERN = re.compile(
        r'\b(date|time|timestamp|datetime|created|updated|modified|'
        r'start|end|due|expir|birth|order_date|ship_date|'
        r'created_at|updated_at|deleted_at|'
        r'_date|_time|_at)\w*\b',
        re.IGNORECASE
    )

    # Common aggregation keywords that indicate expected aggregation
    AGGREGATION_KEYWORDS = {
        'count': 'COUNT',
        'how many': 'COUNT',
        'number of': 'COUNT',
        'total': 'SUM',
        'sum of': 'SUM',
        'average': 'AVG',
        'avg': 'AVG',
        'mean': 'AVG',
        'minimum': 'MIN',
        'min': 'MIN',
        'maximum': 'MAX',
        'max': 'MAX',
        'highest': 'MAX',
        'lowest': 'MIN',
    }

    def validate(
        self,
        sql: str,
        intent_result: "QueryIntentResult",  # Forward reference
        question: Optional[str] = None
    ) -> SemanticValidationResult:
        """Validate that SQL matches the detected intent.

        Args:
            sql: Generated SQL query
            intent_result: Result from QueryIntentClassifier
            question: Original question (optional, for extra validation)

        Returns:
            SemanticValidationResult with validation details
        """
        import time
        start_time = time.time()

        # Skip validation for impossible intents
        if intent_result.intent.value == "impossible":
            return SemanticValidationResult(
                is_valid=True,
                confidence=1.0,
                validation_time_ms=(time.time() - start_time) * 1000
            )

        # Run intent-specific validations
        intent = intent_result.intent.value

        if intent == "aggregation":
            result = self._validate_aggregation_intent(sql, intent_result, question)
        elif intent == "comparison":
            result = self._validate_comparison_intent(sql, intent_result)
        elif intent == "relationship":
            result = self._validate_relationship_intent(sql, intent_result)
        elif intent == "ranking":
            result = self._validate_ranking_intent(sql, intent_result)
        elif intent == "temporal":
            result = self._validate_temporal_intent(sql, intent_result)
        elif intent == "lookup":
            result = self._validate_lookup_intent(sql, intent_result)
        else:
            # Unknown intent, pass through
            result = SemanticValidationResult(is_valid=True, confidence=0.5)

        result.validation_time_ms = (time.time() - start_time) * 1000
        return result

    def _validate_aggregation_intent(
        self,
        sql: str,
        intent_result: "QueryIntentResult",
        question: Optional[str] = None
    ) -> SemanticValidationResult:
        """Validate SQL for aggregation intent."""
        details = []
        suggestions = []

        # Check for aggregation functions
        has_aggregation = bool(self.AGGREGATION_PATTERN.search(sql))

        if not has_aggregation:
            # Check what kind of aggregation is expected
            expected_agg = None
            if question:
                for keyword, agg_type in self.AGGREGATION_KEYWORDS.items():
                    if keyword in question.lower():
                        expected_agg = agg_type
                        break

            details.append("SQL is missing aggregation function (COUNT, SUM, AVG, etc.)")
            if expected_agg:
                suggestions.append(f"Add {expected_agg}() to match the question intent")
            else:
                suggestions.append("Add appropriate aggregation function based on the question")

            return SemanticValidationResult(
                is_valid=False,
                confidence=0.9,
                mismatch_type=SemanticMismatchType.MISSING_AGGREGATION,
                mismatch_details=details,
                suggestions=suggestions,
            )

        # Check for GROUP BY if multiple columns selected with aggregation
        if self.AGGREGATION_PATTERN.search(sql) and not self.GROUP_BY_PATTERN.search(sql):
            # Only flag if there are non-aggregated columns
            # This is a softer check - might still be valid for simple counts
            pass

        return SemanticValidationResult(
            is_valid=True,
            confidence=0.95,
        )

    def _validate_comparison_intent(
        self,
        sql: str,
        intent_result: "QueryIntentResult"
    ) -> SemanticValidationResult:
        """Validate SQL for comparison intent."""
        details = []
        suggestions = []

        # Check for WHERE clause
        has_where = bool(self.WHERE_PATTERN.search(sql))

        if not has_where:
            details.append("SQL is missing WHERE clause for comparison")

            # Get expected filter values
            if intent_result.required_values:
                for col, val in intent_result.required_values.items():
                    suggestions.append(f"Add filter: WHERE {col} = '{val}'")
            else:
                suggestions.append("Add WHERE clause to filter results")

            return SemanticValidationResult(
                is_valid=False,
                confidence=0.85,
                mismatch_type=SemanticMismatchType.MISSING_WHERE,
                mismatch_details=details,
                suggestions=suggestions,
            )

        # Check that filter values are used (if known)
        if intent_result.required_values:
            sql_lower = sql.lower()
            for col, val in intent_result.required_values.items():
                val_str = str(val).lower()
                if val_str not in sql_lower and col.lower() not in sql_lower:
                    details.append(f"Expected filter on '{col}' with value '{val}' not found")
                    suggestions.append(f"Add condition: {col} = '{val}'")

            if details:
                return SemanticValidationResult(
                    is_valid=False,
                    confidence=0.75,
                    mismatch_type=SemanticMismatchType.COLUMN_NOT_REFERENCED,
                    mismatch_details=details,
                    suggestions=suggestions,
                )

        return SemanticValidationResult(
            is_valid=True,
            confidence=0.90,
        )

    def _validate_relationship_intent(
        self,
        sql: str,
        intent_result: "QueryIntentResult"
    ) -> SemanticValidationResult:
        """Validate SQL for relationship (JOIN) intent."""
        details = []
        suggestions = []

        # Check for JOIN
        has_join = bool(self.JOIN_PATTERN.search(sql))

        # Also check for comma-separated tables (implicit join)
        # Pattern: FROM table1, table2
        from_pattern = re.compile(r'\bFROM\s+\w+\s*,\s*\w+', re.IGNORECASE)
        has_implicit_join = bool(from_pattern.search(sql))

        if not has_join and not has_implicit_join:
            details.append("SQL is missing JOIN for multi-table query")

            # Suggest tables to join
            if intent_result.required_tables and len(intent_result.required_tables) > 1:
                tables = list(intent_result.required_tables)
                suggestions.append(f"Join tables: {', '.join(tables)}")
            else:
                suggestions.append("Add JOIN clause to connect related tables")

            return SemanticValidationResult(
                is_valid=False,
                confidence=0.90,
                mismatch_type=SemanticMismatchType.MISSING_JOIN,
                mismatch_details=details,
                suggestions=suggestions,
            )

        return SemanticValidationResult(
            is_valid=True,
            confidence=0.90,
        )

    def _validate_ranking_intent(
        self,
        sql: str,
        intent_result: "QueryIntentResult"
    ) -> SemanticValidationResult:
        """Validate SQL for ranking (TOP N) intent."""
        details = []
        suggestions = []

        # Check for ORDER BY
        has_order_by = bool(self.ORDER_BY_PATTERN.search(sql))

        # Check for LIMIT
        has_limit = bool(self.LIMIT_PATTERN.search(sql))

        if not has_order_by:
            details.append("SQL is missing ORDER BY for ranking query")
            suggestions.append("Add ORDER BY clause to rank results")

            return SemanticValidationResult(
                is_valid=False,
                confidence=0.85,
                mismatch_type=SemanticMismatchType.MISSING_ORDER_BY,
                mismatch_details=details,
                suggestions=suggestions,
            )

        if not has_limit:
            details.append("SQL is missing LIMIT for top-N query")
            suggestions.append("Add LIMIT clause to restrict to top N results")

            return SemanticValidationResult(
                is_valid=False,
                confidence=0.75,
                mismatch_type=SemanticMismatchType.MISSING_LIMIT,
                mismatch_details=details,
                suggestions=suggestions,
            )

        return SemanticValidationResult(
            is_valid=True,
            confidence=0.95,
        )

    def _validate_temporal_intent(
        self,
        sql: str,
        intent_result: "QueryIntentResult"
    ) -> SemanticValidationResult:
        """Validate SQL for temporal (date/time) intent."""
        details = []
        suggestions = []

        # Check for date column references
        has_date_ref = bool(self.DATE_COLUMN_PATTERN.search(sql))

        # Check for WHERE clause (temporal filters usually need WHERE)
        has_where = bool(self.WHERE_PATTERN.search(sql))

        if not has_date_ref:
            details.append("SQL is missing date/time column reference")
            suggestions.append("Add date column (created_at, order_date, etc.) to the query")

            return SemanticValidationResult(
                is_valid=False,
                confidence=0.70,
                mismatch_type=SemanticMismatchType.MISSING_DATE_FILTER,
                mismatch_details=details,
                suggestions=suggestions,
            )

        # Temporal queries usually need filtering
        if not has_where:
            details.append("Temporal query might need date range filter")
            suggestions.append("Consider adding WHERE clause to filter by date range")

            # This is a warning, not a failure
            return SemanticValidationResult(
                is_valid=True,
                confidence=0.70,
                mismatch_details=details,
                suggestions=suggestions,
            )

        return SemanticValidationResult(
            is_valid=True,
            confidence=0.85,
        )

    def _validate_lookup_intent(
        self,
        sql: str,
        intent_result: "QueryIntentResult"
    ) -> SemanticValidationResult:
        """Validate SQL for simple lookup intent."""
        details = []
        suggestions = []

        # Check that required tables are referenced
        if intent_result.required_tables:
            sql_lower = sql.lower()
            for table in intent_result.required_tables:
                if table.lower() not in sql_lower:
                    details.append(f"Expected table '{table}' not found in SQL")
                    suggestions.append(f"Reference table: {table}")

            if details:
                return SemanticValidationResult(
                    is_valid=False,
                    confidence=0.80,
                    mismatch_type=SemanticMismatchType.TABLE_NOT_REFERENCED,
                    mismatch_details=details,
                    suggestions=suggestions,
                )

        return SemanticValidationResult(
            is_valid=True,
            confidence=0.85,
        )

    def validate_table_references(
        self,
        sql: str,
        available_tables: Set[str]
    ) -> SemanticValidationResult:
        """Validate that SQL only references available tables.

        Args:
            sql: SQL query to validate
            available_tables: Set of available table names

        Returns:
            SemanticValidationResult
        """
        details = []
        suggestions = []

        # Extract table references from SQL
        # Pattern: FROM table_name or JOIN table_name
        table_pattern = re.compile(
            r'(?:FROM|JOIN)\s+["\']?(\w+)["\']?',
            re.IGNORECASE
        )

        referenced_tables = set(table_pattern.findall(sql))
        available_lower = {t.lower() for t in available_tables}

        for table in referenced_tables:
            if table.lower() not in available_lower:
                details.append(f"Table '{table}' not found in schema")

                # Find similar table names
                similar = self._find_similar(table, available_tables)
                if similar:
                    suggestions.append(f"Did you mean: {', '.join(similar)}?")

        if details:
            return SemanticValidationResult(
                is_valid=False,
                confidence=0.95,
                mismatch_type=SemanticMismatchType.TABLE_NOT_REFERENCED,
                mismatch_details=details,
                suggestions=suggestions,
            )

        return SemanticValidationResult(
            is_valid=True,
            confidence=1.0,
        )

    def _find_similar(self, name: str, candidates: Set[str], max_results: int = 3) -> List[str]:
        """Find similar names using fuzzy matching.

        Uses centralized FuzzyMatcher for consistent matching (addresses PR review).
        """
        # Use FuzzyMatcher if available (more accurate than character counting)
        if FUZZY_MATCHER_AVAILABLE:
            matcher = FuzzyMatcher(tables=list(candidates))
            similar = matcher.find_similar(name, candidates, max_results=max_results, threshold=0.3)
            return [s for s, _ in similar]

        # Fallback to original logic
        name_lower = name.lower()
        scored = []

        for candidate in candidates:
            candidate_lower = candidate.lower()
            # Simple similarity: common character count
            common = sum(1 for c in name_lower if c in candidate_lower)
            similarity = common / max(len(name_lower), len(candidate_lower))
            if similarity > 0.3:
                scored.append((candidate, similarity))

        # Sort by similarity and return top matches
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:max_results]]


# Convenience function
def validate_sql_semantics(
    sql: str,
    intent_result: "QueryIntentResult",
    question: Optional[str] = None
) -> SemanticValidationResult:
    """Validate that SQL matches detected query intent.

    Args:
        sql: Generated SQL query
        intent_result: Result from QueryIntentClassifier
        question: Original question (optional)

    Returns:
        SemanticValidationResult
    """
    validator = SQLSemanticValidator()
    return validator.validate(sql, intent_result, question)
