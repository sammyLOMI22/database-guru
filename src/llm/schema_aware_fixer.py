"""Schema-Aware SQL Fixer - Fast corrections using schema metadata"""
import logging
import re
from typing import Optional, Dict, List, Tuple, Any
from difflib import SequenceMatcher
from dataclasses import dataclass

from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)


@dataclass
class QuickFix:
    """Result of a quick fix attempt"""
    success: bool
    fixed_sql: Optional[str] = None
    correction_type: Optional[str] = None
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    confidence: float = 0.0
    explanation: Optional[str] = None


class FuzzyMatcher:
    """Fuzzy string matching for finding similar names"""

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """
        Calculate similarity between two strings (0.0 to 1.0)

        Uses SequenceMatcher for accurate similarity scoring
        """
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    @staticmethod
    def find_closest(
        target: str,
        candidates: List[str],
        threshold: float = 0.6,
        max_results: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Find closest matching strings from candidates

        Args:
            target: String to match
            candidates: List of candidate strings
            threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results to return

        Returns:
            List of (candidate, similarity_score) tuples, sorted by score
        """
        if not target or not candidates:
            return []

        # Calculate similarity for all candidates
        similarities = [
            (candidate, FuzzyMatcher.similarity(target, candidate))
            for candidate in candidates
        ]

        # Filter by threshold and sort by similarity
        matches = [
            (candidate, score)
            for candidate, score in similarities
            if score >= threshold
        ]

        # Sort by similarity (descending) and return top results
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_results]

    @staticmethod
    def find_best_match(
        target: str,
        candidates: List[str],
        threshold: float = 0.6
    ) -> Optional[Tuple[str, float]]:
        """
        Find single best match

        Returns:
            (best_candidate, similarity_score) or None
        """
        matches = FuzzyMatcher.find_closest(target, candidates, threshold, max_results=1)
        return matches[0] if matches else None


class SchemaAwareFixer:
    """
    Fast SQL fixer using schema metadata

    This fixer attempts to correct SQL errors using schema information
    WITHOUT calling the LLM. This is 100x faster and has zero API cost.

    Use cases:
    - Column name typos: "pric" → "price"
    - Table name typos: "prodcuts" → "products"
    - Case sensitivity: "Products" → "products"
    - Plural/singular confusion: "customer" → "customers"
    """

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize schema-aware fixer

        Args:
            schema: Database schema information
                Format: {
                    "tables": {
                        "products": {
                            "columns": ["id", "name", "price", "category_id"],
                            "primary_key": "id",
                            "foreign_keys": {...}
                        },
                        ...
                    }
                }
        """
        self.schema = schema
        self.fuzzy_matcher = FuzzyMatcher()
        self._build_lookup_caches()

    def _build_lookup_caches(self):
        """Build fast lookup caches for common corrections"""
        # Extract all table names
        self.table_names = list(self.schema.get("tables", {}).keys())

        # Extract all column names by table
        self.columns_by_table: Dict[str, List[str]] = {}
        for table_name, table_info in self.schema.get("tables", {}).items():
            self.columns_by_table[table_name] = table_info.get("columns", [])

        # Build global column list (for when table is unknown)
        self.all_columns = []
        for columns in self.columns_by_table.values():
            self.all_columns.extend(columns)
        self.all_columns = list(set(self.all_columns))  # Remove duplicates

        logger.info(
            f"Schema cache built: {len(self.table_names)} tables, "
            f"{len(self.all_columns)} unique columns"
        )

    def quick_fix(
        self,
        sql: str,
        error_type: ErrorType,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QuickFix:
        """
        Attempt to fix SQL using schema without LLM

        Args:
            sql: The SQL that failed
            error_type: Type of error
            error_message: Error message from database
            context: Additional context (e.g., missing_table, missing_column)

        Returns:
            QuickFix result
        """
        logger.info(f"Attempting schema-aware quick fix for {error_type.value}")

        try:
            # Route to appropriate fixer based on error type
            if error_type == ErrorType.TABLE_NOT_FOUND:
                return self._fix_table_not_found(sql, error_message, context)

            elif error_type == ErrorType.COLUMN_NOT_FOUND:
                return self._fix_column_not_found(sql, error_message, context)

            elif error_type == ErrorType.SYNTAX_ERROR:
                return self._fix_syntax_error(sql, error_message, context)

            else:
                # Cannot quick-fix this error type
                return QuickFix(success=False)

        except Exception as e:
            logger.error(f"Quick fix failed: {e}")
            return QuickFix(success=False)

    def _fix_table_not_found(
        self,
        sql: str,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> QuickFix:
        """Fix table not found errors"""
        # Extract missing table name
        missing_table = self._extract_table_name(error_message)
        if context and "missing_table" in context:
            missing_table = context["missing_table"]

        if not missing_table:
            return QuickFix(success=False)

        logger.info(f"Looking for match for table: {missing_table}")

        # Find best match in schema
        match = self.fuzzy_matcher.find_best_match(
            missing_table,
            self.table_names,
            threshold=0.6
        )

        if not match:
            logger.info(f"No good match found for table: {missing_table}")
            return QuickFix(success=False)

        correct_table, confidence = match
        logger.info(
            f"Found match: {missing_table} → {correct_table} "
            f"(confidence: {confidence:.2f})"
        )

        # Only use if confidence is high enough
        if confidence < 0.7:
            return QuickFix(success=False, confidence=confidence)

        # Replace table name in SQL
        fixed_sql = self._replace_table_name(sql, missing_table, correct_table)

        return QuickFix(
            success=True,
            fixed_sql=fixed_sql,
            correction_type="table_name",
            original_value=missing_table,
            corrected_value=correct_table,
            confidence=confidence,
            explanation=f"Corrected table name: {missing_table} → {correct_table}"
        )

    def _fix_column_not_found(
        self,
        sql: str,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> QuickFix:
        """Fix column not found errors"""
        # Extract missing column name
        missing_column = self._extract_column_name(error_message)
        if context and "missing_column" in context:
            missing_column = context["missing_column"]

        if not missing_column:
            return QuickFix(success=False)

        logger.info(f"Looking for match for column: {missing_column}")

        # Try to identify which table we're working with
        table_name = self._identify_table_from_sql(sql)

        # Get candidate columns
        if table_name and table_name in self.columns_by_table:
            candidates = self.columns_by_table[table_name]
            logger.info(f"Searching in table {table_name} columns")
        else:
            candidates = self.all_columns
            logger.info("Searching in all columns (table unknown)")

        # Find best match
        match = self.fuzzy_matcher.find_best_match(
            missing_column,
            candidates,
            threshold=0.6
        )

        if not match:
            logger.info(f"No good match found for column: {missing_column}")
            return QuickFix(success=False)

        correct_column, confidence = match
        logger.info(
            f"Found match: {missing_column} → {correct_column} "
            f"(confidence: {confidence:.2f})"
        )

        # Only use if confidence is high enough
        if confidence < 0.7:
            return QuickFix(success=False, confidence=confidence)

        # Replace column name in SQL
        fixed_sql = self._replace_column_name(sql, missing_column, correct_column)

        return QuickFix(
            success=True,
            fixed_sql=fixed_sql,
            correction_type="column_name",
            original_value=missing_column,
            corrected_value=correct_column,
            confidence=confidence,
            explanation=f"Corrected column name: {missing_column} → {correct_column}"
        )

    def _fix_syntax_error(
        self,
        sql: str,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> QuickFix:
        """
        Attempt to fix simple syntax errors

        Note: Most syntax errors need LLM. We only handle very simple cases.
        """
        # Common simple syntax fixes
        fixes = [
            # Missing semicolon (if database requires it)
            (r'^(.*[^;])\s*$', r'\1;', "Added missing semicolon"),

            # Double spaces
            (r'\s{2,}', ' ', "Removed extra spaces"),

            # Missing space after comma
            (r',(\S)', r', \1', "Added space after comma"),
        ]

        for pattern, replacement, description in fixes:
            if re.search(pattern, sql):
                fixed_sql = re.sub(pattern, replacement, sql)
                if fixed_sql != sql:
                    return QuickFix(
                        success=True,
                        fixed_sql=fixed_sql,
                        correction_type="syntax",
                        confidence=0.8,
                        explanation=description
                    )

        return QuickFix(success=False)

    def _extract_table_name(self, error_message: str) -> Optional[str]:
        """Extract table name from error message"""
        patterns = [
            r'table["\s]+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'relation["\s]+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'no such table:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'"([a-zA-Z_][a-zA-Z0-9_]*)".*does not exist',
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_column_name(self, error_message: str) -> Optional[str]:
        """Extract column name from error message"""
        patterns = [
            r'column["\s]+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'field["\s]+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'no such column:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'"([a-zA-Z_][a-zA-Z0-9_]*)".*does not exist',
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _identify_table_from_sql(self, sql: str) -> Optional[str]:
        """Try to identify which table is being queried"""
        # Look for FROM clause
        from_match = re.search(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        if from_match:
            table_name = from_match.group(1)
            # Check if it's in our schema
            if table_name in self.table_names:
                return table_name

        # Look for JOIN clauses
        join_match = re.search(r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        if join_match:
            table_name = join_match.group(1)
            if table_name in self.table_names:
                return table_name

        return None

    def _replace_table_name(self, sql: str, old_name: str, new_name: str) -> str:
        """Replace table name in SQL, being careful about word boundaries"""
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(old_name) + r'\b'
        fixed_sql = re.sub(pattern, new_name, sql, flags=re.IGNORECASE)
        return fixed_sql

    def _replace_column_name(self, sql: str, old_name: str, new_name: str) -> str:
        """Replace column name in SQL"""
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(old_name) + r'\b'
        fixed_sql = re.sub(pattern, new_name, sql, flags=re.IGNORECASE)
        return fixed_sql

    def get_correction_stats(self) -> Dict[str, Any]:
        """Get statistics about available corrections"""
        return {
            "total_tables": len(self.table_names),
            "total_columns": len(self.all_columns),
            "tables_with_columns": len(self.columns_by_table),
            "average_columns_per_table": (
                len(self.all_columns) / len(self.table_names)
                if self.table_names else 0
            )
        }
