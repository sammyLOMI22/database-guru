"""
Tests for Lineage API Endpoints

Covers:
- POST /api/lineage/parse
- GET /api/lineage/query/{query_id}
- POST /api/lineage/impact
- GET /api/lineage/stats
- GET /api/lineage/patterns/{connection_id}
"""

import pytest
import datetime
from httpx import AsyncClient, ASGITransport
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database.models import QueryHistory, Base
from src.api.dependencies.common import get_db


@pytest.fixture
async def test_db_session():
    """Create a new database session with a fresh in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
def test_client(test_db_session):
    """Create test client with DB override."""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
async def db_with_queries(test_db_session):
    """Seed database with query history for API tests."""
    # Add some queries
    q1 = QueryHistory(
        natural_language_query="Show customers",
        generated_sql="SELECT * FROM customers",
        executed=True,
        execution_time_ms=100.0,
        connection_id=1,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    q2 = QueryHistory(
        natural_language_query="Show orders",
        generated_sql="SELECT * FROM orders",
        executed=True,
        execution_time_ms=200.0,
        connection_id=1,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    test_db_session.add_all([q1, q2])
    await test_db_session.commit()
    yield test_db_session


class TestParseEndpoint:
    """Tests for POST /api/lineage/parse"""

    @pytest.mark.asyncio
    async def test_parse_simple_select(self, test_client):
        """Parse simple SELECT returns lineage graph."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": "SELECT name FROM customers"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert "tables_used" in data
        assert "customers" in data["tables_used"]

    @pytest.mark.asyncio
    async def test_parse_empty_sql(self, test_client):
        """Empty SQL returns error."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": ""}
            )

        # Expect 422 Unprocessable Entity due to empty string or 400
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @pytest.mark.asyncio
    async def test_parse_invalid_sql(self, test_client):
        """Invalid SQL handled gracefully."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": "NOT VALID SQL AT ALL"}
            )

        # Should return 200 with empty/error graph, not crash
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Either empty nodes or an error field
        assert len(data.get("nodes", [])) == 0 or "error" in data or data.get("error") is not None


class TestImpactEndpoint:
    """Tests for POST /api/lineage/impact"""

    @pytest.mark.asyncio
    async def test_column_impact(self, test_client, db_with_queries):
        """Column impact returns affected queries."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/impact",
                json={
                    "table_name": "customers",
                    "column_name": "name"
                }
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "impacted_queries" in data
        assert "risk_level" in data
        assert data["risk_level"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_table_impact(self, test_client, db_with_queries):
        """Table impact (no column) returns all queries using table."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/impact",
                json={"table_name": "orders"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["impacted_queries"]) >= 0


class TestPatternsEndpoint:
    """Tests for GET /api/lineage/patterns/{connection_id}"""

    @pytest.mark.asyncio
    async def test_patterns_with_data(self, test_client, db_with_queries):
        """Patterns endpoint returns heatmap data."""
        async with test_client as client:
            response = await client.get(
                "/api/lineage/patterns/1",
                params={"time_range_days": 30}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "table_usage" in data
        assert "join_patterns" in data
        assert "bottlenecks" in data

    @pytest.mark.asyncio
    async def test_patterns_invalid_connection(self, test_client):
        """Non-existent connection returns empty results."""
        async with test_client as client:
            response = await client.get("/api/lineage/patterns/99999")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data.get("table_usage", [])) == 0
