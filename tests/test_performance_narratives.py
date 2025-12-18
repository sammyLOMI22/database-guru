"""Performance testing for narrative generation with latency measurement"""
import asyncio
import time
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock

from src.llm.result_narrator import ResultNarrator, NarrativeResult
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
    """Mock Ollama client for fast testing"""
    client = AsyncMock()
    response_json = {
        "summary": "Test summary",
        "key_insights": ["Insight 1", "Insight 2"],
        "direct_answer": None,
        "confidence": 0.85
    }
    client.generate = AsyncMock(return_value={
        "response": json.dumps(response_json)
    })
    return client


@pytest.mark.asyncio
async def test_narrative_generation_latency_small_dataset(mock_ollama, db_session):
    """Measure latency for small dataset (5 rows, no anomalies)"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    results = [
        {"id": 1, "value": 100, "date": "2024-01-01"},
        {"id": 2, "value": 105, "date": "2024-01-02"},
        {"id": 3, "value": 110, "date": "2024-01-03"},
        {"id": 4, "value": 108, "date": "2024-01-04"},
        {"id": 5, "value": 103, "date": "2024-01-05"},
    ]

    start_time = time.time()
    narrative = await narrator.generate_narrative(
        question="What is the trend?",
        sql="SELECT * FROM test",
        results=results,
        row_count=5,
        execution_time_ms=50
    )
    elapsed = time.time() - start_time

    # Should complete in < 1 second (excluding LLM latency)
    assert elapsed < 1.0, f"Expected < 1.0s, got {elapsed:.3f}s"
    assert narrative.summary
    assert narrative.confidence > 0


@pytest.mark.asyncio
async def test_narrative_generation_latency_medium_dataset(mock_ollama, db_session):
    """Measure latency for medium dataset (20 rows with anomaly)"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Create 20 rows with one outlier
    results = [
        {"id": i, "value": 100 + (i % 5), "date": f"2024-01-{str(i).zfill(2)}"}
        for i in range(1, 20)
    ]
    results.append({"id": 20, "value": 9999, "date": "2024-01-20"})  # Outlier

    start_time = time.time()
    narrative = await narrator.generate_narrative(
        question="Show trends",
        sql="SELECT * FROM test",
        results=results,
        row_count=20,
        execution_time_ms=75
    )
    elapsed = time.time() - start_time

    # Should complete in < 1.5 seconds
    assert elapsed < 1.5, f"Expected < 1.5s, got {elapsed:.3f}s"
    assert narrative.confidence > 0


@pytest.mark.asyncio
async def test_narrative_generation_latency_all_features(mock_ollama, db_session):
    """Measure latency with all advanced features enabled"""
    narrator = ResultNarrator(
        ollama_client=mock_ollama,
        db_session=db_session,
        enable_statistics=True
    )

    # Create dataset triggering all features
    results = [
        {"id": i, "sales": 1000 + (i * 50), "marketing": 500 + (i * 20), "date": f"2024-01-{str(i).zfill(2)}"}
        for i in range(1, 21)
    ]
    # Add anomalies
    results.append({"id": 21, "sales": 50000, "marketing": 100, "date": "2024-01-21"})

    start_time = time.time()
    narrative = await narrator.generate_narrative(
        question="Analyze sales and marketing relationship",
        sql="SELECT id, sales, marketing, date FROM test ORDER BY date",
        results=results,
        row_count=21,
        execution_time_ms=100
    )
    elapsed = time.time() - start_time

    # All features should complete in < 2 seconds
    assert elapsed < 2.0, f"Expected < 2.0s, got {elapsed:.3f}s"
    assert narrative.confidence > 0
    # Should have basic statistics or advanced findings
    # (may be empty if LLM response parsing fails gracefully)
    assert narrative.summary is not None


@pytest.mark.asyncio
async def test_anomaly_detection_performance(mock_ollama, db_session):
    """Measure anomaly detection performance on large numeric dataset"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Create 100 numeric values
    results = [{"value": 100 + (i % 50)} for i in range(100)]
    results.append({"value": 9999})  # Add outlier

    start_time = time.time()
    anomalies = narrator._detect_anomalies(results)
    elapsed = time.time() - start_time

    # Should complete in < 100ms
    assert elapsed < 0.1, f"Expected < 100ms, got {elapsed*1000:.1f}ms"
    assert anomalies.get("anomalies_found") is True
    assert anomalies.get("anomaly_count") > 0


@pytest.mark.asyncio
async def test_trend_detection_performance(mock_ollama, db_session):
    """Measure trend detection performance on time-series data"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Create 50 time-series points
    results = [
        {"date": f"2024-01-{str(i).zfill(2)}", "value": 1000 + (i * 50)}
        for i in range(1, 51)
    ]

    start_time = time.time()
    temporal_cols = narrator._detect_temporal_columns(results)
    trends = narrator._detect_trends(results, temporal_cols)
    elapsed = time.time() - start_time

    # Should complete in < 150ms
    assert elapsed < 0.15, f"Expected < 150ms, got {elapsed*1000:.1f}ms"


@pytest.mark.asyncio
async def test_correlation_detection_performance(mock_ollama, db_session):
    """Measure correlation detection performance on multi-column data"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Create 50 rows with correlated columns
    results = [
        {
            "col_a": 1000 + (i * 50),
            "col_b": 500 + (i * 25),
            "col_c": i * 10
        }
        for i in range(1, 51)
    ]

    start_time = time.time()
    correlations = narrator._calculate_correlations(results)
    elapsed = time.time() - start_time

    # Should complete in < 100ms
    assert elapsed < 0.1, f"Expected < 100ms, got {elapsed*1000:.1f}ms"


@pytest.mark.asyncio
async def test_statistics_extraction_performance(mock_ollama, db_session):
    """Measure statistics extraction performance"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    # Create large result set
    results = [
        {"id": i, "value": 100 + (i % 50), "category": f"cat_{i % 5}"}
        for i in range(1, 101)
    ]

    start_time = time.time()
    stats = narrator._extract_statistics(results[:20])
    elapsed = time.time() - start_time

    # Should complete in < 50ms
    assert elapsed < 0.05, f"Expected < 50ms, got {elapsed*1000:.1f}ms"


@pytest.mark.asyncio
async def test_large_result_sampling(mock_ollama, db_session):
    """Test performance with large result set (>20 rows, should sample)"""
    narrator = ResultNarrator(
        ollama_client=mock_ollama,
        db_session=db_session,
        max_sample_rows=20
    )

    # Create 100 rows
    results = [
        {"id": i, "value": 100 + (i % 50), "date": f"2024-01-{str((i % 28) + 1).zfill(2)}"}
        for i in range(1, 101)
    ]

    start_time = time.time()
    narrative = await narrator.generate_narrative(
        question="Show all data",
        sql="SELECT * FROM test",
        results=results,
        row_count=100,
        execution_time_ms=200
    )
    elapsed = time.time() - start_time

    # Should sample first 20 and complete in < 1.5 seconds
    assert elapsed < 1.5, f"Expected < 1.5s, got {elapsed:.3f}s"
    assert narrative.confidence > 0


@pytest.mark.asyncio
async def test_narrative_latency_breakdown(mock_ollama, db_session):
    """Detailed latency breakdown of narrative generation components"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    results = [
        {"id": i, "value": 100 + (i % 20), "date": f"2024-01-{str(i).zfill(2)}"}
        for i in range(1, 16)
    ]

    # Statistics extraction
    start = time.time()
    stats = narrator._extract_statistics(results[:20])
    stats_time = time.time() - start
    assert stats_time < 0.05

    # Anomaly detection
    start = time.time()
    anomalies = narrator._detect_anomalies(results)
    anomaly_time = time.time() - start
    assert anomaly_time < 0.05

    # Temporal detection
    start = time.time()
    temporal = narrator._detect_temporal_columns(results)
    temporal_time = time.time() - start
    assert temporal_time < 0.01

    # Trend detection (if temporal columns found)
    start = time.time()
    trends = narrator._detect_trends(results, temporal) if temporal else {}
    trend_time = time.time() - start
    assert trend_time < 0.1

    # Correlation
    start = time.time()
    correlations = narrator._calculate_correlations(results)
    corr_time = time.time() - start
    assert corr_time < 0.05

    # Total for all features should be < 300ms
    total_time = stats_time + anomaly_time + temporal_time + trend_time + corr_time
    assert total_time < 0.3, f"Total analysis time: {total_time*1000:.1f}ms"


@pytest.mark.asyncio
async def test_empty_results_performance(mock_ollama, db_session):
    """Test performance with empty results (should be instant)"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    start_time = time.time()
    narrative = await narrator.generate_narrative(
        question="Show data",
        sql="SELECT * FROM test WHERE 1=0",
        results=[],
        row_count=0,
        execution_time_ms=10
    )
    elapsed = time.time() - start_time

    # Should complete almost instantly
    assert elapsed < 0.5, f"Expected < 500ms, got {elapsed*1000:.1f}ms"


@pytest.mark.asyncio
async def test_null_values_performance(mock_ollama, db_session):
    """Test performance with NULL values in data"""
    narrator = ResultNarrator(ollama_client=mock_ollama, db_session=db_session)

    results = [
        {"id": 1, "value": 100, "category": "A"},
        {"id": 2, "value": None, "category": "B"},
        {"id": 3, "value": 110, "category": None},
        {"id": 4, "value": None, "category": "A"},
        {"id": 5, "value": 105, "category": "B"},
    ]

    start_time = time.time()
    narrative = await narrator.generate_narrative(
        question="Analyze data",
        sql="SELECT * FROM test",
        results=results,
        row_count=5,
        execution_time_ms=30
    )
    elapsed = time.time() - start_time

    # Should handle NULLs efficiently in < 1 second
    assert elapsed < 1.0, f"Expected < 1.0s, got {elapsed:.3f}s"


if __name__ == "__main__":
    # Run performance tests: pytest tests/test_performance_narratives.py -v
    pytest.main([__file__, "-v"])
