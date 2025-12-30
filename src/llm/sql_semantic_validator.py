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

    def validate_where_columns_exist(
        self,
        sql: str,
        schema_dict: dict
    ) -> SemanticValidationResult:
        """Validate that WHERE clause columns exist in the queried tables.

        This catches errors like:
        - SELECT * FROM orders WHERE state = 'NY' (when state is in customers, not orders)

        Args:
            sql: SQL query to validate
            schema_dict: Schema dictionary with table/column information

        Returns:
            SemanticValidationResult with suggestions if columns are in wrong table
        """
        details = []
        suggestions = []

        # Extract tables from FROM/JOIN clauses
        tables_in_query = self._extract_table_references(sql)
        if not tables_in_query:
            return SemanticValidationResult(is_valid=True, confidence=1.0)

        # Extract WHERE clause
        where_match = re.search(r'\bWHERE\s+(.+?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)', sql, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return SemanticValidationResult(is_valid=True, confidence=1.0)

        where_clause = where_match.group(1)

        # IMPORTANT: Remove subqueries before extracting columns
        # This prevents false positives like flagging 'city' in:
        # SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE city = 'LA')
        # Without this, 'city' would be flagged as missing from 'orders' table
        where_clause_no_subquery = self._remove_subqueries(where_clause)

        # Extract column names from WHERE clause (handle various formats)
        # Matches: column = value, column LIKE value, column ILIKE value, etc.
        column_pattern = re.compile(r'\b(\w+)\s*(?:=|<|>|<=|>=|<>|!=|LIKE|ILIKE|IN|IS)\s*', re.IGNORECASE)
        where_columns = set(column_pattern.findall(where_clause_no_subquery))

        # Remove SQL keywords that might be caught
        sql_keywords = {'and', 'or', 'not', 'null', 'true', 'false', 'between'}
        where_columns = {c.lower() for c in where_columns if c.lower() not in sql_keywords}

        # Build set of columns available in queried tables
        available_columns = set()
        for table in tables_in_query:
            table_info = schema_dict.get("tables", {}).get(table, {})
            if not table_info:
                # Try case-insensitive match
                for t_name, t_info in schema_dict.get("tables", {}).items():
                    if t_name.lower() == table.lower():
                        table_info = t_info
                        break

            for col in table_info.get("columns", []):
                available_columns.add(col.get("name", "").lower())

        # Check each WHERE column exists in queried tables
        for col in where_columns:
            if col not in available_columns:
                # Find which table has this column
                tables_with_col = []
                for t_name, t_info in schema_dict.get("tables", {}).items():
                    for c in t_info.get("columns", []):
                        if c.get("name", "").lower() == col:
                            tables_with_col.append(t_name)

                if tables_with_col:
                    details.append(
                        f"Column '{col}' not found in queried tables ({', '.join(tables_in_query)})"
                    )
                    # Build explicit JOIN instruction with actual foreign key info
                    target_table = tables_with_col[0]
                    tables_list = list(tables_in_query)
                    source_table = tables_list[0] if tables_list else "your_table"

                    # Look up actual foreign key relationship from schema
                    join_condition = self._find_join_path(
                        schema_dict, source_table, target_table
                    )

                    if join_condition:
                        suggestions.append(
                            f"CRITICAL: Column '{col}' exists in '{target_table}', NOT in '{source_table}'. "
                            f"You MUST add this exact JOIN: "
                            f"'{join_condition}' "
                            f"Then use '{target_table}.{col}' in WHERE clause."
                        )
                    else:
                        # Fallback to generic hint if no FK found
                        suggestions.append(
                            f"CRITICAL: Column '{col}' exists in '{target_table}', NOT in '{source_table}'. "
                            f"You MUST add a JOIN like: "
                            f"'{source_table} JOIN {target_table} ON {source_table}.<id_column> = {target_table}.<foreign_key>' "
                            f"and reference the column as '{target_table}.{col}' in WHERE clause."
                        )

        if details:
            return SemanticValidationResult(
                is_valid=False,
                confidence=0.90,
                mismatch_type=SemanticMismatchType.COLUMN_NOT_REFERENCED,
                mismatch_details=details,
                suggestions=suggestions,
            )

        # NEW: Also validate subqueries (they have their own table context)
        subquery_result = self._validate_subqueries(sql, schema_dict)
        if not subquery_result.is_valid:
            return subquery_result

        return SemanticValidationResult(is_valid=True, confidence=0.95)

    def _validate_subqueries(
        self,
        sql: str,
        schema_dict: dict
    ) -> SemanticValidationResult:
        """Validate columns in subqueries against their table context.

        Subqueries have their own FROM clause and table context, so we need
        to validate their columns separately.

        For example, in:
            SELECT * FROM orders WHERE customer_id IN (
                SELECT id FROM products WHERE state = 'NY'
            )

        This validates that 'products' has 'id' and 'state' columns.

        Args:
            sql: Full SQL query potentially containing subqueries
            schema_dict: Schema dictionary with table/column information

        Returns:
            SemanticValidationResult with errors if invalid columns found
        """
        details = []
        suggestions = []

        # Extract subqueries
        subqueries = self._extract_subqueries(sql)

        for subquery in subqueries:
            # Get tables in this subquery
            subquery_tables = self._extract_table_references(subquery)
            if not subquery_tables:
                continue

            # Build set of columns available in subquery's tables
            available_columns = set()
            available_columns_by_table = {}
            for table in subquery_tables:
                table_info = schema_dict.get("tables", {}).get(table, {})
                if not table_info:
                    # Try case-insensitive match
                    for t_name, t_info in schema_dict.get("tables", {}).items():
                        if t_name.lower() == table.lower():
                            table_info = t_info
                            table = t_name  # Use correct case
                            break

                if not table_info:
                    # Table doesn't exist
                    details.append(
                        f"Subquery references non-existent table: '{table}'"
                    )
                    all_tables = list(schema_dict.get("tables", {}).keys())
                    suggestions.append(
                        f"Table '{table}' does not exist. Available tables: {', '.join(all_tables)}"
                    )
                    continue

                cols = {col.get("name", "").lower() for col in table_info.get("columns", [])}
                available_columns.update(cols)
                available_columns_by_table[table] = cols

            # Extract columns from SELECT and WHERE in subquery
            subquery_columns = self._extract_columns_from_query(subquery)

            # Check each column exists
            for col in subquery_columns:
                if col.lower() not in available_columns:
                    # Column doesn't exist in subquery's tables
                    tables_str = ", ".join(subquery_tables)

                    # Find which table actually has this column
                    tables_with_col = []
                    for t_name, t_info in schema_dict.get("tables", {}).items():
                        for c in t_info.get("columns", []):
                            if c.get("name", "").lower() == col.lower():
                                tables_with_col.append(t_name)

                    details.append(
                        f"Subquery column '{col}' not found in table(s): {tables_str}"
                    )

                    if tables_with_col:
                        suggestions.append(
                            f"Column '{col}' exists in table(s): {', '.join(tables_with_col)}, "
                            f"not in {tables_str}. Fix the subquery to use the correct table."
                        )
                    else:
                        # Find similar column names
                        similar = self._find_similar(col, available_columns)
                        if similar:
                            suggestions.append(
                                f"Column '{col}' does not exist. Did you mean: {', '.join(similar)}?"
                            )
                        else:
                            suggestions.append(
                                f"Column '{col}' does not exist in any table."
                            )

        if details:
            return SemanticValidationResult(
                is_valid=False,
                confidence=0.85,
                mismatch_type=SemanticMismatchType.COLUMN_NOT_REFERENCED,
                mismatch_details=details,
                suggestions=suggestions,
            )

        return SemanticValidationResult(is_valid=True, confidence=0.95)

    def _extract_subqueries(self, sql: str) -> List[str]:
        """Extract all subqueries from SQL.

        Args:
            sql: SQL query potentially containing subqueries

        Returns:
            List of subquery strings (without outer parentheses)
        """
        subqueries = []
        text = sql
        max_iterations = 20

        for _ in range(max_iterations):
            # Find (SELECT pattern
            subquery_start = re.search(r'\(\s*SELECT\b', text, re.IGNORECASE)
            if not subquery_start:
                break

            start_pos = subquery_start.start()

            # Find matching closing parenthesis
            depth = 0
            end_pos = None
            in_string = False
            string_char = None

            for i in range(start_pos, len(text)):
                char = text[i]

                if char in ('"', "'") and (i == 0 or text[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                    continue

                if in_string:
                    continue

                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break

            if end_pos is None:
                break

            # Extract subquery content (without outer parentheses)
            subquery_content = text[start_pos + 1:end_pos - 1].strip()
            subqueries.append(subquery_content)

            # Replace with placeholder to find next subquery
            text = text[:start_pos] + '__SUBQUERY__' + text[end_pos:]

        return subqueries

    def _extract_columns_from_query(self, sql: str) -> Set[str]:
        """Extract column references from a SQL query.

        Finds columns in SELECT list and WHERE clause.

        Args:
            sql: SQL query

        Returns:
            Set of column names found
        """
        columns = set()
        sql_keywords = {'select', 'from', 'where', 'and', 'or', 'not', 'null',
                       'true', 'false', 'between', 'in', 'like', 'is', 'as',
                       'join', 'on', 'order', 'by', 'group', 'having', 'limit',
                       'offset', 'distinct', 'count', 'sum', 'avg', 'max', 'min',
                       'asc', 'desc', 'inner', 'left', 'right', 'outer', 'case',
                       'when', 'then', 'else', 'end', 'cast', 'coalesce', 'nullif'}

        # Extract from SELECT clause
        select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM\b', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_part = select_match.group(1)
            # Remove table prefixes (table.column -> column)
            select_part = re.sub(r'\w+\.', '', select_part)
            # Find word tokens
            tokens = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', select_part)
            for token in tokens:
                if token.lower() not in sql_keywords and token != '*':
                    columns.add(token.lower())

        # Extract from WHERE clause
        where_match = re.search(r'\bWHERE\s+(.+?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)', sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_part = where_match.group(1)
            # Remove subqueries first
            where_part = self._remove_subqueries(where_part)
            # Remove table prefixes
            where_part = re.sub(r'\w+\.', '', where_part)
            # Find word tokens before operators
            tokens = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', where_part)
            for token in tokens:
                if token.lower() not in sql_keywords:
                    columns.add(token.lower())

        return columns

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

    def validate_column_qualification(
        self,
        sql: str,
        schema_dict: dict
    ) -> SemanticValidationResult:
        """Validate that column references are properly qualified in multi-table queries.

        This addresses a common issue where LLMs generate SQL with ambiguous column
        references in JOINs, causing "ambiguous column name" errors at execution time.

        Example issues caught:
        - SELECT name, customer_id FROM orders JOIN customers ON ...
          (if both tables have 'name', this fails)

        Args:
            sql: SQL query to validate
            schema_dict: Schema dictionary with table/column information

        Returns:
            SemanticValidationResult with warnings if columns need qualification
        """
        details = []
        suggestions = []

        # Only validate multi-table queries
        if not self._is_multi_table_query(sql):
            return SemanticValidationResult(is_valid=True, confidence=1.0)

        # Extract table references to know which tables are in the query
        tables_in_query = self._extract_table_references(sql)
        if len(tables_in_query) < 2:
            return SemanticValidationResult(is_valid=True, confidence=1.0)

        # Find columns that exist in multiple tables being joined
        ambiguous_columns = self._find_ambiguous_columns(
            tables_in_query, schema_dict
        )

        if not ambiguous_columns:
            return SemanticValidationResult(is_valid=True, confidence=1.0)

        # Check for unqualified column references in SELECT clause
        select_match = re.search(
            r'\bSELECT\s+(.+?)\s+FROM\b',
            sql,
            re.IGNORECASE | re.DOTALL
        )

        if select_match:
            select_clause = select_match.group(1)
            unqualified = self._find_unqualified_references(
                select_clause, ambiguous_columns, tables_in_query
            )

            if unqualified:
                for col in unqualified:
                    tables_with_col = [
                        t for t, cols in ambiguous_columns.items()
                        if col.lower() in [c.lower() for c in cols]
                    ]
                    details.append(
                        f"Ambiguous column '{col}' exists in multiple tables: "
                        f"{', '.join(tables_with_col)}"
                    )
                    suggestions.append(
                        f"Qualify '{col}' with table name: "
                        f"{tables_with_col[0]}.{col}"
                    )

        if details:
            return SemanticValidationResult(
                is_valid=False,  # Mark as invalid to trigger regeneration
                confidence=0.85,
                mismatch_type=SemanticMismatchType.COLUMN_NOT_REFERENCED,
                mismatch_details=details,
                suggestions=suggestions,
            )

        return SemanticValidationResult(is_valid=True, confidence=0.95)

    def _is_multi_table_query(self, sql: str) -> bool:
        """Check if SQL involves multiple tables."""
        has_join = bool(self.JOIN_PATTERN.search(sql))
        # Also check for comma-separated tables: FROM t1, t2
        comma_tables = re.search(
            r'\bFROM\s+\w+\s*,\s*\w+',
            sql,
            re.IGNORECASE
        )
        return has_join or bool(comma_tables)

    def _remove_subqueries(self, text: str) -> str:
        """Remove subqueries (SELECT statements in parentheses) from text.

        This is used to prevent false positives in WHERE column validation.
        For example, in:
            customer_id IN (SELECT id FROM customers WHERE city = 'LA')

        We want to validate customer_id (outer scope) but NOT city (subquery scope).

        Uses balanced parentheses counting to handle nested subqueries correctly.
        For nested queries like:
            customer_id IN (SELECT id FROM customers WHERE city IN (SELECT name FROM cities))

        This replaces the entire outer subquery (including nested ones) with a placeholder.

        Args:
            text: SQL text potentially containing subqueries

        Returns:
            Text with subquery content replaced by placeholder
        """
        result = text
        max_iterations = 20  # Prevent infinite loops

        for _ in range(max_iterations):
            # Find (SELECT pattern (case insensitive)
            subquery_start = re.search(r'\(\s*SELECT\b', result, re.IGNORECASE)
            if not subquery_start:
                break  # No more subqueries

            start_pos = subquery_start.start()

            # Find matching closing parenthesis using balanced counting
            depth = 0
            end_pos = None
            in_string = False
            string_char = None

            for i in range(start_pos, len(result)):
                char = result[i]

                # Handle string literals to avoid counting parens inside strings
                if char in ('"', "'") and (i == 0 or result[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                    continue

                if in_string:
                    continue

                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break

            if end_pos is None:
                # Unbalanced parentheses, stop to avoid infinite loop
                break

            # Replace the subquery with placeholder
            result = result[:start_pos] + '__SUBQUERY__' + result[end_pos:]

        return result

    def _find_join_path(
        self, schema_dict: dict, source_table: str, target_table: str
    ) -> Optional[str]:
        """Find the JOIN path between two tables using foreign key relationships.

        Searches the schema's relationships array to find a direct or indirect
        join path from source_table to target_table.

        Args:
            schema_dict: Schema dictionary with relationships
            source_table: The table currently in the query (e.g., 'orders')
            target_table: The table containing the missing column (e.g., 'customers')

        Returns:
            A specific JOIN clause string, or None if no relationship found.
            Example: "orders JOIN customers ON orders.customer_id = customers.id"
        """
        relationships = schema_dict.get("relationships", [])
        if not relationships:
            return None

        source_lower = source_table.lower()
        target_lower = target_table.lower()

        # Try direct relationship: source -> target
        for rel in relationships:
            from_t = rel.get("from_table", "").lower()
            to_t = rel.get("to_table", "").lower()
            from_col = rel.get("from_column", "")
            to_col = rel.get("to_column", "")

            if from_t == source_lower and to_t == target_lower:
                # source has FK to target: source.fk_col -> target.pk_col
                return f"{source_table} JOIN {target_table} ON {source_table}.{from_col} = {target_table}.{to_col}"

            if from_t == target_lower and to_t == source_lower:
                # target has FK to source: target.fk_col -> source.pk_col
                # Need to join target to source in reverse
                return f"{source_table} JOIN {target_table} ON {source_table}.{to_col} = {target_table}.{from_col}"

        # Try indirect relationship via intermediate table (one hop)
        for rel1 in relationships:
            from_t1 = rel1.get("from_table", "").lower()
            to_t1 = rel1.get("to_table", "").lower()
            from_col1 = rel1.get("from_column", "")
            to_col1 = rel1.get("to_column", "")

            if from_t1 == source_lower:
                # source -> intermediate
                intermediate = to_t1
                for rel2 in relationships:
                    from_t2 = rel2.get("from_table", "").lower()
                    to_t2 = rel2.get("to_table", "").lower()
                    from_col2 = rel2.get("from_column", "")
                    to_col2 = rel2.get("to_column", "")

                    if from_t2 == intermediate and to_t2 == target_lower:
                        # Found: source -> intermediate -> target
                        int_table = rel1.get("to_table", intermediate)
                        return (
                            f"{source_table} JOIN {int_table} ON {source_table}.{from_col1} = {int_table}.{to_col1} "
                            f"JOIN {target_table} ON {int_table}.{from_col2} = {target_table}.{to_col2}"
                        )

        return None

    def _extract_table_references(self, sql: str) -> Set[str]:
        """Extract all table names referenced in SQL."""
        tables = set()

        # FROM clause
        from_match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        if from_match:
            tables.add(from_match.group(1).lower())

        # JOIN clauses
        join_pattern = re.compile(r'\bJOIN\s+(\w+)', re.IGNORECASE)
        tables.update(m.lower() for m in join_pattern.findall(sql))

        # Comma-separated tables: FROM t1, t2
        comma_match = re.search(
            r'\bFROM\s+(\w+)\s*,\s*(\w+)',
            sql,
            re.IGNORECASE
        )
        if comma_match:
            tables.add(comma_match.group(1).lower())
            tables.add(comma_match.group(2).lower())

        return tables

    def _find_ambiguous_columns(
        self,
        tables_in_query: Set[str],
        schema_dict: dict
    ) -> dict:
        """Find columns that exist in multiple tables being queried.

        Returns:
            Dict mapping table names to their columns that are ambiguous
        """
        # Build column -> tables mapping
        column_tables = {}  # column_name -> [tables that have it]

        for table in tables_in_query:
            table_info = schema_dict.get("tables", {}).get(table, {})
            if not table_info:
                # Try case-insensitive match
                for t_name, t_info in schema_dict.get("tables", {}).items():
                    if t_name.lower() == table.lower():
                        table_info = t_info
                        break

            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                if col_name not in column_tables:
                    column_tables[col_name] = []
                column_tables[col_name].append(table)

        # Find columns in multiple tables
        ambiguous = {}
        for col_name, tables in column_tables.items():
            if len(tables) > 1:
                for table in tables:
                    if table not in ambiguous:
                        ambiguous[table] = []
                    ambiguous[table].append(col_name)

        return ambiguous

    def _find_unqualified_references(
        self,
        select_clause: str,
        ambiguous_columns: dict,
        tables_in_query: Set[str]
    ) -> List[str]:
        """Find unqualified references to ambiguous columns."""
        unqualified = []

        # Get all ambiguous column names
        all_ambiguous = set()
        for cols in ambiguous_columns.values():
            all_ambiguous.update(c.lower() for c in cols)

        # Parse SELECT clause for column references
        # Pattern: match column names that are NOT preceded by table. or table_
        # e.g., "name" is unqualified, but "customers.name" is qualified

        # Split by comma to get individual selections
        selections = re.split(r'\s*,\s*', select_clause)

        for selection in selections:
            selection = selection.strip()

            # Skip if it's a * or table.* or aggregate function
            if selection in ('*', ) or re.match(r'\w+\.\*', selection):
                continue

            # Extract the column name (handle aliases with AS)
            col_match = re.search(r'^(\w+)(?:\s|$)', selection)
            if col_match:
                col_name = col_match.group(1).lower()

                # Check if it's ambiguous and unqualified
                if col_name in all_ambiguous:
                    # Check if it's qualified (table.column or alias.column)
                    qualified_pattern = re.compile(
                        r'(\w+)\.(' + re.escape(col_name) + r')\b',
                        re.IGNORECASE
                    )
                    if not qualified_pattern.search(selection):
                        # Not qualified - this will cause ambiguity
                        unqualified.append(col_name)

        return unqualified


    def analyze_pre_generation_requirements(
        self,
        question: str,
        schema_dict: dict,
        primary_table: Optional[str] = None
    ) -> dict:
        """Analyze question BEFORE SQL generation to identify required JOINs.

        This method detects filter values in the question (state codes, status values, etc.)
        and determines which tables contain the corresponding columns. If a filter column
        is in a different table than the primary query table, it generates explicit JOIN hints.

        This prevents errors like:
        - "Show orders from NY" → generating `WHERE orders.state = 'NY'` when state is in customers

        Args:
            question: Natural language question
            schema_dict: Schema dictionary with table/column information
            primary_table: Optional primary table the query is about (e.g., 'orders')

        Returns:
            Dictionary with:
                - required_joins: List of explicit JOIN requirements
                - filter_column_hints: Dict mapping detected filters to their table locations
                - join_instructions: Formatted string for prompt injection
        """
        result = {
            "required_joins": [],
            "filter_column_hints": {},
            "join_instructions": "",
        }

        if not schema_dict or not question:
            return result

        question_lower = question.lower()

        # Build column-to-table mapping from schema
        column_to_tables = {}  # column_name -> [(table_name, column_info), ...]
        for table_name, table_info in schema_dict.get("tables", {}).items():
            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                if col_name not in column_to_tables:
                    column_to_tables[col_name] = []
                column_to_tables[col_name].append((table_name, col))

        # Detect state/location filters
        state_patterns = [
            # US state codes
            (r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b', 'state'),
            # Full state names
            (r'\b(california|texas|new york|florida|illinois|pennsylvania|ohio|georgia|north carolina|michigan|new jersey|virginia|washington|arizona|massachusetts|tennessee|indiana|missouri|maryland|wisconsin|colorado|minnesota|south carolina|alabama|louisiana|kentucky|oregon|oklahoma|connecticut|utah|iowa|nevada|arkansas|kansas|mississippi|nebraska|new mexico|west virginia|idaho|hawaii|maine|new hampshire|rhode island|montana|delaware|south dakota|north dakota|alaska|vermont|wyoming)\b', 'state'),
            # Common phrases indicating state filter
            (r'\b(?:from|in|to|shipped to|delivered to|located in)\s+([\w\s]+?)(?:\s+state)?\s*$', 'state'),
        ]

        # Detect status filters
        status_patterns = [
            (r'\b(pending|processing|shipped|delivered|cancelled|completed|active|inactive)\b', 'status'),
        ]

        # Detect category filters
        category_patterns = [
            (r'\b(electronics?|clothing|food|beverages?|books?|toys?|furniture|home|garden|sports?|health|beauty)\b', 'category'),
        ]

        detected_filters = []
        seen_columns = set()  # Prevent duplicate detections

        # Check state patterns
        for pattern, col_type in state_patterns:
            matches = re.findall(pattern, question_lower, re.IGNORECASE)
            for match in matches:
                if "state" not in seen_columns:
                    detected_filters.append(("state", match, col_type))
                    seen_columns.add("state")
                    break  # One match per column type is enough

        # Check status patterns
        for pattern, col_type in status_patterns:
            matches = re.findall(pattern, question_lower, re.IGNORECASE)
            for match in matches:
                if "status" not in seen_columns:
                    detected_filters.append(("status", match, col_type))
                    seen_columns.add("status")
                    break

        # Check category patterns
        for pattern, col_type in category_patterns:
            matches = re.findall(pattern, question_lower, re.IGNORECASE)
            for match in matches:
                if "category" not in seen_columns:
                    detected_filters.append(("category", match, col_type))
                    seen_columns.add("category")
                    break

        # Detect primary table from question if not provided
        if not primary_table:
            table_names = list(schema_dict.get("tables", {}).keys())
            for table in table_names:
                # Check if table name (or singular form) is mentioned
                table_lower = table.lower()
                singular = table_lower.rstrip('s')  # Simple singular form
                if table_lower in question_lower or singular in question_lower:
                    primary_table = table
                    break

        if not primary_table or not detected_filters:
            return result

        # Check if filter columns are in a different table than primary
        primary_columns = set()
        primary_table_info = schema_dict.get("tables", {}).get(primary_table, {})
        for col in primary_table_info.get("columns", []):
            primary_columns.add(col.get("name", "").lower())

        join_hints = []
        for col_name, value, col_type in detected_filters:
            if col_name not in primary_columns:
                # Column is not in primary table - find which table has it
                if col_name in column_to_tables:
                    for table_name, col_info in column_to_tables[col_name]:
                        if table_name.lower() != primary_table.lower():
                            # Need to JOIN to this table
                            join_path = self._find_join_path(
                                schema_dict, primary_table, table_name
                            )

                            result["filter_column_hints"][col_name] = {
                                "table": table_name,
                                "value_detected": value,
                            }

                            if join_path:
                                result["required_joins"].append({
                                    "from_table": primary_table,
                                    "to_table": table_name,
                                    "column": col_name,
                                    "join_clause": join_path,
                                })
                                join_hints.append(
                                    f"CRITICAL JOIN REQUIRED: To filter by '{col_name}' (value: '{value}'), "
                                    f"you MUST JOIN '{primary_table}' to '{table_name}' because '{col_name}' "
                                    f"is in '{table_name}', NOT in '{primary_table}'.\n"
                                    f"  → Use: {join_path}\n"
                                    f"  → Then filter with: {table_name}.{col_name} = '{value}'"
                                )
                            else:
                                join_hints.append(
                                    f"CRITICAL: Column '{col_name}' (for value '{value}') is in table "
                                    f"'{table_name}', NOT in '{primary_table}'. You must JOIN to '{table_name}'."
                                )
                            break  # Found the table, stop looking

        if join_hints:
            result["join_instructions"] = "\n\n".join(join_hints)

        return result


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
