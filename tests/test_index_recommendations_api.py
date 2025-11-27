"""
Tests for Index Recommendations API Endpoints

Tests all 8 API routes:
- GET /index-recommendations - List with filters
- GET /index-recommendations/{id} - Get single
- GET /index-recommendations/stats - Statistics
- POST /index-recommendations/analyze - Analyze query
- PUT /index-recommendations/{id} - Update status
- DELETE /index-recommendations/{id} - Delete
- POST /index-recommendations/bulk-update - Bulk update
- DELETE /index-recommendations/connection/{id} - Delete by connection
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.api.endpoints.index_recommendations import router
from src.database.models import IndexRecommendation, DatabaseConnection
from src.models.schemas import IndexRecommendationResponse


@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def sample_recommendation():
    """Create sample recommendation"""
    return IndexRecommendation(
        id=1,
        connection_id=1,
        database_name="testdb",
        database_type="postgresql",
        query_id=1,
        slow_query_sql="SELECT * FROM users WHERE email = 'test@example.com'",
        execution_time_ms=1500.0,
        query_frequency=1,
        table_name="users",
        column_names=["email"],
        index_type="btree",
        index_name="idx_users_email",
        estimated_improvement_pct=50.0,
        estimated_rows_scanned=10000,
        current_cost=1000.0,
        projected_cost=500.0,
        similar_indexes_exist=False,
        conflicting_indexes=None,
        confidence_score=0.85,
        priority="high",
        reason="Query is slow (1500ms). Index on email would improve WHERE performance. Estimated 50% improvement",
        status="pending",
        applied_at=None,
        applied_by=None,
        create_index_sql="CREATE INDEX idx_users_email ON users (email)",
        drop_index_sql="DROP INDEX idx_users_email",
        analysis_method="explain_plan",
        validated=True,
        validation_notes=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestListRecommendations:
    """Tests for GET /index-recommendations"""

    @pytest.mark.asyncio
    async def test_list_recommendations_success(self, app, sample_recommendation):
        """Test listing recommendations"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars().all.return_value = [sample_recommendation]
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/index-recommendations/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0
            assert data[0]["table_name"] == "users"

    @pytest.mark.asyncio
    async def test_list_recommendations_with_connection_filter(self, app):
        """Test filtering by connection_id"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars().all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/index-recommendations/?connection_id=1")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_recommendations_with_status_filter(self, app):
        """Test filtering by status"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars().all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/index-recommendations/?status=pending")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_recommendations_pagination(self, app):
        """Test pagination parameters"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars().all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/index-recommendations/?limit=10&offset=20"
                )

            assert response.status_code == 200


class TestGetRecommendation:
    """Tests for GET /index-recommendations/{id}"""

    @pytest.mark.asyncio
    async def test_get_recommendation_success(self, app, sample_recommendation):
        """Test getting single recommendation"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_recommendation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/index-recommendations/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["table_name"] == "users"

    @pytest.mark.asyncio
    async def test_get_recommendation_not_found(self, app):
        """Test getting non-existent recommendation"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/index-recommendations/999")

            assert response.status_code == 404


class TestGetStats:
    """Tests for GET /index-recommendations/stats"""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, app):
        """Test getting recommendation statistics"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value = mock_session

            with patch('src.api.endpoints.index_recommendations.IndexAdvisor') as mock_advisor:
                mock_advisor_instance = AsyncMock()
                mock_advisor_instance.get_recommendation_stats = AsyncMock(return_value={
                    "total_recommendations": 10,
                    "by_status": {"pending": 5, "applied": 3, "rejected": 2},
                    "by_priority": {"high": 4, "medium": 4, "low": 2},
                    "by_database_type": {"postgresql": 6, "mysql": 4},
                    "avg_execution_time_ms": 1500.0,
                    "avg_improvement_pct": 45.0,
                    "total_applied": 3,
                    "total_pending": 5
                })
                mock_advisor.return_value = mock_advisor_instance

                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.get("/index-recommendations/stats")

                assert response.status_code == 200
                data = response.json()
                assert data["total_recommendations"] == 10
                assert data["total_pending"] == 5


class TestAnalyzeSlowQuery:
    """Tests for POST /index-recommendations/analyze"""

    @pytest.mark.asyncio
    async def test_analyze_query_success(self, app, sample_recommendation):
        """Test analyzing a slow query"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value = mock_session

            with patch('src.api.endpoints.index_recommendations.IndexAdvisor') as mock_advisor:
                mock_advisor_instance = AsyncMock()
                mock_advisor_instance.analyze_query = AsyncMock(
                    return_value=sample_recommendation
                )
                mock_advisor.return_value = mock_advisor_instance

                request_data = {
                    "connection_id": 1,
                    "query_sql": "SELECT * FROM users WHERE email = 'test@example.com'",
                    "execution_time_ms": 1500.0,
                    "auto_save": True
                }

                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.post(
                        "/index-recommendations/analyze",
                        json=request_data
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["table_name"] == "users"

    @pytest.mark.asyncio
    async def test_analyze_query_no_recommendation(self, app):
        """Test when no recommendation can be generated"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value = mock_session

            with patch('src.api.endpoints.index_recommendations.IndexAdvisor') as mock_advisor:
                mock_advisor_instance = AsyncMock()
                mock_advisor_instance.analyze_query = AsyncMock(return_value=None)
                mock_advisor.return_value = mock_advisor_instance

                request_data = {
                    "connection_id": 1,
                    "query_sql": "SELECT 1",
                    "execution_time_ms": 100.0
                }

                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.post(
                        "/index-recommendations/analyze",
                        json=request_data
                    )

                assert response.status_code == 400


class TestUpdateRecommendation:
    """Tests for PUT /index-recommendations/{id}"""

    @pytest.mark.asyncio
    async def test_update_status_success(self, app, sample_recommendation):
        """Test updating recommendation status"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_recommendation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_db.return_value = mock_session

            update_data = {
                "status": "applied",
                "applied_by": "admin"
            }

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put(
                    "/index-recommendations/1",
                    json=update_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "applied"

    @pytest.mark.asyncio
    async def test_update_recommendation_not_found(self, app):
        """Test updating non-existent recommendation"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            update_data = {"status": "applied"}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put(
                    "/index-recommendations/999",
                    json=update_data
                )

            assert response.status_code == 404


class TestDeleteRecommendation:
    """Tests for DELETE /index-recommendations/{id}"""

    @pytest.mark.asyncio
    async def test_delete_recommendation_success(self, app, sample_recommendation):
        """Test deleting a recommendation"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_recommendation
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/index-recommendations/1")

            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_recommendation_not_found(self, app):
        """Test deleting non-existent recommendation"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/index-recommendations/999")

            assert response.status_code == 404


class TestBulkOperations:
    """Tests for bulk operations"""

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, app):
        """Test bulk updating recommendations"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            # Mock finding 2 recommendations
            mock_result.scalar_one_or_none.side_effect = [
                MagicMock(spec=IndexRecommendation),
                MagicMock(spec=IndexRecommendation),
            ]
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_db.return_value = mock_session

            bulk_data = {
                "recommendation_ids": [1, 2],
                "status": "rejected"
            }

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/index-recommendations/bulk-update",
                    json=bulk_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["updated"] == 2

    @pytest.mark.asyncio
    async def test_delete_connection_recommendations(self, app):
        """Test deleting all recommendations for a connection"""
        with patch('src.api.endpoints.index_recommendations.get_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 5
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_db.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete(
                    "/index-recommendations/connection/1"
                )

            assert response.status_code == 204
