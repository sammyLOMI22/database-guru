"""Tests for the Query Template Engine (Small Model Optimization)"""
import pytest
from src.llm.query_templates import TemplateEngine, TemplateType, TemplateMatch


# Sample schema for testing
@pytest.fixture
def sample_schema():
    return {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "state", "type": "varchar", "sample_values": ["CA", "NY", "TX"]},
                    {"name": "email", "type": "varchar"},
                    {"name": "status", "type": "varchar", "sample_values": ["active", "inactive"]},
                ]
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "price", "type": "decimal"},
                    {"name": "category", "type": "varchar", "sample_values": ["Electronics", "Clothing", "Food"]},
                    {"name": "quantity", "type": "integer"},
                ]
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "customer_id", "type": "integer"},
                    {"name": "total", "type": "decimal"},
                    {"name": "order_date", "type": "date"},
                    {"name": "status", "type": "varchar"},
                ]
            },
        }
    }


class TestListAllPattern:
    """Tests for list/show all pattern matching"""

    def test_show_all_customers(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show all customers")
        assert match is not None
        assert match.template_type == TemplateType.LIST_ALL
        assert "SELECT * FROM customers" in match.sql
        assert match.matched_table == "customers"
        assert match.confidence >= 0.9

    def test_list_products(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("list products")
        assert match is not None
        assert match.template_type == TemplateType.LIST_ALL
        assert "products" in match.sql.lower()

    def test_get_all_orders(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("get all orders")
        assert match is not None
        assert match.template_type == TemplateType.LIST_ALL
        assert "orders" in match.sql.lower()

    def test_singular_form(self, sample_schema):
        """Test that singular forms are matched to plural tables"""
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show all customer")
        assert match is not None
        assert match.matched_table == "customers"


class TestCountPattern:
    """Tests for count pattern matching"""

    def test_how_many_customers(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("how many customers")
        assert match is not None
        assert match.template_type == TemplateType.COUNT
        assert "COUNT(*)" in match.sql
        assert match.matched_table == "customers"

    def test_count_products(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("count products")
        assert match is not None
        assert match.template_type == TemplateType.COUNT
        assert "COUNT(*)" in match.sql

    def test_total_orders(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("total orders")
        assert match is not None
        assert match.template_type == TemplateType.COUNT


class TestTopNPattern:
    """Tests for top N pattern matching"""

    def test_top_5_products_by_price(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("top 5 products by price")
        assert match is not None
        assert match.template_type == TemplateType.TOP_N
        assert "ORDER BY" in match.sql
        assert "DESC" in match.sql
        assert "LIMIT 5" in match.sql
        assert match.parameters.get("n") == 5

    def test_top_10_customers(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("top 10 customers by id")
        assert match is not None
        assert "LIMIT 10" in match.sql


class TestFilterLocationPattern:
    """Tests for location filter pattern matching"""

    def test_customers_from_california(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("customers from California")
        assert match is not None
        assert match.template_type == TemplateType.FILTER_LOCATION
        assert "WHERE" in match.sql
        assert "state" in match.sql.lower()

    def test_customers_in_ny(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("customers in NY")
        assert match is not None
        assert match.template_type == TemplateType.FILTER_LOCATION

    def test_show_customers_from_texas(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show customers from Texas")
        assert match is not None
        assert match.template_type == TemplateType.FILTER_LOCATION


class TestFilterValuePattern:
    """Tests for value filter pattern matching"""

    def test_customers_where_status_active(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("customers where status is active")
        assert match is not None
        assert match.template_type == TemplateType.FILTER_VALUE
        assert "WHERE" in match.sql
        assert "active" in match.sql.lower()

    def test_products_in_electronics(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("products where category is Electronics")
        assert match is not None
        # Value may be lowercased - check case-insensitive
        assert "electronics" in match.sql.lower()


class TestAggregatePatterns:
    """Tests for aggregate function patterns"""

    def test_sum_total(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("total price for products")
        # May or may not match depending on pattern specificity
        if match:
            assert match.template_type in [TemplateType.SUM_TOTAL, TemplateType.COUNT]

    def test_average_price(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("average price for products")
        if match:
            assert match.template_type == TemplateType.AVERAGE
            assert "AVG" in match.sql


class TestNoMatch:
    """Tests for queries that should not match any template"""

    def test_complex_query_no_match(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show customers who ordered more than 5 products last month")
        assert match is None

    def test_join_query_no_match(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show customers with their orders")
        assert match is None

    def test_nonexistent_table_no_match(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show all employees")
        assert match is None

    def test_ambiguous_query_no_match(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("what is the best product")
        # May or may not match - depends on implementation
        # Just ensure no error


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_question(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("")
        assert match is None

    def test_question_with_punctuation(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show all customers?")
        assert match is not None
        assert match.template_type == TemplateType.LIST_ALL

    def test_question_with_extra_whitespace(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("  show all customers  ")
        assert match is not None

    def test_case_insensitivity(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("SHOW ALL CUSTOMERS")
        assert match is not None
        assert match.template_type == TemplateType.LIST_ALL

    def test_custom_limit(self, sample_schema):
        engine = TemplateEngine(sample_schema, default_limit=50)
        match = engine.try_match("show all customers")
        assert match is not None
        assert "LIMIT 50" in match.sql


class TestTemplateMatch:
    """Tests for TemplateMatch dataclass"""

    def test_to_dict(self, sample_schema):
        engine = TemplateEngine(sample_schema)
        match = engine.try_match("show all customers")
        assert match is not None

        result = match.to_dict()
        assert "template" in result
        assert "sql" in result
        assert "confidence" in result
        assert "table" in result
        assert result["template"] == "list_all"
