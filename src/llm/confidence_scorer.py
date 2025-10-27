"""
Confidence Scoring System for SQL Corrections

Predicts the likelihood of success for SQL corrections before execution.
Uses multiple factors to calculate a confidence score (0.0 to 1.0).
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of SQL errors - ordered by difficulty to fix"""
    TABLE_NOT_FOUND = "table_not_found"          # Easiest
    COLUMN_NOT_FOUND = "column_not_found"        # Easy
    SYNTAX_ERROR = "syntax_error"                # Medium
    TYPE_MISMATCH = "type_mismatch"              # Medium-Hard
    PERMISSION_DENIED = "permission_denied"       # Hard
    TIMEOUT = "timeout"                           # Hard
    AMBIGUOUS_COLUMN = "ambiguous_column"        # Medium
    CONSTRAINT_VIOLATION = "constraint_violation" # Hard
    CONNECTION_ERROR = "connection_error"         # Very Hard
    UNKNOWN = "unknown"                           # Hardest


@dataclass
class ConfidenceScore:
    """
    Confidence score for a SQL correction attempt

    Attributes:
        overall: Final confidence score (0.0 to 1.0)
        factors: Individual scoring factors and their contributions
        reasoning: Human-readable explanation
        recommendation: Action recommendation
    """
    overall: float
    factors: Dict[str, float]
    reasoning: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "overall": round(self.overall, 3),  # Frontend expects 'overall' not 'confidence'
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
            "reasoning": self.reasoning,
            "recommendation": self.recommendation,
            "level": self.get_level()
        }

    def get_level(self) -> str:
        """Get confidence level description"""
        if self.overall >= 0.8:
            return "HIGH"
        elif self.overall >= 0.5:
            return "MEDIUM"
        elif self.overall >= 0.3:
            return "LOW"
        else:
            return "VERY_LOW"


class ConfidenceScorer:
    """
    Predicts success probability of SQL corrections

    Scoring Factors:
    1. Error Type (30%) - Some errors are easier to fix than others
    2. Schema Match (25%) - Does the correction use valid schema objects?
    3. Historical Success (20%) - Past success rate for this error type
    4. Correction Complexity (15%) - Simple fixes more likely to work
    5. Similarity to Original (10%) - Small changes more likely correct
    """

    # Base confidence scores by error type (difficulty to fix)
    ERROR_TYPE_BASE_CONFIDENCE = {
        ErrorType.TABLE_NOT_FOUND: 0.85,      # Very fixable - usually typo
        ErrorType.COLUMN_NOT_FOUND: 0.80,     # Very fixable - usually typo
        ErrorType.AMBIGUOUS_COLUMN: 0.75,     # Fixable - add table prefix
        ErrorType.SYNTAX_ERROR: 0.60,         # Moderately fixable
        ErrorType.TYPE_MISMATCH: 0.50,        # Harder - semantic issue
        ErrorType.CONSTRAINT_VIOLATION: 0.40, # Hard - business logic
        ErrorType.TIMEOUT: 0.30,              # Very hard - performance
        ErrorType.PERMISSION_DENIED: 0.20,    # Very hard - access control
        ErrorType.CONNECTION_ERROR: 0.10,     # Extremely hard - infrastructure
        ErrorType.UNKNOWN: 0.30,              # Unknown difficulty
    }

    def __init__(self):
        self.historical_stats: Dict[str, Dict[str, Any]] = {}

    def predict_success_probability(
        self,
        error_type: str,
        original_sql: str,
        correction_sql: str,
        schema: Optional[Dict[str, List[str]]] = None,
        historical_success_rate: Optional[float] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceScore:
        """
        Predict the probability that a correction will succeed

        Args:
            error_type: Type of error being corrected
            original_sql: The original (failed) SQL
            correction_sql: The proposed correction
            schema: Database schema (table -> columns mapping)
            historical_success_rate: Past success rate for this error type
            error_message: The actual error message
            context: Additional context (database type, etc.)

        Returns:
            ConfidenceScore with overall score and detailed breakdown
        """
        factors = {}

        # Factor 1: Error Type (30%)
        error_type_score = self._score_error_type(error_type)
        factors["error_type"] = error_type_score * 0.30

        # Factor 2: Schema Match (25%)
        schema_score = self._score_schema_match(
            correction_sql, schema, error_type, error_message
        )
        factors["schema_match"] = schema_score * 0.25

        # Factor 3: Historical Success (20%)
        history_score = self._score_historical_success(
            error_type, historical_success_rate
        )
        factors["historical_success"] = history_score * 0.20

        # Factor 4: Correction Complexity (15%)
        complexity_score = self._score_correction_complexity(
            original_sql, correction_sql
        )
        factors["correction_complexity"] = complexity_score * 0.15

        # Factor 5: Similarity to Original (10%)
        similarity_score = self._score_similarity(
            original_sql, correction_sql
        )
        factors["similarity"] = similarity_score * 0.10

        # Calculate overall confidence
        overall = sum(factors.values())

        # Generate reasoning and recommendation
        reasoning = self._generate_reasoning(
            error_type, overall, factors, schema is not None
        )
        recommendation = self._generate_recommendation(overall, error_type)

        return ConfidenceScore(
            overall=overall,
            factors=factors,
            reasoning=reasoning,
            recommendation=recommendation
        )

    def _score_error_type(self, error_type: str) -> float:
        """
        Score based on error type difficulty

        Returns: 0.0 to 1.0
        """
        try:
            error_enum = ErrorType(error_type)
            return self.ERROR_TYPE_BASE_CONFIDENCE[error_enum]
        except (ValueError, KeyError):
            # Unknown error type - medium confidence
            return 0.50

    def _score_schema_match(
        self,
        sql: str,
        schema: Optional[Dict[str, List[str]]],
        error_type: str,
        error_message: Optional[str]
    ) -> float:
        """
        Score based on whether SQL matches schema

        Returns: 0.0 to 1.0
        """
        if schema is None:
            # No schema provided - neutral score
            return 0.50

        sql_lower = sql.lower()

        # Extract table and column references from SQL
        tables_in_sql = self._extract_tables(sql)
        columns_in_sql = self._extract_columns(sql)

        if not tables_in_sql and not columns_in_sql:
            # Can't extract references - neutral
            return 0.50

        # Check table matches
        valid_tables = 0
        invalid_tables = 0

        for table in tables_in_sql:
            if table in schema:
                valid_tables += 1
            else:
                # Check for close matches
                if self._has_similar_table(table, schema):
                    valid_tables += 0.5  # Partial credit for similar
                else:
                    invalid_tables += 1

        # Check column matches
        valid_columns = 0
        invalid_columns = 0

        for column in columns_in_sql:
            if self._column_exists_in_schema(column, tables_in_sql, schema):
                valid_columns += 1
            else:
                invalid_columns += 1

        # Calculate score
        total_refs = valid_tables + invalid_tables + valid_columns + invalid_columns
        if total_refs == 0:
            return 0.50

        valid_refs = valid_tables + valid_columns
        score = valid_refs / total_refs

        # Boost score if error was about missing table/column and now it exists
        if error_type in ["table_not_found", "column_not_found"]:
            if valid_tables > 0 or valid_columns > 0:
                score = min(1.0, score + 0.2)  # Bonus for fixing the issue

        return score

    def _score_historical_success(
        self,
        error_type: str,
        historical_success_rate: Optional[float]
    ) -> float:
        """
        Score based on past success rate for this error type

        Returns: 0.0 to 1.0
        """
        if historical_success_rate is not None:
            return historical_success_rate

        # Check internal stats
        if error_type in self.historical_stats:
            stats = self.historical_stats[error_type]
            attempts = stats.get("attempts", 0)
            successes = stats.get("successes", 0)

            if attempts > 0:
                return successes / attempts

        # No historical data - return base confidence for error type
        return self._score_error_type(error_type)

    def _score_correction_complexity(
        self,
        original_sql: str,
        correction_sql: str
    ) -> float:
        """
        Score based on complexity of the correction
        Simpler corrections are more likely to be correct

        Returns: 0.0 to 1.0
        """
        # Count changes
        orig_words = original_sql.lower().split()
        corr_words = correction_sql.lower().split()

        # Calculate edit distance
        changes = abs(len(orig_words) - len(corr_words))

        # Count actual word differences
        matcher = SequenceMatcher(None, orig_words, corr_words)
        changes += len([op for op in matcher.get_opcodes()
                       if op[0] in ('replace', 'delete', 'insert')])

        # Fewer changes = higher confidence
        if changes == 0:
            return 0.5  # No change is suspicious
        elif changes <= 2:
            return 1.0  # Simple fix - high confidence
        elif changes <= 5:
            return 0.8  # Moderate fix
        elif changes <= 10:
            return 0.6  # Complex fix
        else:
            return 0.4  # Very complex - lower confidence

    def _score_similarity(
        self,
        original_sql: str,
        correction_sql: str
    ) -> float:
        """
        Score based on similarity between original and correction
        Small targeted changes are better than complete rewrites

        Returns: 0.0 to 1.0
        """
        # Calculate string similarity
        similarity = SequenceMatcher(
            None,
            original_sql.lower(),
            correction_sql.lower()
        ).ratio()

        # High similarity is good (targeted fix)
        # But perfect similarity (1.0) is bad (no fix)
        if similarity >= 0.99:
            return 0.3  # Suspicious - barely changed
        elif similarity >= 0.70:
            return 1.0  # Good - targeted change
        elif similarity >= 0.40:
            return 0.7  # Moderate change
        else:
            return 0.4  # Major rewrite - less confident

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL"""
        tables = []

        # Look for FROM and JOIN clauses
        from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'

        tables.extend(re.findall(from_pattern, sql, re.IGNORECASE))
        tables.extend(re.findall(join_pattern, sql, re.IGNORECASE))

        return list(set([t.lower() for t in tables]))

    def _extract_columns(self, sql: str) -> List[str]:
        """Extract column names from SQL (simplified)"""
        columns = []

        # Extract from SELECT clause (simple cases)
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)

        if match:
            select_clause = match.group(1)
            # Split by comma and clean
            for part in select_clause.split(','):
                part = part.strip()
                # Remove aliases (AS ...)
                part = re.sub(r'\s+AS\s+.*$', '', part, flags=re.IGNORECASE)
                # Extract column name (simple cases)
                if '.' in part:
                    column = part.split('.')[-1].strip()
                else:
                    column = part.strip()

                if column and column != '*' and not column.startswith('('):
                    columns.append(column.lower())

        return columns

    def _column_exists_in_schema(
        self,
        column: str,
        tables: List[str],
        schema: Dict[str, List[str]]
    ) -> bool:
        """Check if column exists in any of the referenced tables"""
        for table in tables:
            if table in schema:
                if column in [c.lower() for c in schema[table]]:
                    return True
        return False

    def _has_similar_table(
        self,
        table: str,
        schema: Dict[str, List[str]],
        threshold: float = 0.8
    ) -> bool:
        """Check if there's a similar table name in schema"""
        for schema_table in schema.keys():
            similarity = SequenceMatcher(
                None, table.lower(), schema_table.lower()
            ).ratio()
            if similarity >= threshold:
                return True
        return False

    def _generate_reasoning(
        self,
        error_type: str,
        overall: float,
        factors: Dict[str, float],
        has_schema: bool
    ) -> str:
        """Generate human-readable reasoning"""
        level = "high" if overall >= 0.8 else "medium" if overall >= 0.5 else "low"

        # Find top contributing factors
        sorted_factors = sorted(
            factors.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_factor = sorted_factors[0][0].replace('_', ' ').title()

        reasoning_parts = [
            f"This correction has {level} confidence ({overall:.1%}).",
        ]

        # Add specific insights
        if factors.get("error_type", 0) > 0.2:
            reasoning_parts.append(
                f"{error_type.replace('_', ' ').title()} errors are "
                f"{'relatively easy' if factors['error_type'] > 0.20 else 'challenging'} to fix."
            )

        if has_schema and factors.get("schema_match", 0) > 0.15:
            reasoning_parts.append(
                "The correction references valid schema objects."
            )
        elif has_schema and factors.get("schema_match", 0) < 0.10:
            reasoning_parts.append(
                "Warning: Some schema objects in the correction may not exist."
            )

        if factors.get("correction_complexity", 0) > 0.10:
            reasoning_parts.append(
                "The correction is relatively simple."
            )

        return " ".join(reasoning_parts)

    def _generate_recommendation(
        self,
        confidence: float,
        error_type: str
    ) -> str:
        """Generate action recommendation"""
        if confidence >= 0.8:
            return "EXECUTE - High confidence, likely to succeed"
        elif confidence >= 0.6:
            return "EXECUTE - Medium-high confidence, worth trying"
        elif confidence >= 0.4:
            return "EXECUTE_WITH_CAUTION - Medium confidence, may need fallback"
        elif confidence >= 0.2:
            return "CONSIDER_ALTERNATIVES - Low confidence, try other approaches"
        else:
            return "SKIP - Very low confidence, likely to fail"

    def update_historical_stats(
        self,
        error_type: str,
        success: bool
    ):
        """Update historical success statistics"""
        if error_type not in self.historical_stats:
            self.historical_stats[error_type] = {
                "attempts": 0,
                "successes": 0
            }

        self.historical_stats[error_type]["attempts"] += 1
        if success:
            self.historical_stats[error_type]["successes"] += 1

        logger.debug(
            f"Updated stats for {error_type}: "
            f"{self.historical_stats[error_type]}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            error_type: {
                **stats,
                "success_rate": (
                    stats["successes"] / stats["attempts"]
                    if stats["attempts"] > 0 else 0.0
                )
            }
            for error_type, stats in self.historical_stats.items()
        }


# Global singleton instance
_scorer_instance: Optional[ConfidenceScorer] = None


def get_confidence_scorer() -> ConfidenceScorer:
    """Get or create global confidence scorer instance"""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = ConfidenceScorer()
    return _scorer_instance
