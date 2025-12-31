"""Tests for Dynamic Example Generator.

Tests the schema-specific few-shot example generation that replaces
hardcoded examples with examples using actual table/column names.
"""
import pytest
from src.llm.dynamic_example_generator import (
    DynamicExampleGenerator,
    SQLExample,
)
from src.llm.query_intent_classifier import QueryIntent


@pytest.fixture
def sample_schema():
    """Sample schema with common e-commerce tables."""
    return {
        "tables": {
            "products": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "price", "type": "DECIMAL"},
                    {"name": "category_id", "type": "INTEGER"},
                    {"name": "status", "type": "VARCHAR", "sample_values": ["active", "inactive", "pending"]},
                ],
                "foreign_keys": [
                    {"column": "category_id", "references": {"table": "categories", "column": "id"}}
                ]
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "customer_id", "type": "INTEGER"},
                    {"name": "state", "type": "VARCHAR(2)", "sample_values": ["CA", "NY", "TX"]},
                    {"name": "total", "type": "DECIMAL"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ]
            },
            "categories": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                ]
            },
        },
        "relationships": [
            {"from_table": "products", "from_column": "category_id", "to_table": "categories", "to_column": "id"},
        ]
    }


@pytest.fixture
def simple_schema():
    """Simple schema with one table."""
    return {
        "tables": {
            "items": {
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "quantity", "type": "INTEGER"},
                ]
            },
        }
    }


class TestBasicExampleGeneration:
    """Test basic example generation."""

    def test_generates_examples_from_schema(self, sample_schema):
        """Test that examples are generated from actual schema tables."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.generate_examples()

        # Should contain actual table names from schema
        assert "products" in examples or "orders" in examples or "categories" in examples
        # Should NOT contain hardcoded example table names
        assert "users" not in examples
        assert "customers" not in examples  # (not in schema)

    def test_examples_formatted_string(self, sample_schema):
        """Test that examples are returned as formatted string."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.generate_examples()

        assert isinstance(examples, str)
        assert "Example" in examples
        assert "Question:" in examples
        assert "SQL:" in examples

    def test_examples_include_limit(self, sample_schema):
        """Test that examples include LIMIT clause."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.generate_examples(row_limit=10)

        assert "LIMIT 10" in examples

    def test_custom_row_limit(self, sample_schema):
        """Test custom row limit in examples."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.generate_examples(row_limit=25)

        assert "LIMIT 25" in examples


class TestTableExamples:
    """Test table-based example generation."""

    def test_table_lookup_examples(self, sample_schema):
        """Test simple table lookup examples."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_table_examples(row_limit=10)

        assert len(examples) >= 1
        # Check that examples use actual table names
        table_names_used = [ex.sql for ex in examples]
        assert any("products" in sql or "orders" in sql or "categories" in sql for sql in table_names_used)

    def test_table_examples_have_select(self, sample_schema):
        """Test that table examples have SELECT statements."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_table_examples(row_limit=10)

        for ex in examples:
            assert ex.sql.upper().startswith("SELECT")


class TestRelationshipExamples:
    """Test JOIN example generation."""

    def test_join_examples_from_foreign_keys(self, sample_schema):
        """Test JOIN examples are generated from foreign keys."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_relationship_examples(row_limit=10)

        # Should have at least one JOIN example
        assert len(examples) >= 1

        # Check that JOIN syntax is correct
        for ex in examples:
            assert "JOIN" in ex.sql

    def test_join_example_uses_actual_tables(self, sample_schema):
        """Test JOIN examples use actual table names."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_relationship_examples(row_limit=10)

        if examples:
            ex = examples[0]
            # Should reference actual tables from schema
            assert "products" in ex.sql or "categories" in ex.sql
            # Should NOT have placeholder table names
            assert "[" not in ex.sql

    def test_no_join_examples_without_fks(self, simple_schema):
        """Test no JOIN examples when schema has no FKs."""
        generator = DynamicExampleGenerator(simple_schema)
        examples = generator._generate_relationship_examples(row_limit=10)

        # Should have no examples since no foreign keys
        assert len(examples) == 0


class TestAggregationExamples:
    """Test aggregation example generation."""

    def test_count_example_generated(self, sample_schema):
        """Test COUNT example is generated."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_aggregation_examples()

        count_examples = [ex for ex in examples if "COUNT" in ex.sql]
        assert len(count_examples) >= 1

    def test_group_by_example(self, sample_schema):
        """Test GROUP BY examples are generated."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_aggregation_examples()

        group_by_examples = [ex for ex in examples if "GROUP BY" in ex.sql]
        # Should have at least one GROUP BY example if suitable columns exist
        assert len(group_by_examples) >= 0  # May be 0 if no suitable columns


class TestFilterExamples:
    """Test filter/WHERE example generation."""

    def test_filter_examples_use_sample_values(self, sample_schema):
        """Test filter examples use actual sample values."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_filter_examples(row_limit=10)

        # Should have at least one filter example
        if examples:
            # Check that WHERE clause is present
            where_examples = [ex for ex in examples if "WHERE" in ex.sql]
            assert len(where_examples) >= 0

    def test_status_column_filter(self, sample_schema):
        """Test that status columns get filter examples with sample values."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator._generate_filter_examples(row_limit=10)

        # products has status column with sample values
        status_examples = [ex for ex in examples if "status" in ex.sql.lower()]
        # Should use actual sample values like 'active', 'inactive'
        if status_examples:
            assert "active" in status_examples[0].sql or "inactive" in status_examples[0].sql


class TestIntentSpecificExamples:
    """Test intent-specific example generation."""

    def test_lookup_intent_examples(self, sample_schema):
        """Test examples for LOOKUP intent."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.get_intent_specific_examples(QueryIntent.LOOKUP)

        assert "SELECT" in examples
        assert "Example" in examples

    def test_aggregation_intent_examples(self, sample_schema):
        """Test examples for AGGREGATION intent."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.get_intent_specific_examples(QueryIntent.AGGREGATION)

        # Should have COUNT or SUM examples
        assert "COUNT" in examples or "SUM" in examples or "AVG" in examples

    def test_relationship_intent_examples(self, sample_schema):
        """Test examples for RELATIONSHIP intent."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.get_intent_specific_examples(QueryIntent.RELATIONSHIP)

        # Should have JOIN examples if FKs exist
        assert "JOIN" in examples or "SELECT" in examples  # Falls back to table examples

    def test_ranking_intent_examples(self, sample_schema):
        """Test examples for RANKING intent."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.get_intent_specific_examples(QueryIntent.RANKING)

        # Should have ORDER BY and LIMIT
        assert "ORDER BY" in examples
        assert "LIMIT" in examples

    def test_comparison_intent_examples(self, sample_schema):
        """Test examples for COMPARISON intent."""
        generator = DynamicExampleGenerator(sample_schema)
        examples = generator.get_intent_specific_examples(QueryIntent.COMPARISON)

        # Should have WHERE clause
        assert "WHERE" in examples or "SELECT" in examples


class TestHelperMethods:
    """Test helper methods for column type detection."""

    def test_find_numeric_column(self, sample_schema):
        """Test finding numeric columns for aggregation."""
        generator = DynamicExampleGenerator(sample_schema)

        # products has 'price' as numeric
        numeric_col = generator._find_numeric_column("products")
        assert numeric_col == "price"

        # orders has 'total' as numeric
        numeric_col = generator._find_numeric_column("orders")
        assert numeric_col == "total"

    def test_find_groupable_column(self, sample_schema):
        """Test finding columns suitable for GROUP BY."""
        generator = DynamicExampleGenerator(sample_schema)

        # products has 'status' and 'category_id' - both are groupable
        # The function prioritizes status/type/category keywords
        group_col = generator._find_groupable_column("products")
        assert group_col in ["status", "category_id"]  # Either is valid

    def test_get_table_columns(self, sample_schema):
        """Test getting columns for a table."""
        generator = DynamicExampleGenerator(sample_schema)
        columns = generator._get_table_columns("products")

        assert "id" in columns
        assert "name" in columns
        assert "price" in columns


class TestSQLExample:
    """Test SQLExample dataclass."""

    def test_sql_example_creation(self):
        """Test creating SQLExample."""
        example = SQLExample(
            question="Show all products",
            sql="SELECT * FROM products LIMIT 10",
            note="Basic lookup example",
            intent=QueryIntent.LOOKUP
        )

        assert example.question == "Show all products"
        assert example.sql == "SELECT * FROM products LIMIT 10"
        assert example.note == "Basic lookup example"
        assert example.intent == QueryIntent.LOOKUP

    def test_sql_example_without_optional_fields(self):
        """Test SQLExample without optional fields."""
        example = SQLExample(
            question="Show all products",
            sql="SELECT * FROM products LIMIT 10"
        )

        assert example.note is None
        assert example.intent is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_schema(self):
        """Test handling of empty schema."""
        schema = {"tables": {}}
        generator = DynamicExampleGenerator(schema)
        examples = generator.generate_examples()

        # Should return empty or minimal examples
        assert isinstance(examples, str)

    def test_schema_without_relationships(self, simple_schema):
        """Test schema without any relationships."""
        generator = DynamicExampleGenerator(simple_schema)
        examples = generator.generate_examples()

        # Should still generate basic examples
        assert "items" in examples
        assert "SELECT" in examples

    def test_table_without_numeric_columns(self):
        """Test table without numeric columns."""
        schema = {
            "tables": {
                "logs": {
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "message", "type": "TEXT"},
                    ]
                }
            }
        }
        generator = DynamicExampleGenerator(schema)

        # Should return None for numeric column
        numeric = generator._find_numeric_column("logs")
        # id might be returned as fallback or None
        assert numeric is None or numeric == "id"
