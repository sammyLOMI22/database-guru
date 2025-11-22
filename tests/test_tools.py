"""
Tests for Tool-Using Agent System

Tests the tool infrastructure including:
- Tool registration and registry
- Schema exploration tools
- Data sampling tools
- Query validation tools
- Tool-Using Agent integration

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.database.models import Base
from src.tools.base import (
    BaseTool,
    ToolResult,
    ToolDefinition,
    ToolCategory,
)
from src.tools.tool_registry import (
    ToolRegistry,
    get_tool_registry,
    reset_tool_registry,
)
from src.tools.schema_tools import (
    SearchSchemaTool,
    GetTableInfoTool,
    FindColumnsTool,
    GetRelationshipsTool,
)
from src.tools.data_tools import (
    GetSampleDataTool,
    GetColumnValuesTool,
    CountRowsTool,
)
from src.tools.query_tools import (
    TestQueryTool,
    ValidateSQLTool,
    ExplainQueryTool,
)
from src.tools import get_all_tools, get_tools_by_category
from src.llm.mapping_cache import reset_mapping_cache


@pytest.fixture
def mock_schema():
    """Sample schema for testing"""
    return {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "name", "type": "varchar", "nullable": False},
                    {"name": "email", "type": "varchar", "nullable": True},
                    {"name": "state", "type": "varchar", "nullable": True},
                ],
                "primary_key": "id",
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "customer_id", "type": "integer", "nullable": False},
                    {"name": "total", "type": "decimal", "nullable": False},
                    {"name": "status", "type": "varchar", "nullable": True},
                    {"name": "created_at", "type": "timestamp", "nullable": True},
                ],
                "primary_key": "id",
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "name", "type": "varchar", "nullable": False},
                    {"name": "price", "type": "decimal", "nullable": False},
                    {"name": "category", "type": "varchar", "nullable": True},
                ],
                "primary_key": "id",
            },
        },
        "foreign_keys": [
            {
                "source_table": "orders",
                "source_column": "customer_id",
                "target_table": "customers",
                "target_column": "id",
            }
        ],
    }


@pytest.fixture
def mock_schema_inspector(mock_schema):
    """Mock schema inspector"""
    inspector = MagicMock()
    inspector.get_schema_dict = AsyncMock(return_value=mock_schema)
    inspector.get_full_schema = AsyncMock(return_value=mock_schema)
    return inspector


@pytest.fixture
def mock_schema_cache(mock_schema):
    """Mock schema cache"""
    cache = MagicMock()
    cache.get = MagicMock(return_value=mock_schema)
    # Mock async get_schema method
    cache.get_schema = AsyncMock(return_value=mock_schema)
    return cache


@pytest.fixture
def mock_session():
    """Mock database session"""
    session = MagicMock()
    return session


class TestToolRegistry:
    """Test tool registry functionality"""

    def setup_method(self):
        """Reset registry before each test"""
        reset_tool_registry()
        reset_mapping_cache()

    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns singleton"""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        assert registry1 is registry2

    def test_registry_has_all_tools(self):
        """Test that registry contains all 10 tools"""
        tools = get_all_tools()
        assert len(tools) == 10

        expected_tools = [
            "search_schema",
            "get_table_info",
            "find_columns",
            "get_relationships",
            "get_sample_data",
            "get_column_values",
            "count_rows",
            "test_query",
            "validate_sql",
            "explain_query",
        ]
        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not found in registry"

    def test_tools_by_category_schema(self):
        """Test filtering tools by schema category"""
        schema_tools = get_tools_by_category(ToolCategory.SCHEMA)
        assert len(schema_tools) == 4

        tool_names = [t().name for t in schema_tools]
        assert "search_schema" in tool_names
        assert "get_table_info" in tool_names
        assert "find_columns" in tool_names
        assert "get_relationships" in tool_names

    def test_tools_by_category_data(self):
        """Test filtering tools by data category"""
        data_tools = get_tools_by_category(ToolCategory.DATA)
        assert len(data_tools) == 3

        tool_names = [t().name for t in data_tools]
        assert "get_sample_data" in tool_names
        assert "get_column_values" in tool_names
        assert "count_rows" in tool_names

    def test_tools_by_category_query(self):
        """Test filtering tools by query category"""
        query_tools = get_tools_by_category(ToolCategory.QUERY)
        assert len(query_tools) == 2

        tool_names = [t().name for t in query_tools]
        assert "test_query" in tool_names
        assert "explain_query" in tool_names

    def test_tools_by_category_validation(self):
        """Test filtering tools by validation category"""
        validation_tools = get_tools_by_category(ToolCategory.VALIDATION)
        assert len(validation_tools) == 1

        tool_names = [t().name for t in validation_tools]
        assert "validate_sql" in tool_names


class TestSchemaTools:
    """Test schema exploration tools"""

    @pytest.mark.asyncio
    async def test_search_schema_exact_match(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test search_schema with exact table match"""
        tool = SearchSchemaTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(keyword="customers")

        assert result.success is True
        assert "tables" in result.data
        assert len(result.data["tables"]) >= 1
        assert result.data["tables"][0]["name"] == "customers"

    @pytest.mark.asyncio
    async def test_search_schema_column_match(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test search_schema with column match"""
        tool = SearchSchemaTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(keyword="customer_id")

        assert result.success is True
        assert "columns" in result.data
        assert len(result.data["columns"]) >= 1
        assert any(c["column"] == "customer_id" for c in result.data["columns"])

    @pytest.mark.asyncio
    async def test_search_schema_fuzzy_match(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test search_schema with fuzzy matching"""
        tool = SearchSchemaTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        # Search for 'custmer' (typo)
        result = await tool.execute(keyword="custmer", fuzzy=True, threshold=0.6)

        assert result.success is True
        # Should find 'customers' via fuzzy match
        assert "tables" in result.data

    @pytest.mark.asyncio
    async def test_get_table_info(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test get_table_info returns correct structure"""
        tool = GetTableInfoTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(table_name="orders")

        assert result.success is True
        assert result.data["table_name"] == "orders"
        assert "columns" in result.data
        assert len(result.data["columns"]) == 5
        assert "relationships" in result.data

    @pytest.mark.asyncio
    async def test_get_table_info_not_found(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test get_table_info with non-existent table"""
        tool = GetTableInfoTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(table_name="nonexistent_table")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_find_columns(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test find_columns finds column across tables"""
        tool = FindColumnsTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(column_name="id")

        assert result.success is True
        assert result.data["count"] >= 3  # id exists in all 3 tables
        assert len(result.data["found_in"]) >= 3

    @pytest.mark.asyncio
    async def test_find_columns_partial_match(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test find_columns with partial matching"""
        tool = FindColumnsTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(column_name="customer", exact=False)

        assert result.success is True
        # Should find customer_id
        assert any("customer" in f["column"].lower() for f in result.data["found_in"])

    @pytest.mark.asyncio
    async def test_get_relationships(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test get_relationships returns foreign keys"""
        tool = GetRelationshipsTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(table_name="orders")

        assert result.success is True
        assert len(result.data["relationships"]) >= 1
        assert len(result.data["join_suggestions"]) >= 1


class TestDataTools:
    """Test data sampling tools"""

    @pytest.mark.asyncio
    async def test_count_rows_security_check(self, mock_schema_inspector, mock_schema_cache, mock_session):
        """Test count_rows blocks dangerous SQL in WHERE clause"""
        tool = CountRowsTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        # Try to inject DROP command
        result = await tool.execute(
            table_name="customers",
            where_clause="1=1; DROP TABLE customers; --"
        )

        assert result.success is False
        assert "blocked" in result.error.lower()


class TestQueryTools:
    """Test query validation tools"""

    @pytest.mark.asyncio
    async def test_validate_sql_valid_query(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test validate_sql with valid SQL"""
        tool = ValidateSQLTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(sql="SELECT * FROM customers")

        assert result.success is True
        assert result.data["valid"] is True
        assert "customers" in result.data["valid_tables"]

    @pytest.mark.asyncio
    async def test_validate_sql_invalid_table(self, mock_schema_inspector, mock_schema_cache, mock_session, mock_schema):
        """Test validate_sql with invalid table name"""
        tool = ValidateSQLTool()
        tool.set_context(mock_session, mock_schema_inspector, mock_schema_cache, connection_id=1)

        result = await tool.execute(sql="SELECT * FROM customerz")

        assert result.success is True
        assert result.data["valid"] is False
        assert len(result.data["issues"]) > 0
        assert len(result.data["suggestions"]) > 0  # Should suggest 'customers'


class TestToolDefinitions:
    """Test tool definitions are correct"""

    def test_all_tools_have_definitions(self):
        """Test all tools have valid definitions"""
        tools = get_all_tools()

        for tool_name, tool_class in tools.items():
            tool = tool_class()
            definition = tool.get_definition()

            assert isinstance(definition, ToolDefinition)
            assert definition.name == tool_name
            assert len(definition.description) > 10
            assert isinstance(definition.parameters, dict)
            assert isinstance(definition.required_params, list)

    def test_tool_cache_key_generation(self):
        """Test cache key generation is deterministic"""
        tool = SearchSchemaTool()

        key1 = tool.get_cache_key(keyword="test", fuzzy=True)
        key2 = tool.get_cache_key(keyword="test", fuzzy=True)
        key3 = tool.get_cache_key(keyword="different", fuzzy=True)

        assert key1 == key2  # Same args = same key
        assert key1 != key3  # Different args = different key


class TestToolUsingAgent:
    """Test the tool-using agent"""

    @pytest.mark.asyncio
    async def test_agent_keyword_extraction(self):
        """Test keyword extraction from questions"""
        from src.llm.tool_using_agent import ToolUsingAgent

        agent = ToolUsingAgent(sql_generator=None)

        # Test with a typical question
        keywords = agent._extract_keywords("Show me all orders from California")

        assert "orders" in keywords
        assert "california" in keywords
        # Common words should be filtered
        assert "show" not in keywords
        assert "me" not in keywords
        assert "all" not in keywords

    @pytest.mark.asyncio
    async def test_agent_tool_planning(self):
        """Test tool call planning"""
        from src.llm.tool_using_agent import ToolUsingAgent

        agent = ToolUsingAgent(sql_generator=None)

        # Test planning for a location-based query
        planned = agent._plan_tool_calls(
            question="Show me orders from California",
            schema=""
        )

        # Should plan search_schema and find_columns for state
        tool_names = [call[0] for call in planned]
        assert "search_schema" in tool_names
        assert "find_columns" in tool_names

    @pytest.mark.asyncio
    async def test_agent_enriched_context_building(self):
        """Test enriched context building"""
        from src.llm.tool_using_agent import ToolUsingAgent

        agent = ToolUsingAgent(sql_generator=None)

        context_parts = [
            "Found tables: customers, orders",
            "Found columns: orders.customer_id",
            "Sample values in customers.state: ['CA', 'NY', 'TX']",
        ]

        context = agent._build_enriched_context(context_parts)

        assert "Schema Exploration Results" in context
        assert "customers" in context
        assert "CA" in context

    @pytest.mark.asyncio
    async def test_agent_confidence_calculation(self):
        """Test confidence score calculation"""
        from src.llm.tool_using_agent import ToolUsingAgent

        agent = ToolUsingAgent(sql_generator=None)

        # Test with successful tools
        confidence = agent._calculate_confidence(
            tools_used=["search_schema", "get_table_info"],
            tool_results=[
                {"success": True, "data": {"tables": ["orders"]}, "cache_hit": False},
                {"success": True, "data": {"columns": []}, "cache_hit": True},
            ]
        )

        assert 0.5 <= confidence <= 0.95  # Should be reasonably confident

        # Test with no tools
        no_tools_confidence = agent._calculate_confidence([], [])
        assert no_tools_confidence == 0.5  # Default confidence


class TestToolRegistryMetrics:
    """Test tool registry metrics tracking"""

    def setup_method(self):
        """Reset registry before each test"""
        reset_tool_registry()
        reset_mapping_cache()

    @pytest.mark.asyncio
    async def test_registry_tracks_stats(self, mock_schema_inspector, mock_schema_cache, mock_session):
        """Test registry tracks execution statistics"""
        registry = get_tool_registry()

        # Execute a tool
        result = await registry.execute_tool(
            tool_name="search_schema",
            session=mock_session,
            schema_inspector=mock_schema_inspector,
            schema_cache=mock_schema_cache,
            keyword="test"
        )

        # Get stats
        stats = await registry.get_tool_stats()

        assert "search_schema" in stats
        assert stats["search_schema"]["times_executed"] >= 1


class TestSelfCorrectingAgentIntegration:
    """Test tool-using integration with self-correcting agent"""

    def test_tool_using_agent_imported(self):
        """Test that tool-using agent is available in self-correcting agent"""
        from src.llm.self_correcting_agent import TOOL_USING_AVAILABLE
        assert TOOL_USING_AVAILABLE is True

    def test_parallel_fixes_include_tool_fix(self):
        """Test that parallel fixes include tool_using strategy"""
        # Verify the code structure includes try_tool_fix
        import inspect
        from src.llm.self_correcting_agent import SelfCorrectingSQLAgent

        source = inspect.getsource(SelfCorrectingSQLAgent._try_parallel_fixes)
        assert "try_tool_fix" in source
        assert "tool_using" in source
