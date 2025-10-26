"""Tests for Query Planning Agent"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.query_planning_agent import (
    QueryPlanningAgent,
    QueryPlan,
    QueryComplexity,
    TableReference,
    JoinSpec,
    FilterSpec,
    AggregationSpec,
    GroupingSpec,
    OrderingSpec
)


@pytest.fixture
def mock_settings():
    """Mock settings"""
    settings = MagicMock()
    settings.OLLAMA_MODEL = "llama3"
    settings.OLLAMA_HOST = "http://localhost:11434"
    return settings


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client"""
    client = AsyncMock()
    client.chat = AsyncMock()
    return client


@pytest.fixture
def sample_schema():
    """Sample database schema for testing"""
    return json.dumps({
        "tables": [
            {
                "name": "products",
                "columns": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "name", "type": "varchar"},
                    {"name": "category", "type": "varchar"},
                    {"name": "price", "type": "decimal"}
                ]
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "customer_id", "type": "integer"},
                    {"name": "order_date", "type": "date"},
                    {"name": "total_amount", "type": "decimal"}
                ]
            },
            {
                "name": "order_items",
                "columns": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "order_id", "type": "integer"},
                    {"name": "product_id", "type": "integer"},
                    {"name": "quantity", "type": "integer"},
                    {"name": "price", "type": "decimal"}
                ]
            }
        ]
    })


class TestQueryPlan:
    """Test QueryPlan data structure"""

    def test_query_plan_creation(self):
        """Test creating a QueryPlan object"""
        plan = QueryPlan(
            question="Show all products",
            complexity=QueryComplexity.SIMPLE,
            intent="List all products",
            tables=[TableReference(name="products", alias="p", purpose="Get products")],
            joins=[],
            filters=[],
            aggregations=[],
            grouping=None,
            ordering=None,
            limit=10,
            reasoning="Simple single-table query",
            confidence=0.95
        )

        assert plan.question == "Show all products"
        assert plan.complexity == QueryComplexity.SIMPLE
        assert len(plan.tables) == 1
        assert plan.tables[0].name == "products"
        assert plan.confidence == 0.95

    def test_query_plan_to_dict(self):
        """Test converting QueryPlan to dictionary"""
        plan = QueryPlan(
            question="Test question",
            complexity=QueryComplexity.MODERATE,
            intent="Test intent",
            tables=[TableReference(name="test", alias="t")],
            joins=[],
            filters=[],
            aggregations=[],
            grouping=None,
            ordering=None,
            limit=None,
            reasoning="Test reasoning",
            confidence=0.8
        )

        plan_dict = plan.to_dict()

        assert plan_dict["question"] == "Test question"
        assert plan_dict["complexity"] == "moderate"
        assert plan_dict["confidence"] == 0.8
        assert len(plan_dict["tables"]) == 1

    def test_query_plan_from_dict(self):
        """Test creating QueryPlan from dictionary"""
        plan_dict = {
            "question": "Test question",
            "complexity": "complex",
            "intent": "Test intent",
            "tables": [{"name": "test", "alias": "t", "purpose": "Test"}],
            "joins": [],
            "filters": [],
            "aggregations": [],
            "grouping": None,
            "ordering": None,
            "limit": 100,
            "reasoning": "Test reasoning",
            "confidence": 0.9
        }

        plan = QueryPlan.from_dict(plan_dict)

        assert plan.question == "Test question"
        assert plan.complexity == QueryComplexity.COMPLEX
        assert plan.confidence == 0.9
        assert len(plan.tables) == 1


class TestQueryPlanningAgent:
    """Test QueryPlanningAgent"""

    @pytest.mark.asyncio
    async def test_should_use_planning_simple_query(self, mock_settings, mock_ollama_client, sample_schema):
        """Test that simple queries don't trigger planning"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client,
            enable_planning=True
        )

        # Simple query
        should_plan = await agent.should_use_planning(
            question="Show all products",
            schema=sample_schema
        )

        assert should_plan == False

    @pytest.mark.asyncio
    async def test_should_use_planning_complex_query(self, mock_settings, mock_ollama_client, sample_schema):
        """Test that complex queries trigger planning"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client,
            enable_planning=True
        )

        # Complex query with keywords
        should_plan = await agent.should_use_planning(
            question="Compare revenue between Q1 and Q2, grouped by category",
            schema=sample_schema
        )

        assert should_plan == True

    @pytest.mark.asyncio
    async def test_should_use_planning_disabled(self, mock_settings, mock_ollama_client, sample_schema):
        """Test that planning can be disabled"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client,
            enable_planning=False
        )

        should_plan = await agent.should_use_planning(
            question="Compare revenue between Q1 and Q2",
            schema=sample_schema
        )

        assert should_plan == False

    @pytest.mark.asyncio
    async def test_create_query_plan_success(self, mock_settings, mock_ollama_client, sample_schema):
        """Test successful query plan creation"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client
        )

        # Mock LLM response
        mock_plan_json = {
            "intent": "Compare revenue across quarters by category",
            "complexity": "complex",
            "tables": [
                {"name": "orders", "alias": "o", "purpose": "Get order data"},
                {"name": "order_items", "alias": "oi", "purpose": "Get line items"},
                {"name": "products", "alias": "p", "purpose": "Get categories"}
            ],
            "joins": [
                {
                    "from_table": "orders",
                    "to_table": "order_items",
                    "join_type": "INNER",
                    "on_condition": "o.id = oi.order_id",
                    "purpose": "Link orders to items"
                }
            ],
            "filters": [
                {
                    "column": "order_date",
                    "operator": "BETWEEN",
                    "value": "'2024-01-01' AND '2024-06-30'",
                    "purpose": "Q1 and Q2 filter"
                }
            ],
            "aggregations": [
                {
                    "function": "SUM",
                    "column": "oi.quantity * oi.price",
                    "alias": "revenue",
                    "purpose": "Calculate revenue"
                }
            ],
            "grouping": {
                "columns": ["p.category", "QUARTER(o.order_date)"],
                "purpose": "Group by category and quarter"
            },
            "ordering": {
                "column": "revenue",
                "direction": "DESC",
                "purpose": "Highest revenue first"
            },
            "limit": 100,
            "reasoning": "This query requires joining multiple tables...",
            "confidence": 0.85
        }

        mock_ollama_client.chat.return_value = json.dumps(mock_plan_json)

        plan = await agent.create_query_plan(
            question="Compare revenue between Q1 and Q2, grouped by category",
            schema=sample_schema,
            database_type="postgresql"
        )

        assert plan.complexity == QueryComplexity.COMPLEX
        assert plan.confidence == 0.85
        assert len(plan.tables) == 3
        assert len(plan.joins) == 1
        assert len(plan.filters) == 1
        assert len(plan.aggregations) == 1
        assert plan.grouping is not None
        assert plan.ordering is not None

    @pytest.mark.asyncio
    async def test_create_query_plan_llm_failure(self, mock_settings, mock_ollama_client, sample_schema):
        """Test query plan creation when LLM fails"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client
        )

        # Mock LLM failure
        mock_ollama_client.chat.side_effect = Exception("LLM error")

        plan = await agent.create_query_plan(
            question="Test question",
            schema=sample_schema,
            database_type="postgresql"
        )

        # Should return fallback plan
        assert plan.complexity == QueryComplexity.SIMPLE
        assert plan.confidence <= 0.5
        assert "failed" in plan.reasoning.lower()

    def test_parse_plan_output_valid_json(self, mock_settings, mock_ollama_client):
        """Test parsing valid JSON plan output"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client
        )

        raw_output = json.dumps({
            "intent": "Test intent",
            "complexity": "simple",
            "tables": [],
            "joins": [],
            "filters": [],
            "aggregations": [],
            "grouping": None,
            "ordering": None,
            "limit": None,
            "reasoning": "Test",
            "confidence": 0.8
        })

        parsed = agent._parse_plan_output(raw_output)

        assert parsed["intent"] == "Test intent"
        assert parsed["complexity"] == "simple"
        assert parsed["confidence"] == 0.8

    def test_parse_plan_output_with_markdown(self, mock_settings, mock_ollama_client):
        """Test parsing JSON wrapped in markdown code blocks"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client
        )

        plan_dict = {
            "intent": "Test",
            "complexity": "simple",
            "tables": [],
            "joins": [],
            "filters": [],
            "aggregations": [],
            "grouping": None,
            "ordering": None,
            "limit": None,
            "reasoning": "Test",
            "confidence": 0.7
        }

        raw_output = f"```json\n{json.dumps(plan_dict)}\n```"

        parsed = agent._parse_plan_output(raw_output)

        assert parsed["intent"] == "Test"
        assert parsed["confidence"] == 0.7

    def test_parse_plan_output_invalid(self, mock_settings, mock_ollama_client):
        """Test parsing invalid JSON returns fallback"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client
        )

        raw_output = "This is not valid JSON"

        parsed = agent._parse_plan_output(raw_output)

        # Should return minimal fallback plan
        assert "reasoning" in parsed
        assert parsed["confidence"] <= 0.5

    def test_explain_plan(self, mock_settings, mock_ollama_client):
        """Test generating human-readable explanation"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client
        )

        plan = QueryPlan(
            question="Test question",
            complexity=QueryComplexity.MODERATE,
            intent="Test intent",
            tables=[
                TableReference(name="products", alias="p", purpose="Get products"),
                TableReference(name="orders", alias="o", purpose="Get orders")
            ],
            joins=[
                JoinSpec(
                    from_table="products",
                    to_table="orders",
                    join_type="INNER",
                    on_condition="p.id = o.product_id",
                    purpose="Link products to orders"
                )
            ],
            filters=[
                FilterSpec(column="status", operator="=", value="'active'", purpose="Active only")
            ],
            aggregations=[
                AggregationSpec(function="COUNT", column="*", alias="total", purpose="Count rows")
            ],
            grouping=GroupingSpec(columns=["category"], purpose="Group by category"),
            ordering=OrderingSpec(column="total", direction="DESC", purpose="Highest first"),
            limit=10,
            reasoning="Test reasoning",
            confidence=0.8
        )

        explanation = agent.explain_plan(plan)

        assert "Test intent" in explanation
        assert "moderate" in explanation
        assert "products" in explanation
        assert "orders" in explanation
        assert "INNER JOIN" in explanation
        assert "COUNT" in explanation
        assert "0.8" in explanation or "80%" in explanation or "80.0%" in explanation

    @pytest.mark.asyncio
    async def test_plan_and_generate_sql_simple_query(self, mock_settings, mock_ollama_client, sample_schema):
        """Test plan_and_generate_sql with simple query (should skip planning)"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client,
            enable_planning=True
        )

        result = await agent.plan_and_generate_sql(
            question="Show all products",
            schema=sample_schema,
            database_type="postgresql",
            sql_generator=None
        )

        assert result["used_planning"] == False
        assert result["plan"] is None
        assert "message" in result

    @pytest.mark.asyncio
    async def test_plan_and_generate_sql_complex_query(self, mock_settings, mock_ollama_client, sample_schema):
        """Test plan_and_generate_sql with complex query (should use planning)"""
        agent = QueryPlanningAgent(
            settings=mock_settings,
            ollama_client=mock_ollama_client,
            enable_planning=True
        )

        # Mock plan creation
        mock_plan_json = {
            "intent": "Test",
            "complexity": "complex",
            "tables": [{"name": "products", "alias": "p", "purpose": "Test"}],
            "joins": [],
            "filters": [],
            "aggregations": [],
            "grouping": None,
            "ordering": None,
            "limit": None,
            "reasoning": "Test",
            "confidence": 0.8
        }

        mock_ollama_client.chat.return_value = json.dumps(mock_plan_json)

        result = await agent.plan_and_generate_sql(
            question="Compare revenue between Q1 and Q2",
            schema=sample_schema,
            database_type="postgresql",
            sql_generator=None
        )

        assert result["used_planning"] == True
        assert result["plan"] is not None
        assert result["plan"].complexity == QueryComplexity.COMPLEX


class TestTableReference:
    """Test TableReference data structure"""

    def test_table_reference_creation(self):
        """Test creating TableReference"""
        table = TableReference(
            name="products",
            alias="p",
            purpose="Get product data"
        )

        assert table.name == "products"
        assert table.alias == "p"
        assert table.purpose == "Get product data"

    def test_table_reference_minimal(self):
        """Test creating TableReference with minimal fields"""
        table = TableReference(name="orders")

        assert table.name == "orders"
        assert table.alias is None
        assert table.purpose is None


class TestJoinSpec:
    """Test JoinSpec data structure"""

    def test_join_spec_creation(self):
        """Test creating JoinSpec"""
        join = JoinSpec(
            from_table="orders",
            to_table="customers",
            join_type="INNER",
            on_condition="orders.customer_id = customers.id",
            purpose="Link orders to customers"
        )

        assert join.from_table == "orders"
        assert join.to_table == "customers"
        assert join.join_type == "INNER"
        assert "customer_id" in join.on_condition


class TestFilterSpec:
    """Test FilterSpec data structure"""

    def test_filter_spec_creation(self):
        """Test creating FilterSpec"""
        filter_spec = FilterSpec(
            column="status",
            operator="=",
            value="'active'",
            purpose="Filter active records"
        )

        assert filter_spec.column == "status"
        assert filter_spec.operator == "="
        assert filter_spec.value == "'active'"


class TestAggregationSpec:
    """Test AggregationSpec data structure"""

    def test_aggregation_spec_with_column(self):
        """Test creating AggregationSpec with column"""
        agg = AggregationSpec(
            function="SUM",
            column="amount",
            alias="total_amount",
            purpose="Calculate total"
        )

        assert agg.function == "SUM"
        assert agg.column == "amount"
        assert agg.alias == "total_amount"

    def test_aggregation_spec_count_star(self):
        """Test creating COUNT(*) aggregation"""
        agg = AggregationSpec(
            function="COUNT",
            column=None,
            alias="count",
            purpose="Count rows"
        )

        assert agg.function == "COUNT"
        assert agg.column is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
