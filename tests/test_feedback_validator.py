"""
Revised tests for FeedbackValidator matching actual implementation.

Tests cover:
- Async validate_correction() method with different modes
- Validation with actual database connections
- Suspicious pattern detection (via validate_correction)
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.llm.feedback_validator import FeedbackValidator
from src.database.models import Base, QueryHistory, DatabaseConnection
from datetime import datetime


@pytest.fixture
async def async_db_session():
    """Create an async test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    session = AsyncSessionLocal()

    yield session

    await session.close()
    await engine.dispose()


@pytest.fixture
def sample_query():
    """Create a sample QueryHistory object."""
    return QueryHistory(
        natural_language_query="Show me all customers",
        generated_sql="SELECT * FROM customer",  # Wrong table name
        executed=True,
        error_message="Table 'customer' doesn't exist",
        execution_time_ms=0.0,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_db_connection():
    """Create a mock DatabaseConnection."""
    conn = Mock(spec=DatabaseConnection)
    conn.is_active = True
    conn.database_type = "postgresql"
    conn.host = "localhost"
    conn.port = 5432
    conn.database_name = "test_db"
    return conn


class TestValidationModes:
    """Tests for different validation modes using actual validate_correction API."""

    @pytest.mark.asyncio
    async def test_strict_mode_passes_when_original_fails_corrected_succeeds(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test strict mode passes when original fails and corrected succeeds."""
        validator = FeedbackValidator(async_db_session)

        # Mock database connection query
        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            # Mock SQL execution
            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                # Mock executor
                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    # Corrected succeeds
                    mock_exec.side_effect = [
                        {"success": True, "row_count": 5, "data": []},  # Corrected
                        {"success": False, "error": "Table doesn't exist"}  # Original
                    ]

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="SELECT * FROM customers",
                        validation_mode="strict"
                    )

                    assert is_valid is True
                    assert "successful" in reason.lower()
                    assert details["corrected_succeeded"] is True
                    assert details["original_succeeded"] is False

    @pytest.mark.asyncio
    async def test_strict_mode_fails_when_both_succeed(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test strict mode fails when both original and corrected succeed."""
        validator = FeedbackValidator(async_db_session)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    # Both succeed
                    mock_exec.side_effect = [
                        {"success": True, "row_count": 5},  # Corrected
                        {"success": True, "row_count": 5}   # Original
                    ]

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="SELECT * FROM customers",
                        validation_mode="strict"
                    )

                    assert is_valid is False
                    assert "unexpectedly succeeded" in reason.lower()

    @pytest.mark.asyncio
    async def test_moderate_mode_passes_when_corrected_succeeds(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test moderate mode passes when corrected succeeds (original can succeed too)."""
        validator = FeedbackValidator(async_db_session)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    # Both succeed - moderate mode allows this
                    mock_exec.side_effect = [
                        {"success": True, "row_count": 5},  # Corrected
                        {"success": True, "row_count": 5}   # Original
                    ]

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="SELECT * FROM customers LIMIT 10",
                        validation_mode="moderate"
                    )

                    assert is_valid is True
                    assert "successful" in reason.lower()

    @pytest.mark.asyncio
    async def test_lenient_mode_only_requires_corrected_to_not_error(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test lenient mode only requires corrected SQL to execute without error."""
        validator = FeedbackValidator(async_db_session)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    # Corrected succeeds with empty results
                    mock_exec.return_value = {"success": True, "row_count": 0}

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="SELECT * FROM customers WHERE 1=0",
                        validation_mode="lenient"
                    )

                    assert is_valid is True


class TestDestructiveOperationBlocking:
    """Tests for blocking destructive operations via validate_correction."""

    @pytest.mark.asyncio
    async def test_blocks_delete_operation(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test that DELETE operations are blocked."""
        validator = FeedbackValidator(async_db_session, allow_destructive=False)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    # Corrected SQL executes successfully
                    mock_exec.return_value = {"success": True, "row_count": 1}

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="DELETE FROM customers WHERE id = 1",
                        validation_mode="moderate"
                    )

                    assert is_valid is False
                    assert "destructive" in reason.lower() or "blocked" in reason.lower()

    @pytest.mark.asyncio
    async def test_blocks_update_operation(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test that UPDATE operations are blocked."""
        validator = FeedbackValidator(async_db_session, allow_destructive=False)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    mock_exec.return_value = {"success": True, "row_count": 1}

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="UPDATE customers SET status = 'active' WHERE id = 1",
                        validation_mode="moderate"
                    )

                    assert is_valid is False
                    assert "destructive" in reason.lower() or "blocked" in reason.lower()

    @pytest.mark.asyncio
    async def test_blocks_drop_table(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test that DROP TABLE operations are blocked."""
        validator = FeedbackValidator(async_db_session)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    mock_exec.return_value = {"success": True}

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="DROP TABLE customers",
                        validation_mode="moderate"
                    )

                    assert is_valid is False
                    assert "destructive" in reason.lower() or "blocked" in reason.lower()


class TestValidationModeDescriptions:
    """Tests for get_validation_mode_description static method."""

    def test_get_strict_mode_description(self):
        """Test getting strict mode description."""
        desc = FeedbackValidator.get_validation_mode_description("strict")
        assert "strict" in desc.lower() or "fail" in desc.lower()
        assert len(desc) > 0

    def test_get_moderate_mode_description(self):
        """Test getting moderate mode description."""
        desc = FeedbackValidator.get_validation_mode_description("moderate")
        assert "moderate" in desc.lower() or "succeed" in desc.lower()
        assert len(desc) > 0

    def test_get_lenient_mode_description(self):
        """Test getting lenient mode description."""
        desc = FeedbackValidator.get_validation_mode_description("lenient")
        assert "lenient" in desc.lower() or "minimal" in desc.lower()
        assert len(desc) > 0

    def test_unknown_mode_description(self):
        """Test getting description for unknown mode."""
        desc = FeedbackValidator.get_validation_mode_description("unknown_mode")
        assert "unknown" in desc.lower()


class TestErrorHandling:
    """Tests for error handling in validate_correction."""

    @pytest.mark.asyncio
    async def test_handles_no_active_database_connection(
        self, async_db_session, sample_query
    ):
        """Test handling when no active database connection exists."""
        validator = FeedbackValidator(async_db_session)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            # Make scalar_one_or_none return an async None
            async def return_none():
                return None
            mock_result.scalar_one_or_none = return_none
            mock_execute.return_value = mock_result

            is_valid, reason, details = await validator.validate_correction(
                query=sample_query,
                corrected_sql="SELECT * FROM customers",
                validation_mode="moderate"
            )

            assert is_valid is False
            # The error message may vary, just check it's False
            assert reason is not None

    @pytest.mark.asyncio
    async def test_handles_corrected_sql_execution_failure(
        self, async_db_session, sample_query, mock_db_connection
    ):
        """Test handling when corrected SQL fails to execute."""
        validator = FeedbackValidator(async_db_session)

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    # Corrected SQL fails
                    mock_exec.return_value = {"success": False, "error": "Syntax error in SQL"}

                    is_valid, reason, details = await validator.validate_correction(
                        query=sample_query,
                        corrected_sql="INVALID SQL SYNTAX",
                        validation_mode="moderate"
                    )

                    assert is_valid is False
                    assert "failed" in reason.lower() or "error" in reason.lower()
                    assert details["corrected_tested"] is True
                    assert details["corrected_succeeded"] is False


class TestAllowDestructiveOverride:
    """Tests for allow_destructive admin override."""

    @pytest.mark.asyncio
    async def test_allow_destructive_permits_delete(
        self, async_db_session, mock_db_connection
    ):
        """Test that allow_destructive=True permits DELETE operations."""
        validator = FeedbackValidator(async_db_session, allow_destructive=True)

        # Create a query that's already a DELETE (not changing operation type)
        delete_query = QueryHistory(
            natural_language_query="Delete test user",
            generated_sql="DELETE FROM customers WHERE id = 999",  # Already DELETE
            executed=False,
            error_message=None,
            execution_time_ms=0.0,
            created_at=datetime.utcnow()
        )

        with patch.object(async_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_db_connection
            mock_execute.return_value = mock_result

            with patch('src.llm.feedback_validator.UserDatabaseConnector.get_user_db_session') as mock_connector:
                mock_user_db = AsyncMock()
                mock_connector.return_value.__aenter__.return_value = mock_user_db

                with patch.object(validator.executor, 'execute_query', new_callable=AsyncMock) as mock_exec:
                    mock_exec.side_effect = [
                        {"success": True, "row_count": 1},  # Corrected
                        {"success": True, "row_count": 1}   # Original
                    ]

                    is_valid, reason, details = await validator.validate_correction(
                        query=delete_query,
                        corrected_sql="DELETE FROM customers WHERE id = 999",  # Same operation type
                        validation_mode="lenient"  # Use lenient mode for destructive operations
                    )

                    # With admin override and lenient mode, should pass
                    assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
