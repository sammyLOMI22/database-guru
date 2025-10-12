"""Self-Correcting SQL Agent with automatic error recovery"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from src.llm.sql_generator import SQLGenerator
from src.core.executor import SQLExecutor
from src.database.models import DatabaseConnection

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of SQL errors for better diagnosis"""
    SYNTAX_ERROR = "syntax_error"
    TABLE_NOT_FOUND = "table_not_found"
    COLUMN_NOT_FOUND = "column_not_found"
    TYPE_MISMATCH = "type_mismatch"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class CorrectionAttempt:
    """Record of a correction attempt"""
    attempt_number: int
    sql: str
    error: Optional[str]
    error_type: ErrorType
    success: bool
    execution_time_ms: Optional[float]
    row_count: Optional[int]


class ErrorDiagnostics:
    """Analyze and categorize SQL errors"""

    @staticmethod
    def categorize_error(error_message: str) -> ErrorType:
        """
        Categorize error type from error message

        Args:
            error_message: Error message from database

        Returns:
            ErrorType enum
        """
        error_lower = error_message.lower()

        # Syntax errors
        if any(keyword in error_lower for keyword in [
            "syntax error", "syntax", "parse error", "unexpected"
        ]):
            return ErrorType.SYNTAX_ERROR

        # Table not found
        if any(keyword in error_lower for keyword in [
            "table", "relation", "does not exist", "no such table"
        ]):
            return ErrorType.TABLE_NOT_FOUND

        # Column not found
        if any(keyword in error_lower for keyword in [
            "column", "field", "unknown column", "no such column"
        ]):
            return ErrorType.COLUMN_NOT_FOUND

        # Type mismatch
        if any(keyword in error_lower for keyword in [
            "type", "cast", "conversion", "incompatible"
        ]):
            return ErrorType.TYPE_MISMATCH

        # Permission issues
        if any(keyword in error_lower for keyword in [
            "permission", "denied", "access", "unauthorized"
        ]):
            return ErrorType.PERMISSION_DENIED

        # Timeout
        if any(keyword in error_lower for keyword in [
            "timeout", "timed out", "exceeded"
        ]):
            return ErrorType.TIMEOUT

        return ErrorType.UNKNOWN

    @staticmethod
    def extract_error_context(error_message: str, error_type: ErrorType) -> Dict[str, Any]:
        """
        Extract useful context from error message

        Args:
            error_message: Error message from database
            error_type: Categorized error type

        Returns:
            Dictionary with extracted context
        """
        context = {
            "error_type": error_type.value,
            "raw_error": error_message
        }

        error_lower = error_message.lower()

        if error_type == ErrorType.TABLE_NOT_FOUND:
            # Try to extract table name
            import re
            match = re.search(r'table["\s]+([a-z_][a-z0-9_]*)', error_lower)
            if match:
                context["missing_table"] = match.group(1)

        elif error_type == ErrorType.COLUMN_NOT_FOUND:
            # Try to extract column name
            import re
            match = re.search(r'column["\s]+([a-z_][a-z0-9_]*)', error_lower)
            if match:
                context["missing_column"] = match.group(1)

        return context

    @staticmethod
    def generate_fix_hints(error_type: ErrorType, context: Dict[str, Any]) -> str:
        """
        Generate helpful hints for fixing the error

        Args:
            error_type: Type of error
            context: Error context

        Returns:
            Hints for fixing the error
        """
        hints = []

        if error_type == ErrorType.TABLE_NOT_FOUND:
            hints.append("Check the schema for the correct table name.")
            hints.append("Table names may be case-sensitive.")
            if "missing_table" in context:
                hints.append(f"Could not find table: {context['missing_table']}")

        elif error_type == ErrorType.COLUMN_NOT_FOUND:
            hints.append("Check the schema for the correct column name.")
            hints.append("Make sure you're referencing the right table.")
            if "missing_column" in context:
                hints.append(f"Could not find column: {context['missing_column']}")

        elif error_type == ErrorType.SYNTAX_ERROR:
            hints.append("Check for missing commas, parentheses, or keywords.")
            hints.append("Verify SQL syntax is correct for the database type.")

        elif error_type == ErrorType.TYPE_MISMATCH:
            hints.append("Check data types in comparisons and operations.")
            hints.append("You may need to cast values to the correct type.")

        return "\n".join(hints)


class SelfCorrectingSQLAgent:
    """
    Agent that automatically retries and fixes failed SQL queries

    This agent will:
    1. Generate initial SQL
    2. Execute and check for errors
    3. If error occurs, analyze and attempt to fix
    4. Retry with corrected SQL
    5. Repeat up to max_retries times
    """

    def __init__(
        self,
        sql_generator: SQLGenerator,
        max_retries: int = 3,
        enable_diagnostics: bool = True
    ):
        """
        Initialize the self-correcting agent

        Args:
            sql_generator: SQL generator instance
            max_retries: Maximum number of correction attempts
            enable_diagnostics: Whether to provide detailed error diagnostics
        """
        self.generator = sql_generator
        self.max_retries = max_retries
        self.enable_diagnostics = enable_diagnostics
        self.diagnostics = ErrorDiagnostics()

    async def generate_and_execute_with_retry(
        self,
        question: str,
        schema: str,
        session,  # Database session
        database_type: str = "postgresql",
        allow_write: bool = False,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate SQL with automatic error correction and retry

        Args:
            question: Natural language question
            schema: Database schema information
            session: Database session for execution
            database_type: Type of database
            allow_write: Whether to allow write operations
            model: Optional model name to use

        Returns:
            Dictionary with:
                - success: bool
                - sql: Final SQL query
                - result: Query results (if successful)
                - attempts: List of CorrectionAttempt objects
                - self_corrected: Whether auto-correction was used
                - total_attempts: Total number of attempts
                - error: Final error message (if failed)
        """
        attempts: List[CorrectionAttempt] = []
        last_error = None
        sql = None

        executor = SQLExecutor(
            max_rows=1000,
            timeout_seconds=30,
            allow_write=allow_write
        )

        for attempt_num in range(1, self.max_retries + 1):
            try:
                # Generate or fix SQL
                if attempt_num == 1:
                    # First attempt: generate from scratch
                    logger.info(f"Attempt {attempt_num}/{self.max_retries}: Generating SQL for: {question}")
                    gen_result = await self.generator.generate_sql(
                        question=question,
                        schema=schema,
                        database_type=database_type,
                        allow_write=allow_write,
                        model=model
                    )
                    sql = gen_result["sql"]
                else:
                    # Retry: fix the error
                    logger.info(f"Attempt {attempt_num}/{self.max_retries}: Attempting to fix SQL error")

                    # Categorize error
                    error_type = self.diagnostics.categorize_error(last_error)
                    error_context = self.diagnostics.extract_error_context(last_error, error_type)
                    hints = self.diagnostics.generate_fix_hints(error_type, error_context)

                    # Add hints to error message for better correction
                    enhanced_error = f"{last_error}\n\nHints:\n{hints}"

                    # Generate corrected SQL
                    fix_result = await self.generator.fix_sql_error(
                        sql=sql,
                        error=enhanced_error,
                        schema=schema,
                        database_type=database_type
                    )
                    sql = fix_result["sql"]

                    logger.info(f"Generated corrected SQL: {sql[:100]}...")

                # Validate SQL before executing
                if not gen_result.get("is_valid", True) if attempt_num == 1 else True:
                    logger.warning(f"Generated SQL failed validation: {gen_result.get('warnings')}")

                # Execute SQL
                exec_result = await executor.execute_query(
                    session=session,
                    sql=sql
                )

                # Record attempt
                attempt = CorrectionAttempt(
                    attempt_number=attempt_num,
                    sql=sql,
                    error=None if exec_result["success"] else exec_result["error"],
                    error_type=ErrorType.UNKNOWN if exec_result["success"] else self.diagnostics.categorize_error(exec_result["error"]),
                    success=exec_result["success"],
                    execution_time_ms=exec_result.get("execution_time_ms"),
                    row_count=exec_result.get("row_count")
                )
                attempts.append(attempt)

                if exec_result["success"]:
                    # Success!
                    logger.info(f"✅ Query succeeded on attempt {attempt_num}/{self.max_retries}")
                    return {
                        "success": True,
                        "sql": sql,
                        "result": exec_result,
                        "attempts": attempts,
                        "self_corrected": attempt_num > 1,
                        "total_attempts": attempt_num,
                        "question": question,
                        "model_used": model or self.generator.settings.OLLAMA_MODEL
                    }

                # Failed - save error for next retry
                last_error = exec_result["error"]
                logger.warning(f"❌ Attempt {attempt_num} failed: {last_error[:200]}")

                # If this is the last attempt, don't retry
                if attempt_num >= self.max_retries:
                    break

            except Exception as e:
                logger.error(f"Exception during attempt {attempt_num}: {e}")
                last_error = str(e)

                # Record failed attempt
                attempt = CorrectionAttempt(
                    attempt_number=attempt_num,
                    sql=sql or "",
                    error=str(e),
                    error_type=ErrorType.UNKNOWN,
                    success=False,
                    execution_time_ms=None,
                    row_count=None
                )
                attempts.append(attempt)

                if attempt_num >= self.max_retries:
                    break

        # All retries exhausted
        logger.error(f"❌ Query failed after {self.max_retries} attempts")
        return {
            "success": False,
            "sql": sql or "",
            "error": last_error,
            "attempts": attempts,
            "self_corrected": len(attempts) > 1,
            "total_attempts": len(attempts),
            "question": question,
            "model_used": model or self.generator.settings.OLLAMA_MODEL,
            "message": f"Failed after {self.max_retries} attempts"
        }

    async def execute_with_retry(
        self,
        sql: str,
        schema: str,
        session,
        database_type: str,
        question: str,
        allow_write: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute pre-generated SQL with automatic error correction and retry

        This method is useful when you already have SQL generated and just need
        the retry/correction logic.

        Args:
            sql: Pre-generated SQL query
            schema: Database schema information
            session: Database session for execution
            database_type: Type of database
            question: Original natural language question (for context in corrections)
            allow_write: Whether to allow write operations

        Returns:
            Dictionary with:
                - success: bool
                - sql: Final SQL query (may be corrected)
                - result: Query results (if successful)
                - corrections: List of correction attempt details
                - attempts: Total number of attempts
                - final_error: Final error message (if failed)
        """
        attempts: List[Dict[str, Any]] = []
        last_error = None
        current_sql = sql

        executor = SQLExecutor(
            max_rows=1000,
            timeout_seconds=30,
            allow_write=allow_write
        )

        for attempt_num in range(1, self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt_num}/{self.max_retries}: Executing SQL")

                # Execute SQL
                exec_result = await executor.execute_query(
                    session=session,
                    sql=current_sql
                )

                # Record attempt
                attempt_info = {
                    "attempt_number": attempt_num,
                    "sql": current_sql,
                    "error": None if exec_result["success"] else exec_result.get("error"),
                    "error_type": ErrorType.UNKNOWN.value if not exec_result["success"] else None,
                    "success": exec_result["success"],
                    "execution_time_ms": exec_result.get("execution_time_ms"),
                    "row_count": exec_result.get("row_count")
                }

                if not exec_result["success"]:
                    error_type = self.diagnostics.categorize_error(exec_result["error"])
                    attempt_info["error_type"] = error_type.value

                attempts.append(attempt_info)

                if exec_result["success"]:
                    # Success!
                    logger.info(f"✅ Query succeeded on attempt {attempt_num}/{self.max_retries}")
                    return {
                        "success": True,
                        "sql": current_sql,
                        "result": exec_result,
                        "corrections": attempts,
                        "attempts": attempt_num,
                        "self_corrected": attempt_num > 1,
                    }

                # Failed - try to correct
                last_error = exec_result["error"]
                logger.warning(f"❌ Attempt {attempt_num} failed: {last_error[:200]}")

                # If this is the last attempt, don't retry
                if attempt_num >= self.max_retries:
                    break

                # Generate correction
                error_type = self.diagnostics.categorize_error(last_error)
                error_context = self.diagnostics.extract_error_context(last_error, error_type)
                hints = self.diagnostics.generate_fix_hints(error_type, error_context)

                # Add hints to error message
                enhanced_error = f"{last_error}\n\nHints:\n{hints}"

                # Generate corrected SQL
                fix_result = await self.generator.fix_sql_error(
                    sql=current_sql,
                    error=enhanced_error,
                    schema=schema,
                    database_type=database_type
                )
                current_sql = fix_result["sql"]

                logger.info(f"Generated corrected SQL: {current_sql[:100]}...")

            except Exception as e:
                logger.error(f"Exception during attempt {attempt_num}: {e}")
                last_error = str(e)

                # Record failed attempt
                attempts.append({
                    "attempt_number": attempt_num,
                    "sql": current_sql,
                    "error": str(e),
                    "error_type": ErrorType.UNKNOWN.value,
                    "success": False,
                    "execution_time_ms": None,
                    "row_count": None
                })

                if attempt_num >= self.max_retries:
                    break

        # All retries exhausted
        logger.error(f"❌ Query failed after {self.max_retries} attempts")
        return {
            "success": False,
            "sql": current_sql,
            "final_error": last_error,
            "corrections": attempts,
            "attempts": len(attempts),
            "self_corrected": len(attempts) > 1,
        }

    def get_correction_summary(self, result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the correction process

        Args:
            result: Result from generate_and_execute_with_retry

        Returns:
            Summary string
        """
        if result["success"]:
            if result["self_corrected"]:
                return (
                    f"✅ Query succeeded after {result['total_attempts']} attempts "
                    f"(auto-corrected from {result['total_attempts'] - 1} error(s))"
                )
            else:
                return "✅ Query succeeded on first try"
        else:
            return (
                f"❌ Query failed after {result['total_attempts']} attempts\n"
                f"Final error: {result['error'][:200]}"
            )

    def get_detailed_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a detailed report of all correction attempts

        Args:
            result: Result from generate_and_execute_with_retry

        Returns:
            Detailed report dictionary
        """
        attempts_detail = []

        for attempt in result.get("attempts", []):
            attempts_detail.append({
                "attempt": attempt.attempt_number,
                "sql": attempt.sql[:200] + "..." if len(attempt.sql) > 200 else attempt.sql,
                "success": attempt.success,
                "error_type": attempt.error_type.value if attempt.error_type else None,
                "error": attempt.error[:200] if attempt.error else None,
                "execution_time_ms": attempt.execution_time_ms,
                "row_count": attempt.row_count
            })

        return {
            "summary": self.get_correction_summary(result),
            "success": result["success"],
            "total_attempts": result["total_attempts"],
            "self_corrected": result["self_corrected"],
            "final_sql": result["sql"],
            "attempts": attempts_detail,
            "question": result["question"],
            "model_used": result.get("model_used")
        }
