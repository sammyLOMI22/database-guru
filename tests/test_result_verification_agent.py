"""Tests for Result Verification Agent"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.llm.result_verification_agent import (
    ResultVerificationAgent,
    VerificationIssue,
    VerificationResult,
    DiagnosticResult
)


class TestResultVerificationAgent:
    """Test suite for ResultVerificationAgent"""

    @pytest.fixture
    def agent(self):
        """Create a verification agent for testing"""
        return ResultVerificationAgent(
            enable_diagnostics=True,
            enable_auto_fix=True,
            extreme_value_threshold=1e9
        )

    @pytest.mark.asyncio
    async def test_empty_result_detection(self, agent):
        """Test detection of empty results"""
        question = "Show me all customers"
        sql = "SELECT * FROM customers WHERE age > 100"
        result = {
            "success": True,
            "data": [],
            "columns": ["id", "name"],
            "row_count": 0
        }
        schema = '{"tables": [{"name": "customers", "columns": ["id", "name", "age"]}]}'

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is True
        assert verification.issue_type == VerificationIssue.EMPTY_RESULT
        assert verification.confidence == 0.7
        assert "0 rows" in verification.description.lower()
        assert verification.diagnostic_queries is not None
        assert len(verification.diagnostic_queries) > 0

    @pytest.mark.asyncio
    async def test_all_nulls_detection(self, agent):
        """Test detection of all NULL values"""
        question = "Show me product prices"
        sql = "SELECT price FROM products"
        result = {
            "success": True,
            "data": [
                {"price": None},
                {"price": None},
                {"price": None}
            ],
            "columns": ["price"],
            "row_count": 3
        }
        schema = "{}"

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is True
        assert verification.issue_type == VerificationIssue.ALL_NULLS
        assert verification.confidence == 0.8
        assert "null" in verification.description.lower()

    @pytest.mark.asyncio
    async def test_extreme_value_detection(self, agent):
        """Test detection of extreme values"""
        question = "What's the total revenue?"
        sql = "SELECT SUM(price) as total FROM orders"
        result = {
            "success": True,
            "data": [{"total": 9e12}],  # 9 trillion - clearly wrong
            "columns": ["total"],
            "row_count": 1
        }
        schema = "{}"

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is True
        assert verification.issue_type == VerificationIssue.EXTREME_VALUE
        assert "extreme value" in verification.description.lower()

    @pytest.mark.asyncio
    async def test_count_zero_detection(self, agent):
        """Test detection of COUNT returning 0"""
        question = "How many customers do we have?"
        sql = "SELECT COUNT(*) as count FROM customers"
        result = {
            "success": True,
            "data": [{"count": 0}],
            "columns": ["count"],
            "row_count": 1
        }
        schema = "{}"

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is True
        assert verification.issue_type == VerificationIssue.UNEXPECTED_COUNT
        assert "count returned 0" in verification.description.lower()

    @pytest.mark.asyncio
    async def test_negative_count_detection(self, agent):
        """Test detection of negative counts (should never happen)"""
        question = "Count orders"
        sql = "SELECT COUNT(*) as count FROM orders"
        result = {
            "success": True,
            "data": [{"count": -5}],
            "columns": ["count"],
            "row_count": 1
        }
        schema = "{}"

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is True
        assert verification.issue_type == VerificationIssue.NEGATIVE_COUNT
        assert verification.confidence == 1.0  # Very high confidence
        assert "negative count" in verification.description.lower()

    @pytest.mark.asyncio
    async def test_valid_result_passes(self, agent):
        """Test that valid results pass verification"""
        question = "Show me top 5 products"
        sql = "SELECT * FROM products LIMIT 5"
        result = {
            "success": True,
            "data": [
                {"id": 1, "name": "Product 1", "price": 19.99},
                {"id": 2, "name": "Product 2", "price": 29.99},
                {"id": 3, "name": "Product 3", "price": 39.99}
            ],
            "columns": ["id", "name", "price"],
            "row_count": 3
        }
        schema = "{}"

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is False
        assert verification.issue_type == VerificationIssue.NO_ISSUE
        assert verification.confidence == 0.0

    @pytest.mark.asyncio
    async def test_failed_query_no_verification(self, agent):
        """Test that failed queries are not verified"""
        question = "Show me products"
        sql = "SELECT * FROM prodcts"  # Typo
        result = {
            "success": False,
            "error": "table prodcts does not exist",
            "data": [],
            "columns": [],
            "row_count": 0
        }
        schema = "{}"

        verification = await agent.verify_results(
            question=question,
            sql=sql,
            result=result,
            schema=schema,
            database_type="postgresql"
        )

        assert verification.is_suspicious is False
        assert "failed" in verification.description.lower()

    def test_extract_table_names(self, agent):
        """Test extraction of table names from SQL"""
        sql = "SELECT * FROM customers JOIN orders ON customers.id = orders.customer_id"
        tables = agent._extract_table_names(sql)

        assert "customers" in tables
        assert "orders" in tables
        assert len(tables) == 2

    def test_has_all_nulls(self, agent):
        """Test detection of all NULL values"""
        # All nulls
        data_all_nulls = [
            {"col1": None, "col2": None},
            {"col1": None, "col2": None}
        ]
        assert agent._has_all_nulls(data_all_nulls) is True

        # Some nulls
        data_some_nulls = [
            {"col1": None, "col2": "value"},
            {"col1": None, "col2": None}
        ]
        assert agent._has_all_nulls(data_some_nulls) is False

        # No nulls
        data_no_nulls = [
            {"col1": "value1", "col2": "value2"}
        ]
        assert agent._has_all_nulls(data_no_nulls) is False

        # Empty data
        assert agent._has_all_nulls([]) is False

    def test_generate_improvement_hints(self, agent):
        """Test generation of improvement hints"""
        question = "Show me customers"
        sql = "SELECT * FROM customers WHERE age > 100"

        verification = VerificationResult(
            is_suspicious=True,
            confidence=0.8,
            issue_type=VerificationIssue.EMPTY_RESULT,
            description="Empty result",
            suggested_fix="Check filters"
        )

        hints = agent.generate_improvement_hints(
            question=question,
            sql=sql,
            verification=verification,
            diagnostics=None
        )

        assert "Empty result" in hints
        assert "Check filters" in hints
        assert "WHERE clause" in hints

    def test_get_verification_summary(self, agent):
        """Test generation of verification summary"""
        verification = VerificationResult(
            is_suspicious=True,
            confidence=0.7,
            issue_type=VerificationIssue.EMPTY_RESULT,
            description="Empty result",
            suggested_fix="Check table"
        )

        diagnostics = DiagnosticResult(
            table_exists=True,
            table_has_data=False,
            column_exists=True,
            row_count=0,
            diagnosis="Table is empty"
        )

        summary = agent.get_verification_summary(verification, diagnostics)

        assert summary["is_suspicious"] is True
        assert summary["confidence"] == 0.7
        assert summary["issue_type"] == "empty_result"
        assert summary["description"] == "Empty result"
        assert "diagnostics" in summary
        assert summary["diagnostics"]["table_exists"] is True
        assert summary["diagnostics"]["row_count"] == 0

    @pytest.mark.asyncio
    async def test_run_diagnostics_disabled(self, agent):
        """Test diagnostics when disabled"""
        agent.enable_diagnostics = False

        verification = VerificationResult(
            is_suspicious=True,
            confidence=0.7,
            issue_type=VerificationIssue.EMPTY_RESULT,
            description="Empty result",
            diagnostic_queries=["SELECT COUNT(*) FROM customers"]
        )

        session = MagicMock()

        diagnostics = await agent.run_diagnostics(
            sql="SELECT * FROM customers",
            verification=verification,
            session=session,
            database_type="postgresql"
        )

        assert diagnostics.diagnosis == "Diagnostics disabled"

    @pytest.mark.asyncio
    async def test_run_diagnostics_with_queries(self, agent):
        """Test diagnostics with queries"""
        verification = VerificationResult(
            is_suspicious=True,
            confidence=0.7,
            issue_type=VerificationIssue.EMPTY_RESULT,
            description="Empty result",
            diagnostic_queries=[
                "SELECT COUNT(*) as count FROM customers",
                "SELECT * FROM customers LIMIT 5"
            ]
        )

        # Mock executor
        mock_session = MagicMock()

        with patch('src.core.executor.SQLExecutor') as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Mock first query (count)
            mock_executor.execute_query = AsyncMock(side_effect=[
                {
                    "success": True,
                    "data": [{"count": 100}],
                    "columns": ["count"]
                },
                {
                    "success": True,
                    "data": [
                        {"id": 1, "name": "Customer 1"},
                        {"id": 2, "name": "Customer 2"}
                    ],
                    "columns": ["id", "name"]
                }
            ])

            diagnostics = await agent.run_diagnostics(
                sql="SELECT * FROM customers",
                verification=verification,
                session=mock_session,
                database_type="postgresql"
            )

            assert diagnostics.table_has_data is True
            assert diagnostics.row_count == 100
            assert diagnostics.sample_data is not None
            assert len(diagnostics.sample_data) == 2


class TestLearnedPatternIntegration:
    """Test integration with learned result validation patterns"""

    @pytest.mark.asyncio
    async def test_learned_pattern_detects_empty_result_issue(self):
        """Test that learned patterns detect known empty result issues"""
        # Mock database session
        mock_db_session = AsyncMock()

        # Create agent with db_session
        agent = ResultVerificationAgent(
            enable_diagnostics=True,
            enable_auto_fix=True,
            db_session=mock_db_session
        )

        question = "Show me inactive users"
        sql = "SELECT * FROM users WHERE status = 'inactive'"
        result = {
            "success": True,
            "data": [],
            "columns": ["id", "name", "status"],
            "row_count": 0
        }
        schema = '{"tables": [{"name": "users", "columns": ["id", "name", "status"]}]}'

        # Mock ResultPatternLearner
        with patch('src.llm.result_verification_agent.ResultPatternLearner') as MockPatternLearner:
            mock_pattern_learner = AsyncMock()

            # Mock pattern validation result indicating an issue was detected
            mock_validation_result = MagicMock()
            mock_validation_result.is_valid = False
            mock_validation_result.message = "Empty result for status='inactive' query - likely no inactive users exist"
            mock_validation_result.suggestion = "Check if there are any users with status='inactive' in the database"
            mock_validation_result.pattern_type = "empty_result"

            mock_pattern_learner.validate_result = AsyncMock(return_value=mock_validation_result)
            MockPatternLearner.return_value = mock_pattern_learner

            # Verify results with connection_name to trigger pattern check
            verification = await agent.verify_results(
                question=question,
                sql=sql,
                result=result,
                schema=schema,
                database_type="postgresql",
                connection_name="test_connection",
                table_name="users"
            )

            # Verify pattern learner was called
            MockPatternLearner.assert_called_once_with(db_session=mock_db_session)
            mock_pattern_learner.validate_result.assert_called_once_with(
                sql=sql,
                result_data=[],
                row_count=0,
                table_name="users"
            )

            # Verify verification result indicates issue was detected
            assert verification.is_suspicious is True
            assert verification.confidence == 0.8
            assert verification.issue_type == VerificationIssue.EMPTY_RESULT
            assert "learned pattern detected" in verification.description.lower()
            assert verification.suggested_fix == "Check if there are any users with status='inactive' in the database"

    @pytest.mark.asyncio
    async def test_no_pattern_check_without_connection_name(self):
        """Test that patterns are NOT checked when connection_name is missing"""
        # Mock database session
        mock_db_session = AsyncMock()

        # Create agent with db_session
        agent = ResultVerificationAgent(
            enable_diagnostics=True,
            db_session=mock_db_session
        )

        question = "Show me users"
        sql = "SELECT * FROM users"
        result = {
            "success": True,
            "data": [{"id": 1, "name": "Test"}],
            "columns": ["id", "name"],
            "row_count": 1
        }
        schema = '{"tables": [{"name": "users", "columns": ["id", "name"]}]}'

        # Mock ResultPatternLearner
        with patch('src.llm.result_verification_agent.ResultPatternLearner') as MockPatternLearner:
            mock_pattern_learner = AsyncMock()
            MockPatternLearner.return_value = mock_pattern_learner

            # Verify WITHOUT connection_name
            verification = await agent.verify_results(
                question=question,
                sql=sql,
                result=result,
                schema=schema,
                database_type="postgresql",
                connection_name=None  # No connection name
            )

            # Verify pattern learner was NOT called
            MockPatternLearner.assert_not_called()
            mock_pattern_learner.validate_result.assert_not_called()

            # Verify normal validation continues
            assert verification.is_suspicious is False
            assert verification.issue_type == VerificationIssue.NO_ISSUE

    @pytest.mark.asyncio
    async def test_pattern_check_gracefully_handles_errors(self):
        """Test that errors in pattern checking don't break verification"""
        # Mock database session
        mock_db_session = AsyncMock()

        # Create agent with db_session
        agent = ResultVerificationAgent(
            enable_diagnostics=True,
            db_session=mock_db_session
        )

        question = "Show me products"
        sql = "SELECT * FROM products"
        result = {
            "success": True,
            "data": [{"id": 1, "name": "Widget"}],
            "columns": ["id", "name"],
            "row_count": 1
        }
        schema = '{"tables": [{"name": "products", "columns": ["id", "name"]}]}'

        # Mock ResultPatternLearner to raise an exception
        with patch('src.llm.result_verification_agent.ResultPatternLearner') as MockPatternLearner:
            mock_pattern_learner = AsyncMock()
            mock_pattern_learner.validate_result = AsyncMock(side_effect=Exception("Database error"))
            MockPatternLearner.return_value = mock_pattern_learner

            # Verify with connection_name (pattern check will fail)
            verification = await agent.verify_results(
                question=question,
                sql=sql,
                result=result,
                schema=schema,
                database_type="postgresql",
                connection_name="test_connection"
            )

            # Verify pattern check was attempted
            MockPatternLearner.assert_called_once()

            # Verify normal validation continues despite error
            assert verification.is_suspicious is False
            assert verification.issue_type == VerificationIssue.NO_ISSUE


class TestVerificationWithSelfCorrectingAgent:
    """Test integration with SelfCorrectingAgent"""

    @pytest.mark.asyncio
    async def test_verification_triggers_retry(self):
        """Test that suspicious results trigger a retry"""
        # This would require mocking SelfCorrectingSQLAgent
        # and testing the integration
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
