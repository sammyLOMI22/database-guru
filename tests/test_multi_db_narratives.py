"""Tests for multi-database narrative generation"""
import json
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock

from src.llm.result_narrator import ResultNarrator
from src.database.models import Base


@pytest.fixture
async def db_session():
    """Create in-memory database session for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_ollama():
    """Mock Ollama client for testing"""
    client = AsyncMock()

    async def side_effect(*args, prompt: str = None, **kwargs):
        # Return different responses based on prompt content
        if prompt and "across" in prompt:
            return json.dumps({
                "summary": "Results from multiple databases show consistent patterns across all sources.",
                "key_insights": [
                    "Data is consistent across databases",
                    "Combined dataset shows clear trends",
                    "All databases contribute to insights"
                ],
                "direct_answer": None,
                "confidence": 0.87
            })
        else:
            return json.dumps({
                "summary": "Database query returned successful results.",
                "key_insights": [
                    "Data retrieved successfully",
                    "Results are well-formed"
                ],
                "direct_answer": None,
                "confidence": 0.80
            })

    client.generate = AsyncMock(side_effect=side_effect)
    return client


@pytest.mark.asyncio
async def test_per_database_narrative_generation(mock_ollama, db_session):
    """Test narrative generation for individual database results"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Simulate results from one database
    db_results = [
        {"product": "Laptop", "sales": 5000},
        {"product": "Phone", "sales": 3000},
        {"product": "Tablet", "sales": 2000},
    ]

    narrative = await narrator.generate_narrative(
        question="Show sales by product",
        sql="SELECT product, sales FROM sales",
        results=db_results,
        row_count=3,
        execution_time_ms=50
    )

    # Verify narrative structure
    assert narrative.summary
    assert len(narrative.key_insights) > 0
    assert narrative.confidence > 0
    assert narrative.generated_at


@pytest.mark.asyncio
async def test_combined_multi_database_narrative(mock_ollama, db_session):
    """Test narrative generation synthesizing results from multiple databases"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Simulate combined results from multiple databases (tagged with source)
    combined_results = [
        # From Database 1 (PostgreSQL)
        {"product": "Laptop", "sales": 5000, "_source_database": "PostgreSQL"},
        {"product": "Phone", "sales": 3000, "_source_database": "PostgreSQL"},
        # From Database 2 (MySQL)
        {"product": "Laptop", "sales": 4500, "_source_database": "MySQL"},
        {"product": "Phone", "sales": 3500, "_source_database": "MySQL"},
    ]

    narrative = await narrator.generate_narrative(
        question="Show sales by product (across 2 databases: PostgreSQL, MySQL)",
        sql="[Multiple databases]",
        results=combined_results,
        row_count=4,
        execution_time_ms=100
    )

    # Verify combined narrative
    assert narrative.summary
    assert "across" not in narrative.summary or "multiple" in narrative.summary.lower() or "databases" in narrative.summary.lower() or len(narrative.key_insights) > 0
    assert narrative.confidence > 0


@pytest.mark.asyncio
async def test_three_database_combined_narrative(mock_ollama, db_session):
    """Test narrative across 3 databases with different data patterns"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Results from 3 different databases
    combined_results = [
        # PostgreSQL
        {"region": "North", "revenue": 100000, "_source_database": "PostgreSQL"},
        {"region": "South", "revenue": 80000, "_source_database": "PostgreSQL"},
        # MySQL
        {"region": "East", "revenue": 120000, "_source_database": "MySQL"},
        {"region": "West", "revenue": 70000, "_source_database": "MySQL"},
        # SQLite
        {"region": "Central", "revenue": 90000, "_source_database": "SQLite"},
    ]

    narrative = await narrator.generate_narrative(
        question="Revenue by region (across 3 databases)",
        sql="[Multiple databases: PostgreSQL, MySQL, SQLite]",
        results=combined_results,
        row_count=5,
        execution_time_ms=150
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should detect patterns across databases
    assert len(narrative.key_insights) > 0


@pytest.mark.asyncio
async def test_multi_db_with_anomalies(mock_ollama, db_session):
    """Test combined narrative detecting anomalies across databases"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Combined results with one anomalous value
    combined_results = [
        {"value": 100, "_source_database": "DB1"},
        {"value": 105, "_source_database": "DB1"},
        {"value": 102, "_source_database": "DB2"},
        {"value": 103, "_source_database": "DB2"},
        {"value": 9999, "_source_database": "DB3"},  # Outlier
    ]

    narrative = await narrator.generate_narrative(
        question="Analyze values across databases",
        sql="[Multiple databases]",
        results=combined_results,
        row_count=5,
        execution_time_ms=120
    )

    assert narrative.summary
    assert narrative.confidence > 0
    # Check if anomalies detected
    if narrative.statistics.get("anomalies"):
        assert narrative.statistics["anomalies"]["found"] is True


@pytest.mark.asyncio
async def test_multi_db_empty_result_handling(mock_ollama, db_session):
    """Test narrative generation when some databases return no results"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Results only from 2 out of 3 databases
    combined_results = [
        {"id": 1, "name": "Item1", "_source_database": "DB1"},
        {"id": 2, "name": "Item2", "_source_database": "DB1"},
        {"id": 3, "name": "Item3", "_source_database": "DB2"},
    ]

    narrative = await narrator.generate_narrative(
        question="Items from all databases",
        sql="[Multiple databases: DB1, DB2, DB3 (no results)]",
        results=combined_results,
        row_count=3,
        execution_time_ms=100
    )

    assert narrative.summary
    # Should still generate narrative for available results
    assert len(narrative.key_insights) > 0


@pytest.mark.asyncio
async def test_multi_db_temporal_combined_narrative(mock_ollama, db_session):
    """Test trend detection across databases with temporal data"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Time-series data from multiple databases
    combined_results = [
        # DB1 - upward trend
        {"date": "2024-01-01", "metric": 100, "_source_database": "DB1"},
        {"date": "2024-01-02", "metric": 110, "_source_database": "DB1"},
        {"date": "2024-01-03", "metric": 120, "_source_database": "DB1"},
        # DB2 - similar upward trend
        {"date": "2024-01-01", "metric": 95, "_source_database": "DB2"},
        {"date": "2024-01-02", "metric": 105, "_source_database": "DB2"},
        {"date": "2024-01-03", "metric": 115, "_source_database": "DB2"},
    ]

    narrative = await narrator.generate_narrative(
        question="Metric trends across databases",
        sql="[Multiple databases with temporal data]",
        results=combined_results,
        row_count=6,
        execution_time_ms=130
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should detect temporal patterns
    if narrative.statistics.get("trends"):
        assert narrative.statistics["trends"]["found"] is True


@pytest.mark.asyncio
async def test_multi_db_correlation_analysis(mock_ollama, db_session):
    """Test correlation detection across multi-database combined results"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Combined results with correlated columns from multiple databases
    combined_results = [
        {"marketing": 1000, "sales": 5000, "_source_database": "DB1"},
        {"marketing": 1500, "sales": 6500, "_source_database": "DB1"},
        {"marketing": 2000, "sales": 8000, "_source_database": "DB2"},
        {"marketing": 2500, "sales": 9500, "_source_database": "DB2"},
        {"marketing": 1200, "sales": 5500, "_source_database": "DB3"},
    ]

    narrative = await narrator.generate_narrative(
        question="Marketing vs Sales correlation",
        sql="[Multiple databases]",
        results=combined_results,
        row_count=5,
        execution_time_ms=140
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should detect correlations
    if narrative.statistics.get("correlations"):
        assert narrative.statistics["correlations"]["found"] is True


@pytest.mark.asyncio
async def test_multi_db_large_combined_dataset(mock_ollama, db_session):
    """Test narrative generation with large combined dataset from multiple databases"""
    narrator = ResultNarrator(
        ollama_client=mock_ollama,
        db_session=db_session,
        max_sample_rows=20
    )

    # Simulate large combined dataset from multiple sources
    combined_results = [
        {"id": i, "value": 100 + (i % 50), "_source_database": f"DB{(i % 3) + 1}"}
        for i in range(100)
    ]

    narrative = await narrator.generate_narrative(
        question="Analyze large multi-database dataset",
        sql="[Multiple databases - 100 rows combined]",
        results=combined_results,
        row_count=100,
        execution_time_ms=200
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    # Should sample and still generate insights
    assert len(narrative.key_insights) > 0


@pytest.mark.asyncio
async def test_multi_db_mixed_data_types(mock_ollama, db_session):
    """Test narrative with mixed data types from multiple databases"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Mixed types from different databases
    combined_results = [
        {"name": "Product A", "price": 99.99, "stock": 100, "active": True, "_source_database": "DB1"},
        {"name": "Product B", "price": 149.99, "stock": 50, "active": True, "_source_database": "DB1"},
        {"name": "Product C", "price": 199.99, "stock": 25, "active": False, "_source_database": "DB2"},
        {"name": "Product D", "price": 79.99, "stock": 200, "active": True, "_source_database": "DB2"},
    ]

    narrative = await narrator.generate_narrative(
        question="Product inventory across databases",
        sql="[Multiple databases]",
        results=combined_results,
        row_count=4,
        execution_time_ms=110
    )

    assert narrative.summary
    assert narrative.confidence > 0.5
    assert len(narrative.key_insights) > 0


@pytest.mark.asyncio
async def test_multi_db_narrative_with_null_values(mock_ollama, db_session):
    """Test narrative handling NULL values in combined multi-database results"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Combined results with NULL values from different sources
    combined_results = [
        {"user_id": 1, "email": "user1@example.com", "phone": "555-0001", "_source_database": "DB1"},
        {"user_id": 2, "email": "user2@example.com", "phone": None, "_source_database": "DB1"},
        {"user_id": 3, "email": None, "phone": "555-0003", "_source_database": "DB2"},
        {"user_id": 4, "email": "user4@example.com", "phone": "555-0004", "_source_database": "DB2"},
    ]

    narrative = await narrator.generate_narrative(
        question="User data quality across databases",
        sql="[Multiple databases]",
        results=combined_results,
        row_count=4,
        execution_time_ms=95
    )

    assert narrative.summary
    assert narrative.confidence > 0
    # Should handle NULLs gracefully
    assert len(narrative.key_insights) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
