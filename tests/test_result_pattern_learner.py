"""
Tests for Result Pattern Learner

Tests the result validation pattern learning system for handling
user feedback about result issues.

Part of Phase 2: Non-SQL Feedback Implementation
"""
import pytest
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.database.models import Base
from src.llm.result_pattern_learner import (
    ResultPatternLearner,
    ResultPattern,
    ValidationResult,
    PatternType,
    PatternAction
)
from src.llm.mapping_cache import reset_mapping_cache


@pytest.fixture
async def db_session():
    """Create a test async database session with result_validation_patterns table"""
    # Use in-memory SQLite for testing (async version)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create result_validation_patterns table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS result_validation_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type VARCHAR(50) NOT NULL,
                pattern_description TEXT NOT NULL,
                matching_criteria TEXT NOT NULL,
                action VARCHAR(50) NOT NULL,
                suggestion TEXT NULL,
                times_triggered INTEGER DEFAULT 0,
                times_helpful INTEGER DEFAULT 0,
                confidence_score REAL DEFAULT 1.0,
                learned_from_feedback_id INTEGER NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_triggered_at TIMESTAMP NULL
            )
        """))

    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create and yield session
    async with AsyncSessionLocal() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def pattern_learner(db_session: AsyncSession) -> ResultPatternLearner:
    """Create a ResultPatternLearner instance for testing"""
    # Reset cache before each test to ensure clean state
    reset_mapping_cache()
    return ResultPatternLearner(db_session=db_session)


class TestResultPatternLearning:
    """Test learning result validation patterns from feedback"""

    @pytest.mark.asyncio
    async def test_learn_empty_result_pattern(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test learning an empty result pattern"""
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Query returns no results for inactive users",
            matching_criteria={
                "table_name": "users",
                "filters": {"status": "inactive"}
            },
            action="suggest_rewrite",
            feedback_id=1,
            suggestion="Check if status should be 'disabled' instead",
            confidence_score=0.90
        )

        assert pattern_id > 0

        # Verify pattern was created
        result = await db_session.execute(
            text("SELECT * FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id}
        )
        row = result.fetchone()

        assert row is not None
        assert row[1] == "empty_result"  # pattern_type
        assert "inactive users" in row[2]  # pattern_description
        assert row[4] == "suggest_rewrite"  # action
        assert row[8] == 0.90  # confidence_score

    @pytest.mark.asyncio
    async def test_learn_missing_data_pattern(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test learning a missing data pattern"""
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="missing_data",
            pattern_description="Email column contains NULL values",
            matching_criteria={
                "table_name": "users",
                "column_checks": {
                    "email": {"not_null": True}
                }
            },
            action="warn_user",
            feedback_id=2,
            suggestion="Add WHERE email IS NOT NULL filter"
        )

        assert pattern_id > 0

        # Verify criteria was stored as JSON
        result = await db_session.execute(
            text("SELECT matching_criteria FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id}
        )
        row = result.fetchone()
        criteria = json.loads(row[0])

        assert "column_checks" in criteria
        assert criteria["column_checks"]["email"]["not_null"] is True

    @pytest.mark.asyncio
    async def test_learn_suspicious_values_pattern(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test learning a suspicious values pattern"""
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="suspicious_values",
            pattern_description="Price values are negative",
            matching_criteria={
                "table_name": "products",
                "value_ranges": {
                    "price": {"min": 0, "max": 100000}
                }
            },
            action="flag_review",
            feedback_id=3
        )

        assert pattern_id > 0

    @pytest.mark.asyncio
    async def test_learn_duplicate_pattern_updates(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test that learning a duplicate pattern updates the existing one"""
        # Create first pattern
        pattern_id1 = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Empty result for active users",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=4,
            confidence_score=0.80
        )

        # Try to create similar pattern
        pattern_id2 = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Updated: Empty result for active users",
            matching_criteria={"table_name": "users"},
            action="suggest_rewrite",
            feedback_id=5,
            confidence_score=0.95
        )

        # Should return same ID
        assert pattern_id1 == pattern_id2

        # Verify confidence was updated
        result = await db_session.execute(
            text("SELECT confidence_score, action FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id1}
        )
        row = result.fetchone()
        assert row[0] == 0.95
        assert row[1] == "suggest_rewrite"


class TestResultValidation:
    """Test validating results against learned patterns"""

    @pytest.mark.asyncio
    async def test_validate_empty_result_pattern_match(self, pattern_learner: ResultPatternLearner):
        """Test that empty result pattern triggers correctly"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Empty result for users table",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=10,
            suggestion="Check your filters"
        )

        # Validate empty result
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM users WHERE active = true",
            result_data=[],
            row_count=0,
            table_name="users"
        )

        assert result.is_valid is False
        assert result.pattern_type == "empty_result"
        assert result.action == "warn_user"
        assert "Check your filters" in result.suggestion

    @pytest.mark.asyncio
    async def test_validate_empty_result_pattern_no_match(self, pattern_learner: ResultPatternLearner):
        """Test that pattern doesn't trigger when result has rows"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Empty result for users table",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=11
        )

        # Validate non-empty result
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM users",
            result_data=[{"id": 1, "name": "John"}],
            row_count=1,
            table_name="users"
        )

        assert result.is_valid is True
        assert result.pattern_type is None

    @pytest.mark.asyncio
    async def test_validate_missing_data_pattern_match(self, pattern_learner: ResultPatternLearner):
        """Test that missing data pattern triggers correctly"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="missing_data",
            pattern_description="Email should not be NULL",
            matching_criteria={
                "column_checks": {
                    "email": {"not_null": True}
                }
            },
            action="flag_review",
            feedback_id=12,
            suggestion="Add WHERE email IS NOT NULL"
        )

        # Validate result with NULL email
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM users",
            result_data=[
                {"id": 1, "name": "John", "email": None}
            ],
            row_count=1
        )

        assert result.is_valid is False
        assert result.pattern_type == "missing_data"
        assert result.action == "flag_review"

    @pytest.mark.asyncio
    async def test_validate_missing_data_pattern_no_match(self, pattern_learner: ResultPatternLearner):
        """Test that missing data pattern doesn't trigger with valid data"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="missing_data",
            pattern_description="Email should not be NULL",
            matching_criteria={
                "column_checks": {
                    "email": {"not_null": True}
                }
            },
            action="flag_review",
            feedback_id=13
        )

        # Validate result with valid email
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM users",
            result_data=[
                {"id": 1, "name": "John", "email": "john@example.com"}
            ],
            row_count=1
        )

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_suspicious_values_pattern_match(self, pattern_learner: ResultPatternLearner):
        """Test that suspicious values pattern triggers correctly"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="suspicious_values",
            pattern_description="Price should be positive",
            matching_criteria={
                "value_ranges": {
                    "price": {"min": 0, "max": 100000}
                }
            },
            action="warn_user",
            feedback_id=14,
            suggestion="Check for negative prices"
        )

        # Validate result with negative price
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM products",
            result_data=[
                {"id": 1, "name": "Product", "price": -10}
            ],
            row_count=1
        )

        assert result.is_valid is False
        assert result.pattern_type == "suspicious_values"

    @pytest.mark.asyncio
    async def test_validate_suspicious_values_pattern_no_match(self, pattern_learner: ResultPatternLearner):
        """Test that suspicious values pattern doesn't trigger with valid values"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="suspicious_values",
            pattern_description="Price should be positive",
            matching_criteria={
                "value_ranges": {
                    "price": {"min": 0, "max": 100000}
                }
            },
            action="warn_user",
            feedback_id=15
        )

        # Validate result with valid price
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM products",
            result_data=[
                {"id": 1, "name": "Product", "price": 99.99}
            ],
            row_count=1
        )

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_wrong_aggregation_pattern(self, pattern_learner: ResultPatternLearner):
        """Test wrong aggregation pattern detection"""
        # Learn pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="wrong_aggregation",
            pattern_description="COUNT should return at least 1",
            matching_criteria={
                "expected_min_value": 1
            },
            action="suggest_rewrite",
            feedback_id=16,
            suggestion="Check your filters or JOIN conditions"
        )

        # Validate result with count of 0
        result = await pattern_learner.validate_result(
            sql="SELECT COUNT(*) FROM users WHERE active = true",
            result_data=[{"count": 0}],
            row_count=1
        )

        assert result.is_valid is False
        assert result.pattern_type == "wrong_aggregation"

    @pytest.mark.asyncio
    async def test_validate_no_patterns(self, pattern_learner: ResultPatternLearner):
        """Test validation when no patterns exist"""
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM users",
            result_data=[{"id": 1}],
            row_count=1
        )

        assert result.is_valid is True
        assert result.pattern_type is None

    @pytest.mark.asyncio
    async def test_validate_low_confidence_filtered(self, pattern_learner: ResultPatternLearner):
        """Test that low-confidence patterns are filtered out"""
        # Learn low-confidence pattern
        await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Low confidence pattern",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=17,
            confidence_score=0.40
        )

        # Validate with default min_confidence=0.6
        result = await pattern_learner.validate_result(
            sql="SELECT * FROM users",
            result_data=[],
            row_count=0,
            table_name="users"
        )

        # Should not trigger because confidence is too low
        assert result.is_valid is True


class TestPatternTracking:
    """Test pattern usage tracking"""

    @pytest.mark.asyncio
    async def test_pattern_trigger_increments_counter(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test that triggering a pattern increments times_triggered"""
        # Learn pattern
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Empty result",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=20
        )

        # Trigger pattern once
        await pattern_learner.validate_result(
            sql="SELECT * FROM users",
            result_data=[],
            row_count=0,
            table_name="users"
        )

        # Check times_triggered
        result = await db_session.execute(
            text("SELECT times_triggered FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id}
        )
        row = result.fetchone()
        assert row[0] == 1

        # Trigger again
        await pattern_learner.validate_result(
            sql="SELECT * FROM users WHERE active = true",
            result_data=[],
            row_count=0,
            table_name="users"
        )

        # Check times_triggered again
        result = await db_session.execute(
            text("SELECT times_triggered FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id}
        )
        row = result.fetchone()
        assert row[0] == 2

    @pytest.mark.asyncio
    async def test_mark_pattern_helpful(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test marking a pattern as helpful"""
        # Learn pattern
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Empty result",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=21
        )

        # Mark as helpful
        success = await pattern_learner.mark_pattern_helpful(pattern_id)
        assert success is True

        # Verify times_helpful was incremented
        result = await db_session.execute(
            text("SELECT times_helpful FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id}
        )
        row = result.fetchone()
        assert row[0] == 1


class TestPatternStats:
    """Test pattern statistics"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, pattern_learner: ResultPatternLearner):
        """Test stats when no patterns exist"""
        stats = await pattern_learner.get_pattern_stats()

        assert stats["total_patterns"] == 0
        assert stats["total_triggers"] == 0
        assert stats["total_helpful"] == 0
        assert stats["helpfulness_rate"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_patterns(self, pattern_learner: ResultPatternLearner):
        """Test stats with multiple patterns"""
        # Create patterns of different types
        await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Empty result pattern",
            matching_criteria={},
            action="warn_user",
            feedback_id=30
        )

        await pattern_learner.learn_from_feedback(
            pattern_type="missing_data",
            pattern_description="Missing data pattern",
            matching_criteria={},
            action="flag_review",
            feedback_id=31
        )

        await pattern_learner.learn_from_feedback(
            pattern_type="suspicious_values",
            pattern_description="Suspicious values pattern",
            matching_criteria={},
            action="warn_user",
            feedback_id=32
        )

        stats = await pattern_learner.get_pattern_stats()

        assert stats["total_patterns"] == 3
        assert stats["empty_result_patterns"] == 1
        assert stats["missing_data_patterns"] == 1
        assert stats["suspicious_values_patterns"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_helpfulness_rate(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test helpfulness rate calculation"""
        # Create pattern
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Test pattern",
            matching_criteria={"table_name": "users"},
            action="warn_user",
            feedback_id=33
        )

        # Trigger 10 times
        for _ in range(10):
            await pattern_learner.validate_result(
                sql="SELECT * FROM users",
                result_data=[],
                row_count=0,
                table_name="users"
            )

        # Mark as helpful 6 times
        for _ in range(6):
            await pattern_learner.mark_pattern_helpful(pattern_id)

        stats = await pattern_learner.get_pattern_stats()

        assert stats["total_triggers"] == 10
        assert stats["total_helpful"] == 6
        assert stats["helpfulness_rate"] == 60.0


class TestPatternDeletion:
    """Test deleting patterns"""

    @pytest.mark.asyncio
    async def test_delete_pattern(self, pattern_learner: ResultPatternLearner, db_session: AsyncSession):
        """Test deleting a pattern"""
        # Create pattern
        pattern_id = await pattern_learner.learn_from_feedback(
            pattern_type="empty_result",
            pattern_description="Test pattern",
            matching_criteria={},
            action="warn_user",
            feedback_id=40
        )

        # Delete it
        deleted = await pattern_learner.delete_pattern(pattern_id)
        assert deleted is True

        # Verify it's gone
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM result_validation_patterns WHERE id = :id"),
            {"id": pattern_id}
        )
        count = result.scalar()
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_pattern(self, pattern_learner: ResultPatternLearner):
        """Test deleting a pattern that doesn't exist"""
        deleted = await pattern_learner.delete_pattern(99999)
        assert deleted is False
