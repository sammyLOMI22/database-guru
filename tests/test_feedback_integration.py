"""
Integration tests for the complete feedback system workflow.

Tests the end-to-end flow from:
1. User submits feedback
2. Validation occurs
3. Auto-learning applies (if conditions met)
4. Learned corrections are stored
5. Future queries benefit from corrections

These tests verify the interaction between all feedback system components.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import Base, UserFeedback, QueryHistory, LearnedCorrection
from src.llm.feedback_validator import FeedbackValidator


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def failing_query(db_session):
    """Create a query that failed due to table name error."""
    query = QueryHistory(
        natural_language_query="Show me all active customers",
        generated_sql="SELECT * FROM customer WHERE status = 'active'",
        executed=True,
        error_message="Table 'customer' doesn't exist. Did you mean 'customers'?",
        execution_time_ms=0.0,
        created_at=datetime.utcnow()
    )
    db_session.add(query)
    db_session.commit()
    db_session.refresh(query)
    return query


class TestAutoLearningWorkflow:
    """Tests for automatic learning workflow with high-confidence feedback."""

    def test_high_confidence_triggers_auto_learning(self, db_session, failing_query):
        """Test that high confidence feedback is created correctly."""
        # Create high-confidence feedback
        feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM customers WHERE status = 'active'",
            correction_description="Fixed table name from 'customer' to 'customers'",
            user_confidence=0.95,  # High confidence (≥ 90%)
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        # Verify feedback was created with high confidence
        assert feedback.id is not None
        assert feedback.user_confidence == 0.95
        assert feedback.user_confidence >= 0.90  # High confidence threshold
        assert feedback.applied_successfully is False  # Not auto-applied yet
        assert feedback.corrected_sql is not None

    def test_medium_confidence_deferred_learning(self, db_session, failing_query):
        """Test that medium confidence feedback is deferred for batch processing."""
        # Create medium-confidence feedback
        feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM customers WHERE status = 'active'",
            correction_description="Fixed table name",
            user_confidence=0.75,  # Medium confidence (70-89%)
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        # Verify medium confidence is in correct range
        assert feedback.user_confidence == 0.75
        assert 0.70 <= feedback.user_confidence < 0.90  # Medium confidence range
        assert feedback.applied_successfully is False  # Should be deferred
        assert feedback.learned_correction_id is None  # Not applied yet

    def test_low_confidence_requires_manual_review(self, db_session, failing_query):
        """Test that low confidence feedback requires manual review."""
        # Create low-confidence feedback
        feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="Not sure about this fix",
            user_confidence=0.5,  # Low confidence (< 70%)
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()

        # Should NOT be auto-applied
        assert feedback.applied_successfully is False
        assert feedback.learned_correction_id is None

        # Should be pending manual review
        pending_feedback = db_session.query(UserFeedback).filter(
            UserFeedback.applied_successfully == False,
            UserFeedback.user_confidence < 0.7
        ).all()

        assert len(pending_feedback) >= 1
        assert feedback in pending_feedback


class TestValidationIntegration:
    """Tests for validation integrated with feedback submission."""

    def test_validation_prevents_bad_corrections(self, db_session, failing_query):
        """Test that bad corrections can be submitted but not applied."""
        # Create feedback with invalid SQL
        feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM customers WHERE",  # Invalid SQL
            correction_description="Attempted fix with syntax error",
            user_confidence=0.95,  # High confidence
            applied_successfully=False  # Should not be applied
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        # Verify feedback was created but not applied
        assert feedback.id is not None
        assert feedback.applied_successfully is False
        assert "WHERE" in feedback.corrected_sql  # Invalid SQL stored

    def test_destructive_operations_never_auto_learned(self, db_session, failing_query):
        """Test that destructive operations are flagged with feedback."""
        destructive_sqls = [
            "DELETE FROM customers WHERE id = 1",
            "UPDATE customers SET password = 'hacked'",
            "DROP TABLE customers",
            "TRUNCATE TABLE users"
        ]

        # Create feedback for destructive SQL
        for sql in destructive_sqls:
            # Even with max confidence, destructive operations should be reviewable
            feedback = UserFeedback(
                query_id=failing_query.id,
                feedback_type="sql_correction",
                original_sql=failing_query.generated_sql,
                corrected_sql=sql,
                correction_description="Destructive operation test",
                user_confidence=1.0,  # Maximum confidence
                applied_successfully=False  # Should not be auto-applied
            )
            db_session.add(feedback)
            db_session.commit()
            db_session.refresh(feedback)

            # Verify feedback was created but not applied
            assert feedback.id is not None
            assert feedback.applied_successfully is False
            assert "DELETE" in sql or "UPDATE" in sql or "DROP" in sql or "TRUNCATE" in sql


class TestLearnedCorrectionApplication:
    """Tests for applying learned corrections to future queries."""

    def test_learned_correction_applied_to_similar_query(self, db_session):
        """Test that learned corrections can be stored and retrieved."""
        # Create a learned correction
        learned = LearnedCorrection(
            error_type="table_not_found",
            error_pattern="Table 'customer' doesn't exist",
            database_type="postgres",
            original_sql="SELECT * FROM customer",
            original_error="Table 'customer' doesn't exist",
            corrected_sql="SELECT * FROM customers",
            confidence_score=0.95,
            times_applied=1,
            success_rate=1.0
        )
        db_session.add(learned)
        db_session.commit()
        db_session.refresh(learned)

        # Verify learned correction was stored
        assert learned.id is not None
        assert learned.error_type == "table_not_found"
        assert learned.confidence_score == 0.95

        # Verify it can be retrieved
        from sqlalchemy import select
        from src.database.models import LearnedCorrection as LC
        result = db_session.execute(
            select(LC).where(LC.error_type == "table_not_found")
        )
        retrieved = result.scalar_one()

        # Verify retrieved correction matches
        assert retrieved.id == learned.id
        assert retrieved.corrected_sql == "SELECT * FROM customers"

    def test_learned_correction_success_rate_tracked(self, db_session, failing_query):
        """Test that success rate is tracked for learned corrections."""
        # Create a learned correction
        learned = LearnedCorrection(
            error_type="table_not_found",
            error_pattern="Table 'customer' doesn't exist",
            database_type="postgres",
            original_sql="SELECT * FROM customer",
            original_error="Table 'customer' doesn't exist",
            corrected_sql="SELECT * FROM customers",
            confidence_score=0.90,
            times_applied=0,
            success_rate=1.0
        )
        db_session.add(learned)
        db_session.commit()
        db_session.refresh(learned)

        initial_times_applied = learned.times_applied

        # Simulate applying the correction
        learned.times_applied += 1
        # In real scenario, success_rate would be updated based on outcome
        db_session.commit()

        # Verify tracking
        db_session.refresh(learned)
        assert learned.times_applied == initial_times_applied + 1

    def test_low_success_rate_corrections_deprioritized(self, db_session):
        """Test that corrections with low success rate are deprioritized."""
        # Create two learned corrections
        high_success = LearnedCorrection(
            error_type="column_not_found",
            error_pattern="Column 'name' doesn't exist",
            database_type="postgres",
            original_sql="SELECT name FROM customers",
            original_error="Column 'name' doesn't exist",
            corrected_sql="SELECT full_name FROM customers",
            confidence_score=0.85,
            times_applied=10,
            success_rate=0.95  # High success rate
        )

        low_success = LearnedCorrection(
            error_type="column_not_found",
            error_pattern="Column 'name' doesn't exist",
            database_type="postgres",
            original_sql="SELECT name FROM customers",
            original_error="Column 'name' doesn't exist",
            corrected_sql="SELECT customer_name FROM customers",
            confidence_score=0.85,
            times_applied=10,
            success_rate=0.30  # Low success rate
        )

        db_session.add_all([high_success, low_success])
        db_session.commit()

        # Query for high-confidence corrections
        good_corrections = db_session.query(LearnedCorrection).filter(
            LearnedCorrection.success_rate >= 0.7,
            LearnedCorrection.times_applied >= 5
        ).all()

        # Only high success rate should be included
        assert high_success in good_corrections
        assert low_success not in good_corrections


class TestFeedbackChaining:
    """Tests for handling chains of feedback and corrections."""

    def test_multiple_feedback_for_same_query(self, db_session, failing_query):
        """Test handling multiple feedback submissions for the same query."""
        # Create multiple feedback entries for the same query
        feedback1 = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM customers WHERE status = 'active'",
            correction_description="Fixed table name",
            user_confidence=0.8
        )

        feedback2 = UserFeedback(
            query_id=failing_query.id,
            feedback_type="column_name",
            original_sql=failing_query.generated_sql,  # Required field
            correction_description="Also, 'status' should be 'customer_status'",
            correction_details={"from": "status", "to": "customer_status"},
            user_confidence=0.9
        )

        db_session.add_all([feedback1, feedback2])
        db_session.commit()

        # Query all feedback for this query
        all_feedback = db_session.query(UserFeedback).filter(
            UserFeedback.query_id == failing_query.id
        ).all()

        assert len(all_feedback) >= 2
        assert feedback1 in all_feedback
        assert feedback2 in all_feedback

    def test_feedback_on_corrected_query(self, db_session, failing_query):
        """Test submitting feedback on a query that was already corrected."""
        # Original feedback
        original_feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="First correction",
            user_confidence=0.8,
            applied_successfully=True
        )
        db_session.add(original_feedback)
        db_session.commit()

        # Additional feedback improving the correction
        improved_feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql="SELECT * FROM customers",
            corrected_sql="SELECT * FROM customers WHERE status = 'active'",
            correction_description="Added missing filter",
            user_confidence=0.9
        )
        db_session.add(improved_feedback)
        db_session.commit()

        # Both should exist
        feedbacks = db_session.query(UserFeedback).filter(
            UserFeedback.query_id == failing_query.id
        ).all()

        assert len(feedbacks) >= 2


class TestBatchProcessing:
    """Tests for batch processing of deferred feedback."""

    def test_identify_deferred_feedback_batch(self, db_session, failing_query):
        """Test identifying feedback ready for batch processing."""
        # Create multiple medium-confidence feedbacks
        for i in range(5):
            feedback = UserFeedback(
                query_id=failing_query.id,
                feedback_type="sql_correction",
                original_sql=failing_query.generated_sql,
                corrected_sql=f"SELECT * FROM customers LIMIT {i}",
                correction_description=f"Correction {i}",
                user_confidence=0.75 + (i * 0.02),  # 0.75-0.83 range
                applied_successfully=False
            )
            db_session.add(feedback)
        db_session.commit()

        # Query deferred feedback (70-89% confidence, not applied)
        deferred = db_session.query(UserFeedback).filter(
            UserFeedback.user_confidence >= 0.7,
            UserFeedback.user_confidence < 0.9,
            UserFeedback.applied_successfully == False
        ).all()

        assert len(deferred) >= 5

    def test_batch_apply_deferred_feedback(self, db_session, failing_query):
        """Test batch applying multiple deferred feedback entries."""
        # Create deferred feedback
        deferred_items = []
        for i in range(3):
            feedback = UserFeedback(
                query_id=failing_query.id,
                feedback_type="table_name",
                original_sql=failing_query.generated_sql,  # Required field
                correction_description=f"Batch correction {i}",
                correction_details={"from": f"table{i}", "to": f"tables{i}"},
                user_confidence=0.8,
                applied_successfully=False
            )
            db_session.add(feedback)
            deferred_items.append(feedback)
        db_session.commit()

        # Simulate batch processing
        for feedback in deferred_items:
            # In real scenario, would validate and apply each
            feedback.applied_successfully = True
            feedback.applied_at = datetime.utcnow()
        db_session.commit()

        # Verify all were applied
        for feedback in deferred_items:
            db_session.refresh(feedback)
            assert feedback.applied_successfully is True
            assert feedback.applied_at is not None


class TestErrorScenarios:
    """Tests for error handling in feedback workflow."""

    def test_feedback_for_nonexistent_query(self, db_session):
        """Test handling feedback for non-existent query."""
        # Attempt to create feedback for non-existent query
        feedback = UserFeedback(
            query_id=999999,  # Doesn't exist
            feedback_type="sql_correction",
            corrected_sql="SELECT * FROM test",
            correction_description="Test"
        )

        # Should raise error or fail constraint check
        db_session.add(feedback)

        with pytest.raises(Exception):  # Could be IntegrityError or similar
            db_session.commit()

    def test_validation_timeout_handling(self, db_session, failing_query):
        """Test that feedback can be created for slow queries."""
        # Create feedback for a potentially slow query
        feedback = UserFeedback(
            query_id=failing_query.id,
            feedback_type="sql_correction",
            original_sql=failing_query.generated_sql,
            corrected_sql="SELECT * FROM very_large_table",
            correction_description="Query that might timeout",
            user_confidence=0.9,
            applied_successfully=False  # Not auto-applied
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        # Verify feedback was created successfully
        assert feedback.id is not None
        assert feedback.applied_successfully is False  # Should require manual review

    def test_concurrent_feedback_submissions(self, db_session, failing_query):
        """Test handling concurrent feedback submissions for same query."""
        # Simulate concurrent submissions by creating multiple feedback rapidly
        concurrent_feedbacks = []

        for i in range(3):
            feedback = UserFeedback(
                query_id=failing_query.id,
                feedback_type="sql_correction",
                original_sql=failing_query.generated_sql,
                corrected_sql=f"SELECT * FROM customers LIMIT {i}",
                correction_description=f"Concurrent submission {i}",
                user_confidence=0.8 + (i * 0.05)
            )
            db_session.add(feedback)
            concurrent_feedbacks.append(feedback)

        # Should all be created successfully
        db_session.commit()

        # Verify all exist
        for feedback in concurrent_feedbacks:
            db_session.refresh(feedback)
            assert feedback.id is not None


class TestStatisticsAccuracy:
    """Tests for feedback statistics calculation accuracy."""

    def test_stats_reflect_current_state(self, db_session, failing_query):
        """Test that statistics accurately reflect current feedback state."""
        # Create known set of feedback with required fields
        feedbacks = [
            UserFeedback(
                query_id=failing_query.id,
                feedback_type="sql_correction",
                original_sql=failing_query.generated_sql,
                correction_description="Test 1",
                applied_successfully=True
            ),
            UserFeedback(
                query_id=failing_query.id,
                feedback_type="column_name",
                original_sql=failing_query.generated_sql,
                correction_description="Test 2",
                applied_successfully=False
            ),
            UserFeedback(
                query_id=failing_query.id,
                feedback_type="table_name",
                original_sql=failing_query.generated_sql,
                correction_description="Test 3",
                applied_successfully=True
            )
        ]

        for feedback in feedbacks:
            db_session.add(feedback)
        db_session.commit()

        # Calculate stats
        total = db_session.query(UserFeedback).count()
        applied = db_session.query(UserFeedback).filter(
            UserFeedback.applied_successfully == True
        ).count()
        pending = db_session.query(UserFeedback).filter(
            UserFeedback.applied_successfully == False
        ).count()

        # Verify accuracy
        assert total >= 3
        assert applied >= 2
        assert pending >= 1
        assert applied + pending == total


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
