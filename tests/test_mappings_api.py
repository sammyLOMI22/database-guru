"""
Comprehensive tests for the Mapping Management API endpoints.

Tests cover:
- Column mapping CRUD operations
- Table mapping CRUD operations
- Result pattern CRUD operations
- Statistics endpoints
- Filtering and pagination
- Error handling and edge cases
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.database.models import Base
from src.api.dependencies.common import get_db


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create a test database engine shared across fixtures."""
    # Use in-memory SQLite with async driver
    from sqlalchemy.pool import StaticPool
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Create mapping tables
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS column_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_column TEXT NOT NULL,
                target_column TEXT NOT NULL,
                table_name TEXT,
                connection_name TEXT,
                database_type TEXT NOT NULL,
                description TEXT,
                confidence_score REAL NOT NULL,
                times_applied INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                created_by TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_applied_at TIMESTAMP
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS table_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table TEXT NOT NULL,
                target_table TEXT NOT NULL,
                connection_name TEXT,
                database_type TEXT NOT NULL,
                mapping_type TEXT NOT NULL,
                description TEXT,
                confidence_score REAL NOT NULL,
                times_applied INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                created_by TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_applied_at TIMESTAMP
            )
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS result_validation_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_description TEXT NOT NULL,
                matching_criteria TEXT NOT NULL,
                action TEXT NOT NULL,
                suggestion TEXT,
                confidence_score REAL NOT NULL,
                times_triggered INTEGER DEFAULT 0,
                times_helpful INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_triggered_at TIMESTAMP
            )
        """))

    yield test_engine

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Create an async test database session from shared engine."""
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session
        # Don't rollback - let the data persist for the test


@pytest_asyncio.fixture
async def client(engine):
    """Create an async test client with overridden database dependency using shared engine."""
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_column_mappings(db_session: AsyncSession):
    """Create sample column mappings for testing."""
    await db_session.execute(text("""
        INSERT INTO column_mappings
        (source_column, target_column, table_name, connection_name, database_type,
         confidence_score, times_applied, success_rate, created_by)
        VALUES
        ('price', 'unit_price', 'products', 'test_db', 'postgresql', 0.95, 10, 0.9, 'system'),
        ('qty', 'quantity', 'orders', 'test_db', 'postgresql', 0.88, 5, 0.8, 'system'),
        ('amt', 'amount', 'payments', 'other_db', 'mysql', 0.92, 3, 1.0, 'system')
    """))
    await db_session.commit()

    # Return mapping IDs for reference
    result = await db_session.execute(text("SELECT id FROM column_mappings ORDER BY id"))
    return [{"id": row[0]} for row in result.fetchall()]


@pytest_asyncio.fixture
async def sample_table_mappings(db_session: AsyncSession):
    """Create sample table mappings for testing."""
    await db_session.execute(text("""
        INSERT INTO table_mappings
        (source_table, target_table, connection_name, database_type, mapping_type,
         confidence_score, times_applied, success_rate, created_by)
        VALUES
        ('customer', 'customers', 'test_db', 'postgresql', 'alias', 0.90, 15, 0.93, 'system'),
        ('product', 'products', 'test_db', 'postgresql', 'synonym', 0.85, 8, 0.875, 'system')
    """))
    await db_session.commit()

    # Return mapping IDs for reference
    result = await db_session.execute(text("SELECT id FROM table_mappings ORDER BY id"))
    return [{"id": row[0]} for row in result.fetchall()]


@pytest_asyncio.fixture
async def sample_result_patterns(db_session: AsyncSession):
    """Create sample result validation patterns for testing."""
    await db_session.execute(text("""
        INSERT INTO result_validation_patterns
        (pattern_type, pattern_description, matching_criteria, action, suggestion,
         confidence_score, times_triggered, times_helpful, created_by)
        VALUES
        ('empty_result', 'No inactive users found',
         '{"table": "users", "filter": "status=''inactive''"}',
         'warn_user', 'Check if any users have status=''inactive''', 0.80, 5, 4, 'system'),
        ('missing_data', 'Products with missing prices',
         '{"table": "products", "null_column": "price"}',
         'suggest_fix', 'Update products to include price data', 0.75, 3, 2, 'system')
    """))
    await db_session.commit()

    # Return pattern IDs for reference
    result = await db_session.execute(text("SELECT id FROM result_validation_patterns ORDER BY id"))
    return [{"id": row[0]} for row in result.fetchall()]


class TestColumnMappingsEndpoints:
    """Tests for column mapping endpoints."""

    @pytest.mark.asyncio
    async def test_get_column_mappings_all(self, client, sample_column_mappings):
        """Test retrieving all column mappings."""
        response = await client.get("/api/mappings/columns")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        assert all("source_column" in item for item in data)
        assert all("target_column" in item for item in data)

    @pytest.mark.asyncio
    async def test_get_column_mappings_filter_by_connection(self, client, sample_column_mappings):
        """Test filtering column mappings by connection name."""
        response = await client.get("/api/mappings/columns?connection_name=test_db")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert all(item["connection_name"] == "test_db" for item in data)

    @pytest.mark.asyncio
    async def test_get_column_mappings_filter_by_table(self, client, sample_column_mappings):
        """Test filtering column mappings by table name."""
        response = await client.get("/api/mappings/columns?table_name=products")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["table_name"] == "products"
        assert data[0]["source_column"] == "price"

    @pytest.mark.asyncio
    async def test_get_column_mappings_filter_by_database_type(self, client, sample_column_mappings):
        """Test filtering column mappings by database type."""
        response = await client.get("/api/mappings/columns?database_type=mysql")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["database_type"] == "mysql"

    @pytest.mark.asyncio
    async def test_get_column_mappings_pagination(self, client, sample_column_mappings):
        """Test pagination of column mappings."""
        response = await client.get("/api/mappings/columns?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

        response2 = await client.get("/api/mappings/columns?limit=2&offset=2")
        data2 = response2.json()

        assert len(data2) == 1
        assert data[0]["id"] != data2[0]["id"]

    @pytest.mark.asyncio
    async def test_delete_column_mapping(self, client, sample_column_mappings):
        """Test deleting a column mapping."""
        mapping_id = sample_column_mappings[0]["id"]

        response = await client.delete(f"/api/mappings/columns/{mapping_id}")

        assert response.status_code == 204  # No content

        # Verify it's deleted
        get_response = await client.get("/api/mappings/columns")
        get_data = get_response.json()
        assert len(get_data) == 2
        assert not any(item["id"] == mapping_id for item in get_data)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_column_mapping(self, client):
        """Test deleting a nonexistent column mapping."""
        response = await client.delete("/api/mappings/columns/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_column_mapping_stats(self, client, sample_column_mappings):
        """Test retrieving column mapping statistics."""
        response = await client.get("/api/mappings/columns/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_mappings"] == 3
        assert data["total_applications"] == 18  # 10 + 5 + 3
        assert "average_success_rate" in data
        assert "by_database_type" in data
        assert "most_used" in data


class TestTableMappingsEndpoints:
    """Tests for table mapping endpoints."""

    @pytest.mark.asyncio
    async def test_get_table_mappings_all(self, client, sample_table_mappings):
        """Test retrieving all table mappings."""
        response = await client.get("/api/mappings/tables")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert all("source_table" in item for item in data)
        assert all("target_table" in item for item in data)

    @pytest.mark.asyncio
    async def test_get_table_mappings_filter_by_type(self, client, sample_table_mappings):
        """Test filtering table mappings by type."""
        response = await client.get("/api/mappings/tables?mapping_type=alias")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["mapping_type"] == "alias"

    @pytest.mark.asyncio
    async def test_delete_table_mapping(self, client, sample_table_mappings):
        """Test deleting a table mapping."""
        mapping_id = sample_table_mappings[0]["id"]

        response = await client.delete(f"/api/mappings/tables/{mapping_id}")

        assert response.status_code == 204  # No content

        # Verify it's deleted
        get_response = await client.get("/api/mappings/tables")
        get_data = get_response.json()
        assert len(get_data) == 1

    @pytest.mark.asyncio
    async def test_get_table_mapping_stats(self, client, sample_table_mappings):
        """Test retrieving table mapping statistics."""
        response = await client.get("/api/mappings/tables/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_mappings"] == 2
        assert data["total_applications"] == 23  # 15 + 8
        assert "average_success_rate" in data
        assert "by_database_type" in data


class TestResultPatternsEndpoints:
    """Tests for result validation pattern endpoints."""

    @pytest.mark.asyncio
    async def test_get_result_patterns_all(self, client, sample_result_patterns):
        """Test retrieving all result patterns."""
        response = await client.get("/api/mappings/patterns")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert all("pattern_type" in item for item in data)
        assert all("pattern_description" in item for item in data)

    @pytest.mark.asyncio
    async def test_get_result_patterns_filter_by_type(self, client, sample_result_patterns):
        """Test filtering result patterns by type."""
        response = await client.get("/api/mappings/patterns?pattern_type=empty_result")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["pattern_type"] == "empty_result"

    @pytest.mark.asyncio
    async def test_get_result_patterns_filter_by_action(self, client, sample_result_patterns):
        """Test filtering result patterns by action."""
        response = await client.get("/api/mappings/patterns?action=warn_user")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["action"] == "warn_user"

    @pytest.mark.asyncio
    async def test_mark_pattern_helpful(self, client, sample_result_patterns):
        """Test marking a pattern as helpful."""
        pattern_id = sample_result_patterns[0]["id"]

        response = await client.post(f"/api/mappings/patterns/{pattern_id}/helpful")

        assert response.status_code == 200
        data = response.json()
        assert data["pattern_id"] == pattern_id
        assert "helpful" in data["message"].lower()

        # Verify helpful count increased
        get_response = await client.get("/api/mappings/patterns")
        get_data = get_response.json()
        pattern = next((p for p in get_data if p["id"] == pattern_id), None)
        assert pattern is not None
        assert pattern["times_helpful"] == 5  # Original 4 + 1

    @pytest.mark.asyncio
    async def test_delete_result_pattern(self, client, sample_result_patterns):
        """Test deleting a result pattern."""
        pattern_id = sample_result_patterns[0]["id"]

        response = await client.delete(f"/api/mappings/patterns/{pattern_id}")

        assert response.status_code == 204  # No content

        # Verify it's deleted
        get_response = await client.get("/api/mappings/patterns")
        get_data = get_response.json()
        assert len(get_data) == 1

    @pytest.mark.asyncio
    async def test_get_result_pattern_stats(self, client, sample_result_patterns):
        """Test retrieving result pattern statistics."""
        response = await client.get("/api/mappings/patterns/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_patterns"] == 2
        assert data["total_triggers"] == 8  # 5 + 3
        assert data["total_helpful"] == 6  # 4 + 2
        assert "helpfulness_rate" in data
        assert "by_type" in data


class TestCombinedFilters:
    """Tests for combined filtering scenarios."""

    @pytest.mark.asyncio
    async def test_column_mappings_multiple_filters(self, client, sample_column_mappings):
        """Test applying multiple filters to column mappings."""
        response = await client.get(
            "/api/mappings/columns?connection_name=test_db&database_type=postgresql"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert all(item["connection_name"] == "test_db" for item in data)
        assert all(item["database_type"] == "postgresql" for item in data)

    @pytest.mark.asyncio
    async def test_empty_result_with_filters(self, client, sample_column_mappings):
        """Test that filters correctly return empty results."""
        response = await client.get("/api/mappings/columns?connection_name=nonexistent")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 0


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_limit_parameter(self, client):
        """Test invalid limit parameter."""
        response = await client.get("/api/mappings/columns?limit=1000")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_invalid_offset_parameter(self, client):
        """Test invalid offset parameter."""
        response = await client.get("/api/mappings/columns?offset=-1")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_delete_with_invalid_id(self, client):
        """Test deleting with an invalid ID format."""
        response = await client.delete("/api/mappings/columns/invalid")

        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
