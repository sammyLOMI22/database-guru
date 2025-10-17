"""Result Verification Agent - Validates and checks SQL query results for logical errors"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class VerificationIssue(Enum):
    """Types of issues detected in query results"""
    EMPTY_RESULT = "empty_result"
    ALL_NULLS = "all_nulls"
    EXTREME_VALUE = "extreme_value"
    UNEXPECTED_COUNT = "unexpected_count"
    SINGLE_ROW_AGGREGATE = "single_row_aggregate"
    NEGATIVE_COUNT = "negative_count"
    TYPE_INCONSISTENCY = "type_inconsistency"
    NO_ISSUE = "no_issue"


@dataclass
class VerificationResult:
    """Result of verification check"""
    is_suspicious: bool
    confidence: float  # 0.0 to 1.0, how confident we are there's an issue
    issue_type: VerificationIssue
    description: str
    suggested_fix: Optional[str] = None
    diagnostic_queries: Optional[List[str]] = None  # Queries to run for diagnosis


@dataclass
class DiagnosticResult:
    """Result from running diagnostic queries"""
    table_exists: bool
    table_has_data: bool
    column_exists: bool
    sample_data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    diagnosis: Optional[str] = None


class ResultVerificationAgent:
    """
    Agent that verifies query results make sense and catches logical errors

    This agent will:
    1. Check if results are suspicious (empty, all nulls, extreme values)
    2. Run diagnostic queries to understand the issue
    3. Suggest improvements or regenerate the query
    4. Catch logical errors before showing results to user
    """

    def __init__(
        self,
        enable_diagnostics: bool = True,
        enable_auto_fix: bool = True,
        extreme_value_threshold: float = 1e9
    ):
        """
        Initialize the result verification agent

        Args:
            enable_diagnostics: Whether to run diagnostic queries
            enable_auto_fix: Whether to attempt automatic fixes
            extreme_value_threshold: Threshold for detecting extreme values
        """
        self.enable_diagnostics = enable_diagnostics
        self.enable_auto_fix = enable_auto_fix
        self.extreme_value_threshold = extreme_value_threshold

    async def verify_results(
        self,
        question: str,
        sql: str,
        result: Dict[str, Any],
        schema: str,
        database_type: str = "postgresql"
    ) -> VerificationResult:
        """
        Verify if query results make sense

        Args:
            question: Original natural language question
            sql: SQL query that was executed
            result: Query execution result
            schema: Database schema
            database_type: Type of database

        Returns:
            VerificationResult with details about any issues found
        """
        # If query failed, no need to verify
        if not result.get("success", False):
            return VerificationResult(
                is_suspicious=False,
                confidence=0.0,
                issue_type=VerificationIssue.NO_ISSUE,
                description="Query failed, cannot verify results"
            )

        data = result.get("data", [])
        columns = result.get("columns", [])
        row_count = result.get("row_count", 0)

        # Check 1: Empty results
        if row_count == 0:
            return await self._check_empty_result(question, sql, schema, database_type)

        # Check 2: All NULL values
        if self._has_all_nulls(data):
            return await self._check_all_nulls(question, sql, data, schema, database_type)

        # Check 3: Extreme values
        extreme_check = self._check_extreme_values(data, columns)
        if extreme_check.is_suspicious:
            return extreme_check

        # Check 4: Unexpected counts (for COUNT queries)
        count_check = self._check_count_queries(question, sql, data)
        if count_check.is_suspicious:
            return count_check

        # Check 5: Negative counts (shouldn't happen)
        negative_check = self._check_negative_values(question, sql, data)
        if negative_check.is_suspicious:
            return negative_check

        # All checks passed
        logger.info("✅ Result verification passed - results look good")
        return VerificationResult(
            is_suspicious=False,
            confidence=0.0,
            issue_type=VerificationIssue.NO_ISSUE,
            description="Results look valid"
        )

    async def _check_empty_result(
        self,
        question: str,
        sql: str,
        schema: str,
        database_type: str
    ) -> VerificationResult:
        """
        Check if empty result is suspicious

        Args:
            question: Natural language question
            sql: SQL query
            schema: Database schema
            database_type: Database type

        Returns:
            VerificationResult
        """
        # Extract table names from SQL
        tables = self._extract_table_names(sql)

        # Generate diagnostic queries
        diagnostic_queries = []
        for table in tables:
            # Check if table has data
            diagnostic_queries.append(f"SELECT COUNT(*) as count FROM {table}")
            # Get sample data
            diagnostic_queries.append(f"SELECT * FROM {table} LIMIT 5")

        return VerificationResult(
            is_suspicious=True,
            confidence=0.7,  # Medium confidence - empty could be valid
            issue_type=VerificationIssue.EMPTY_RESULT,
            description=f"Query returned 0 rows. This might be correct, but let's verify the table(s) {', '.join(tables)} actually contain data.",
            suggested_fix="Verify table has data, check WHERE clause filters, or adjust query logic",
            diagnostic_queries=diagnostic_queries
        )

    async def _check_all_nulls(
        self,
        question: str,
        sql: str,
        data: List[Dict[str, Any]],
        schema: str,
        database_type: str
    ) -> VerificationResult:
        """
        Check if all values are NULL (suspicious)

        Args:
            question: Natural language question
            sql: SQL query
            data: Query results
            schema: Database schema
            database_type: Database type

        Returns:
            VerificationResult
        """
        return VerificationResult(
            is_suspicious=True,
            confidence=0.8,  # High confidence - all NULLs is usually wrong
            issue_type=VerificationIssue.ALL_NULLS,
            description="All values in the result are NULL. This usually indicates wrong column names or JOINs.",
            suggested_fix="Check column names in SELECT clause, verify JOIN conditions, or check for missing data",
            diagnostic_queries=None
        )

    def _check_extreme_values(
        self,
        data: List[Dict[str, Any]],
        columns: List[str]
    ) -> VerificationResult:
        """
        Check for extreme values that might indicate errors

        Args:
            data: Query results
            columns: Column names

        Returns:
            VerificationResult
        """
        extreme_values = []

        for row in data:
            for col, val in row.items():
                # Check numeric values
                if isinstance(val, (int, float)):
                    if abs(val) > self.extreme_value_threshold:
                        extreme_values.append((col, val))

        if extreme_values:
            col_name, val = extreme_values[0]
            return VerificationResult(
                is_suspicious=True,
                confidence=0.6,  # Medium confidence - could be legitimate
                issue_type=VerificationIssue.EXTREME_VALUE,
                description=f"Found extreme value: {val} in column '{col_name}'. This might indicate wrong aggregation or calculation.",
                suggested_fix="Check aggregation functions (SUM, COUNT), verify JOIN multipliers, or check data types",
                diagnostic_queries=None
            )

        return VerificationResult(
            is_suspicious=False,
            confidence=0.0,
            issue_type=VerificationIssue.NO_ISSUE,
            description="No extreme values detected"
        )

    def _check_count_queries(
        self,
        question: str,
        sql: str,
        data: List[Dict[str, Any]]
    ) -> VerificationResult:
        """
        Check if COUNT results make sense

        Args:
            question: Natural language question
            sql: SQL query
            data: Query results

        Returns:
            VerificationResult
        """
        # Check if this is a COUNT query
        sql_upper = sql.upper()
        is_count_query = 'COUNT(' in sql_upper

        if not is_count_query:
            return VerificationResult(
                is_suspicious=False,
                confidence=0.0,
                issue_type=VerificationIssue.NO_ISSUE,
                description="Not a count query"
            )

        # If COUNT query returns 0, that's suspicious if question expects data
        if len(data) > 0:
            first_row = data[0]
            # Look for count columns
            for col, val in first_row.items():
                if 'count' in col.lower() and val == 0:
                    # Check if question expects results
                    expects_data_keywords = ['how many', 'count', 'number of', 'total']
                    if any(keyword in question.lower() for keyword in expects_data_keywords):
                        return VerificationResult(
                            is_suspicious=True,
                            confidence=0.5,
                            issue_type=VerificationIssue.UNEXPECTED_COUNT,
                            description=f"COUNT returned 0 for question '{question}'. Verify this is expected.",
                            suggested_fix="Check table has data, verify WHERE clause filters",
                            diagnostic_queries=None
                        )

        return VerificationResult(
            is_suspicious=False,
            confidence=0.0,
            issue_type=VerificationIssue.NO_ISSUE,
            description="Count query looks valid"
        )

    def _check_negative_values(
        self,
        question: str,
        sql: str,
        data: List[Dict[str, Any]]
    ) -> VerificationResult:
        """
        Check for negative values in COUNT or similar queries (shouldn't happen)

        Args:
            question: Natural language question
            sql: SQL query
            data: Query results

        Returns:
            VerificationResult
        """
        for row in data:
            for col, val in row.items():
                # Check for negative counts
                if 'count' in col.lower() and isinstance(val, (int, float)) and val < 0:
                    return VerificationResult(
                        is_suspicious=True,
                        confidence=1.0,  # Very high confidence - negative count is always wrong
                        issue_type=VerificationIssue.NEGATIVE_COUNT,
                        description=f"Negative count detected: {val}. This indicates a serious error in the query.",
                        suggested_fix="Check query logic, aggregation functions, or data types",
                        diagnostic_queries=None
                    )

        return VerificationResult(
            is_suspicious=False,
            confidence=0.0,
            issue_type=VerificationIssue.NO_ISSUE,
            description="No negative counts detected"
        )

    def _has_all_nulls(self, data: List[Dict[str, Any]]) -> bool:
        """
        Check if all values in result are NULL

        Args:
            data: Query results

        Returns:
            True if all values are NULL
        """
        if not data:
            return False

        for row in data:
            for val in row.values():
                if val is not None:
                    return False

        return True

    def _extract_table_names(self, sql: str) -> List[str]:
        """
        Extract table names from SQL query (simple heuristic)

        Args:
            sql: SQL query

        Returns:
            List of table names
        """
        tables = []
        sql_upper = sql.upper()

        # Simple regex to find table names after FROM and JOIN
        # Pattern: FROM/JOIN <table_name>
        pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, sql_upper)

        # Also check original case for actual names
        pattern_case = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches_case = re.findall(pattern_case, sql, re.IGNORECASE)

        tables.extend(matches_case)

        # Remove duplicates and return
        return list(set(tables))

    async def run_diagnostics(
        self,
        sql: str,
        verification: VerificationResult,
        session,
        database_type: str
    ) -> DiagnosticResult:
        """
        Run diagnostic queries to understand the issue

        Args:
            sql: Original SQL query
            verification: Verification result
            session: Database session
            database_type: Database type

        Returns:
            DiagnosticResult with findings
        """
        if not self.enable_diagnostics:
            logger.info("Diagnostics disabled, skipping")
            return DiagnosticResult(
                table_exists=True,
                table_has_data=True,
                column_exists=True,
                diagnosis="Diagnostics disabled"
            )

        # Import executor
        from src.core.executor import SQLExecutor
        executor = SQLExecutor(max_rows=10, timeout_seconds=10)

        diagnostic_result = DiagnosticResult(
            table_exists=True,
            table_has_data=True,
            column_exists=True
        )

        # Run diagnostic queries if provided
        if verification.diagnostic_queries:
            logger.info(f"Running {len(verification.diagnostic_queries)} diagnostic queries...")

            for query in verification.diagnostic_queries:
                try:
                    result = await executor.execute_query(session, query)
                    if result["success"]:
                        logger.info(f"Diagnostic query succeeded: {query[:100]}")

                        # Parse results
                        if 'COUNT(*)' in query.upper() or 'COUNT(' in query.upper():
                            # This is a count query
                            if result["data"] and len(result["data"]) > 0:
                                count = list(result["data"][0].values())[0]
                                diagnostic_result.row_count = count
                                diagnostic_result.table_has_data = count > 0
                                logger.info(f"Table has {count} rows")
                        else:
                            # This is a sample data query
                            diagnostic_result.sample_data = result["data"]
                            logger.info(f"Retrieved {len(result['data'])} sample rows")
                    else:
                        logger.warning(f"Diagnostic query failed: {result.get('error')}")
                        diagnostic_result.table_exists = False
                except Exception as e:
                    logger.error(f"Error running diagnostic query: {e}")
                    diagnostic_result.table_exists = False

        # Generate diagnosis
        if not diagnostic_result.table_has_data:
            diagnostic_result.diagnosis = "Table exists but is empty. The query is correct but there's no data to return."
        elif not diagnostic_result.table_exists:
            diagnostic_result.diagnosis = "Table does not exist or is not accessible."
        else:
            diagnostic_result.diagnosis = "Table exists and has data. The query logic might need adjustment."

        return diagnostic_result

    def generate_improvement_hints(
        self,
        question: str,
        sql: str,
        verification: VerificationResult,
        diagnostics: Optional[DiagnosticResult] = None
    ) -> str:
        """
        Generate hints for improving the query based on verification results

        Args:
            question: Original question
            sql: SQL query
            verification: Verification result
            diagnostics: Optional diagnostic results

        Returns:
            Improvement hints as a string
        """
        hints = []

        hints.append(f"Issue detected: {verification.description}")

        if verification.suggested_fix:
            hints.append(f"Suggested fix: {verification.suggested_fix}")

        if diagnostics:
            hints.append(f"Diagnostics: {diagnostics.diagnosis}")

            if diagnostics.row_count is not None:
                hints.append(f"Table has {diagnostics.row_count} rows")

            if diagnostics.sample_data:
                hints.append(f"Sample data available: {len(diagnostics.sample_data)} rows")

        # Issue-specific hints
        if verification.issue_type == VerificationIssue.EMPTY_RESULT:
            hints.append("Consider: Are the WHERE clause filters too restrictive?")
            hints.append("Consider: Are you using the correct table name?")
            hints.append("Consider: Do you need to use LEFT JOIN instead of INNER JOIN?")

        elif verification.issue_type == VerificationIssue.ALL_NULLS:
            hints.append("Consider: Are column names correct?")
            hints.append("Consider: Are JOIN conditions correct?")
            hints.append("Consider: Are you selecting from the right table?")

        elif verification.issue_type == VerificationIssue.EXTREME_VALUE:
            hints.append("Consider: Are you using SUM when you should use COUNT?")
            hints.append("Consider: Are JOINs creating duplicate rows?")
            hints.append("Consider: Do you need DISTINCT?")

        return "\n".join(hints)

    def get_verification_summary(
        self,
        verification: VerificationResult,
        diagnostics: Optional[DiagnosticResult] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary of verification results

        Args:
            verification: Verification result
            diagnostics: Optional diagnostic results

        Returns:
            Summary dictionary
        """
        summary = {
            "is_suspicious": verification.is_suspicious,
            "confidence": verification.confidence,
            "issue_type": verification.issue_type.value,
            "description": verification.description,
            "suggested_fix": verification.suggested_fix,
        }

        if diagnostics:
            summary["diagnostics"] = {
                "table_exists": diagnostics.table_exists,
                "table_has_data": diagnostics.table_has_data,
                "row_count": diagnostics.row_count,
                "diagnosis": diagnostics.diagnosis,
            }

        return summary
