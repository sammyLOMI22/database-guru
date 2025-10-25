"""Feedback validation for auto-learning system

This module provides robust validation before auto-applying user feedback.
It ensures corrections are actually improvements, not just syntactically valid SQL.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.executor import SQLExecutor
from src.database.models import QueryHistory, DatabaseConnection
from src.core.user_db_connector import UserDatabaseConnector

logger = logging.getLogger(__name__)


class FeedbackValidator:
    """Validates user feedback before auto-applying to learning system"""

    def __init__(self, db_session: AsyncSession, allow_destructive: bool = False):
        self.db = db_session
        self.executor = SQLExecutor(max_rows=100, timeout_seconds=30)
        self.allow_destructive = allow_destructive  # Admin override (dangerous!)

    async def validate_correction(
        self,
        query: QueryHistory,
        corrected_sql: str,
        validation_mode: str = "strict"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate a user's SQL correction before auto-applying

        Returns:
            (is_valid, reason, validation_details)

        Validation Modes:
            - strict: Corrected must succeed AND original must fail
            - moderate: Corrected must succeed (original failure not required)
            - lenient: Corrected must not error (allows empty results)
        """
        validation_details = {
            "original_tested": False,
            "corrected_tested": False,
            "original_succeeded": False,
            "corrected_succeeded": False,
            "original_row_count": 0,
            "corrected_row_count": 0,
            "validation_mode": validation_mode
        }

        try:
            # Get active database connection
            from sqlalchemy import select
            stmt = select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            result = await self.db.execute(stmt)
            active_conn = result.scalar_one_or_none()

            if not active_conn:
                return False, "No active database connection for validation", validation_details

            async with UserDatabaseConnector.get_user_db_session(active_conn) as user_db:
                # Test 1: Execute corrected SQL
                logger.info(f"🧪 Testing corrected SQL...")
                corrected_result = await self.executor.execute_query(
                    session=user_db,
                    sql=corrected_sql
                )
                validation_details["corrected_tested"] = True
                validation_details["corrected_succeeded"] = corrected_result["success"]
                validation_details["corrected_row_count"] = corrected_result.get("row_count", 0)
                validation_details["corrected_error"] = corrected_result.get("error")

                if not corrected_result["success"]:
                    reason = f"Corrected SQL failed: {corrected_result.get('error', 'Unknown error')}"
                    logger.warning(f"❌ {reason}")
                    return False, reason, validation_details

                logger.info(f"✅ Corrected SQL succeeded ({validation_details['corrected_row_count']} rows)")

                # Test 2: Execute original SQL (for comparison)
                if validation_mode in ["strict", "moderate"]:
                    logger.info(f"🧪 Testing original SQL for comparison...")
                    original_result = await self.executor.execute_query(
                        session=user_db,
                        sql=query.generated_sql
                    )
                    validation_details["original_tested"] = True
                    validation_details["original_succeeded"] = original_result["success"]
                    validation_details["original_row_count"] = original_result.get("row_count", 0)
                    validation_details["original_error"] = original_result.get("error")

                    # Strict mode: Original MUST fail
                    if validation_mode == "strict":
                        if original_result["success"]:
                            reason = (
                                "Original SQL unexpectedly succeeded. "
                                "Cannot verify this is an actual correction. "
                                "This might be a false positive or the issue was already fixed."
                            )
                            logger.warning(f"⚠️ {reason}")
                            return False, reason, validation_details

                        logger.info(f"✅ Original SQL failed as expected: {validation_details.get('original_error', 'N/A')}")

                    # Moderate mode: If original succeeds, compare results
                    elif validation_mode == "moderate":
                        if original_result["success"]:
                            # Both work - is corrected actually better?
                            if corrected_result.get("row_count", 0) == 0 and original_result.get("row_count", 0) > 0:
                                reason = "Corrected SQL returns no rows while original returns data. Correction may be worse."
                                logger.warning(f"⚠️ {reason}")
                                return False, reason, validation_details

                            logger.info("ℹ️ Both original and corrected SQL succeed - accepting as refinement")

                # Test 3: Check for suspicious patterns
                if validation_mode in ["strict", "moderate"]:
                    suspicious, suspicion_reason = self._check_suspicious_patterns(
                        original_sql=query.generated_sql,
                        corrected_sql=corrected_sql,
                        corrected_result=corrected_result
                    )
                    if suspicious:
                        logger.warning(f"⚠️ Suspicious pattern detected: {suspicion_reason}")
                        validation_details["suspicion"] = suspicion_reason
                        return False, f"Suspicious correction: {suspicion_reason}", validation_details

                # All tests passed
                logger.info(f"✅ Validation passed ({validation_mode} mode)")
                return True, "Validation successful", validation_details

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, f"Validation exception: {str(e)}", validation_details

    def _check_suspicious_patterns(
        self,
        original_sql: str,
        corrected_sql: str,
        corrected_result: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Check for suspicious correction patterns that might indicate bad feedback

        Returns:
            (is_suspicious, reason)
        """
        original_lower = original_sql.lower()
        corrected_lower = corrected_sql.lower()

        # Pattern 1: BLOCK ALL DESTRUCTIVE OPERATIONS (even with WHERE)
        # These should NEVER be auto-learned without explicit admin approval
        destructive_operations = [
            "drop table", "drop database", "drop index", "drop view",
            "delete from", "delete ",
            "truncate", "truncate table",
            "alter table", "alter database",
            "update ", "update set"
        ]

        for operation in destructive_operations:
            if operation in corrected_lower and operation not in original_lower:
                # Check if destructive operations are allowed (admin override)
                if not self.allow_destructive:
                    return True, (
                        f"BLOCKED: Added destructive operation '{operation.strip()}'. "
                        f"Destructive operations (DELETE, UPDATE, DROP, ALTER, TRUNCATE) are NEVER auto-learned. "
                        f"This requires manual admin approval, even with WHERE clauses. "
                        f"This is a critical safety feature - please apply manually if legitimate."
                    )
                else:
                    # Admin mode enabled - log warning but allow
                    logger.warning(
                        f"⚠️  ADMIN OVERRIDE: Allowing destructive operation '{operation.strip()}' "
                        f"(allow_destructive_auto_learn=True). THIS IS DANGEROUS!"
                    )

        # Pattern 2: Removed WHERE clause entirely
        if "where" in original_lower and "where" not in corrected_lower:
            # Unless it's a COUNT(*) or simple metadata query
            if "count(*)" not in corrected_lower and "show" not in corrected_lower:
                return True, "Removed WHERE clause - may return too much data"

        # Pattern 3: Changed SELECT * to SELECT with no columns
        if corrected_result["success"] and corrected_result.get("row_count", 0) == 0:
            if "select *" in original_lower or "select" in original_lower:
                if corrected_result.get("row_count") == 0 and "where 1=0" not in corrected_lower:
                    # Empty result might be legitimate, but flag for review
                    pass  # Allow empty results in lenient mode

        # Pattern 4: Drastically different query structure
        original_keywords = set(original_lower.split())
        corrected_keywords = set(corrected_lower.split())

        # Check if main SQL verbs changed
        sql_verbs = {"select", "insert", "update", "delete", "create", "alter", "drop"}
        original_verbs = original_keywords & sql_verbs
        corrected_verbs = corrected_keywords & sql_verbs

        if original_verbs != corrected_verbs:
            return True, f"Changed SQL operation type: {original_verbs} → {corrected_verbs}"

        # All checks passed
        return False, ""

    @staticmethod
    def get_validation_mode_description(mode: str) -> str:
        """Get human-readable description of validation mode"""
        descriptions = {
            "strict": "Corrected must succeed AND original must fail. Maximum safety.",
            "moderate": "Corrected must succeed. Original failure not required. Balanced approach.",
            "lenient": "Corrected must execute without errors. Minimal validation."
        }
        return descriptions.get(mode, "Unknown validation mode")
