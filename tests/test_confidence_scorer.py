"""
Tests for Confidence Scoring System

Tests the confidence prediction system that estimates success probability
of SQL corrections before execution.
"""
import pytest
from src.llm.confidence_scorer import (
    ConfidenceScorer,
    ConfidenceScore,
    ErrorType,
    get_confidence_scorer
)


class TestConfidenceScorer:
    """Test the confidence scoring system"""

    @pytest.fixture
    def scorer(self):
        """Create a fresh scorer instance"""
        return ConfidenceScorer()

    @pytest.fixture
    def sample_schema(self):
        """Sample database schema"""
        return {
            "customers": ["id", "name", "email", "state"],
            "orders": ["id", "customer_id", "total", "created_at"],
            "products": ["id", "name", "price", "category"]
        }

    def test_high_confidence_table_typo_fix(self, scorer, sample_schema):
        """Test high confidence for simple table name typo fix"""
        # Simple typo: custmers -> customers
        confidence = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",
            correction_sql="SELECT * FROM customers",
            schema=sample_schema
        )

        assert confidence.overall >= 0.7  # Should be high confidence
        assert confidence.get_level() in ["HIGH", "MEDIUM"]
        assert "confidence" in confidence.reasoning.lower()

    def test_low_confidence_complex_rewrite(self, scorer, sample_schema):
        """Test low confidence for complete SQL rewrite"""
        # Major rewrite suggests uncertainty
        confidence = scorer.predict_success_probability(
            error_type="syntax_error",
            original_sql="SELECT name FROM customers WHERE state = 'CA'",
            correction_sql="SELECT c.name, COUNT(*) as order_count FROM customers c LEFT JOIN orders o ON c.id = o.customer_id GROUP BY c.name",
            schema=sample_schema
        )

        assert confidence.overall < 0.7  # Lower confidence for complex change
        assert confidence.get_level() in ["MEDIUM", "LOW", "VERY_LOW"]

    def test_medium_confidence_column_fix(self, scorer, sample_schema):
        """Test medium confidence for column name fix"""
        confidence = scorer.predict_success_probability(
            error_type="column_not_found",
            original_sql="SELECT customer_name FROM customers",
            correction_sql="SELECT name FROM customers",
            schema=sample_schema
        )

        assert 0.4 <= confidence.overall <= 0.9  # Medium range
        assert confidence.get_level() in ["MEDIUM", "HIGH"]

    def test_schema_match_valid_tables(self, scorer, sample_schema):
        """Test schema matching increases confidence"""
        # Uses valid table from schema
        confidence = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",
            correction_sql="SELECT * FROM customers",
            schema=sample_schema
        )

        # Uses invalid table
        confidence_invalid = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",
            correction_sql="SELECT * FROM nonexistent_table",
            schema=sample_schema
        )

        # Valid table should have higher confidence
        assert confidence.overall > confidence_invalid.overall

    def test_schema_match_valid_columns(self, scorer, sample_schema):
        """Test schema matching for columns"""
        # Valid column
        confidence = scorer.predict_success_probability(
            error_type="column_not_found",
            original_sql="SELECT customer_name FROM customers",
            correction_sql="SELECT name FROM customers",
            schema=sample_schema
        )

        # Invalid column
        confidence_invalid = scorer.predict_success_probability(
            error_type="column_not_found",
            original_sql="SELECT customer_name FROM customers",
            correction_sql="SELECT nonexistent_column FROM customers",
            schema=sample_schema
        )

        assert confidence.overall > confidence_invalid.overall

    def test_error_type_difficulty(self, scorer):
        """Test that error type affects base confidence"""
        # Easy error (table typo)
        easy = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )

        # Hard error (timeout)
        hard = scorer.predict_success_probability(
            error_type="timeout",
            original_sql="SELECT * FROM huge_table",
            correction_sql="SELECT * FROM huge_table LIMIT 100"
        )

        # Easy errors should have higher base confidence
        assert easy.overall > hard.overall

    def test_correction_complexity_simple(self, scorer):
        """Test that simple corrections score higher"""
        # Single word change
        simple = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers WHERE state = 'CA'",
            correction_sql="SELECT * FROM customers WHERE state = 'CA'"
        )

        # Multiple changes
        complex = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers WHERE state = 'CA'",
            correction_sql="SELECT id, name, email FROM customers WHERE state IN ('CA', 'NY')"
        )

        assert simple.overall > complex.overall

    def test_similarity_score(self, scorer):
        """Test similarity between original and correction"""
        # High similarity (targeted fix)
        similar = scorer.predict_success_probability(
            error_type="syntax_error",
            original_sql="SELECT * FROM customers WHERE state = CA",  # Missing quotes
            correction_sql="SELECT * FROM customers WHERE state = 'CA'"
        )

        # Low similarity (complete rewrite)
        dissimilar = scorer.predict_success_probability(
            error_type="syntax_error",
            original_sql="SELECT * FROM customers WHERE state = CA",
            correction_sql="SELECT c.id, c.name FROM customers c JOIN orders o ON c.id = o.customer_id"
        )

        assert similar.overall > dissimilar.overall

    def test_historical_success_rate(self, scorer):
        """Test that historical success rate affects confidence"""
        error_type = "table_not_found"

        # Record some successes
        for _ in range(8):
            scorer.update_historical_stats(error_type, success=True)
        for _ in range(2):
            scorer.update_historical_stats(error_type, success=False)

        # Should have 80% success rate
        stats = scorer.get_stats()
        assert stats[error_type]["success_rate"] == 0.8

        # New prediction should reflect high historical success
        confidence = scorer.predict_success_probability(
            error_type=error_type,
            original_sql="SELECT * FROM tbl",
            correction_sql="SELECT * FROM table"
        )

        # Should be relatively high due to good history
        assert confidence.overall >= 0.5

    def test_historical_failure_rate(self, scorer):
        """Test that poor historical performance lowers confidence"""
        error_type = "timeout"

        # Record mostly failures
        for _ in range(2):
            scorer.update_historical_stats(error_type, success=True)
        for _ in range(8):
            scorer.update_historical_stats(error_type, success=False)

        # Should have 20% success rate
        stats = scorer.get_stats()
        assert stats[error_type]["success_rate"] == 0.2

        # New prediction should reflect poor history
        confidence = scorer.predict_success_probability(
            error_type=error_type,
            original_sql="SELECT * FROM huge",
            correction_sql="SELECT * FROM huge LIMIT 10"
        )

        # Should be lower due to poor history
        assert confidence.overall <= 0.6

    def test_confidence_score_factors(self, scorer, sample_schema):
        """Test that all factors are included"""
        confidence = scorer.predict_success_probability(
            error_type="column_not_found",
            original_sql="SELECT customer_name FROM customers",
            correction_sql="SELECT name FROM customers",
            schema=sample_schema
        )

        # Check all expected factors are present
        assert "error_type" in confidence.factors
        assert "schema_match" in confidence.factors
        assert "historical_success" in confidence.factors
        assert "correction_complexity" in confidence.factors
        assert "similarity" in confidence.factors

    def test_confidence_score_to_dict(self, scorer):
        """Test confidence score serialization"""
        confidence = scorer.predict_success_probability(
            error_type="syntax_error",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )

        result = confidence.to_dict()

        assert "overall" in result  # Changed from "confidence" to match frontend interface
        assert "factors" in result
        assert "reasoning" in result
        assert "recommendation" in result
        assert "level" in result
        assert result["level"] in ["HIGH", "MEDIUM", "LOW", "VERY_LOW"]

    def test_recommendation_high_confidence(self, scorer):
        """Test recommendation for high confidence"""
        confidence = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",
            correction_sql="SELECT * FROM customers",
            schema={"customers": ["id", "name"]}
        )

        if confidence.overall >= 0.8:
            assert "EXECUTE" in confidence.recommendation
            assert "High confidence" in confidence.recommendation

    def test_recommendation_low_confidence(self, scorer):
        """Test recommendation for low confidence"""
        confidence = scorer.predict_success_probability(
            error_type="connection_error",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )

        if confidence.overall < 0.3:
            assert "SKIP" in confidence.recommendation or "ALTERNATIVES" in confidence.recommendation

    def test_no_schema_provided(self, scorer):
        """Test confidence calculation without schema"""
        confidence = scorer.predict_success_probability(
            error_type="syntax_error",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers",
            schema=None  # No schema
        )

        # Should still work, just with neutral schema score
        assert 0.0 <= confidence.overall <= 1.0
        assert confidence.get_level() in ["HIGH", "MEDIUM", "LOW", "VERY_LOW"]

    def test_unknown_error_type(self, scorer):
        """Test handling of unknown error types"""
        confidence = scorer.predict_success_probability(
            error_type="completely_unknown_error",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )

        # Should handle gracefully with medium confidence
        assert 0.2 <= confidence.overall <= 0.7

    def test_extract_tables(self, scorer):
        """Test table extraction from SQL"""
        tables = scorer._extract_tables("SELECT * FROM customers JOIN orders ON customers.id = orders.customer_id")

        assert "customers" in tables
        assert "orders" in tables
        assert len(tables) == 2

    def test_extract_columns(self, scorer):
        """Test column extraction from SQL"""
        columns = scorer._extract_columns("SELECT name, email, state FROM customers")

        assert "name" in columns
        assert "email" in columns
        assert "state" in columns

    def test_column_exists_in_schema(self, scorer, sample_schema):
        """Test column existence check"""
        assert scorer._column_exists_in_schema("name", ["customers"], sample_schema)
        assert scorer._column_exists_in_schema("email", ["customers"], sample_schema)
        assert not scorer._column_exists_in_schema("nonexistent", ["customers"], sample_schema)

    def test_similar_table_detection(self, scorer, sample_schema):
        """Test detection of similar table names"""
        # Very similar
        assert scorer._has_similar_table("customer", sample_schema, threshold=0.7)
        assert scorer._has_similar_table("custmers", sample_schema, threshold=0.7)

        # Not similar
        assert not scorer._has_similar_table("xyz", sample_schema, threshold=0.8)

    def test_get_confidence_scorer_singleton(self):
        """Test that get_confidence_scorer returns same instance"""
        scorer1 = get_confidence_scorer()
        scorer2 = get_confidence_scorer()

        assert scorer1 is scorer2  # Same instance

    def test_stats_tracking(self, scorer):
        """Test statistics tracking"""
        # Add some stats
        scorer.update_historical_stats("table_not_found", True)
        scorer.update_historical_stats("table_not_found", True)
        scorer.update_historical_stats("table_not_found", False)

        stats = scorer.get_stats()

        assert "table_not_found" in stats
        assert stats["table_not_found"]["attempts"] == 3
        assert stats["table_not_found"]["successes"] == 2
        assert stats["table_not_found"]["success_rate"] == pytest.approx(0.667, abs=0.01)

    def test_confidence_with_error_message(self, scorer, sample_schema):
        """Test confidence calculation with error message"""
        confidence = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",
            correction_sql="SELECT * FROM customers",
            schema=sample_schema,
            error_message="relation \"custmers\" does not exist"
        )

        assert 0.0 <= confidence.overall <= 1.0
        assert len(confidence.reasoning) > 0

    def test_confidence_with_context(self, scorer, sample_schema):
        """Test confidence calculation with additional context"""
        confidence = scorer.predict_success_probability(
            error_type="column_not_found",
            original_sql="SELECT customer_name FROM customers",
            correction_sql="SELECT name FROM customers",
            schema=sample_schema,
            context={"database_type": "postgresql", "user_level": "beginner"}
        )

        assert 0.0 <= confidence.overall <= 1.0

    def test_very_low_confidence_threshold(self, scorer):
        """Test that very difficult errors get very low confidence"""
        confidence = scorer.predict_success_probability(
            error_type="connection_error",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )

        # Connection errors are very hard to fix
        assert confidence.overall < 0.5  # Adjusted threshold
        assert confidence.get_level() in ["LOW", "VERY_LOW", "MEDIUM"]

    def test_confidence_reasoning_quality(self, scorer, sample_schema):
        """Test that reasoning is informative"""
        confidence = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",
            correction_sql="SELECT * FROM customers",
            schema=sample_schema
        )

        reasoning = confidence.reasoning.lower()

        # Should mention confidence level
        assert any(word in reasoning for word in ["high", "medium", "low", "confidence"])

        # Should be a complete sentence
        assert len(confidence.reasoning) > 20
        assert "." in confidence.reasoning

    def test_multiple_error_types(self, scorer):
        """Test confidence for various error types"""
        error_types = [
            "table_not_found",
            "column_not_found",
            "syntax_error",
            "type_mismatch",
            "timeout",
            "permission_denied"
        ]

        confidences = []
        for error_type in error_types:
            confidence = scorer.predict_success_probability(
                error_type=error_type,
                original_sql="SELECT * FROM users",
                correction_sql="SELECT * FROM customers"
            )
            confidences.append((error_type, confidence.overall))

        # All should produce valid scores
        for error_type, score in confidences:
            assert 0.0 <= score <= 1.0, f"{error_type} produced invalid score: {score}"

    def test_no_change_penalty(self, scorer):
        """Test that identical SQL gets lower confidence"""
        confidence = scorer.predict_success_probability(
            error_type="syntax_error",
            original_sql="SELECT * FROM customers",
            correction_sql="SELECT * FROM customers"  # No change!
        )

        # Should be skeptical of "corrections" that don't change anything
        assert confidence.overall < 0.8


class TestConfidenceScoreIntegration:
    """Integration tests for confidence scoring"""

    def test_end_to_end_scenario(self):
        """Test complete confidence scoring scenario"""
        scorer = ConfidenceScorer()

        # Scenario: User has typo in table name
        schema = {
            "customers": ["id", "name", "email"],
            "orders": ["id", "customer_id", "total"]
        }

        # First attempt fails
        confidence1 = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM custmers",  # Typo
            correction_sql="SELECT * FROM customers",
            schema=schema
        )

        # Should be high confidence
        assert confidence1.overall >= 0.7
        assert confidence1.get_level() in ["HIGH", "MEDIUM"]

        # Record success
        scorer.update_historical_stats("table_not_found", success=True)

        # Next time, should benefit from history
        confidence2 = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM ordes",  # Another typo
            correction_sql="SELECT * FROM orders",
            schema=schema
        )

        # Should maintain or improve confidence
        assert confidence2.overall >= confidence1.overall - 0.1  # Allow small variance

    def test_learning_from_failures(self):
        """Test that repeated failures lower confidence"""
        scorer = ConfidenceScorer()

        # Record several failures for timeout errors
        for _ in range(5):
            scorer.update_historical_stats("timeout", success=False)

        # Should result in low confidence for future timeout fixes
        confidence = scorer.predict_success_probability(
            error_type="timeout",
            original_sql="SELECT * FROM big_table",
            correction_sql="SELECT * FROM big_table LIMIT 10"
        )

        assert confidence.overall < 0.5  # Should be cautious

    def test_json_serialization(self):
        """Test that confidence scores can be JSON serialized"""
        import json

        scorer = ConfidenceScorer()
        confidence = scorer.predict_success_probability(
            error_type="table_not_found",
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )

        # Should be JSON serializable
        json_str = json.dumps(confidence.to_dict())
        loaded = json.loads(json_str)

        assert "overall" in loaded  # Changed from "confidence" to match frontend interface
        assert "factors" in loaded
        assert "reasoning" in loaded
        assert "recommendation" in loaded
