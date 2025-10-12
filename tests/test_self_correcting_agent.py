#!/usr/bin/env python3
"""
Tests for Self-Correcting SQL Agent

Run with: pytest tests/test_self_correcting_agent.py -v
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.llm.self_correcting_agent import (
    SelfCorrectingSQLAgent,
    ErrorDiagnostics,
    ErrorType,
    CorrectionAttempt
)


class TestErrorDiagnostics:
    """Test error categorization and diagnosis"""

    def test_categorize_syntax_error(self):
        """Test syntax error detection"""
        error = "syntax error at or near 'SLECT'"
        result = ErrorDiagnostics.categorize_error(error)
        assert result == ErrorType.SYNTAX_ERROR

    def test_categorize_table_not_found(self):
        """Test table not found error detection"""
        error = 'relation "products" does not exist'
        result = ErrorDiagnostics.categorize_error(error)
        assert result == ErrorType.TABLE_NOT_FOUND

    def test_categorize_column_not_found(self):
        """Test column not found error detection"""
        error = 'column "pric" does not exist'
        result = ErrorDiagnostics.categorize_error(error)
        assert result == ErrorType.COLUMN_NOT_FOUND

    def test_categorize_type_mismatch(self):
        """Test type mismatch error detection"""
        error = "operator does not exist: integer = text"
        result = ErrorDiagnostics.categorize_error(error)
        assert result == ErrorType.TYPE_MISMATCH

    def test_categorize_timeout(self):
        """Test timeout error detection"""
        error = "query timeout exceeded"
        result = ErrorDiagnostics.categorize_error(error)
        assert result == ErrorType.TIMEOUT

    def test_extract_table_context(self):
        """Test extracting table name from error"""
        error = 'table "products" does not exist'
        context = ErrorDiagnostics.extract_error_context(error, ErrorType.TABLE_NOT_FOUND)
        assert context["missing_table"] == "products"

    def test_extract_column_context(self):
        """Test extracting column name from error"""
        error = 'column "price" does not exist'
        context = ErrorDiagnostics.extract_error_context(error, ErrorType.COLUMN_NOT_FOUND)
        assert context["missing_column"] == "price"

    def test_generate_fix_hints(self):
        """Test hint generation"""
        context = {"missing_table": "products"}
        hints = ErrorDiagnostics.generate_fix_hints(ErrorType.TABLE_NOT_FOUND, context)
        assert "products" in hints
        assert "schema" in hints.lower()


class TestSelfCorrectingAgent:
    """Test self-correcting agent functionality"""

    @pytest.fixture
    def mock_sql_generator(self):
        """Create a mock SQL generator"""
        generator = Mock()
        generator.settings = Mock()
        generator.settings.OLLAMA_MODEL = "test-model"
        generator.generate_sql = AsyncMock()
        generator.fix_sql_error = AsyncMock()
        return generator

    @pytest.fixture
    def agent(self, mock_sql_generator):
        """Create agent instance"""
        return SelfCorrectingSQLAgent(
            sql_generator=mock_sql_generator,
            max_retries=3,
            enable_diagnostics=True
        )

    @pytest.mark.asyncio
    async def test_first_attempt_success(self, agent, mock_sql_generator):
        """Test successful query on first attempt"""
        # Mock SQL generation
        mock_sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM products LIMIT 10",
            "is_valid": True,
            "is_read_only": True,
            "warnings": [],
            "model_used": "test-model"
        }

        # Mock session with successful execution
        mock_session = Mock()

        # Mock executor result
        with patch('src.llm.self_correcting_agent.SQLExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute_query = AsyncMock(return_value={
                "success": True,
                "data": [{"id": 1, "name": "Product 1"}],
                "row_count": 1,
                "execution_time_ms": 15.5
            })

            result = await agent.generate_and_execute_with_retry(
                question="Show me all products",
                schema="Table: products (id, name, price)",
                session=mock_session,
                database_type="postgresql"
            )

            assert result["success"] is True
            assert result["total_attempts"] == 1
            assert result["self_corrected"] is False
            assert len(result["attempts"]) == 1
            assert result["attempts"][0].success is True

    @pytest.mark.asyncio
    async def test_error_then_success(self, agent, mock_sql_generator):
        """Test error on first attempt, then success after correction"""
        # First attempt - generate with error
        mock_sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM prodcuts",  # Typo
            "is_valid": True,
            "is_read_only": True,
            "warnings": [],
            "model_used": "test-model"
        }

        # Second attempt - fixed
        mock_sql_generator.fix_sql_error.return_value = {
            "sql": "SELECT * FROM products",  # Fixed
            "is_valid": True,
            "warnings": []
        }

        mock_session = Mock()

        with patch('src.llm.self_correcting_agent.SQLExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value

            # First execution fails, second succeeds
            mock_executor.execute_query = AsyncMock(side_effect=[
                {
                    "success": False,
                    "error": 'table "prodcuts" does not exist',
                    "data": [],
                    "row_count": 0
                },
                {
                    "success": True,
                    "data": [{"id": 1}],
                    "row_count": 1,
                    "execution_time_ms": 12.3
                }
            ])

            result = await agent.generate_and_execute_with_retry(
                question="Show me products",
                schema="Table: products (id, name)",
                session=mock_session,
                database_type="postgresql"
            )

            assert result["success"] is True
            assert result["total_attempts"] == 2
            assert result["self_corrected"] is True
            assert len(result["attempts"]) == 2
            assert result["attempts"][0].success is False
            assert result["attempts"][1].success is True

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, agent, mock_sql_generator):
        """Test failure after max retries"""
        mock_sql_generator.generate_sql.return_value = {
            "sql": "SELECT * FROM bad_table",
            "is_valid": True,
            "is_read_only": True,
            "warnings": [],
            "model_used": "test-model"
        }

        mock_sql_generator.fix_sql_error.return_value = {
            "sql": "SELECT * FROM bad_table",  # Still wrong
            "is_valid": True,
            "warnings": []
        }

        mock_session = Mock()

        with patch('src.llm.self_correcting_agent.SQLExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute_query = AsyncMock(return_value={
                "success": False,
                "error": "table not found",
                "data": [],
                "row_count": 0
            })

            result = await agent.generate_and_execute_with_retry(
                question="Show me data",
                schema="Table: products (id)",
                session=mock_session,
                database_type="postgresql"
            )

            assert result["success"] is False
            assert result["total_attempts"] == 3  # max_retries
            assert result["self_corrected"] is True
            assert len(result["attempts"]) == 3

    def test_correction_summary_first_try(self, agent):
        """Test summary for first-try success"""
        result = {
            "success": True,
            "total_attempts": 1,
            "self_corrected": False
        }
        summary = agent.get_correction_summary(result)
        assert "succeeded on first try" in summary.lower()

    def test_correction_summary_self_corrected(self, agent):
        """Test summary for self-corrected success"""
        result = {
            "success": True,
            "total_attempts": 2,
            "self_corrected": True
        }
        summary = agent.get_correction_summary(result)
        assert "auto-corrected" in summary.lower()
        assert "2 attempts" in summary

    def test_correction_summary_failed(self, agent):
        """Test summary for failure"""
        result = {
            "success": False,
            "total_attempts": 3,
            "error": "syntax error"
        }
        summary = agent.get_correction_summary(result)
        assert "failed" in summary.lower()
        assert "3 attempts" in summary

    def test_detailed_report(self, agent):
        """Test detailed report generation"""
        attempts = [
            CorrectionAttempt(
                attempt_number=1,
                sql="SELECT * FROM bad",
                error="table not found",
                error_type=ErrorType.TABLE_NOT_FOUND,
                success=False,
                execution_time_ms=None,
                row_count=None
            ),
            CorrectionAttempt(
                attempt_number=2,
                sql="SELECT * FROM products",
                error=None,
                error_type=ErrorType.UNKNOWN,
                success=True,
                execution_time_ms=15.5,
                row_count=10
            )
        ]

        result = {
            "success": True,
            "total_attempts": 2,
            "self_corrected": True,
            "sql": "SELECT * FROM products",
            "question": "Show products",
            "attempts": attempts
        }

        report = agent.get_detailed_report(result)

        assert report["success"] is True
        assert report["total_attempts"] == 2
        assert report["self_corrected"] is True
        assert len(report["attempts"]) == 2
        assert report["attempts"][0]["success"] is False
        assert report["attempts"][1]["success"] is True


class TestIntegration:
    """Integration tests (requires actual database)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_error_correction(self):
        """
        Test with actual database (requires test DB to be set up)
        Run with: pytest -v -m integration
        """
        # This would test with a real database connection
        # Skipping for unit tests
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
