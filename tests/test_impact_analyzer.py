"""
Tests for Impact Analyzer

Covers:
- Column impact with seeded query_history
- Table impact scanning
- Risk level classification
- No matching queries (empty result)
"""

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, QueryHistory
from src.lineage.impact_analyzer import ImpactAnalyzer, RiskLevel


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory database with seeded query history."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed query history with various queries
        queries = [
            QueryHistory(
                natural_language_query="Show all customers",
                generated_sql="SELECT * FROM customers",
                executed=True,
            ),
            QueryHistory(
                natural_language_query="Get customer names",
                generated_sql="SELECT name, email FROM customers WHERE status = 'active'",
                executed=True,
            ),
            QueryHistory(
                natural_language_query="Show orders with customer info",
                generated_sql="SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
                executed=True,
            ),
            QueryHistory(
                natural_language_query="Count orders by status",
                generated_sql="SELECT status, COUNT(*) FROM orders GROUP BY status",
                executed=True,
            ),
            QueryHistory(
                natural_language_query="Get product prices",
                generated_sql="SELECT name, price FROM products ORDER BY price DESC",
                executed=True,
            ),
            QueryHistory(
                natural_language_query="Total revenue",
                generated_sql="SELECT SUM(total) AS revenue FROM orders WHERE status = 'completed'",
                executed=True,
            ),
            QueryHistory(
                natural_language_query="Customer order history",
                generated_sql="SELECT c.name, o.id, o.total FROM customers c LEFT JOIN orders o ON c.id = o.customer_id",
                executed=True,
            ),
            # Not executed - should be excluded
            QueryHistory(
                natural_language_query="Draft query",
                generated_sql="SELECT * FROM customers",
                executed=False,
            ),
            # Substring trap: "customer_orders" contains "orders" as substring
            QueryHistory(
                natural_language_query="Customer order join table",
                generated_sql="SELECT * FROM customer_orders WHERE created_at > '2024-01-01'",
                executed=True,
            ),
            # Substring trap: "orders_archive" contains "orders" as substring
            QueryHistory(
                natural_language_query="Archived orders",
                generated_sql="SELECT * FROM orders_archive LIMIT 100",
                executed=True,
            ),
        ]

        for q in queries:
            session.add(q)
        await session.commit()

        yield session

    await engine.dispose()


@pytest.fixture
def analyzer():
    return ImpactAnalyzer()


# =============================================================================
# Table Impact Tests
# =============================================================================

class TestTableImpact:
    @pytest.mark.asyncio
    async def test_table_with_multiple_references(self, analyzer, db_session):
        """Customers table is referenced in multiple queries."""
        analysis = await analyzer.analyze_table_impact(db_session, "customers")

        assert analysis.total_affected >= 3  # At least 3 queries reference customers
        assert analysis.object_type == "table"
        assert analysis.changed_object == "customers"

    @pytest.mark.asyncio
    async def test_table_with_few_references(self, analyzer, db_session):
        """Products table has fewer references."""
        analysis = await analyzer.analyze_table_impact(db_session, "products")

        assert analysis.total_affected >= 1
        assert analysis.risk_level == RiskLevel.LOW.value

    @pytest.mark.asyncio
    async def test_table_not_referenced(self, analyzer, db_session):
        """Table with no references."""
        analysis = await analyzer.analyze_table_impact(db_session, "nonexistent_table")

        assert analysis.total_affected == 0
        assert analysis.risk_level == RiskLevel.LOW.value
        assert "Safe to modify" in analysis.summary

    @pytest.mark.asyncio
    async def test_table_impact_excludes_unexecuted(self, analyzer, db_session):
        """Should not include queries that weren't executed."""
        analysis = await analyzer.analyze_table_impact(db_session, "customers")

        # The unexecuted query should not be in results
        for q in analysis.impacted_queries:
            assert q.natural_language_query != "Draft query"

    @pytest.mark.asyncio
    async def test_orders_table_references(self, analyzer, db_session):
        """Orders table is heavily referenced."""
        analysis = await analyzer.analyze_table_impact(db_session, "orders")

        assert analysis.total_affected >= 3
        assert analysis.object_type == "table"


# =============================================================================
# Column Impact Tests
# =============================================================================

class TestColumnImpact:
    @pytest.mark.asyncio
    async def test_column_impact_name(self, analyzer, db_session):
        """The 'name' column in customers is used in several queries."""
        analysis = await analyzer.analyze_column_impact(db_session, "customers", "name")

        assert analysis.total_affected >= 2
        assert analysis.object_type == "column"
        assert analysis.changed_object == "customers.name"

    @pytest.mark.asyncio
    async def test_column_impact_status(self, analyzer, db_session):
        """The 'status' column is used in WHERE and GROUP BY."""
        analysis = await analyzer.analyze_column_impact(db_session, "orders", "status")

        assert analysis.total_affected >= 1
        # Should detect filter/group impact types
        impact_types = [q.impact_type for q in analysis.impacted_queries]
        assert len(impact_types) >= 1

    @pytest.mark.asyncio
    async def test_column_not_referenced(self, analyzer, db_session):
        """Column with no references."""
        analysis = await analyzer.analyze_column_impact(db_session, "customers", "zzz_unused_column")

        assert analysis.total_affected == 0

    @pytest.mark.asyncio
    async def test_column_impact_price(self, analyzer, db_session):
        """Price column in products."""
        analysis = await analyzer.analyze_column_impact(db_session, "products", "price")

        assert analysis.total_affected >= 1
        assert analysis.changed_object == "products.price"


# =============================================================================
# Risk Level Tests
# =============================================================================

class TestRiskLevels:
    @pytest.mark.asyncio
    async def test_low_risk(self, analyzer, db_session):
        """Few affected queries = low risk."""
        analysis = await analyzer.analyze_table_impact(db_session, "products")

        assert analysis.risk_level == RiskLevel.LOW.value

    @pytest.mark.asyncio
    async def test_risk_counts_structure(self, analyzer, db_session):
        """Risk counts should have all levels."""
        analysis = await analyzer.analyze_table_impact(db_session, "customers")

        assert "low" in analysis.risk_counts
        assert "medium" in analysis.risk_counts
        assert "high" in analysis.risk_counts

    def test_assess_risk_boundaries(self, analyzer):
        """Test risk assessment thresholds."""
        assert analyzer._assess_risk(0) == RiskLevel.LOW.value
        assert analyzer._assess_risk(4) == RiskLevel.LOW.value
        assert analyzer._assess_risk(5) == RiskLevel.MEDIUM.value
        assert analyzer._assess_risk(20) == RiskLevel.MEDIUM.value
        assert analyzer._assess_risk(21) == RiskLevel.HIGH.value


# =============================================================================
# False Positive Prevention Tests
# =============================================================================

class TestFalsePositivePrevention:
    @pytest.mark.asyncio
    async def test_no_substring_match_prefix(self, analyzer, db_session):
        """'orders' should NOT match 'customer_orders' (prefix substring)."""
        analysis = await analyzer.analyze_table_impact(db_session, "orders")

        matched_sqls = [q.generated_sql for q in analysis.impacted_queries]
        for sql in matched_sqls:
            assert "customer_orders" not in sql

    @pytest.mark.asyncio
    async def test_no_substring_match_suffix(self, analyzer, db_session):
        """'orders' should NOT match 'orders_archive' (suffix substring)."""
        analysis = await analyzer.analyze_table_impact(db_session, "orders")

        matched_sqls = [q.generated_sql for q in analysis.impacted_queries]
        for sql in matched_sqls:
            assert "orders_archive" not in sql

    @pytest.mark.asyncio
    async def test_exact_table_still_matches(self, analyzer, db_session):
        """'orders' should still match queries that actually use 'orders' table."""
        analysis = await analyzer.analyze_table_impact(db_session, "orders")

        # Should match: "FROM orders o JOIN", "FROM orders GROUP BY", "FROM orders WHERE"
        assert analysis.total_affected >= 3

    @pytest.mark.asyncio
    async def test_qualified_name_matches(self, analyzer, db_session):
        """Table name after a dot (schema.table) should still match."""
        analysis = await analyzer.analyze_table_impact(db_session, "customer_id")

        # customer_id appears as o.customer_id and c.id in JOIN queries
        assert analysis.total_affected >= 1

    def test_identifier_match_word_boundary(self, analyzer):
        """Direct test of _is_identifier_match for various patterns."""
        # Should match: standalone identifier
        assert analyzer._is_identifier_match("SELECT * FROM orders", "orders")
        # Should match: with alias
        assert analyzer._is_identifier_match("FROM orders o", "orders")
        # Should match: after dot (qualified)
        assert analyzer._is_identifier_match("o.customer_id = c.id", "customer_id")
        # Should NOT match: substring of longer identifier
        assert not analyzer._is_identifier_match("FROM customer_orders", "orders")
        assert not analyzer._is_identifier_match("FROM orders_archive", "orders")
        # Should NOT match: embedded in word
        assert not analyzer._is_identifier_match("FROM reorders", "orders")

    def test_column_identifier_match(self, analyzer):
        """Column names should match as standalone identifiers."""
        assert analyzer._is_identifier_match("SELECT name FROM t", "name")
        assert not analyzer._is_identifier_match("SELECT username FROM t", "name")
        assert not analyzer._is_identifier_match("SELECT name_full FROM t", "name")


# =============================================================================
# Impact Type Detection Tests
# =============================================================================

class TestImpactTypeDetection:
    def test_select_impact(self, analyzer):
        sql = "SELECT name FROM customers"
        impact = analyzer._detect_impact_type(sql, "customers", "name")
        assert impact == "select"

    def test_filter_impact(self, analyzer):
        sql = "SELECT id FROM customers WHERE status = 'active'"
        impact = analyzer._detect_impact_type(sql, "customers", "status")
        assert impact == "filter"

    def test_join_impact(self, analyzer):
        sql = "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id"
        impact = analyzer._detect_impact_type(sql, "customers", "customer_id")
        assert impact == "join"


# =============================================================================
# Get Table Queries Tests
# =============================================================================

class TestGetTableQueries:
    @pytest.mark.asyncio
    async def test_get_queries_for_table(self, analyzer, db_session):
        queries = await analyzer.get_queries_for_table(db_session, "orders")

        assert len(queries) >= 3
        for q in queries:
            assert "orders" in q.generated_sql.lower()

    @pytest.mark.asyncio
    async def test_get_queries_empty(self, analyzer, db_session):
        queries = await analyzer.get_queries_for_table(db_session, "nonexistent")

        assert len(queries) == 0


# =============================================================================
# Stats Tests
# =============================================================================

class TestLineageStats:
    @pytest.mark.asyncio
    async def test_get_stats(self, analyzer, db_session):
        stats = await analyzer.get_lineage_stats(db_session)

        assert stats["total_queries"] >= 7  # 7 executed queries
        assert stats["unique_tables_referenced"] >= 2
        assert "tables" in stats
        assert isinstance(stats["tables"], list)


# =============================================================================
# Summary Tests
# =============================================================================

class TestSummary:
    @pytest.mark.asyncio
    async def test_summary_no_impact(self, analyzer, db_session):
        analysis = await analyzer.analyze_table_impact(db_session, "nonexistent")
        assert "Safe to modify" in analysis.summary

    @pytest.mark.asyncio
    async def test_summary_with_impact(self, analyzer, db_session):
        analysis = await analyzer.analyze_table_impact(db_session, "customers")
        assert "queries reference" in analysis.summary
        assert "customers" in analysis.summary


class TestRiskLevelThresholds:
    """Test risk level boundary conditions."""

    def test_risk_level_boundaries(self, analyzer):
        """Verify risk level thresholds are correct."""
        # Test the assess_risk method directly
        assert analyzer._assess_risk(21) == RiskLevel.HIGH.value
        assert analyzer._assess_risk(20) == RiskLevel.MEDIUM.value
        assert analyzer._assess_risk(5) == RiskLevel.MEDIUM.value
        assert analyzer._assess_risk(4) == RiskLevel.LOW.value
        assert analyzer._assess_risk(0) == RiskLevel.LOW.value

