"""
Tests for QueryPatternAnalyzer (Phase 11.5)

Covers:
- Table usage frequency counting
- JOIN pattern detection and symmetry
- Performance bottleneck identification
- Time range filtering
- Connection ID scoping
- Empty history handling
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, QueryHistory
from src.lineage.query_pattern_analyzer import (
    QueryPatternAnalyzer,
    TableUsageEntry,
    JoinPattern,
    PerformanceBottleneck,
)


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory database with seeded query history."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed with various query patterns
        queries = [
            QueryHistory(
                natural_language_query="Show all orders",
                generated_sql="SELECT * FROM orders",
                executed=True,
                execution_time_ms=120.0,
                connection_id=1,
                created_at=datetime.utcnow() - timedelta(days=5),
            ),
            QueryHistory(
                natural_language_query="Get orders with customers",
                generated_sql="SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
                executed=True,
                execution_time_ms=250.0,
                connection_id=1,
                created_at=datetime.utcnow() - timedelta(days=3),
            ),
            QueryHistory(
                natural_language_query="Orders with products",
                generated_sql="SELECT o.id, p.name FROM orders o JOIN products p ON o.product_id = p.id",
                executed=True,
                execution_time_ms=180.0,
                connection_id=1,
                created_at=datetime.utcnow() - timedelta(days=2),
            ),
            QueryHistory(
                natural_language_query="Full order details",
                generated_sql="SELECT o.id, c.name, p.title FROM orders o JOIN customers c ON o.customer_id = c.id JOIN products p ON o.product_id = p.id",
                executed=True,
                execution_time_ms=500.0,
                connection_id=1,
                created_at=datetime.utcnow() - timedelta(days=1),
            ),
            QueryHistory(
                natural_language_query="Show products",
                generated_sql="SELECT * FROM products",
                executed=True,
                execution_time_ms=50.0,
                connection_id=2,
                created_at=datetime.utcnow() - timedelta(days=10),
            ),
            QueryHistory(
                natural_language_query="Old query",
                generated_sql="SELECT * FROM archive",
                executed=True,
                execution_time_ms=30.0,
                connection_id=1,
                created_at=datetime.utcnow() - timedelta(days=100),
            ),
            # Non-executed query (should be excluded)
            QueryHistory(
                natural_language_query="Draft query",
                generated_sql="SELECT * FROM drafts",
                executed=False,
                connection_id=1,
            ),
        ]
        session.add_all(queries)
        await session.commit()

        yield session

    await engine.dispose()


@pytest.fixture
def analyzer():
    return QueryPatternAnalyzer()


class TestTableUsageFrequency:
    @pytest.mark.asyncio
    async def test_counts_all_tables(self, analyzer, db_session):
        result = await analyzer.get_table_usage_frequency(db_session)
        assert "orders" in result
        assert result["orders"] == 4  # Referenced in 4 queries

    @pytest.mark.asyncio
    async def test_excludes_non_executed(self, analyzer, db_session):
        result = await analyzer.get_table_usage_frequency(db_session)
        assert "drafts" not in result

    @pytest.mark.asyncio
    async def test_connection_id_filter(self, analyzer, db_session):
        result = await analyzer.get_table_usage_frequency(db_session, connection_id=2)
        assert "products" in result
        assert "orders" not in result

    @pytest.mark.asyncio
    async def test_time_range_filter(self, analyzer, db_session):
        result = await analyzer.get_table_usage_frequency(db_session, time_range_days=7)
        assert "orders" in result
        assert "archive" not in result  # 100 days old

    @pytest.mark.asyncio
    async def test_empty_result(self, analyzer, db_session):
        result = await analyzer.get_table_usage_frequency(db_session, connection_id=999)
        assert result == {}


class TestJoinPatterns:
    @pytest.mark.asyncio
    async def test_detects_join_pairs(self, analyzer, db_session):
        result = await analyzer.get_common_join_patterns(db_session)
        pair_tuples = [(j.table_a, j.table_b) for j in result]
        # orders-customers should be detected (appears in 2 queries)
        assert ("customers", "orders") in pair_tuples or ("orders", "customers") in pair_tuples

    @pytest.mark.asyncio
    async def test_symmetry(self, analyzer, db_session):
        """Pairs are normalized: sorted alphabetically."""
        result = await analyzer.get_common_join_patterns(db_session)
        for jp in result:
            assert jp.table_a <= jp.table_b, f"Pair not sorted: {jp.table_a}, {jp.table_b}"

    @pytest.mark.asyncio
    async def test_ranks_by_frequency(self, analyzer, db_session):
        result = await analyzer.get_common_join_patterns(db_session)
        if len(result) > 1:
            assert result[0].join_count >= result[1].join_count

    @pytest.mark.asyncio
    async def test_includes_sample_sql(self, analyzer, db_session):
        result = await analyzer.get_common_join_patterns(db_session)
        for jp in result:
            assert jp.sample_sql != ""

    @pytest.mark.asyncio
    async def test_no_joins_returns_empty(self, analyzer, db_session):
        result = await analyzer.get_common_join_patterns(db_session, connection_id=2)
        assert result == []


class TestBottlenecks:
    @pytest.mark.asyncio
    async def test_identifies_bottlenecks(self, analyzer, db_session):
        result = await analyzer.identify_bottlenecks(db_session, min_query_count=2)
        assert len(result) > 0
        # orders has 4 queries with high avg time
        table_names = [b.table_name for b in result]
        assert "orders" in table_names

    @pytest.mark.asyncio
    async def test_score_ranking(self, analyzer, db_session):
        result = await analyzer.identify_bottlenecks(db_session, min_query_count=2)
        if len(result) > 1:
            assert result[0].bottleneck_score >= result[1].bottleneck_score

    @pytest.mark.asyncio
    async def test_excludes_low_frequency(self, analyzer, db_session):
        result = await analyzer.identify_bottlenecks(db_session, min_query_count=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_score_between_0_and_1(self, analyzer, db_session):
        result = await analyzer.identify_bottlenecks(db_session, min_query_count=2)
        for b in result:
            assert 0 <= b.bottleneck_score <= 1


class TestHeatmapData:
    @pytest.mark.asyncio
    async def test_returns_all_sections(self, analyzer, db_session):
        result = await analyzer.get_heatmap_data(db_session)
        assert len(result.table_usage) > 0
        assert result.total_queries_analyzed > 0

    @pytest.mark.asyncio
    async def test_table_usage_sorted_by_count(self, analyzer, db_session):
        result = await analyzer.get_heatmap_data(db_session)
        counts = [t.query_count for t in result.table_usage]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    async def test_time_range_passed_through(self, analyzer, db_session):
        result = await analyzer.get_heatmap_data(db_session, time_range_days=30)
        assert result.time_range_days == 30

    @pytest.mark.asyncio
    async def test_connection_id_passed_through(self, analyzer, db_session):
        result = await analyzer.get_heatmap_data(db_session, connection_id=1)
        assert result.connection_id == 1

    @pytest.mark.asyncio
    async def test_empty_history(self, analyzer, db_session):
        result = await analyzer.get_heatmap_data(db_session, connection_id=999)
        assert result.table_usage == []
        assert result.join_patterns == []
        assert result.bottlenecks == []
        assert result.total_queries_analyzed == 0


class TestHeatmapDataIntegration:
    """Test the combined get_heatmap_data() method."""

    @pytest.mark.asyncio
    async def test_heatmap_data_structure(self, analyzer, db_session):
        """Verify heatmap data has all required fields."""
        data = await analyzer.get_heatmap_data(
            db_session,
            connection_id=1,
            time_range_days=30
        )

        # Verify structure
        assert hasattr(data, 'table_usage')
        assert hasattr(data, 'join_patterns')
        assert hasattr(data, 'bottlenecks')

        # Verify types
        assert all(isinstance(t, TableUsageEntry) for t in data.table_usage)
        assert all(isinstance(j, JoinPattern) for j in data.join_patterns)
        assert all(isinstance(b, PerformanceBottleneck) for b in data.bottlenecks)

    @pytest.mark.asyncio
    async def test_bottleneck_score_range(self, analyzer, db_session):
        """Verify bottleneck scores are in 0-1 range."""
        data = await analyzer.get_heatmap_data(db_session, connection_id=1)

        for bottleneck in data.bottlenecks:
            assert 0.0 <= bottleneck.bottleneck_score <= 1.0


class TestTimeRangeFiltering:
    """Test time range filtering accuracy."""

    @pytest.mark.asyncio
    async def test_7_day_filter(self, analyzer, db_session):
        """Verify 7-day filter excludes older queries."""
        # Get data for 7 days
        data_7 = await analyzer.get_heatmap_data(db_session, time_range_days=7)

        # Get data for 30 days
        data_30 = await analyzer.get_heatmap_data(db_session, time_range_days=30)

        # 30-day should have >= 7-day counts
        assert sum(t.query_count for t in data_30.table_usage) >= sum(t.query_count for t in data_7.table_usage)

