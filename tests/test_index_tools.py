"""
Tests for Index Analysis Tools

Tests the 4 index recommendation tools:
- AnalyzeSlowQueryTool
- CheckExistingIndexesTool
- RecommendIndexTool
- ValidateIndexImpactTool
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.index_tools import (
    AnalyzeSlowQueryTool,
    CheckExistingIndexesTool,
    RecommendIndexTool,
    ValidateIndexImpactTool,
)


class TestAnalyzeSlowQueryTool:
    """Tests for AnalyzeSlowQueryTool"""

    @pytest.mark.asyncio
    async def test_build_explain_query_postgresql(self):
        """Test building EXPLAIN query for PostgreSQL"""
        tool = AnalyzeSlowQueryTool()
        query = "SELECT * FROM users WHERE email = 'test@example.com'"

        explain_query = tool._build_explain_query(query, "postgresql")

        assert "EXPLAIN (FORMAT JSON)" in explain_query
        assert query in explain_query

    @pytest.mark.asyncio
    async def test_build_explain_query_mysql(self):
        """Test building EXPLAIN query for MySQL"""
        tool = AnalyzeSlowQueryTool()
        query = "SELECT * FROM users WHERE id = 1"

        explain_query = tool._build_explain_query(query, "mysql")

        assert "EXPLAIN FORMAT=JSON" in explain_query

    @pytest.mark.asyncio
    async def test_build_explain_query_sqlite(self):
        """Test building EXPLAIN query for SQLite"""
        tool = AnalyzeSlowQueryTool()
        query = "SELECT * FROM products"

        explain_query = tool._build_explain_query(query, "sqlite")

        assert "EXPLAIN QUERY PLAN" in explain_query

    @pytest.mark.asyncio
    async def test_parse_sqlite_explain_sequential_scan(self):
        """Test parsing SQLite EXPLAIN output with sequential scan"""
        tool = AnalyzeSlowQueryTool()

        mock_result = [
            {"detail": "SCAN TABLE users"},
            {"detail": "USE TEMP B-TREE FOR ORDER BY"},
        ]

        analysis = tool._parse_sqlite_explain(mock_result)

        assert analysis["is_slow"] is True
        assert len(analysis["sequential_scans"]) == 1
        assert analysis["sequential_scans"][0]["table"] == "users"

    @pytest.mark.asyncio
    async def test_parse_sqlite_explain_index_scan(self):
        """Test parsing SQLite EXPLAIN with index scan (not slow)"""
        tool = AnalyzeSlowQueryTool()

        mock_result = [
            {"detail": "SEARCH TABLE users USING INDEX idx_email"},
        ]

        analysis = tool._parse_sqlite_explain(mock_result)

        assert analysis["is_slow"] is False
        assert len(analysis["sequential_scans"]) == 0

    @pytest.mark.asyncio
    async def test_analyze_sql_statically(self):
        """Test static SQL analysis fallback"""
        tool = AnalyzeSlowQueryTool()

        query = "SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending'"

        analysis = tool._analyze_sql_statically(query)

        assert "static_analysis" in analysis
        assert len(analysis["recommendations"]) > 0
        assert "customer_id" in analysis["recommendations"][0] or "status" in analysis["recommendations"][0]

    @pytest.mark.asyncio
    async def test_execute_without_context(self):
        """Test execution fails gracefully without database context"""
        tool = AnalyzeSlowQueryTool()

        result = await tool.execute(
            query_sql="SELECT * FROM users",
            database_type="postgresql"
        )

        assert not result.success
        assert result.error_type == "missing_context"


class TestCheckExistingIndexesTool:
    """Tests for CheckExistingIndexesTool"""

    @pytest.mark.asyncio
    async def test_build_index_query_postgresql(self):
        """Test building index query for PostgreSQL"""
        tool = CheckExistingIndexesTool()

        query = tool._build_index_query("users", "postgresql")

        assert "pg_class" in query
        assert "pg_index" in query
        assert "users" in query

    @pytest.mark.asyncio
    async def test_build_index_query_mysql(self):
        """Test building index query for MySQL"""
        tool = CheckExistingIndexesTool()

        query = tool._build_index_query("products", "mysql")

        assert "SHOW INDEXES FROM" in query
        assert "products" in query

    @pytest.mark.asyncio
    async def test_build_index_query_sqlite(self):
        """Test building index query for SQLite"""
        tool = CheckExistingIndexesTool()

        query = tool._build_index_query("orders", "sqlite")

        assert "PRAGMA index_list" in query
        assert "orders" in query

    @pytest.mark.asyncio
    async def test_parse_index_results_postgresql(self):
        """Test parsing PostgreSQL index results"""
        tool = CheckExistingIndexesTool()

        mock_results = [
            {
                "index_name": "idx_users_email",
                "column_name": "email",
                "is_unique": True,
                "index_type": "btree"
            },
            {
                "index_name": "idx_users_created",
                "column_name": "created_at",
                "is_unique": False,
                "index_type": "btree"
            },
        ]

        indexes = tool._parse_index_results(mock_results, "postgresql")

        assert len(indexes) == 2
        assert indexes[0]["name"] == "idx_users_email"
        assert indexes[0]["unique"] is True
        assert "email" in indexes[0]["columns"]

    @pytest.mark.asyncio
    async def test_execute_without_context(self):
        """Test execution fails without database context"""
        tool = CheckExistingIndexesTool()

        result = await tool.execute(
            table_name="users",
            database_type="postgresql"
        )

        assert not result.success
        assert result.error_type == "missing_context"


class TestRecommendIndexTool:
    """Tests for RecommendIndexTool"""

    @pytest.mark.asyncio
    async def test_extract_index_columns_simple_where(self):
        """Test extracting columns from simple WHERE clause"""
        tool = RecommendIndexTool()

        query = "SELECT * FROM users WHERE email = 'test@example.com'"

        columns = tool._extract_index_columns(query, "users")

        assert "email" in columns

    @pytest.mark.asyncio
    async def test_extract_index_columns_multiple_conditions(self):
        """Test extracting columns from multiple WHERE conditions"""
        tool = RecommendIndexTool()

        query = "SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending' AND created_at > '2024-01-01'"

        columns = tool._extract_index_columns(query, "orders")

        assert "customer_id" in columns
        assert "status" in columns
        assert "created_at" in columns

    @pytest.mark.asyncio
    async def test_extract_index_columns_with_order_by(self):
        """Test extracting ORDER BY column for index"""
        tool = RecommendIndexTool()

        query = "SELECT * FROM products WHERE category = 'electronics' ORDER BY price"

        columns = tool._extract_index_columns(query, "products")

        assert "category" in columns
        assert "price" in columns

    @pytest.mark.asyncio
    async def test_extract_index_columns_limit_to_five(self):
        """Test that column extraction limits to 5 columns"""
        tool = RecommendIndexTool()

        query = "SELECT * FROM logs WHERE col1 = 1 AND col2 = 2 AND col3 = 3 AND col4 = 4 AND col5 = 5 AND col6 = 6"

        columns = tool._extract_index_columns(query, "logs")

        assert len(columns) <= 5

    @pytest.mark.asyncio
    async def test_generate_create_index_sql_postgresql(self):
        """Test generating CREATE INDEX for PostgreSQL"""
        tool = RecommendIndexTool()

        create_sql = tool._generate_create_index_sql(
            "idx_users_email",
            "users",
            ["email"],
            "postgresql"
        )

        assert "CREATE INDEX idx_users_email ON users (email)" == create_sql

    @pytest.mark.asyncio
    async def test_generate_create_index_sql_multi_column(self):
        """Test generating multi-column index"""
        tool = RecommendIndexTool()

        create_sql = tool._generate_create_index_sql(
            "idx_orders_customer_status",
            "orders",
            ["customer_id", "status"],
            "postgresql"
        )

        assert "customer_id, status" in create_sql

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful index recommendation"""
        tool = RecommendIndexTool()

        result = await tool.execute(
            query_sql="SELECT * FROM users WHERE email = 'test@example.com'",
            table_name="users",
            database_type="postgresql"
        )

        assert result.success
        assert "index_name" in result.data
        assert "create_sql" in result.data
        assert "drop_sql" in result.data
        assert "email" in result.data["columns"]

    @pytest.mark.asyncio
    async def test_execute_no_suitable_columns(self):
        """Test when no suitable columns found for indexing"""
        tool = RecommendIndexTool()

        result = await tool.execute(
            query_sql="SELECT * FROM users",
            table_name="users",
            database_type="postgresql"
        )

        assert result.success
        assert result.data["recommendation"] is None


class TestValidateIndexImpactTool:
    """Tests for ValidateIndexImpactTool"""

    @pytest.mark.asyncio
    async def test_execute_returns_impact_estimate(self):
        """Test that validation returns impact estimate"""
        tool = ValidateIndexImpactTool()

        result = await tool.execute(
            query_sql="SELECT * FROM users WHERE email = 'test@example.com'",
            proposed_index_sql="CREATE INDEX idx_users_email ON users (email)",
            database_type="postgresql"
        )

        assert result.success
        assert "current_cost" in result.data
        assert "projected_cost" in result.data
        assert "improvement_pct" in result.data
        assert "confidence" in result.data

    @pytest.mark.asyncio
    async def test_execute_shows_estimated_metadata(self):
        """Test that validation marks results as estimated"""
        tool = ValidateIndexImpactTool()

        result = await tool.execute(
            query_sql="SELECT * FROM products WHERE category = 'electronics'",
            proposed_index_sql="CREATE INDEX idx_products_category ON products (category)",
            database_type="mysql"
        )

        assert result.success
        assert result.metadata.get("estimated") is True

    @pytest.mark.asyncio
    async def test_execute_calculates_improvement(self):
        """Test that improvement percentage is calculated"""
        tool = ValidateIndexImpactTool()

        result = await tool.execute(
            query_sql="SELECT * FROM orders WHERE status = 'pending'",
            proposed_index_sql="CREATE INDEX idx_orders_status ON orders (status)",
            database_type="sqlite"
        )

        assert result.success
        improvement = result.data["improvement_pct"]
        assert improvement > 0
        assert improvement <= 100


class TestIndexToolsIntegration:
    """Integration tests for index tools working together"""

    @pytest.mark.asyncio
    async def test_tool_workflow(self):
        """Test typical workflow: analyze -> check -> recommend -> validate"""
        # 1. Analyze slow query
        analyze_tool = AnalyzeSlowQueryTool()
        query = "SELECT * FROM users WHERE email = 'test@example.com'"

        # Static analysis (no DB context)
        analysis = analyze_tool._analyze_sql_statically(query)
        assert len(analysis["recommendations"]) > 0

        # 2. Recommend index
        recommend_tool = RecommendIndexTool()
        recommendation = await recommend_tool.execute(
            query_sql=query,
            table_name="users",
            database_type="postgresql"
        )

        assert recommendation.success
        assert "create_sql" in recommendation.data

        # 3. Validate impact
        validate_tool = ValidateIndexImpactTool()
        validation = await validate_tool.execute(
            query_sql=query,
            proposed_index_sql=recommendation.data["create_sql"],
            database_type="postgresql"
        )

        assert validation.success
        assert validation.data["improvement_pct"] > 0
