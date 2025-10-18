"""Tests for Schema Validator"""
import pytest
from src.core.schema_validator import (
    SchemaValidator,
    SchemaValidationError,
    JoinPath
)


@pytest.fixture
def ecommerce_schema():
    """Sample e-commerce database schema for testing"""
    return {
        "tables": {
            "customers": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "email", "type": "varchar"},
                    {"name": "state", "type": "varchar"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": []
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "customer_id", "type": "integer"},
                    {"name": "total_amount", "type": "decimal"},
                    {"name": "status", "type": "varchar"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [
                    {
                        "column": "customer_id",
                        "referred_table": "customers",
                        "referred_column": "id",
                        "constraint_name": "fk_customer"
                    }
                ],
                "indexes": []
            },
            "order_items": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "order_id", "type": "integer"},
                    {"name": "product_id", "type": "integer"},
                    {"name": "quantity", "type": "integer"},
                    {"name": "price", "type": "decimal"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [
                    {
                        "column": "order_id",
                        "referred_table": "orders",
                        "referred_column": "id",
                        "constraint_name": "fk_order"
                    },
                    {
                        "column": "product_id",
                        "referred_table": "products",
                        "referred_column": "id",
                        "constraint_name": "fk_product"
                    }
                ],
                "indexes": []
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "varchar"},
                    {"name": "price", "type": "decimal"},
                    {"name": "category", "type": "varchar"}
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
                "indexes": []
            }
        },
        "relationships": [
            {
                "from_table": "orders",
                "from_column": "customer_id",
                "to_table": "customers",
                "to_column": "id"
            },
            {
                "from_table": "order_items",
                "from_column": "order_id",
                "to_table": "orders",
                "to_column": "id"
            },
            {
                "from_table": "order_items",
                "from_column": "product_id",
                "to_table": "products",
                "to_column": "id"
            }
        ],
        "summary": {
            "table_count": 4,
            "total_columns": 17
        }
    }


class TestSchemaValidator:
    """Test SchemaValidator class"""

    def test_initialization(self, ecommerce_schema):
        """Test validator initialization"""
        validator = SchemaValidator(ecommerce_schema)

        assert len(validator.table_names) == 4
        assert "customers" in validator.table_names
        assert "orders" in validator.table_names
        assert "products" in validator.table_names
        assert "order_items" in validator.table_names

    def test_validate_table_valid(self, ecommerce_schema):
        """Test validating an existing table"""
        validator = SchemaValidator(ecommerce_schema)

        error = validator.validate_table("customers")
        assert error is None

    def test_validate_table_invalid(self, ecommerce_schema):
        """Test validating a non-existent table"""
        validator = SchemaValidator(ecommerce_schema)

        error = validator.validate_table("invalid_table")
        assert error is not None
        assert error.error_type == "missing_table"
        assert "invalid_table" in error.message

    def test_validate_table_suggestions(self, ecommerce_schema):
        """Test that similar table names are suggested"""
        validator = SchemaValidator(ecommerce_schema)

        # Typo: "costumers" instead of "customers"
        error = validator.validate_table("costumers")
        assert error is not None
        assert "customers" in error.suggestions

    def test_validate_column_valid(self, ecommerce_schema):
        """Test validating an existing column"""
        validator = SchemaValidator(ecommerce_schema)

        error = validator.validate_column("customers", "state")
        assert error is None

    def test_validate_column_invalid(self, ecommerce_schema):
        """Test validating a non-existent column"""
        validator = SchemaValidator(ecommerce_schema)

        # "shipping_address" doesn't exist in orders table
        error = validator.validate_column("orders", "shipping_address")
        assert error is not None
        assert error.error_type == "missing_column"
        assert "shipping_address" in error.message

    def test_validate_column_suggestions_same_table(self, ecommerce_schema):
        """Test column suggestions from same table"""
        validator = SchemaValidator(ecommerce_schema)

        # Typo: "custmer_id" instead of "customer_id"
        error = validator.validate_column("orders", "custmer_id")
        assert error is not None
        assert any("customer_id" in s for s in error.suggestions)

    def test_validate_column_suggestions_related_table(self, ecommerce_schema):
        """Test column suggestions from related tables"""
        validator = SchemaValidator(ecommerce_schema)

        # "state" exists in customers table, not orders
        error = validator.validate_column("orders", "state", check_related_tables=True)
        assert error is not None
        # Should suggest customers.state since orders is related to customers
        assert any("customers.state" in s for s in error.suggestions)

    def test_validate_column_invalid_table(self, ecommerce_schema):
        """Test validating column with invalid table"""
        validator = SchemaValidator(ecommerce_schema)

        error = validator.validate_column("invalid_table", "some_column")
        assert error is not None
        assert error.error_type == "missing_table"

    def test_find_join_path_direct(self, ecommerce_schema):
        """Test finding direct join path"""
        validator = SchemaValidator(ecommerce_schema)

        # Direct FK relationship: orders -> customers
        path = validator.find_join_path("orders", "customers")
        assert path is not None
        assert path.from_table == "orders"
        assert path.to_table == "customers"
        assert len(path.path) == 1
        assert path.path[0]["from_column"] == "customer_id"
        assert path.path[0]["to_column"] == "id"

    def test_find_join_path_multi_hop(self, ecommerce_schema):
        """Test finding multi-hop join path"""
        validator = SchemaValidator(ecommerce_schema)

        # Two hops: order_items -> orders -> customers
        path = validator.find_join_path("order_items", "customers")
        assert path is not None
        assert path.from_table == "order_items"
        assert path.to_table == "customers"
        assert len(path.path) == 2

    def test_find_join_path_no_path(self, ecommerce_schema):
        """Test when no join path exists"""
        # Create isolated table
        schema_with_isolated = ecommerce_schema.copy()
        schema_with_isolated["tables"]["isolated_table"] = {
            "columns": [{"name": "id", "type": "integer"}],
            "primary_keys": ["id"],
            "foreign_keys": [],
            "indexes": []
        }

        validator = SchemaValidator(schema_with_isolated)

        path = validator.find_join_path("isolated_table", "customers")
        assert path is None

    def test_validate_join_valid(self, ecommerce_schema):
        """Test validating a valid join"""
        validator = SchemaValidator(ecommerce_schema)

        error = validator.validate_join(
            "orders",
            "customers",
            "orders.customer_id = customers.id"
        )
        # Should find a valid relationship
        assert error is None

    def test_validate_join_invalid_tables(self, ecommerce_schema):
        """Test validating join with invalid table"""
        validator = SchemaValidator(ecommerce_schema)

        error = validator.validate_join(
            "invalid_table",
            "customers",
            "invalid_table.id = customers.id"
        )
        assert error is not None
        assert error.error_type == "missing_table"

    def test_suggest_join_conditions(self, ecommerce_schema):
        """Test suggesting join conditions"""
        validator = SchemaValidator(ecommerce_schema)

        suggestions = validator.suggest_join_conditions("orders", "customers")
        assert len(suggestions) > 0
        assert any("customer_id" in s for s in suggestions)

    def test_get_validation_report_no_errors(self, ecommerce_schema):
        """Test validation report with no errors"""
        validator = SchemaValidator(ecommerce_schema)

        report = validator.get_validation_report([])
        assert "no errors" in report.lower() or "passed" in report.lower()

    def test_get_validation_report_with_errors(self, ecommerce_schema):
        """Test validation report with errors"""
        validator = SchemaValidator(ecommerce_schema)

        errors = [
            SchemaValidationError(
                error_type="missing_table",
                message="Table 'foo' does not exist",
                table="foo",
                suggestions=["customers", "orders"]
            ),
            SchemaValidationError(
                error_type="missing_column",
                message="Column 'bar' does not exist",
                table="customers",
                column="bar",
                suggestions=["name", "email"]
            )
        ]

        report = validator.get_validation_report(errors)
        assert "2 error" in report
        assert "foo" in report
        assert "bar" in report
        assert "Suggestions" in report

    def test_find_similar_names(self, ecommerce_schema):
        """Test fuzzy name matching"""
        validator = SchemaValidator(ecommerce_schema)

        # Test with table names
        similar = validator._find_similar_names("costumer", validator.table_names)
        assert "customers" in similar

        # Test with column names (state vs status)
        columns = {"state", "status", "name", "email"}
        similar = validator._find_similar_names("stat", columns)
        assert len(similar) > 0
        assert "state" in similar or "status" in similar

    def test_get_related_tables(self, ecommerce_schema):
        """Test getting related tables"""
        validator = SchemaValidator(ecommerce_schema)

        # Orders is related to customers and order_items
        related = validator._get_related_tables("orders")
        assert "customers" in related  # orders references customers
        assert "order_items" in related  # order_items references orders

    def test_california_products_scenario(self, ecommerce_schema):
        """Test the California products scenario that failed"""
        validator = SchemaValidator(ecommerce_schema)

        # The original error: "shipping_address" doesn't exist in orders
        error = validator.validate_column("orders", "shipping_address", check_related_tables=True)
        assert error is not None
        assert error.error_type == "missing_column"

        # Should suggest looking in the customers table which has "state"
        # Since orders is related to customers via customer_id
        assert any("customers" in s for s in error.suggestions)

        # Validate the correct approach: state is in customers table
        error = validator.validate_column("customers", "state")
        assert error is None  # This should pass

        # Find join path from order_items to customers (for products shipped to CA)
        path = validator.find_join_path("order_items", "customers")
        assert path is not None
        assert len(path.path) == 2  # order_items -> orders -> customers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
