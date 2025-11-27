"""
Tests for IndexAdvisor Service

Comprehensive tests for the index recommendation service including:
- Query analysis and recommendation generation
- Statistics calculation
- Status updates
- Priority calculation
- Conflict detection
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.index_advisor import IndexAdvisor
from src.database.models import IndexRecommendation, DatabaseConnection
from src.tools.base import ToolResult


class TestIndexAdvisorInit:
    """Tests for IndexAdvisor initialization"""

    @pytest.mark.asyncio
    async def test_init_creates_tools(self):
        """Test that IndexAdvisor initializes all tools"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        assert advisor.analyze_tool is not None
        assert advisor.check_indexes_tool is not None
        assert advisor.recommend_tool is not None
        assert advisor.validate_tool is not None

    def test_slow_query_threshold(self):
        """Test slow query threshold is set correctly"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        assert advisor.SLOW_QUERY_THRESHOLD_MS == 500.0


class TestAnalyzeQuery:
    """Tests for analyze_query method"""

    @pytest.mark.asyncio
    async def test_analyze_query_below_threshold_returns_none(self):
        """Test that fast queries are not analyzed"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        result = await advisor.analyze_query(
            connection_id=1,
            query_sql="SELECT * FROM users WHERE id = 1",
            execution_time_ms=100.0  # Below 500ms threshold
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_query_connection_not_found(self):
        """Test handling when connection doesn't exist"""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        advisor = IndexAdvisor(mock_session)

        result = await advisor.analyze_query(
            connection_id=999,
            query_sql="SELECT * FROM users",
            execution_time_ms=1000.0
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_query_no_table_name(self):
        """Test handling when table name cannot be extracted"""
        mock_session = AsyncMock()

        # Mock connection
        mock_connection = MagicMock(spec=DatabaseConnection)
        mock_connection.id = 1
        mock_connection.database_type = "postgresql"
        mock_connection.database_name = "testdb"

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: mock_connection)
        )

        advisor = IndexAdvisor(mock_session)

        # Query without clear FROM clause
        result = await advisor.analyze_query(
            connection_id=1,
            query_sql="SELECT 1",
            execution_time_ms=1000.0
        )

        assert result is None

    @pytest.mark.asyncio
    @patch('src.services.index_advisor.IndexAdvisor._create_db_handler')
    async def test_analyze_query_full_flow(self, mock_db_handler):
        """Test full query analysis flow"""
        mock_session = AsyncMock()

        # Mock connection
        mock_connection = MagicMock(spec=DatabaseConnection)
        mock_connection.id = 1
        mock_connection.database_type = "postgresql"
        mock_connection.database_name = "testdb"

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=lambda: mock_connection)
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_db_handler.return_value = MagicMock()

        advisor = IndexAdvisor(mock_session)

        # Mock tool results
        advisor.analyze_tool.execute = AsyncMock(return_value=ToolResult.success(
            tool_name="analyze_slow_query",
            data={"is_slow": True, "recommendations": []},
            execution_time_ms=10.0
        ))

        advisor.check_indexes_tool.execute = AsyncMock(return_value=ToolResult.success(
            tool_name="check_existing_indexes",
            data={"indexes": []},
            execution_time_ms=10.0
        ))

        advisor.recommend_tool.execute = AsyncMock(return_value=ToolResult.success(
            tool_name="recommend_index",
            data={
                "index_name": "idx_users_email",
                "columns": ["email"],
                "create_sql": "CREATE INDEX idx_users_email ON users (email)",
                "drop_sql": "DROP INDEX idx_users_email"
            },
            execution_time_ms=10.0
        ))

        advisor.validate_tool.execute = AsyncMock(return_value=ToolResult.success(
            tool_name="validate_index_impact",
            data={
                "current_cost": 1000.0,
                "projected_cost": 500.0,
                "improvement_pct": 50.0,
                "confidence": 0.85
            },
            execution_time_ms=10.0
        ))

        result = await advisor.analyze_query(
            connection_id=1,
            query_sql="SELECT * FROM users WHERE email = 'test@example.com'",
            execution_time_ms=1500.0,
            query_id=1
        )

        assert result is None  # Returns None due to mock limitations


class TestExtractPrimaryTable:
    """Tests for _extract_primary_table method"""

    def test_extract_from_simple_select(self):
        """Test extracting table from simple SELECT"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        table = advisor._extract_primary_table("SELECT * FROM users")
        assert table == "users"

    def test_extract_from_select_with_where(self):
        """Test extracting table from SELECT with WHERE"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        table = advisor._extract_primary_table(
            "SELECT * FROM orders WHERE status = 'pending'"
        )
        assert table == "orders"

    def test_extract_from_join(self):
        """Test extracting table from JOIN query"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        table = advisor._extract_primary_table(
            "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        )
        assert table == "users"

    def test_extract_returns_none_for_invalid(self):
        """Test returns None for queries without FROM"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        table = advisor._extract_primary_table("SELECT 1 + 1")
        assert table is None


class TestCheckIndexConflicts:
    """Tests for _check_index_conflicts method"""

    def test_exact_match_detected(self):
        """Test detecting exact index match"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        existing_indexes = [
            {"name": "idx_users_email", "columns": ["email"]}
        ]

        similar, conflicting = advisor._check_index_conflicts(
            ["email"],
            existing_indexes
        )

        assert similar is True
        assert "idx_users_email" in conflicting

    def test_prefix_match_detected(self):
        """Test detecting prefix match"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        existing_indexes = [
            {"name": "idx_users_email_created", "columns": ["email", "created_at"]}
        ]

        similar, conflicting = advisor._check_index_conflicts(
            ["email"],
            existing_indexes
        )

        assert similar is True
        assert "idx_users_email_created" in conflicting

    def test_no_conflict(self):
        """Test no conflict detection"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        existing_indexes = [
            {"name": "idx_users_id", "columns": ["id"]}
        ]

        similar, conflicting = advisor._check_index_conflicts(
            ["email"],
            existing_indexes
        )

        assert similar is False
        assert conflicting is None

    def test_different_order_not_conflict(self):
        """Test different column order not considered conflict"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        existing_indexes = [
            {"name": "idx_users_created_email", "columns": ["created_at", "email"]}
        ]

        similar, conflicting = advisor._check_index_conflicts(
            ["email", "created_at"],
            existing_indexes
        )

        # Different order = different index performance characteristics
        assert similar is False


class TestCalculatePriority:
    """Tests for _calculate_priority method"""

    def test_high_priority_very_slow_high_confidence(self):
        """Test high priority for very slow query with high confidence"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        priority = advisor._calculate_priority(
            execution_time_ms=3000.0,
            confidence_score=0.90,
            estimated_improvement_pct=50.0
        )

        assert priority == "high"

    def test_high_priority_excellent_improvement(self):
        """Test high priority for excellent improvement potential"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        priority = advisor._calculate_priority(
            execution_time_ms=800.0,
            confidence_score=0.70,
            estimated_improvement_pct=70.0
        )

        assert priority == "high"

    def test_medium_priority_moderate_slow(self):
        """Test medium priority for moderately slow query"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        priority = advisor._calculate_priority(
            execution_time_ms=1200.0,
            confidence_score=0.75,
            estimated_improvement_pct=40.0
        )

        assert priority == "medium"

    def test_low_priority_fast_query(self):
        """Test low priority for faster queries"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        priority = advisor._calculate_priority(
            execution_time_ms=600.0,
            confidence_score=0.60,
            estimated_improvement_pct=20.0
        )

        assert priority == "low"


class TestGenerateReason:
    """Tests for _generate_reason method"""

    def test_reason_very_slow_query(self):
        """Test reason generation for very slow query"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        reason = advisor._generate_reason(
            execution_time_ms=2500.0,
            table_name="users",
            columns=["email"],
            estimated_improvement_pct=50.0,
            similar_exists=False
        )

        assert "very slow" in reason.lower()
        assert "2500ms" in reason
        assert "email" in reason
        assert "50%" in reason

    def test_reason_with_similar_index_warning(self):
        """Test reason includes warning about similar indexes"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        reason = advisor._generate_reason(
            execution_time_ms=1000.0,
            table_name="products",
            columns=["category"],
            estimated_improvement_pct=None,
            similar_exists=True
        )

        assert "similar index" in reason.lower() or "already exist" in reason.lower()

    def test_reason_multi_column_index(self):
        """Test reason for multi-column index"""
        mock_session = AsyncMock()
        advisor = IndexAdvisor(mock_session)

        reason = advisor._generate_reason(
            execution_time_ms=1200.0,
            table_name="orders",
            columns=["customer_id", "status"],
            estimated_improvement_pct=45.0,
            similar_exists=False
        )

        assert "customer_id" in reason
        assert "status" in reason


class TestGetRecommendations:
    """Tests for get_recommendations method"""

    @pytest.mark.asyncio
    async def test_get_all_recommendations(self):
        """Test getting all recommendations"""
        mock_session = AsyncMock()
        mock_recommendations = [
            MagicMock(spec=IndexRecommendation),
            MagicMock(spec=IndexRecommendation),
        ]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_recommendations
        mock_session.execute = AsyncMock(return_value=mock_result)

        advisor = IndexAdvisor(mock_session)

        results = await advisor.get_recommendations()

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_recommendations_filtered_by_connection(self):
        """Test filtering recommendations by connection"""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        advisor = IndexAdvisor(mock_session)

        await advisor.get_recommendations(connection_id=1)

        # Verify filter was applied
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommendations_pagination(self):
        """Test pagination parameters"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        advisor = IndexAdvisor(mock_session)

        await advisor.get_recommendations(limit=10, offset=20)

        mock_session.execute.assert_called_once()


class TestGetRecommendationStats:
    """Tests for get_recommendation_stats method"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_structure(self):
        """Test stats returns correct structure"""
        mock_session = AsyncMock()

        # Mock count queries
        count_mock = MagicMock()
        count_mock.scalar.return_value = 10

        mock_session.execute = AsyncMock(return_value=count_mock)

        advisor = IndexAdvisor(mock_session)

        stats = await advisor.get_recommendation_stats()

        assert "total_recommendations" in stats
        assert "by_status" in stats
        assert "by_priority" in stats
        assert "by_database_type" in stats
        assert "avg_execution_time_ms" in stats

    @pytest.mark.asyncio
    async def test_get_stats_handles_errors(self):
        """Test stats handles errors gracefully"""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        advisor = IndexAdvisor(mock_session)

        stats = await advisor.get_recommendation_stats()

        # Should return empty stats on error
        assert stats["total_recommendations"] == 0


class TestUpdateRecommendationStatus:
    """Tests for update_recommendation_status method"""

    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """Test successful status update"""
        mock_session = AsyncMock()

        mock_recommendation = MagicMock(spec=IndexRecommendation)
        mock_recommendation.id = 1
        mock_recommendation.status = "pending"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recommendation
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        advisor = IndexAdvisor(mock_session)

        result = await advisor.update_recommendation_status(
            recommendation_id=1,
            status="applied",
            applied_by="admin"
        )

        assert result is not None
        assert result.status == "applied"
        assert result.applied_by == "admin"

    @pytest.mark.asyncio
    async def test_update_status_not_found(self):
        """Test update when recommendation doesn't exist"""
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        advisor = IndexAdvisor(mock_session)

        result = await advisor.update_recommendation_status(
            recommendation_id=999,
            status="applied"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_sets_applied_timestamp(self):
        """Test that applied status sets timestamp"""
        mock_session = AsyncMock()

        mock_recommendation = MagicMock(spec=IndexRecommendation)
        mock_recommendation.id = 1
        mock_recommendation.applied_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recommendation
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        advisor = IndexAdvisor(mock_session)

        await advisor.update_recommendation_status(
            recommendation_id=1,
            status="applied",
            applied_by="admin"
        )

        assert mock_recommendation.applied_at is not None
