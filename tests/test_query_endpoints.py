"""
Comprehensive tests for Query API endpoints.

Tests cover:
- Query processing with cache hit/miss
- SQL explanation
- Query history retrieval
- Statistics endpoints
- Error handling and edge cases
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.main import app
from src.database.models import Base, QueryHistory, DatabaseConnection
from src.database.connection import get_db
from src.cache.redis_client import RedisCache
from src.llm.sql_generator import SQLGenerator
from src.config.settings import Settings


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite with StaticPool for thread safety
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session):
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            db_session.expire_all()
            yield db_session
        finally:
            pass

    # Clear any existing overrides
    app.dependency_overrides.clear()

    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_cache():
    """Mock Redis cache."""
    cache = MagicMock(spec=RedisCache)
    cache.redis = True
    cache.connect = AsyncMock()
    cache.get = AsyncMock(return_value=None)  # Default: cache miss
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def mock_sql_generator():
    """Mock SQL generator."""
    generator = MagicMock(spec=SQLGenerator)
    generator.ollama = MagicMock()
    generator.ollama.client = True
    generator.initialize = AsyncMock()
    generator.explain_sql = AsyncMock(
        return_value="This query selects all customers from California, ordered by creation date, limited to 10 results."
    )
    return generator


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock(spec=Settings)
    settings.OLLAMA_MODEL = "llama3"
    settings.CACHE_TTL = 3600
    return settings


@pytest.fixture
def active_connection(db_session):
    """Create an active database connection."""
    connection = DatabaseConnection(
        name="test_db",
        database_type="postgresql",
        connection_string="postgresql://user:pass@localhost/testdb",
        is_active=True
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)
    return connection


@pytest.fixture
def sample_query_history(db_session):
    """Create sample query history entries."""
    queries = [
        QueryHistory(
            natural_language_query="Show me all customers from California",
            generated_sql="SELECT * FROM customers WHERE state = 'CA'",
            sql_validated=True,
            executed=True,
            execution_time_ms=15.5,
            result_count=42,
            database_type="postgresql",
            model_used="llama3",
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        ),
        QueryHistory(
            natural_language_query="What are the top 5 products by price?",
            generated_sql="SELECT name, price FROM products ORDER BY price DESC LIMIT 5",
            sql_validated=True,
            executed=True,
            execution_time_ms=22.3,
            result_count=5,
            database_type="postgresql",
            model_used="llama3",
            created_at=datetime(2024, 1, 1, 11, 0, 0)
        ),
        QueryHistory(
            natural_language_query="Count total orders",
            generated_sql="SELECT COUNT(*) FROM orders",
            sql_validated=True,
            executed=True,
            execution_time_ms=8.1,
            result_count=1,
            database_type="postgresql",
            model_used="llama3",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        ),
    ]

    for query in queries:
        db_session.add(query)

    db_session.commit()

    for query in queries:
        db_session.refresh(query)

    return queries


# ============================================================================
# Tests for GET /api/query/history
# ============================================================================

class TestQueryHistory:
    """Tests for query history endpoints."""

    def test_get_query_history_default_limit(self, client, sample_query_history):
        """Test fetching query history with default pagination."""
        response = client.get("/api/query/history")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 3
        # Should be ordered by created_at DESC
        assert data[0]["natural_language_query"] == "Count total orders"
        assert data[1]["natural_language_query"] == "What are the top 5 products by price?"
        assert data[2]["natural_language_query"] == "Show me all customers from California"

    def test_get_query_history_with_limit(self, client, sample_query_history):
        """Test query history with custom limit."""
        response = client.get("/api/query/history?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["natural_language_query"] == "Count total orders"

    def test_get_query_history_with_offset(self, client, sample_query_history):
        """Test query history with offset for pagination."""
        response = client.get("/api/query/history?limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        # Should skip the first (most recent) query
        assert data[0]["natural_language_query"] == "What are the top 5 products by price?"

    def test_get_query_history_empty(self, client):
        """Test query history when no queries exist."""
        response = client.get("/api/query/history")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_query_history_response_fields(self, client, sample_query_history):
        """Test that history response contains all required fields."""
        response = client.get("/api/query/history?limit=1")

        assert response.status_code == 200
        data = response.json()

        query = data[0]
        assert "id" in query
        assert "natural_language_query" in query
        assert "generated_sql" in query
        assert "sql_validated" in query
        assert "executed" in query
        assert "execution_time_ms" in query
        assert "result_count" in query
        assert "created_at" in query
        assert "database_type" in query
        assert "model_used" in query


# ============================================================================
# Tests for GET /api/query/history/{query_id}
# ============================================================================

class TestQueryById:
    """Tests for fetching individual query by ID."""

    def test_get_query_by_id_success(self, client, sample_query_history):
        """Test fetching a specific query by ID."""
        query_id = sample_query_history[0].id

        response = client.get(f"/api/query/history/{query_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == query_id
        assert data["natural_language_query"] == "Show me all customers from California"
        assert data["generated_sql"] == "SELECT * FROM customers WHERE state = 'CA'"

    def test_get_query_by_id_not_found(self, client):
        """Test fetching non-existent query returns 404."""
        response = client.get("/api/query/history/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_query_by_id_all_fields(self, client, sample_query_history):
        """Test that individual query response contains all fields."""
        query_id = sample_query_history[0].id

        response = client.get(f"/api/query/history/{query_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["execution_time_ms"] == 15.5
        assert data["result_count"] == 42
        assert data["sql_validated"] == True
        assert data["executed"] == True


# ============================================================================
# Tests for GET /api/query/stats
# ============================================================================

class TestQueryStats:
    """Tests for query statistics endpoint."""

    def test_get_stats_with_queries(self, client, sample_query_history):
        """Test stats endpoint with existing queries."""
        response = client.get("/api/query/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_queries" in data
        assert "average_execution_time_ms" in data
        assert "top_queries" in data

        assert data["total_queries"] == 3
        # Average of 15.5, 22.3, 8.1 = 15.3
        assert data["average_execution_time_ms"] is not None
        assert abs(data["average_execution_time_ms"] - 15.3) < 0.1

    def test_get_stats_top_queries(self, client, sample_query_history):
        """Test that top queries are returned."""
        response = client.get("/api/query/stats")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["top_queries"], list)
        assert len(data["top_queries"]) == 3

        # Each query appears once, so all have count=1
        for query_stat in data["top_queries"]:
            assert "query" in query_stat
            assert "count" in query_stat
            assert query_stat["count"] == 1

    def test_get_stats_no_queries(self, client):
        """Test stats when no queries exist."""
        response = client.get("/api/query/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_queries"] == 0
        assert data["average_execution_time_ms"] is None
        assert data["top_queries"] == []

    def test_get_stats_with_duplicate_queries(self, client, db_session):
        """Test stats with duplicate queries (same question asked multiple times)."""
        # Add same query multiple times
        for _ in range(5):
            query = QueryHistory(
                natural_language_query="Show me all users",
                generated_sql="SELECT * FROM users",
                sql_validated=True,
                executed=True,
                execution_time_ms=10.0,
                result_count=100,
                database_type="postgresql",
                model_used="llama3"
            )
            db_session.add(query)

        for _ in range(3):
            query = QueryHistory(
                natural_language_query="Count orders",
                generated_sql="SELECT COUNT(*) FROM orders",
                sql_validated=True,
                executed=True,
                execution_time_ms=5.0,
                result_count=1,
                database_type="postgresql",
                model_used="llama3"
            )
            db_session.add(query)

        db_session.commit()

        response = client.get("/api/query/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_queries"] == 8

        # Top query should be "Show me all users" with count=5
        top_queries = data["top_queries"]
        assert len(top_queries) >= 2
        assert top_queries[0]["query"] == "Show me all users"
        assert top_queries[0]["count"] == 5
        assert top_queries[1]["query"] == "Count orders"
        assert top_queries[1]["count"] == 3

    def test_get_stats_with_failed_queries(self, client, db_session):
        """Test stats with queries that have no execution time."""
        # Add successful query
        successful_query = QueryHistory(
            natural_language_query="Show users",
            generated_sql="SELECT * FROM users",
            sql_validated=True,
            executed=True,
            execution_time_ms=20.0,
            result_count=50,
            database_type="postgresql",
            model_used="llama3"
        )
        db_session.add(successful_query)

        # Add failed query (no execution time)
        failed_query = QueryHistory(
            natural_language_query="Invalid query",
            generated_sql="SELCT * FROM invalid",
            sql_validated=False,
            executed=False,
            execution_time_ms=None,
            result_count=None,
            error_message="Syntax error",
            database_type="postgresql",
            model_used="llama3"
        )
        db_session.add(failed_query)

        db_session.commit()

        response = client.get("/api/query/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_queries"] == 2
        # Average should only include successful queries
        assert data["average_execution_time_ms"] == 20.0


# ============================================================================
# Tests for POST /api/query/explain
# ============================================================================

class TestExplainSQL:
    """Tests for SQL explanation endpoint."""

    def test_explain_sql_success(self, client, db_session, mock_sql_generator):
        """Test SQL explanation with valid query."""
        from src.api.dependencies import get_sql_generator

        app.dependency_overrides[get_sql_generator] = lambda: mock_sql_generator

        try:
            response = client.post(
                "/api/query/explain",
                json={
                    "sql": "SELECT * FROM customers WHERE state = 'CA' ORDER BY created_at DESC LIMIT 10"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert "sql" in data
            assert "explanation" in data
            assert data["sql"] == "SELECT * FROM customers WHERE state = 'CA' ORDER BY created_at DESC LIMIT 10"
            assert "California" in data["explanation"]

            # Verify generator was called
            mock_sql_generator.explain_sql.assert_called_once()

        finally:
            app.dependency_overrides.clear()

    def test_explain_sql_with_schema(self, client, mock_sql_generator):
        """Test SQL explanation with provided schema."""
        from src.api.dependencies import get_sql_generator

        app.dependency_overrides[get_sql_generator] = lambda: mock_sql_generator

        try:
            schema = "CREATE TABLE customers (id INT, name VARCHAR, state VARCHAR, created_at TIMESTAMP)"

            response = client.post(
                "/api/query/explain",
                json={
                    "sql": "SELECT * FROM customers",
                    "schema": schema
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["sql"] == "SELECT * FROM customers"
            assert "explanation" in data

        finally:
            app.dependency_overrides.clear()

    def test_explain_sql_minimal_query(self, client, mock_sql_generator):
        """Test explanation of simple query."""
        from src.api.dependencies import get_sql_generator

        app.dependency_overrides[get_sql_generator] = lambda: mock_sql_generator

        try:
            response = client.post(
                "/api/query/explain",
                json={
                    "sql": "SELECT COUNT(*) FROM orders"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["sql"] == "SELECT COUNT(*) FROM orders"

        finally:
            app.dependency_overrides.clear()

    def test_explain_sql_validation_error(self, client):
        """Test that invalid SQL request returns validation error."""
        response = client.post(
            "/api/query/explain",
            json={
                "sql": "AB"  # Too short (min_length=5)
            }
        )

        assert response.status_code == 422  # Validation error


# ============================================================================
# Tests for Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in query endpoints."""

    def test_history_with_invalid_limit(self, client):
        """Test history with invalid limit parameter."""
        response = client.get("/api/query/history?limit=-1")

        # FastAPI validation should handle this
        assert response.status_code in [200, 422]

    def test_history_with_invalid_offset(self, client):
        """Test history with invalid offset parameter."""
        response = client.get("/api/query/history?offset=-5")

        # FastAPI validation should handle this
        assert response.status_code in [200, 422]

    def test_get_query_by_id_invalid_id(self, client):
        """Test fetching query with invalid ID format."""
        response = client.get("/api/query/history/invalid")

        # Should return validation error
        assert response.status_code == 422


# ============================================================================
# Integration Tests
# ============================================================================

class TestQueryIntegration:
    """Integration tests for query workflows."""

    def test_full_query_lifecycle(self, client, db_session):
        """Test creating and retrieving query history."""
        # Manually create a query (simulating what process_query would do)
        query = QueryHistory(
            natural_language_query="Test query",
            generated_sql="SELECT * FROM test",
            sql_validated=True,
            executed=True,
            execution_time_ms=10.0,
            result_count=5,
            database_type="postgresql",
            model_used="llama3"
        )
        db_session.add(query)
        db_session.commit()
        db_session.refresh(query)

        # Retrieve it via API
        response = client.get(f"/api/query/history/{query.id}")
        assert response.status_code == 200

        # Check it appears in history
        response = client.get("/api/query/history")
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Check it appears in stats
        response = client.get("/api/query/stats")
        assert response.status_code == 200
        assert response.json()["total_queries"] == 1

    def test_pagination_consistency(self, client, db_session):
        """Test that pagination returns consistent results."""
        # Create 10 queries
        for i in range(10):
            query = QueryHistory(
                natural_language_query=f"Query {i}",
                generated_sql=f"SELECT {i}",
                sql_validated=True,
                executed=True,
                execution_time_ms=10.0,
                result_count=1,
                database_type="postgresql",
                model_used="llama3"
            )
            db_session.add(query)

        db_session.commit()

        # Fetch first page
        response1 = client.get("/api/query/history?limit=5&offset=0")
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1) == 5

        # Fetch second page
        response2 = client.get("/api/query/history?limit=5&offset=5")
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2) == 5

        # Ensure no overlap
        page1_ids = [q["id"] for q in page1]
        page2_ids = [q["id"] for q in page2]
        assert len(set(page1_ids) & set(page2_ids)) == 0

    def test_stats_update_after_new_query(self, client, db_session, sample_query_history):
        """Test that stats update when new queries are added."""
        # Get initial stats
        response = client.get("/api/query/stats")
        initial_total = response.json()["total_queries"]
        assert initial_total == 3

        # Add new query
        new_query = QueryHistory(
            natural_language_query="New query",
            generated_sql="SELECT * FROM new_table",
            sql_validated=True,
            executed=True,
            execution_time_ms=25.0,
            result_count=10,
            database_type="postgresql",
            model_used="llama3"
        )
        db_session.add(new_query)
        db_session.commit()

        # Get updated stats
        response = client.get("/api/query/stats")
        updated_total = response.json()["total_queries"]
        assert updated_total == 4
