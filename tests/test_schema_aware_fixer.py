"""Tests for schema-aware SQL fixer"""
import pytest
from src.llm.schema_aware_fixer import SchemaAwareFixer, FuzzyMatcher, QuickFix
from src.llm.self_correcting_agent import ErrorType


# Sample schema for testing
SAMPLE_SCHEMA = {
    "tables": {
        "products": {
            "columns": ["id", "name", "price", "category_id", "stock_quantity"],
            "primary_key": "id",
        },
        "customers": {
            "columns": ["id", "name", "email", "phone", "created_at"],
            "primary_key": "id",
        },
        "orders": {
            "columns": ["id", "customer_id", "total_amount", "order_date", "status"],
            "primary_key": "id",
        },
        "categories": {
            "columns": ["id", "name", "description"],
            "primary_key": "id",
        }
    }
}


class TestFuzzyMatcher:
    """Test fuzzy string matching"""

    def test_exact_match(self):
        """Test exact string match"""
        similarity = FuzzyMatcher.similarity("products", "products")
        assert similarity == 1.0

    def test_close_match(self):
        """Test close but not exact match"""
        similarity = FuzzyMatcher.similarity("prodcuts", "products")
        assert similarity > 0.7  # Should be high similarity

    def test_different_strings(self):
        """Test completely different strings"""
        similarity = FuzzyMatcher.similarity("products", "customers")
        assert similarity < 0.5  # Should be low similarity

    def test_case_insensitive(self):
        """Test that matching is case-insensitive"""
        similarity = FuzzyMatcher.similarity("Products", "products")
        assert similarity == 1.0

    def test_find_closest_match(self):
        """Test finding closest match from candidates"""
        candidates = ["products", "customers", "orders"]
        matches = FuzzyMatcher.find_closest("prodcuts", candidates, threshold=0.6)

        assert len(matches) > 0
        assert matches[0][0] == "products"  # Best match should be "products"
        assert matches[0][1] > 0.7  # High similarity

    def test_find_closest_no_match(self):
        """Test when no good match exists"""
        candidates = ["customers", "orders"]
        matches = FuzzyMatcher.find_closest("xyz123", candidates, threshold=0.6)

        assert len(matches) == 0  # No matches above threshold

    def test_find_best_match(self):
        """Test finding single best match"""
        candidates = ["products", "customers", "orders"]
        match = FuzzyMatcher.find_best_match("prodct", candidates, threshold=0.6)

        assert match is not None
        assert match[0] == "products"
        assert match[1] > 0.6


class TestSchemaAwareFixer:
    """Test schema-aware SQL fixer"""

    @pytest.fixture
    def fixer(self):
        """Create fixer instance with sample schema"""
        return SchemaAwareFixer(SAMPLE_SCHEMA)

    def test_init_builds_caches(self, fixer):
        """Test that initialization builds lookup caches"""
        assert len(fixer.table_names) == 4
        assert "products" in fixer.table_names
        assert "customers" in fixer.table_names

        assert "products" in fixer.columns_by_table
        assert "price" in fixer.columns_by_table["products"]

        assert len(fixer.all_columns) > 0

    def test_fix_table_typo(self, fixer):
        """Test fixing table name typo"""
        sql = "SELECT * FROM prodcuts LIMIT 10"
        error_msg = 'relation "prodcuts" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        assert fix.success is True
        assert fix.correction_type == "table_name"
        assert fix.original_value == "prodcuts"
        assert fix.corrected_value == "products"
        assert fix.confidence > 0.7
        assert "products" in fix.fixed_sql
        assert "prodcuts" not in fix.fixed_sql.lower()

    def test_fix_column_typo(self, fixer):
        """Test fixing column name typo"""
        sql = "SELECT id, nam, price FROM products"
        error_msg = 'column "nam" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.COLUMN_NOT_FOUND,
            error_message=error_msg
        )

        assert fix.success is True
        assert fix.correction_type == "column_name"
        assert fix.original_value == "nam"
        assert fix.corrected_value == "name"
        assert "name" in fix.fixed_sql

    def test_fix_column_with_table_context(self, fixer):
        """Test fixing column with table context"""
        sql = "SELECT pric FROM products WHERE id = 1"
        error_msg = 'column "pric" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.COLUMN_NOT_FOUND,
            error_message=error_msg,
            context={"table": "products"}
        )

        assert fix.success is True
        assert fix.corrected_value == "price"

    def test_no_fix_for_unknown_error(self, fixer):
        """Test that unknown error types return no fix"""
        sql = "SELECT * FROM products"
        error_msg = "some random error"

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.PERMISSION_DENIED,
            error_message=error_msg
        )

        assert fix.success is False

    def test_no_fix_for_low_confidence(self, fixer):
        """Test that low confidence matches are rejected"""
        sql = "SELECT * FROM xyz123"
        error_msg = 'table "xyz123" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        # Should fail because xyz123 doesn't match any table well
        assert fix.success is False or fix.confidence < 0.7

    def test_extract_table_name(self, fixer):
        """Test extracting table name from error message"""
        error = 'relation "products" does not exist'
        table = fixer._extract_table_name(error)
        assert table == "products"

        error2 = 'no such table: customers'
        table2 = fixer._extract_table_name(error2)
        assert table2 == "customers"

    def test_extract_column_name(self, fixer):
        """Test extracting column name from error message"""
        error = 'column "price" does not exist'
        column = fixer._extract_column_name(error)
        assert column == "price"

        error2 = 'no such column: name'
        column2 = fixer._extract_column_name(error2)
        assert column2 == "name"

    def test_identify_table_from_sql(self, fixer):
        """Test identifying table from SQL"""
        sql = "SELECT * FROM products WHERE price > 10"
        table = fixer._identify_table_from_sql(sql)
        assert table == "products"

        sql2 = "SELECT p.name FROM products p JOIN categories c ON p.category_id = c.id"
        table2 = fixer._identify_table_from_sql(sql2)
        assert table2 == "products"

    def test_replace_table_name(self, fixer):
        """Test replacing table name in SQL"""
        sql = "SELECT * FROM prodcuts WHERE id = 1"
        fixed = fixer._replace_table_name(sql, "prodcuts", "products")
        assert fixed == "SELECT * FROM products WHERE id = 1"

    def test_replace_column_name(self, fixer):
        """Test replacing column name in SQL"""
        sql = "SELECT nam, price FROM products"
        fixed = fixer._replace_column_name(sql, "nam", "name")
        assert fixed == "SELECT name, price FROM products"

    def test_word_boundary_replacement(self, fixer):
        """Test that replacements respect word boundaries"""
        # Should not replace "name" inside "username"
        sql = "SELECT username FROM users WHERE name = 'John'"
        fixed = fixer._replace_column_name(sql, "user", "customer")
        # "user" in "username" should NOT be replaced
        assert "username" in fixed or "customer" not in fixed.split("username")[0]

    def test_case_insensitive_matching(self, fixer):
        """Test that matching works regardless of case"""
        sql = "SELECT * FROM PRODUCTS"
        error_msg = 'table "PRODUCTS" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        # Should still match "products" (lowercase in schema)
        assert fix.success is True or fix.corrected_value == "products"

    def test_plural_singular_confusion(self, fixer):
        """Test fixing plural/singular confusion"""
        sql = "SELECT * FROM product"  # Missing 's'
        error_msg = 'table "product" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        assert fix.success is True
        assert fix.corrected_value == "products"

    def test_correction_stats(self, fixer):
        """Test getting correction statistics"""
        stats = fixer.get_correction_stats()

        assert stats["total_tables"] == 4
        assert stats["total_columns"] > 0
        assert stats["average_columns_per_table"] > 0

    def test_multiple_typos_in_query(self, fixer):
        """Test fixing query with multiple potential typos"""
        sql = "SELECT nam, pric FROM prodcuts"
        error_msg = 'table "prodcuts" does not exist'

        # First fix table
        fix1 = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        assert fix1.success is True
        assert "products" in fix1.fixed_sql

        # Then fix columns
        sql2 = fix1.fixed_sql
        error_msg2 = 'column "nam" does not exist'

        fix2 = fixer.quick_fix(
            sql=sql2,
            error_type=ErrorType.COLUMN_NOT_FOUND,
            error_message=error_msg2
        )

        assert fix2.success is True
        assert "name" in fix2.fixed_sql


class TestQuickFixDataclass:
    """Test QuickFix dataclass"""

    def test_quick_fix_success(self):
        """Test successful quick fix"""
        fix = QuickFix(
            success=True,
            fixed_sql="SELECT * FROM products",
            correction_type="table_name",
            original_value="prodcuts",
            corrected_value="products",
            confidence=0.9,
            explanation="Corrected table name"
        )

        assert fix.success is True
        assert fix.confidence == 0.9
        assert fix.corrected_value == "products"

    def test_quick_fix_failure(self):
        """Test failed quick fix"""
        fix = QuickFix(success=False)

        assert fix.success is False
        assert fix.fixed_sql is None
        assert fix.confidence == 0.0


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    @pytest.fixture
    def fixer(self):
        return SchemaAwareFixer(SAMPLE_SCHEMA)

    def test_ecommerce_query_typo(self, fixer):
        """Test realistic e-commerce query with typo"""
        sql = "SELECT p.name, p.pric FROM prodcuts p WHERE p.stock_quantity > 0"
        error_msg = 'table "prodcuts" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        assert fix.success is True
        assert "products" in fix.fixed_sql
        assert fix.confidence > 0.7

    def test_join_query_typo(self, fixer):
        """Test JOIN query with table typo"""
        sql = """
        SELECT o.id, c.name
        FROM ordes o
        JOIN customers c ON o.customer_id = c.id
        """
        error_msg = 'table "ordes" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.TABLE_NOT_FOUND,
            error_message=error_msg
        )

        assert fix.success is True
        assert "orders" in fix.fixed_sql

    def test_aggregate_query_column_typo(self, fixer):
        """Test aggregate query with column typo"""
        sql = "SELECT COUNT(*), AVG(tota_amount) FROM orders"
        error_msg = 'column "tota_amount" does not exist'

        fix = fixer.quick_fix(
            sql=sql,
            error_type=ErrorType.COLUMN_NOT_FOUND,
            error_message=error_msg
        )

        assert fix.success is True
        assert "total_amount" in fix.fixed_sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
