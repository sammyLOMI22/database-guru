"""
Result validation pattern learning system

Learns patterns from user feedback about result issues (empty results,
suspicious values, missing data, etc.) and applies them to validate
future query results.

Part of Phase 2: Non-SQL Feedback Implementation
"""
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of result validation patterns"""
    EMPTY_RESULT = "empty_result"
    MISSING_DATA = "missing_data"
    SUSPICIOUS_VALUES = "suspicious_values"
    DUPLICATE_DATA = "duplicate_data"
    WRONG_AGGREGATION = "wrong_aggregation"
    INCOMPLETE_JOIN = "incomplete_join"


class PatternAction(str, Enum):
    """Actions to take when pattern matches"""
    SUGGEST_REWRITE = "suggest_rewrite"
    FLAG_REVIEW = "flag_review"
    AUTO_CORRECT = "auto_correct"
    WARN_USER = "warn_user"


class ValidationResult:
    """Result of applying a validation pattern"""
    def __init__(
        self,
        is_valid: bool,
        pattern_id: Optional[int] = None,
        pattern_type: Optional[str] = None,
        action: Optional[str] = None,
        suggestion: Optional[str] = None,
        message: Optional[str] = None
    ):
        self.is_valid = is_valid
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.action = action
        self.suggestion = suggestion
        self.message = message

    def __repr__(self):
        status = "✅ Valid" if self.is_valid else "⚠️ Issue detected"
        pattern_info = f" ({self.pattern_type})" if self.pattern_type else ""
        return f"<ValidationResult: {status}{pattern_info}>"


class ResultPattern:
    """Represents a learned result validation pattern"""
    def __init__(
        self,
        id: int,
        pattern_type: str,
        pattern_description: str,
        matching_criteria: Dict[str, Any],
        action: str,
        suggestion: Optional[str],
        confidence_score: float,
        times_triggered: int = 0,
        times_helpful: int = 0
    ):
        self.id = id
        self.pattern_type = pattern_type
        self.pattern_description = pattern_description
        self.matching_criteria = matching_criteria
        self.action = action
        self.suggestion = suggestion
        self.confidence_score = confidence_score
        self.times_triggered = times_triggered
        self.times_helpful = times_helpful

    def __repr__(self):
        return f"<ResultPattern: {self.pattern_type} (confidence={self.confidence_score:.2f})>"


class ResultPatternLearner:
    """
    Learns and applies result validation patterns

    Features:
    - Learn from user feedback about result issues
    - Validate query results against learned patterns
    - Suggest corrections for common result problems
    - Track pattern effectiveness over time
    - Support multiple validation pattern types

    Example:
        learner = ResultPatternLearner(db_session=db)

        # Learn from feedback
        pattern_id = await learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Query returns no results when filtering by inactive status",
            matching_criteria={
                "table_name": "users",
                "filters": {"status": "inactive"}
            },
            action="suggest_rewrite",
            suggestion="Check if 'inactive' should be 'disabled' or use IS NULL",
            feedback_id=123
        )

        # Validate results
        result = await learner.validate_result(
            sql="SELECT * FROM users WHERE status = 'inactive'",
            result_data=[],  # Empty result
            row_count=0
        )

        if not result.is_valid:
            print(f"Issue: {result.message}")
            print(f"Suggestion: {result.suggestion}")
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the result pattern learner

        Args:
            db_session: Async database session for persistence
        """
        self.db_session = db_session

    async def learn_from_feedback(
        self,
        pattern_type: str,
        pattern_description: str,
        matching_criteria: Dict[str, Any],
        action: str,
        feedback_id: int,
        suggestion: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> int:
        """
        Learn a new validation pattern from user feedback

        Args:
            pattern_type: Type of pattern (empty_result, missing_data, etc.)
            pattern_description: Human-readable description
            matching_criteria: Dictionary of criteria to match against
            action: Action to take when pattern matches
            feedback_id: ID of the feedback that taught us this
            suggestion: Optional suggestion for fixing the issue
            confidence_score: Confidence in this pattern (0.0-1.0)

        Returns:
            The ID of the created pattern

        Example matching_criteria:
            {
                "table_name": "users",
                "expected_min_rows": 1,
                "filters": {"status": "active"},
                "column_checks": {"email": {"not_null": true}}
            }
        """
        try:
            logger.info(
                f"📚 Learning result pattern: {pattern_type} - {pattern_description} "
                f"(confidence={confidence_score})"
            )

            # Check if similar pattern already exists
            existing_pattern = await self._find_similar_pattern(
                pattern_type=pattern_type,
                matching_criteria=matching_criteria
            )

            if existing_pattern:
                logger.warning(
                    f"⚠️  Similar pattern already exists: {existing_pattern}"
                )
                # Update the existing pattern
                await self.db_session.execute(
                    text("""
                        UPDATE result_validation_patterns
                        SET confidence_score = :confidence,
                            pattern_description = :description,
                            action = :action,
                            suggestion = COALESCE(:suggestion, suggestion),
                            learned_from_feedback_id = :feedback_id
                        WHERE id = :pattern_id
                    """),
                    {
                        "confidence": confidence_score,
                        "description": pattern_description,
                        "action": action,
                        "suggestion": suggestion,
                        "feedback_id": feedback_id,
                        "pattern_id": existing_pattern.id
                    }
                )
                await self.db_session.commit()
                return existing_pattern.id

            # Create new pattern
            result = await self.db_session.execute(
                text("""
                    INSERT INTO result_validation_patterns (
                        pattern_type,
                        pattern_description,
                        matching_criteria,
                        action,
                        suggestion,
                        confidence_score,
                        learned_from_feedback_id,
                        created_at
                    ) VALUES (
                        :pattern_type,
                        :description,
                        :criteria,
                        :action,
                        :suggestion,
                        :confidence,
                        :feedback_id,
                        CURRENT_TIMESTAMP
                    )
                """),
                {
                    "pattern_type": pattern_type,
                    "description": pattern_description,
                    "criteria": json.dumps(matching_criteria),
                    "action": action,
                    "suggestion": suggestion,
                    "confidence": confidence_score,
                    "feedback_id": feedback_id
                }
            )

            await self.db_session.commit()
            pattern_id = result.lastrowid

            logger.info(
                f"✅ Result pattern created: id={pattern_id}, type={pattern_type}"
            )

            return pattern_id

        except Exception as e:
            await self.db_session.rollback()
            logger.error(
                f"❌ Failed to learn result pattern: {e}",
                exc_info=True
            )
            raise

    async def validate_result(
        self,
        sql: str,
        result_data: List[Dict[str, Any]],
        row_count: int,
        table_name: Optional[str] = None,
        min_confidence: float = 0.6
    ) -> ValidationResult:
        """
        Validate query result against learned patterns

        Args:
            sql: The SQL query that was executed
            result_data: The result data (list of row dicts)
            row_count: Number of rows returned
            table_name: Primary table queried (optional)
            min_confidence: Minimum confidence threshold

        Returns:
            ValidationResult indicating if result is valid
        """
        try:
            # Get applicable patterns
            patterns = await self._get_applicable_patterns(
                pattern_type=None,  # Check all types
                min_confidence=min_confidence
            )

            if not patterns:
                # No patterns to check, assume valid
                return ValidationResult(is_valid=True)

            # Check each pattern
            for pattern in patterns:
                matches = self._check_pattern_match(
                    pattern=pattern,
                    sql=sql,
                    result_data=result_data,
                    row_count=row_count,
                    table_name=table_name
                )

                if matches:
                    # Pattern matched - record trigger
                    await self._record_pattern_trigger(pattern.id)
                    await self.db_session.commit()

                    logger.warning(
                        f"⚠️  Result validation pattern triggered: {pattern.pattern_type}"
                    )

                    return ValidationResult(
                        is_valid=False,
                        pattern_id=pattern.id,
                        pattern_type=pattern.pattern_type,
                        action=pattern.action,
                        suggestion=pattern.suggestion,
                        message=pattern.pattern_description
                    )

            # No patterns matched - result is valid
            return ValidationResult(is_valid=True)

        except Exception as e:
            logger.error(f"❌ Failed to validate result: {e}", exc_info=True)
            # Return valid on error to avoid blocking
            return ValidationResult(is_valid=True)

    async def mark_pattern_helpful(self, pattern_id: int) -> bool:
        """
        Mark a pattern as helpful (user confirmed it was useful)

        Args:
            pattern_id: ID of the pattern

        Returns:
            True if successful
        """
        try:
            await self.db_session.execute(
                text("""
                    UPDATE result_validation_patterns
                    SET times_helpful = times_helpful + 1
                    WHERE id = :pattern_id
                """),
                {"pattern_id": pattern_id}
            )
            await self.db_session.commit()

            logger.info(f"✅ Marked pattern {pattern_id} as helpful")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to mark pattern helpful: {e}", exc_info=True)
            return False

    async def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Get statistics about learned patterns

        Returns:
            Dictionary with pattern statistics
        """
        try:
            result = await self.db_session.execute(
                text("""
                    SELECT
                        COUNT(*) as total_patterns,
                        SUM(times_triggered) as total_triggers,
                        SUM(times_helpful) as total_helpful,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN pattern_type = 'empty_result' THEN 1 END) as empty_result_patterns,
                        COUNT(CASE WHEN pattern_type = 'missing_data' THEN 1 END) as missing_data_patterns,
                        COUNT(CASE WHEN pattern_type = 'suspicious_values' THEN 1 END) as suspicious_values_patterns
                    FROM result_validation_patterns
                """)
            )

            row = result.fetchone()

            total_triggers = row[1] or 0
            total_helpful = row[2] or 0
            helpfulness_rate = (total_helpful / total_triggers * 100) if total_triggers > 0 else 0

            return {
                "total_patterns": row[0] or 0,
                "total_triggers": total_triggers,
                "total_helpful": total_helpful,
                "helpfulness_rate": round(helpfulness_rate, 1),
                "average_confidence": round(row[3] or 0.0, 2),
                "empty_result_patterns": row[4] or 0,
                "missing_data_patterns": row[5] or 0,
                "suspicious_values_patterns": row[6] or 0
            }

        except Exception as e:
            logger.error(f"Failed to get pattern stats: {e}", exc_info=True)
            return {}

    async def delete_pattern(self, pattern_id: int) -> bool:
        """
        Delete a validation pattern

        Args:
            pattern_id: ID of the pattern to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.db_session.execute(
                text("DELETE FROM result_validation_patterns WHERE id = :pattern_id"),
                {"pattern_id": pattern_id}
            )
            await self.db_session.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"🗑️  Deleted result pattern: id={pattern_id}")
            else:
                logger.warning(f"⚠️  Result pattern not found: id={pattern_id}")

            return deleted

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to delete pattern: {e}", exc_info=True)
            return False

    # Private helper methods

    async def _find_similar_pattern(
        self,
        pattern_type: str,
        matching_criteria: Dict[str, Any]
    ) -> Optional[ResultPattern]:
        """Find if a similar pattern already exists"""
        # For now, just check for exact pattern_type match
        # Could be enhanced with fuzzy matching of criteria
        result = await self.db_session.execute(
            text("""
                SELECT
                    id, pattern_type, pattern_description, matching_criteria,
                    action, suggestion, confidence_score, times_triggered, times_helpful
                FROM result_validation_patterns
                WHERE pattern_type = :pattern_type
                LIMIT 1
            """),
            {"pattern_type": pattern_type}
        )

        row = result.fetchone()
        if row:
            return ResultPattern(
                id=row[0],
                pattern_type=row[1],
                pattern_description=row[2],
                matching_criteria=json.loads(row[3]),
                action=row[4],
                suggestion=row[5],
                confidence_score=row[6],
                times_triggered=row[7],
                times_helpful=row[8]
            )

        return None

    async def _get_applicable_patterns(
        self,
        pattern_type: Optional[str],
        min_confidence: float = 0.6
    ) -> List[ResultPattern]:
        """Get all applicable validation patterns"""
        where_clause = ""
        params: Dict[str, Any] = {"min_confidence": min_confidence}

        if pattern_type:
            where_clause = "WHERE pattern_type = :pattern_type AND confidence_score >= :min_confidence"
            params["pattern_type"] = pattern_type
        else:
            where_clause = "WHERE confidence_score >= :min_confidence"

        result = await self.db_session.execute(
            text(f"""
                SELECT
                    id, pattern_type, pattern_description, matching_criteria,
                    action, suggestion, confidence_score, times_triggered, times_helpful
                FROM result_validation_patterns
                {where_clause}
                ORDER BY confidence_score DESC, times_helpful DESC
            """),
            params
        )

        patterns = []
        for row in result.fetchall():
            patterns.append(ResultPattern(
                id=row[0],
                pattern_type=row[1],
                pattern_description=row[2],
                matching_criteria=json.loads(row[3]),
                action=row[4],
                suggestion=row[5],
                confidence_score=row[6],
                times_triggered=row[7],
                times_helpful=row[8]
            ))

        return patterns

    def _check_pattern_match(
        self,
        pattern: ResultPattern,
        sql: str,
        result_data: List[Dict[str, Any]],
        row_count: int,
        table_name: Optional[str]
    ) -> bool:
        """
        Check if a pattern matches the current result

        Returns True if pattern matches (issue detected)
        """
        criteria = pattern.matching_criteria

        # Check pattern type specific conditions
        if pattern.pattern_type == PatternType.EMPTY_RESULT:
            # Check if result is empty when it shouldn't be
            if row_count == 0:
                # Check if table name matches (if specified)
                if "table_name" in criteria:
                    if table_name and table_name.lower() == criteria["table_name"].lower():
                        return True
                else:
                    # No specific table - matches any empty result
                    return True

        elif pattern.pattern_type == PatternType.MISSING_DATA:
            # Check for NULL values in important columns
            if "column_checks" in criteria and result_data:
                column_checks = criteria["column_checks"]
                for row in result_data:
                    for col, checks in column_checks.items():
                        if checks.get("not_null") and row.get(col) is None:
                            return True

        elif pattern.pattern_type == PatternType.SUSPICIOUS_VALUES:
            # Check for values outside expected ranges
            if "value_ranges" in criteria and result_data:
                value_ranges = criteria["value_ranges"]
                for row in result_data:
                    for col, range_spec in value_ranges.items():
                        value = row.get(col)
                        if value is not None:
                            if "min" in range_spec and value < range_spec["min"]:
                                return True
                            if "max" in range_spec and value > range_spec["max"]:
                                return True

        elif pattern.pattern_type == PatternType.WRONG_AGGREGATION:
            # Check if aggregation result seems wrong
            if "expected_min_value" in criteria and result_data:
                # Assume first row, first column is the aggregation
                if result_data and len(result_data) > 0:
                    first_value = next(iter(result_data[0].values()), None)
                    if first_value is not None and first_value < criteria["expected_min_value"]:
                        return True

        # Pattern didn't match
        return False

    async def _record_pattern_trigger(self, pattern_id: int):
        """Record that a pattern was triggered"""
        await self.db_session.execute(
            text("""
                UPDATE result_validation_patterns
                SET times_triggered = times_triggered + 1,
                    last_triggered_at = CURRENT_TIMESTAMP
                WHERE id = :pattern_id
            """),
            {"pattern_id": pattern_id}
        )
