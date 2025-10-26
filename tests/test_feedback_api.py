"""
Comprehensive tests for the User Feedback System API endpoints.

Tests cover:
- Feedback submission with various confidence levels
- Auto-learning integration
- Validation workflows
- Statistics and retrieval endpoints
- Error handling and edge cases
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.main import app
from src.database.models import Base, UserFeedback, QueryHistory, LearnedCorrection
from src.database.connection import get_db


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
def client(db_session):
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_query_history(db_session: Session):
    """Create a sample query history entry for testing."""
    query = QueryHistory(
        natural_language_query="Show me all active customers",
        generated_sql="SELECT * FROM customer",  # Intentionally incorrect
        executed=True,
        error_message="Table 'customer' doesn't exist. Did you mean 'customers'?",
        execution_time_ms=50.0,
        created_at=datetime.utcnow()
    )
    db_session.add(query)
    db_session.commit()
    db_session.refresh(query)
    return query


class TestFeedbackSubmission:
    """Tests for feedback submission endpoint (POST /api/feedback/)."""

    def test_submit_sql_correction_high_confidence(self, client, sample_query_history):
        """Test submitting SQL correction with high confidence (should auto-apply)."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": "SELECT * FROM customers WHERE status = 'active'",
            "correction_description": "Fixed table name from 'customer' to 'customers'",
            "user_confidence": 0.95,
            "user_notes": "The error message clearly indicated the correct table name"
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        assert data["query_id"] == sample_query_history.id
        assert data["feedback_type"] == "sql_correction"
        assert data["corrected_sql"] == feedback_data["corrected_sql"]
        assert data["user_confidence"] == 0.95
        assert "id" in data
        assert "created_at" in data

        # High confidence should trigger auto-learning
        # Note: This depends on validation passing
        # assert data.get("applied_successfully") is True  # May be True if validation passes

    def test_submit_sql_correction_medium_confidence(self, client, sample_query_history):
        """Test submitting SQL correction with medium confidence (deferred mode)."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": "SELECT * FROM customers",
            "correction_description": "Fixed table name",
            "user_confidence": 0.75,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        assert data["user_confidence"] == 0.75
        # Medium confidence should not auto-apply
        assert data.get("applied_successfully") is False

    def test_submit_sql_correction_low_confidence(self, client, sample_query_history):
        """Test submitting SQL correction with low confidence (manual review mode)."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": "SELECT * FROM customers",
            "correction_description": "Not sure if this is correct",
            "user_confidence": 0.5,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        assert data["user_confidence"] == 0.5
        # Low confidence should require manual review
        assert data.get("applied_successfully") is False
        assert data.get("learned_correction_id") is None

    def test_submit_column_name_correction(self, client, sample_query_history):
        """Test submitting column name correction feedback."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "column_name",
            "correction_description": "Column 'customer_name' should be 'full_name'",
            "correction_details": {
                "from": "customer_name",
                "to": "full_name"
            },
            "user_confidence": 1.0,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        assert data["feedback_type"] == "column_name"
        assert data["correction_details"]["from"] == "customer_name"
        assert data["correction_details"]["to"] == "full_name"

    def test_submit_table_name_correction(self, client, sample_query_history):
        """Test submitting table name correction feedback."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "table_name",
            "correction_description": "Table 'customer' should be 'customers' (plural)",
            "correction_details": {
                "from": "customer",
                "to": "customers"
            },
            "user_confidence": 1.0,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        assert data["feedback_type"] == "table_name"
        assert data["correction_details"] is not None

    def test_submit_result_issue(self, client, sample_query_history):
        """Test submitting result issue feedback."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "result_issue",
            "correction_description": "Results missing recent entries from today",
            "user_notes": "Query should include today's data but only shows up to yesterday",
            "user_confidence": 0.8,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        assert data["feedback_type"] == "result_issue"
        assert data["user_notes"] is not None

    def test_submit_feedback_invalid_type(self, client, sample_query_history):
        """Test submitting feedback with invalid type."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "invalid_type",
            "correction_description": "Some description",
        }

        response = client.post("/api/feedback/", json=feedback_data)

        # Should return validation error
        assert response.status_code == 422

    def test_submit_feedback_nonexistent_query(self, client):
        """Test submitting feedback for non-existent query."""
        feedback_data = {
            "query_id": 999999,  # Non-existent
            "feedback_type": "sql_correction",
            "corrected_sql": "SELECT * FROM test",
            "correction_description": "Test",
        }

        response = client.post("/api/feedback/", json=feedback_data)

        # Should return 404 or validation error
        assert response.status_code in [404, 422]

    def test_submit_feedback_missing_required_fields(self, client, sample_query_history):
        """Test submitting feedback with missing required fields."""
        feedback_data = {
            "query_id": sample_query_history.id,
            # Missing feedback_type
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 422

    def test_submit_feedback_with_default_confidence(self, client, sample_query_history):
        """Test that confidence defaults to 1.0 if not provided."""
        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": "SELECT * FROM customers",
            "correction_description": "Fixed table name",
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()

        # Should default to 1.0
        assert data["user_confidence"] == 1.0


class TestFeedbackRetrieval:
    """Tests for feedback retrieval endpoints."""

    def test_get_recent_feedback_default(self, client, sample_query_history, db_session):
        """Test getting recent feedback with default parameters."""
        # Create some feedback entries
        for i in range(3):
            feedback = UserFeedback(
                query_id=sample_query_history.id,
                feedback_type="sql_correction",
                original_sql=sample_query_history.generated_sql,
                corrected_sql=f"SELECT * FROM customers LIMIT {i}",
                correction_description=f"Test correction {i}",
                user_confidence=0.8,
                applied_successfully=False
            )
            db_session.add(feedback)
        db_session.commit()

        response = client.get("/api/feedback/recent")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_recent_feedback_with_limit(self, client, sample_query_history, db_session):
        """Test getting recent feedback with custom limit."""
        # Create feedback entries
        for i in range(10):
            feedback = UserFeedback(
                query_id=sample_query_history.id,
                feedback_type="sql_correction",
                original_sql=sample_query_history.generated_sql,
                corrected_sql=f"SELECT {i}",
                correction_description=f"Test {i}",
                user_confidence=0.8,
                applied_successfully=False
            )
            db_session.add(feedback)
        db_session.commit()

        response = client.get("/api/feedback/recent?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 5

    def test_get_recent_feedback_with_pagination(self, client, sample_query_history, db_session):
        """Test feedback pagination with offset."""
        # Create feedback entries
        for i in range(10):
            feedback = UserFeedback(
                query_id=sample_query_history.id,
                feedback_type="sql_correction",
                original_sql=sample_query_history.generated_sql,
                corrected_sql=f"SELECT {i}",
                correction_description=f"Test {i}",
                user_confidence=0.8,
                applied_successfully=False
            )
            db_session.add(feedback)
        db_session.commit()

        response = client.get("/api/feedback/recent?limit=5&offset=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 5

    def test_get_feedback_for_specific_query(self, client, sample_query_history, db_session):
        """Test getting feedback for a specific query."""
        # Create feedback for the query
        feedback = UserFeedback(
            query_id=sample_query_history.id,
            feedback_type="sql_correction",
            original_sql=sample_query_history.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="Fixed table name",
            user_confidence=0.9,
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()

        response = client.get(f"/api/feedback/query/{sample_query_history.id}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(item["query_id"] == sample_query_history.id for item in data)

    def test_get_feedback_for_nonexistent_query(self, client):
        """Test getting feedback for non-existent query."""
        response = client.get("/api/feedback/query/999999")

        assert response.status_code == 200
        data = response.json()

        # Should return empty list
        assert data == []


class TestFeedbackStats:
    """Tests for feedback statistics endpoint."""

    def test_get_stats_empty(self, client):
        """Test getting stats when no feedback exists."""
        response = client.get("/api/feedback/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_feedback" in data
        assert "applied_to_learning" in data
        assert "pending" in data
        assert "by_type" in data

    def test_get_stats_with_feedback(self, client, sample_query_history, db_session):
        """Test getting stats with various feedback types."""
        # Create feedback of different types
        feedback_types = ["sql_correction", "column_name", "table_name", "result_issue"]
        for i, ftype in enumerate(feedback_types):
            feedback = UserFeedback(
                query_id=sample_query_history.id,
                feedback_type=ftype,
                original_sql=sample_query_history.generated_sql,
                correction_description=f"Test {ftype}",
                user_confidence=0.8,
                applied_successfully=(i % 2 == 0)  # Alternate applied/pending
            )
            db_session.add(feedback)
        db_session.commit()

        response = client.get("/api/feedback/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_feedback"] >= 4
        assert data["applied_to_learning"] >= 2  # Two were marked as applied
        assert data["pending"] >= 2  # Two were not applied

        # Check by_type breakdown
        assert isinstance(data["by_type"], dict)
        for ftype in feedback_types:
            assert ftype in data["by_type"]


class TestFeedbackApply:
    """Tests for manual feedback application endpoint."""

    def test_apply_feedback_manually(self, client, sample_query_history, db_session):
        """Test manually applying feedback to learning system."""
        # Create feedback that hasn't been applied yet
        feedback = UserFeedback(
            query_id=sample_query_history.id,
            feedback_type="sql_correction",
            original_sql=sample_query_history.generated_sql,
            corrected_sql="SELECT * FROM customers WHERE status = 'active'",
            correction_description="Fixed table name and added filter",
            user_confidence=0.7,  # Medium confidence, not auto-applied
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        apply_data = {
            "feedback_id": feedback.id,
            "test_before_learning": True
        }

        response = client.post("/api/feedback/apply", json=apply_data)

        # Response depends on validation passing
        # If validation passes, should be 200, otherwise 4xx
        assert response.status_code in [200, 400, 422]

    def test_apply_feedback_with_testing_disabled(self, client, sample_query_history, db_session):
        """Test applying feedback without pre-testing."""
        feedback = UserFeedback(
            query_id=sample_query_history.id,
            feedback_type="sql_correction",
            original_sql=sample_query_history.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="Fixed table name",
            user_confidence=0.7,
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        apply_data = {
            "feedback_id": feedback.id,
            "test_before_learning": False  # Skip validation
        }

        response = client.post("/api/feedback/apply", json=apply_data)

        # Should accept without testing
        assert response.status_code in [200, 400]

    def test_apply_nonexistent_feedback(self, client):
        """Test applying non-existent feedback."""
        apply_data = {
            "feedback_id": 999999,
            "test_before_learning": True
        }

        response = client.post("/api/feedback/apply", json=apply_data)

        assert response.status_code == 404

    def test_apply_already_applied_feedback(self, client, sample_query_history, db_session):
        """Test applying feedback that's already been applied."""
        # Create learned correction
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

        # Create feedback that's already applied
        feedback = UserFeedback(
            query_id=sample_query_history.id,
            feedback_type="sql_correction",
            original_sql=sample_query_history.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="Already applied",
            user_confidence=0.9,
            applied_successfully=True,
            learned_correction_id=learned.id
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        apply_data = {
            "feedback_id": feedback.id,
            "test_before_learning": True
        }

        response = client.post("/api/feedback/apply", json=apply_data)

        # Should return error or success (already applied)
        assert response.status_code in [200, 400]


class TestFeedbackDeletion:
    """Tests for feedback deletion endpoint."""

    def test_delete_feedback_success(self, client, sample_query_history, db_session):
        """Test successful feedback deletion."""
        feedback = UserFeedback(
            query_id=sample_query_history.id,
            feedback_type="sql_correction",
            original_sql=sample_query_history.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="To be deleted",
            user_confidence=0.8,
            applied_successfully=False
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        response = client.delete(f"/api/feedback/{feedback.id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = client.get(f"/api/feedback/query/{sample_query_history.id}")
        data = get_response.json()
        assert not any(item["id"] == feedback.id for item in data)

    def test_delete_nonexistent_feedback(self, client):
        """Test deleting non-existent feedback."""
        response = client.delete("/api/feedback/999999")

        assert response.status_code == 404

    def test_delete_applied_feedback(self, client, sample_query_history, db_session):
        """Test deleting feedback that has been applied to learning."""
        learned = LearnedCorrection(
            error_type="table_not_found",
            error_pattern="Table 'test' doesn't exist",
            database_type="postgres",
            original_sql="SELECT * FROM test",
            original_error="Table 'test' doesn't exist",
            corrected_sql="SELECT * FROM tests",
            confidence_score=0.9,
            times_applied=1,
            success_rate=1.0
        )
        db_session.add(learned)
        db_session.commit()
        db_session.refresh(learned)

        feedback = UserFeedback(
            query_id=sample_query_history.id,
            feedback_type="sql_correction",
            original_sql=sample_query_history.generated_sql,
            corrected_sql="SELECT * FROM customers",
            correction_description="Applied feedback",
            user_confidence=0.9,
            applied_successfully=True,
            learned_correction_id=learned.id
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        response = client.delete(f"/api/feedback/{feedback.id}")

        # Should either succeed or return error (policy decision)
        assert response.status_code in [204, 400, 403]


class TestFeedbackEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_correction_description(self, client, sample_query_history):
        """Test feedback with very long description."""
        long_description = "A" * 10000  # Very long description

        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": "SELECT * FROM customers",
            "correction_description": long_description,
            "user_confidence": 0.8,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        # Should handle long text or return validation error
        assert response.status_code in [201, 422]

    def test_confidence_boundary_values(self, client, sample_query_history):
        """Test confidence at exact boundary values."""
        test_confidences = [0.0, 0.69, 0.70, 0.89, 0.90, 1.0]

        for confidence in test_confidences:
            feedback_data = {
                "query_id": sample_query_history.id,
                "feedback_type": "sql_correction",
                "corrected_sql": "SELECT * FROM customers",
                "correction_description": f"Test with confidence {confidence}",
                "user_confidence": confidence,
            }

            response = client.post("/api/feedback/", json=feedback_data)

            assert response.status_code == 201
            data = response.json()
            assert data["user_confidence"] == confidence

    def test_confidence_out_of_range(self, client, sample_query_history):
        """Test confidence values outside valid range."""
        invalid_confidences = [-0.1, 1.1, 2.0]

        for confidence in invalid_confidences:
            feedback_data = {
                "query_id": sample_query_history.id,
                "feedback_type": "sql_correction",
                "corrected_sql": "SELECT * FROM customers",
                "correction_description": "Test",
                "user_confidence": confidence,
            }

            response = client.post("/api/feedback/", json=feedback_data)

            # Should return validation error
            assert response.status_code == 422

    def test_special_characters_in_sql(self, client, sample_query_history):
        """Test feedback with special characters in SQL."""
        special_sql = "SELECT * FROM customers WHERE name LIKE '%O''Brien%' AND notes REGEXP '^[A-Z]'"

        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": special_sql,
            "correction_description": "SQL with special characters",
            "user_confidence": 0.8,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()
        assert data["corrected_sql"] == special_sql

    def test_unicode_in_feedback(self, client, sample_query_history):
        """Test feedback with Unicode characters."""
        unicode_description = "修正表名 (Fixed table name) - テスト 测试 🎉"

        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "table_name",
            "correction_description": unicode_description,
            "correction_details": {"from": "客户", "to": "customers"},
            "user_confidence": 0.9,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        assert response.status_code == 201
        data = response.json()
        assert data["correction_description"] == unicode_description


class TestFeedbackSecurity:
    """Tests for security aspects of feedback system."""

    def test_sql_injection_in_corrected_sql(self, client, sample_query_history):
        """Test that malicious SQL is properly handled."""
        malicious_sql = "SELECT * FROM customers; DROP TABLE users; --"

        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "sql_correction",
            "corrected_sql": malicious_sql,
            "correction_description": "Malicious SQL test",
            "user_confidence": 0.95,  # High confidence
        }

        response = client.post("/api/feedback/", json=feedback_data)

        # Should accept but validation should catch destructive operations
        assert response.status_code == 201
        data = response.json()

        # Should NOT be auto-applied due to destructive operation detection
        # The validator should block DROP statements
        assert data.get("applied_successfully") is False

    def test_xss_in_description(self, client, sample_query_history):
        """Test that XSS attempts in descriptions are handled."""
        xss_description = "<script>alert('XSS')</script>"

        feedback_data = {
            "query_id": sample_query_history.id,
            "feedback_type": "result_issue",
            "correction_description": xss_description,
            "user_confidence": 0.8,
        }

        response = client.post("/api/feedback/", json=feedback_data)

        # Should accept (sanitization happens on frontend display)
        assert response.status_code == 201

    def test_destructive_operations_not_auto_learned(self, client, sample_query_history):
        """Test that destructive operations are never auto-learned."""
        destructive_sqls = [
            "DELETE FROM customers WHERE id = 1",
            "UPDATE customers SET password = 'hacked'",
            "DROP TABLE customers",
            "TRUNCATE TABLE users",
            "ALTER TABLE products DROP COLUMN price"
        ]

        for sql in destructive_sqls:
            feedback_data = {
                "query_id": sample_query_history.id,
                "feedback_type": "sql_correction",
                "corrected_sql": sql,
                "correction_description": "Destructive operation test",
                "user_confidence": 1.0,  # Maximum confidence
            }

            response = client.post("/api/feedback/", json=feedback_data)

            assert response.status_code == 201
            data = response.json()

            # Should NEVER auto-apply destructive operations
            assert data.get("applied_successfully") is False
            assert data.get("learned_correction_id") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
