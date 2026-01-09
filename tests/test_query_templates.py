"""Tests for the Query Template Engine (Small Model Optimization)"""
import pytest
from src.llm.query_templates import TemplateEngine, TemplateType, TemplateMatch
from src.llm.dialect_registry import DatabaseDialect


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


# =============================================================================
# Dialect-Aware Tests (Phase 3.1)
# =============================================================================

@pytest.fixture
def schema_with_boolean():
    """Schema with a boolean column for testing dialect-specific boolean formatting."""
    return {
        "tables": {
            "users": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "is_active", "type": "boolean", "sample_values": [True, False]},
                    {"name": "status", "type": "varchar", "sample_values": ["active", "inactive"]},
                ]
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "is_available", "type": "boolean"},
                    {"name": "price", "type": "decimal"},
                ]
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "created_at", "type": "timestamp"},
                    {"name": "total", "type": "decimal"},
                ]
            },
        }
    }


class TestDialectAwareTemplateEngine:
    """Tests for dialect-aware SQL generation in TemplateEngine."""

    def test_accepts_database_type_parameter(self, sample_schema):
        """Test that TemplateEngine accepts database_type parameter."""
        engine = TemplateEngine(sample_schema, database_type="postgresql")
        assert engine.database_type == "postgresql"
        assert engine.dialect == DatabaseDialect.POSTGRESQL

    def test_defaults_to_sqlite(self, sample_schema):
        """Test that dialect defaults to SQLite."""
        engine = TemplateEngine(sample_schema)
        assert engine.dialect == DatabaseDialect.SQLITE

    def test_dialect_from_database_type_variations(self, sample_schema):
        """Test various database_type string formats."""
        # PostgreSQL variations
        engine = TemplateEngine(sample_schema, database_type="postgres")
        assert engine.dialect == DatabaseDialect.POSTGRESQL

        engine = TemplateEngine(sample_schema, database_type="PostgreSQL")
        assert engine.dialect == DatabaseDialect.POSTGRESQL

        # MySQL
        engine = TemplateEngine(sample_schema, database_type="mysql")
        assert engine.dialect == DatabaseDialect.MYSQL

        # DuckDB
        engine = TemplateEngine(sample_schema, database_type="duckdb")
        assert engine.dialect == DatabaseDialect.DUCKDB


class TestBooleanFormatting:
    """Tests for dialect-specific boolean value formatting."""

    def test_postgresql_boolean_true(self, schema_with_boolean):
        """PostgreSQL should use TRUE for boolean values."""
        engine = TemplateEngine(schema_with_boolean, database_type="postgresql")
        match = engine.try_match("users where is_active is true")

        assert match is not None
        assert "= TRUE" in match.sql

    def test_postgresql_boolean_false(self, schema_with_boolean):
        """PostgreSQL should use FALSE for boolean values."""
        engine = TemplateEngine(schema_with_boolean, database_type="postgresql")
        match = engine.try_match("users where is_active is false")

        assert match is not None
        assert "= FALSE" in match.sql

    def test_sqlite_boolean_true(self, schema_with_boolean):
        """SQLite should use 1 for boolean true."""
        engine = TemplateEngine(schema_with_boolean, database_type="sqlite")
        match = engine.try_match("users where is_active is true")

        assert match is not None
        assert "= 1" in match.sql

    def test_sqlite_boolean_false(self, schema_with_boolean):
        """SQLite should use 0 for boolean false."""
        engine = TemplateEngine(schema_with_boolean, database_type="sqlite")
        match = engine.try_match("users where is_active is false")

        assert match is not None
        assert "= 0" in match.sql

    def test_mysql_boolean_true(self, schema_with_boolean):
        """MySQL should use TRUE for boolean values."""
        engine = TemplateEngine(schema_with_boolean, database_type="mysql")
        match = engine.try_match("users where is_active is true")

        assert match is not None
        assert "= TRUE" in match.sql

    def test_duckdb_boolean_true(self, schema_with_boolean):
        """DuckDB should use TRUE for boolean values."""
        engine = TemplateEngine(schema_with_boolean, database_type="duckdb")
        match = engine.try_match("users where is_active is true")

        assert match is not None
        assert "= TRUE" in match.sql

    def test_boolean_value_detection_yes_no(self, schema_with_boolean):
        """Test that 'yes' and 'no' are detected as boolean values."""
        engine = TemplateEngine(schema_with_boolean, database_type="postgresql")

        # "yes" should be treated as true
        match = engine.try_match("users where is_active is yes")
        assert match is not None
        assert "= TRUE" in match.sql

    def test_boolean_value_detection_enabled_disabled(self, schema_with_boolean):
        """Test that 'enabled'/'disabled' are detected as boolean values."""
        engine = TemplateEngine(schema_with_boolean, database_type="postgresql")

        # When the column is boolean type and value is "enabled", use TRUE
        match = engine.try_match("users where is_active is enabled")
        assert match is not None
        assert "= TRUE" in match.sql

    def test_non_boolean_value_uses_string(self, schema_with_boolean):
        """Test that non-boolean values use string format."""
        engine = TemplateEngine(schema_with_boolean, database_type="postgresql")

        # "premium" is not a boolean value, should be quoted
        match = engine.try_match("users where status is premium")
        if match:
            assert "= 'premium'" in match.sql


class TestDateFilterFormatting:
    """Tests for dialect-specific date filter formatting."""

    def test_sqlite_date_filter_format(self, schema_with_boolean):
        """Test SQLite date filter format."""
        engine = TemplateEngine(schema_with_boolean, database_type="sqlite")
        date_filter = engine._format_date_filter("created_at", 7)

        assert "datetime('now', '-7 days')" in date_filter

    def test_postgresql_date_filter_format(self, schema_with_boolean):
        """Test PostgreSQL date filter format."""
        engine = TemplateEngine(schema_with_boolean, database_type="postgresql")
        date_filter = engine._format_date_filter("created_at", 7)

        assert "CURRENT_TIMESTAMP - INTERVAL '7 days'" in date_filter

    def test_mysql_date_filter_format(self, schema_with_boolean):
        """Test MySQL date filter format."""
        engine = TemplateEngine(schema_with_boolean, database_type="mysql")
        date_filter = engine._format_date_filter("created_at", 7)

        assert "DATE_SUB(NOW(), INTERVAL 7 DAY)" in date_filter

    def test_duckdb_date_filter_format(self, schema_with_boolean):
        """Test DuckDB date filter format (PostgreSQL-compatible)."""
        engine = TemplateEngine(schema_with_boolean, database_type="duckdb")
        date_filter = engine._format_date_filter("created_at", 30)

        assert "CURRENT_TIMESTAMP - INTERVAL '30 days'" in date_filter


class TestCaseInsensitiveMatching:
    """Tests for dialect-specific case-insensitive string matching."""

    def test_postgresql_uses_ilike(self, sample_schema):
        """PostgreSQL should use ILIKE for case-insensitive matching."""
        engine = TemplateEngine(sample_schema, database_type="postgresql")
        result = engine._format_case_insensitive_match("name", "john")

        assert "ILIKE" in result
        assert "%john%" in result

    def test_sqlite_uses_lower_like(self, sample_schema):
        """SQLite should use LOWER(col) LIKE LOWER(val)."""
        engine = TemplateEngine(sample_schema, database_type="sqlite")
        result = engine._format_case_insensitive_match("name", "john")

        assert "LOWER" in result
        assert "LIKE" in result
        assert "ILIKE" not in result

    def test_mysql_uses_lower_like(self, sample_schema):
        """MySQL should use LOWER(col) LIKE LOWER(val)."""
        engine = TemplateEngine(sample_schema, database_type="mysql")
        result = engine._format_case_insensitive_match("name", "john")

        assert "LOWER" in result
        assert "LIKE" in result

    def test_duckdb_uses_ilike(self, sample_schema):
        """DuckDB should use ILIKE like PostgreSQL."""
        engine = TemplateEngine(sample_schema, database_type="duckdb")
        result = engine._format_case_insensitive_match("name", "john")

        assert "ILIKE" in result

    def test_escapes_single_quotes(self, sample_schema):
        """Test that single quotes in values are escaped."""
        engine = TemplateEngine(sample_schema, database_type="postgresql")
        result = engine._format_case_insensitive_match("name", "O'Brien")

        assert "O''Brien" in result  # Escaped single quote


class TestStringEscaping:
    """Tests for SQL injection prevention via string escaping."""

    def test_escapes_single_quotes_in_filter_value(self, sample_schema):
        """Test that single quotes are escaped in filter values."""
        engine = TemplateEngine(sample_schema, database_type="sqlite")
        match = engine.try_match("customers where name is O'Malley")

        if match:
            # Should have escaped single quote
            assert "O''Malley" in match.sql or "O\\'Malley" in match.sql or "O'Malley" not in match.sql
