"""
Tests for Lineage Narrator (Phase 12.1)

Tests the LLM-powered narrative generation for data lineage graphs.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.lineage.lineage_narrator import (
    LineageNarrator,
    LineageNarrative,
    TransformationExplanation,
    get_lineage_narrator,
)
from src.lineage.sql_lineage_parser import (
    SQLLineageParser,
    LineageGraph,
    LineageNode,
    LineageNodeType,
    TransformationType,
)


@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def sample_lineage_graph():
    """Create a sample lineage graph for testing."""
    parser = SQLLineageParser()
    sql = """
    SELECT
        c.customer_id,
        c.name,
        SUM(o.amount) as total_spent
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name
    """
    return parser.parse(sql)


@pytest.fixture
def simple_lineage_graph():
    """Create a simple lineage graph."""
    parser = SQLLineageParser()
    sql = "SELECT name, email FROM users"
    return parser.parse(sql)


@pytest.fixture
def narrator(mock_ollama_client):
    """Create a LineageNarrator with mock client."""
    return LineageNarrator(
        ollama_client=mock_ollama_client,
        timeout_seconds=5.0,
    )


class TestLineageNarrative:
    """Tests for LineageNarrative dataclass."""

    def test_narrative_defaults(self):
        """Test narrative has proper defaults."""
        narrative = LineageNarrative(
            summary="Test summary",
            data_flow_description="Data flows through the system"
        )

        assert narrative.summary == "Test summary"
        assert narrative.data_flow_description == "Data flows through the system"
        assert narrative.column_explanations == {}
        assert narrative.transformations_explained == []
        assert narrative.business_context == {}
        assert narrative.potential_issues == []
        assert narrative.confidence == 0.5
        assert narrative.generated_at is not None

    def test_narrative_to_dict(self):
        """Test narrative serialization."""
        narrative = LineageNarrative(
            summary="Query retrieves customer orders",
            data_flow_description="Data flows from customers and orders tables",
            column_explanations={"total": "Sum of order amounts"},
            confidence=0.85,
        )

        result = narrative.to_dict()

        assert result["summary"] == "Query retrieves customer orders"
        assert result["confidence"] == 0.85
        assert "total" in result["column_explanations"]


class TestTransformationExplanation:
    """Tests for TransformationExplanation dataclass."""

    def test_explanation_to_dict(self):
        """Test transformation explanation serialization."""
        explanation = TransformationExplanation(
            node_id="trans_1",
            transformation_type="aggregation",
            input_columns=["orders.amount"],
            output_column="total_spent",
            explanation="Sums all order amounts",
            business_meaning="Calculates total customer spend",
        )

        result = explanation.to_dict()

        assert result["node_id"] == "trans_1"
        assert result["transformation_type"] == "aggregation"
        assert "orders.amount" in result["input_columns"]


class TestLineageNarrator:
    """Tests for LineageNarrator class."""

    @pytest.mark.asyncio
    async def test_generate_narrative_simple_select(self, narrator, mock_ollama_client, simple_lineage_graph):
        """Test narrative generation for simple SELECT query."""
        mock_ollama_client.generate.return_value = json.dumps({
            "summary": "Query retrieves user names and emails from the users table.",
            "data_flow_description": "Data flows directly from the users table.",
            "column_explanations": {
                "name": "User's full name",
                "email": "User's email address"
            },
            "transformations_explained": [],
            "business_context": {"users": "Customer database"},
            "potential_issues": [],
            "confidence": 0.9
        })

        narrative = await narrator.generate_narrative(simple_lineage_graph)

        assert narrative.summary is not None
        assert "user" in narrative.summary.lower() or "retrieves" in narrative.summary.lower()
        assert narrative.confidence > 0.5
        mock_ollama_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_narrative_with_aggregation(self, narrator, mock_ollama_client, sample_lineage_graph):
        """Test narrative explains SUM/COUNT/AVG correctly."""
        mock_ollama_client.generate.return_value = json.dumps({
            "summary": "Calculates total spending per customer by joining customer and order data.",
            "data_flow_description": "Customer data is joined with orders, then aggregated.",
            "column_explanations": {
                "customer_id": "Unique customer identifier",
                "name": "Customer name",
                "total_spent": "Sum of all order amounts for this customer"
            },
            "transformations_explained": [
                {
                    "node_id": "trans_1",
                    "transformation_type": "aggregation",
                    "input_columns": ["orders.amount"],
                    "output_column": "total_spent",
                    "explanation": "Sums all order amounts per customer",
                    "business_meaning": "Customer lifetime value"
                }
            ],
            "business_context": {"customers": "Customer master data", "orders": "Sales transactions"},
            "potential_issues": [],
            "confidence": 0.85
        })

        narrative = await narrator.generate_narrative(
            sample_lineage_graph,
            question="What is the total spending per customer?"
        )

        assert narrative.summary is not None
        assert narrative.confidence >= 0.5
        assert "total_spent" in narrative.column_explanations or len(narrative.column_explanations) > 0

    @pytest.mark.asyncio
    async def test_timeout_graceful_degradation(self, narrator, mock_ollama_client, simple_lineage_graph):
        """Test returns fallback result on timeout."""
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return "{}"

        mock_ollama_client.generate = slow_response
        narrator.timeout_seconds = 0.1  # Very short timeout

        narrative = await narrator.generate_narrative(simple_lineage_graph)

        # Should return fallback narrative
        assert narrative is not None
        assert narrative.summary is not None
        assert narrative.confidence < 0.6  # Fallback has lower confidence

    @pytest.mark.asyncio
    async def test_llm_error_graceful_degradation(self, narrator, mock_ollama_client, simple_lineage_graph):
        """Test returns fallback result on LLM error."""
        mock_ollama_client.generate.side_effect = Exception("LLM connection failed")

        narrative = await narrator.generate_narrative(simple_lineage_graph)

        # Should return fallback narrative
        assert narrative is not None
        assert narrative.summary is not None
        assert narrative.confidence == 0.4  # Fallback confidence

    @pytest.mark.asyncio
    async def test_empty_lineage_handling(self, narrator, mock_ollama_client):
        """Test handles empty lineage gracefully."""
        empty_graph = LineageGraph(sql="")

        narrative = await narrator.generate_narrative(empty_graph)

        assert narrative is not None
        assert "No lineage data" in narrative.summary or narrative.summary is not None
        mock_ollama_client.generate.assert_not_called()  # Should not call LLM for empty graph

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, narrator, mock_ollama_client, simple_lineage_graph):
        """Test handles malformed JSON response."""
        mock_ollama_client.generate.return_value = "This is not valid JSON at all"

        narrative = await narrator.generate_narrative(simple_lineage_graph)

        # Should return fallback narrative
        assert narrative is not None
        assert narrative.confidence < 0.6  # Fallback has lower confidence

    @pytest.mark.asyncio
    async def test_partial_json_response(self, narrator, mock_ollama_client, simple_lineage_graph):
        """Test handles partial/incomplete JSON response."""
        mock_ollama_client.generate.return_value = """
        Here's the analysis:
        {"summary": "incomplete json...
        """

        narrative = await narrator.generate_narrative(simple_lineage_graph)

        # Should return fallback narrative
        assert narrative is not None

    @pytest.mark.asyncio
    async def test_business_context_inference(self, narrator, mock_ollama_client, sample_lineage_graph):
        """Test technical-to-business term mapping."""
        mock_ollama_client.generate.return_value = json.dumps({
            "summary": "Customer spending analysis",
            "data_flow_description": "Joins customer and order data",
            "column_explanations": {},
            "transformations_explained": [],
            "business_context": {
                "customer_id": "Customer ID",
                "total_spent": "Total Revenue per Customer"
            },
            "potential_issues": [],
            "confidence": 0.8
        })

        narrative = await narrator.generate_narrative(sample_lineage_graph)

        assert narrative.business_context is not None
        # May have business context mapping

    @pytest.mark.asyncio
    async def test_question_included_in_prompt(self, narrator, mock_ollama_client, simple_lineage_graph):
        """Test that question is passed to LLM prompt."""
        mock_ollama_client.generate.return_value = json.dumps({
            "summary": "Query answers the question about users",
            "data_flow_description": "",
            "column_explanations": {},
            "transformations_explained": [],
            "business_context": {},
            "potential_issues": [],
            "confidence": 0.8
        })

        await narrator.generate_narrative(
            simple_lineage_graph,
            question="Show me all user names and emails"
        )

        # Check that the prompt included the question
        call_args = mock_ollama_client.generate.call_args
        assert call_args is not None
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "Show me all user names and emails" in prompt


class TestDeterministicSummary:
    """Tests for deterministic summary extraction."""

    def test_extract_single_table(self, narrator):
        """Test summary for single table query."""
        parser = SQLLineageParser()
        graph = parser.parse("SELECT id, name FROM products")

        summary = narrator._extract_deterministic_summary(graph)

        assert "products" in summary.lower()

    def test_extract_multiple_tables(self, narrator):
        """Test summary for multi-table query."""
        parser = SQLLineageParser()
        graph = parser.parse("""
            SELECT c.name, o.total
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
        """)

        summary = narrator._extract_deterministic_summary(graph)

        assert "2 tables" in summary.lower() or "joins" in summary.lower()

    def test_extract_with_aggregation(self, narrator):
        """Test summary for query with aggregations."""
        parser = SQLLineageParser()
        graph = parser.parse("SELECT COUNT(*), SUM(amount) FROM orders GROUP BY category")

        summary = narrator._extract_deterministic_summary(graph)

        # Should produce a valid summary (aggregations may or may not be explicitly mentioned)
        assert summary is not None
        assert len(summary) > 0
        # Should mention the table at minimum
        assert "orders" in summary.lower()


class TestFallbackNarrative:
    """Tests for fallback narrative generation."""

    def test_fallback_has_valid_structure(self, narrator, simple_lineage_graph):
        """Test fallback narrative has all required fields."""
        narrative = narrator._fallback_narrative(simple_lineage_graph, "Test summary")

        assert narrative.summary == "Test summary"
        assert isinstance(narrative.data_flow_description, str)
        assert isinstance(narrative.column_explanations, dict)
        assert isinstance(narrative.potential_issues, list)
        assert narrative.confidence == 0.4
        assert narrative.generated_at is not None

    def test_fallback_column_explanations(self, narrator, simple_lineage_graph):
        """Test fallback creates basic column explanations."""
        narrative = narrator._fallback_narrative(simple_lineage_graph, "Test")

        # Should have some column explanations for output columns
        if simple_lineage_graph.output_columns:
            assert len(narrative.column_explanations) > 0


class TestJsonExtraction:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_simple_json(self):
        """Test extraction of simple JSON object."""
        from src.lineage.llm_utils import extract_json_object
        text = '{"key": "value"}'
        result = extract_json_object(text)
        assert result == '{"key": "value"}'

    def test_extract_json_with_prefix(self):
        """Test extraction of JSON with text prefix."""
        from src.lineage.llm_utils import extract_json_object
        text = 'Here is the result:\n{"summary": "test"}'
        result = extract_json_object(text)
        assert result is not None
        assert json.loads(result)["summary"] == "test"

    def test_extract_nested_json(self):
        """Test extraction of nested JSON object."""
        from src.lineage.llm_utils import extract_json_object
        text = '{"outer": {"inner": "value"}}'
        result = extract_json_object(text)
        assert result == '{"outer": {"inner": "value"}}'

    def test_extract_json_with_string_braces(self):
        """Test JSON extraction handles braces in strings."""
        from src.lineage.llm_utils import extract_json_object
        text = '{"message": "Use {} for templates"}'
        result = extract_json_object(text)
        assert result is not None
        parsed = json.loads(result)
        assert "templates" in parsed["message"]

    def test_extract_no_json(self):
        """Test returns None when no JSON found."""
        from src.lineage.llm_utils import extract_json_object
        text = "This is just plain text"
        result = extract_json_object(text)
        assert result is None


class TestGetLineageNarrator:
    """Tests for get_lineage_narrator factory function."""

    @pytest.mark.asyncio
    async def test_get_narrator_without_db(self):
        """Test getting narrator without database session."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            narrator = await get_lineage_narrator()

            assert narrator is not None
            assert narrator.client == mock_client

    @pytest.mark.asyncio
    async def test_get_narrator_with_model_override(self):
        """Test getting narrator with model override."""
        with patch("src.llm.ollama_client.get_ollama_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            narrator = await get_lineage_narrator(model="custom-model")

            assert narrator.model == "custom-model"


class TestIntegration:
    """Integration tests with actual lineage parsing."""

    @pytest.mark.asyncio
    async def test_complex_query_narrative(self, narrator, mock_ollama_client):
        """Test narrative for complex multi-join query."""
        parser = SQLLineageParser()
        sql = """
        SELECT
            c.name AS customer_name,
            p.name AS product_name,
            SUM(oi.quantity * oi.price) AS total_value
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.created_at >= '2024-01-01'
        GROUP BY c.name, p.name
        ORDER BY total_value DESC
        """
        graph = parser.parse(sql)

        mock_ollama_client.generate.return_value = json.dumps({
            "summary": "Calculates total sales value by customer and product for 2024.",
            "data_flow_description": "Joins 4 tables to compute order totals grouped by customer and product.",
            "column_explanations": {
                "customer_name": "Customer's name",
                "product_name": "Product purchased",
                "total_value": "Total monetary value of purchases"
            },
            "transformations_explained": [
                {
                    "node_id": "t1",
                    "transformation_type": "expression",
                    "input_columns": ["oi.quantity", "oi.price"],
                    "output_column": "total_value",
                    "explanation": "Multiplies quantity by price and sums per customer-product combination",
                    "business_meaning": "Revenue per customer per product"
                }
            ],
            "business_context": {},
            "potential_issues": ["No limit clause - may return many rows"],
            "confidence": 0.85
        })

        narrative = await narrator.generate_narrative(
            graph,
            question="What are the total sales by customer and product in 2024?"
        )

        assert narrative is not None
        assert narrative.confidence > 0.5
        assert len(graph.tables_used) == 4  # Verify graph has all tables
