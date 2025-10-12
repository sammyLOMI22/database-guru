"""Learning system for SQL corrections"""
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from src.database.models import LearnedCorrection
from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)


class CorrectionLearner:
    """
    System that learns from successful SQL corrections and applies them to future queries

    This system:
    1. Records successful corrections made by the self-correcting agent
    2. Extracts patterns from errors and corrections
    3. Stores corrections in a searchable database
    4. Retrieves similar corrections when new errors occur
    5. Applies learned corrections to speed up error recovery
    """

    def __init__(self, db_session: Session, enable_learning: bool = True):
        """
        Initialize the correction learner

        Args:
            db_session: Database session for storing/retrieving corrections
            enable_learning: Whether learning is enabled
        """
        self.db_session = db_session
        self.enable_learning = enable_learning

    async def learn_from_correction(
        self,
        error_type: ErrorType,
        original_sql: str,
        original_error: str,
        corrected_sql: str,
        database_type: str,
        was_successful: bool = True
    ) -> Optional[int]:
        """
        Learn from a successful correction

        Args:
            error_type: Type of error that was corrected
            original_sql: The SQL that failed
            original_error: The error message
            corrected_sql: The SQL that succeeded
            database_type: Type of database (postgres, mysql, duckdb, etc.)
            was_successful: Whether the correction was successful

        Returns:
            ID of the learned correction, or None if learning is disabled
        """
        if not self.enable_learning or not was_successful:
            return None

        try:
            # Extract patterns from the error and correction
            patterns = self._extract_patterns(
                error_type=error_type,
                original_sql=original_sql,
                original_error=original_error,
                corrected_sql=corrected_sql
            )

            # Check if we already have a similar correction
            existing = await self._find_similar_correction(
                error_type=error_type,
                error_pattern=patterns["error_pattern"],
                database_type=database_type,
                table_pattern=patterns.get("table_pattern"),
                column_pattern=patterns.get("column_pattern")
            )

            if existing:
                # Update existing correction
                existing.times_applied += 1
                existing.last_applied_at = datetime.utcnow()
                existing.confidence_score = min(1.0, existing.confidence_score + 0.1)
                self.db_session.commit()
                logger.info(f"Updated existing correction {existing.id}, now applied {existing.times_applied} times")
                return existing.id

            # Create new learned correction
            correction = LearnedCorrection(
                error_type=error_type.value,
                error_pattern=patterns["error_pattern"],
                database_type=database_type,
                original_sql=original_sql,
                original_error=original_error,
                corrected_sql=corrected_sql,
                correction_description=patterns.get("description"),
                table_pattern=patterns.get("table_pattern"),
                column_pattern=patterns.get("column_pattern"),
                times_applied=1,
                success_rate=1.0,
                confidence_score=0.7  # Initial confidence
            )

            self.db_session.add(correction)
            self.db_session.commit()
            self.db_session.refresh(correction)

            logger.info(f"Learned new correction {correction.id} for {error_type.value}")
            return correction.id

        except Exception as e:
            logger.error(f"Failed to learn from correction: {e}")
            self.db_session.rollback()
            return None

    async def find_applicable_corrections(
        self,
        error_type: ErrorType,
        error_message: str,
        database_type: str,
        sql: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find learned corrections that might apply to the current error

        Args:
            error_type: Type of error
            error_message: The error message
            database_type: Type of database
            sql: The SQL that failed (optional, for better matching)
            limit: Maximum number of corrections to return

        Returns:
            List of applicable corrections, sorted by relevance
        """
        if not self.enable_learning:
            return []

        try:
            # Extract patterns from current error
            table_match = self._extract_table_name(error_message)
            column_match = self._extract_column_name(error_message)

            # Build query for similar corrections
            query = self.db_session.query(LearnedCorrection).filter(
                and_(
                    LearnedCorrection.error_type == error_type.value,
                    LearnedCorrection.database_type == database_type,
                    LearnedCorrection.confidence_score >= 0.5  # Only high-confidence corrections
                )
            )

            # Add table/column pattern matching if available
            if table_match:
                query = query.filter(
                    or_(
                        LearnedCorrection.table_pattern == table_match,
                        LearnedCorrection.table_pattern.is_(None)
                    )
                )

            if column_match:
                query = query.filter(
                    or_(
                        LearnedCorrection.column_pattern == column_match,
                        LearnedCorrection.column_pattern.is_(None)
                    )
                )

            # Order by confidence and times applied
            corrections = query.order_by(
                desc(LearnedCorrection.confidence_score),
                desc(LearnedCorrection.times_applied)
            ).limit(limit).all()

            # Convert to dictionaries
            results = []
            for correction in corrections:
                results.append({
                    "id": correction.id,
                    "error_type": correction.error_type,
                    "original_sql": correction.original_sql,
                    "corrected_sql": correction.corrected_sql,
                    "correction_description": correction.correction_description,
                    "times_applied": correction.times_applied,
                    "confidence_score": correction.confidence_score,
                    "table_pattern": correction.table_pattern,
                    "column_pattern": correction.column_pattern
                })

            logger.info(f"Found {len(results)} applicable corrections for {error_type.value}")
            return results

        except Exception as e:
            logger.error(f"Failed to find applicable corrections: {e}")
            return []

    async def apply_learned_correction(
        self,
        correction_id: int,
        current_sql: str,
        was_successful: bool
    ) -> None:
        """
        Record that a learned correction was applied

        Args:
            correction_id: ID of the correction that was applied
            current_sql: The SQL it was applied to
            was_successful: Whether the application was successful
        """
        try:
            correction = self.db_session.query(LearnedCorrection).filter(
                LearnedCorrection.id == correction_id
            ).first()

            if not correction:
                return

            correction.last_applied_at = datetime.utcnow()

            if was_successful:
                correction.times_applied += 1
                # Increase confidence on success
                correction.confidence_score = min(1.0, correction.confidence_score + 0.05)
            else:
                # Decrease confidence on failure
                correction.confidence_score = max(0.0, correction.confidence_score - 0.1)

            # Update success rate
            total_applications = correction.times_applied
            if total_applications > 0:
                correction.success_rate = (
                    correction.success_rate * (total_applications - 1) + (1.0 if was_successful else 0.0)
                ) / total_applications

            self.db_session.commit()
            logger.info(f"Updated correction {correction_id}, success={was_successful}")

        except Exception as e:
            logger.error(f"Failed to update correction: {e}")
            self.db_session.rollback()

    def _extract_patterns(
        self,
        error_type: ErrorType,
        original_sql: str,
        original_error: str,
        corrected_sql: str
    ) -> Dict[str, Any]:
        """
        Extract patterns from an error and its correction

        Returns:
            Dictionary with extracted patterns
        """
        patterns = {
            "error_pattern": self._normalize_error(original_error),
            "description": None,
            "table_pattern": None,
            "column_pattern": None
        }

        # Extract table name if relevant
        if error_type in [ErrorType.TABLE_NOT_FOUND]:
            table = self._extract_table_name(original_error)
            if table:
                patterns["table_pattern"] = table
                patterns["description"] = f"Fix for missing table: {table}"

        # Extract column name if relevant
        if error_type in [ErrorType.COLUMN_NOT_FOUND]:
            column = self._extract_column_name(original_error)
            if column:
                patterns["column_pattern"] = column
                patterns["description"] = f"Fix for missing column: {column}"

        # Analyze the correction
        if not patterns["description"]:
            diff = self._analyze_sql_diff(original_sql, corrected_sql)
            patterns["description"] = diff

        return patterns

    def _normalize_error(self, error_message: str) -> str:
        """
        Normalize error message to create a pattern for matching

        Removes specific names and values to create a general pattern
        """
        error_lower = error_message.lower()

        # Replace quoted strings with placeholder
        error_lower = re.sub(r'"[^"]*"', '"<name>"', error_lower)
        error_lower = re.sub(r"'[^']*'", "'<name>'", error_lower)

        # Replace numbers with placeholder
        error_lower = re.sub(r'\b\d+\b', '<num>', error_lower)

        return error_lower

    def _extract_table_name(self, error_message: str) -> Optional[str]:
        """Extract table name from error message"""
        patterns = [
            r'table["\s]+([a-z_][a-z0-9_]*)',
            r'relation["\s]+([a-z_][a-z0-9_]*)',
            r'no such table:\s*([a-z_][a-z0-9_]*)',
        ]

        error_lower = error_message.lower()
        for pattern in patterns:
            match = re.search(pattern, error_lower)
            if match:
                return match.group(1)

        return None

    def _extract_column_name(self, error_message: str) -> Optional[str]:
        """Extract column name from error message"""
        patterns = [
            r'column["\s]+([a-z_][a-z0-9_]*)',
            r'field["\s]+([a-z_][a-z0-9_]*)',
            r'no such column:\s*([a-z_][a-z0-9_]*)',
        ]

        error_lower = error_message.lower()
        for pattern in patterns:
            match = re.search(pattern, error_lower)
            if match:
                return match.group(1)

        return None

    def _analyze_sql_diff(self, original: str, corrected: str) -> str:
        """Analyze the difference between original and corrected SQL"""
        original_words = set(original.lower().split())
        corrected_words = set(corrected.lower().split())

        added = corrected_words - original_words
        removed = original_words - corrected_words

        if added and removed:
            return f"Changed {', '.join(list(removed)[:3])} to {', '.join(list(added)[:3])}"
        elif added:
            return f"Added {', '.join(list(added)[:3])}"
        elif removed:
            return f"Removed {', '.join(list(removed)[:3])}"
        else:
            return "Minor correction"

    async def _find_similar_correction(
        self,
        error_type: ErrorType,
        error_pattern: str,
        database_type: str,
        table_pattern: Optional[str] = None,
        column_pattern: Optional[str] = None
    ) -> Optional[LearnedCorrection]:
        """
        Find an existing similar correction

        Returns:
            Existing correction or None
        """
        query = self.db_session.query(LearnedCorrection).filter(
            and_(
                LearnedCorrection.error_type == error_type.value,
                LearnedCorrection.database_type == database_type,
                LearnedCorrection.error_pattern == error_pattern
            )
        )

        if table_pattern:
            query = query.filter(LearnedCorrection.table_pattern == table_pattern)

        if column_pattern:
            query = query.filter(LearnedCorrection.column_pattern == column_pattern)

        return query.first()

    async def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get statistics about learned corrections

        Returns:
            Dictionary with learning statistics
        """
        try:
            total_corrections = self.db_session.query(LearnedCorrection).count()

            # Count by error type
            by_error_type = {}
            for error_type in ErrorType:
                count = self.db_session.query(LearnedCorrection).filter(
                    LearnedCorrection.error_type == error_type.value
                ).count()
                if count > 0:
                    by_error_type[error_type.value] = count

            # Most applied corrections
            top_corrections = self.db_session.query(LearnedCorrection).order_by(
                desc(LearnedCorrection.times_applied)
            ).limit(10).all()

            return {
                "total_corrections": total_corrections,
                "by_error_type": by_error_type,
                "top_corrections": [
                    {
                        "id": c.id,
                        "error_type": c.error_type,
                        "description": c.correction_description,
                        "times_applied": c.times_applied,
                        "confidence": c.confidence_score
                    }
                    for c in top_corrections
                ],
                "learning_enabled": self.enable_learning
            }

        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {
                "total_corrections": 0,
                "by_error_type": {},
                "top_corrections": [],
                "learning_enabled": self.enable_learning
            }
