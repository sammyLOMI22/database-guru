"""
Unit tests for SQLNormalizer

Tests cover:
- Basic normalization (simple WHERE clauses)
- Edge cases (NULL, TRUE, FALSE, special keywords)
- Complex patterns (IN clauses, LIKE patterns, ranges)
- Structural preservation (LIMIT, OFFSET)
- Type inference
- Hash stability
- Metadata extraction
- Error handling
"""

import pytest
from src.core.sql_normalizer import SQLNormalizer, NormalizedQuery, get_normalizer


class TestSQLNormalizerBasic:
    """Test basic SQL normalization"""

    def test_normalize_simple_where_clause(self):
        """Test normalization of simple WHERE clause with literals"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM products WHERE id = 123"
        result = normalizer.normalize(sql)

        assert result.template == "SELECT * FROM products WHERE id = :p0"
        assert result.parameters == {'p0': 123}
        assert result.parameter_types == {'p0': 'int'}
        assert result.original_sql == sql
        assert len(result.normalization_hash) == 16

    def test_normalize_string_literal(self):
        """Test normalization of string literals"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM users WHERE name = 'John'"
        result = normalizer.normalize(sql)

        assert ":p" in result.template
        assert 'John' in result.parameters.values()
        assert result.parameter_types['p0'] == 'str'

    def test_normalize_multiple_parameters(self):
        """Test normalization with multiple parameters"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM products WHERE category = 'electronics' AND price > 100"
        result = normalizer.normalize(sql)

        assert ':p0' in result.template
        assert ':p1' in result.template
        assert len(result.parameters) == 2
        assert result.parameters['p0'] == 'electronics'
        assert result.parameters['p1'] == 100

    def test_normalize_float_literal(self):
        """Test normalization of float literals"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM products WHERE price > 19.99"
        result = normalizer.normalize(sql)

        assert result.parameters['p0'] == 19.99
        assert result.parameter_types['p0'] == 'float'

    def test_normalize_multiple_same_table(self):
        """Test normalizing query with same literal appearing twice"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM users WHERE age > 18 AND age < 65"
        result = normalizer.normalize(sql)

        # Each occurrence should be a separate parameter
        assert len(result.parameters) == 2
        assert 18 in result.parameters.values()
        assert 65 in result.parameters.values()


class TestSQLNormalizerEdgeCases:
    """Test edge cases and special keywords"""

    def test_preserve_null_keyword(self):
        """Test that NULL keyword is preserved"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM users WHERE email = NULL"
        result = normalizer.normalize(sql)

        # NULL should NOT be parameterized
        assert "NULL" in result.template
        assert len(result.parameters) == 0

    def test_preserve_true_false_keywords(self):
        """Test that TRUE/FALSE keywords are preserved"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM users WHERE is_active = TRUE"
        result = normalizer.normalize(sql)

        assert "TRUE" in result.template
        assert len(result.parameters) == 0

    def test_preserve_current_timestamp(self):
        """Test that CURRENT_TIMESTAMP is preserved"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM events WHERE created_at > CURRENT_TIMESTAMP"
        result = normalizer.normalize(sql)

        assert "CURRENT_TIMESTAMP" in result.template
        assert len(result.parameters) == 0

    def test_preserve_limit_clause(self):
        """Test that LIMIT values are preserved (not parameterized)"""
        normalizer = SQLNormalizer(preserve_limit=True)

        sql = "SELECT * FROM users LIMIT 10"
        result = normalizer.normalize(sql)

        # LIMIT 10 should be preserved as-is
        assert "LIMIT 10" in result.template
        assert len(result.parameters) == 0

    def test_preserve_offset_clause(self):
        """Test that OFFSET values are preserved"""
        normalizer = SQLNormalizer(preserve_offset=True)

        sql = "SELECT * FROM users LIMIT 10 OFFSET 20"
        result = normalizer.normalize(sql)

        assert "OFFSET 20" in result.template
        assert len(result.parameters) == 0

    def test_escaped_single_quotes_in_string(self):
        """Test handling of escaped single quotes in strings"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM messages WHERE content = 'It''s a test'"
        result = normalizer.normalize(sql)

        # Should extract the string with escaped quotes handled
        assert len(result.parameters) == 1
        assert "It's a test" in result.parameters.values()

    def test_double_quoted_string(self):
        """Test handling of double-quoted strings"""
        normalizer = SQLNormalizer()

        sql = 'SELECT * FROM users WHERE name = "Alice"'
        result = normalizer.normalize(sql)

        assert len(result.parameters) == 1
        assert 'Alice' in result.parameters.values()


class TestSQLNormalizerComplexPatterns:
    """Test complex SQL patterns"""

    def test_in_clause_with_multiple_values(self):
        """Test normalization of IN clause"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM products WHERE id IN (1, 2, 3)"
        result = normalizer.normalize(sql)

        # Each value in IN clause should be parameterized
        assert len(result.parameters) >= 3
        assert 1 in result.parameters.values()
        assert 2 in result.parameters.values()
        assert 3 in result.parameters.values()

    def test_like_pattern(self):
        """Test normalization of LIKE pattern"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM users WHERE name LIKE '%John%'"
        result = normalizer.normalize(sql)

        assert len(result.parameters) == 1
        assert '%John%' in result.parameters.values()

    def test_between_clause(self):
        """Test normalization of BETWEEN clause"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM products WHERE price BETWEEN 10 AND 100"
        result = normalizer.normalize(sql)

        # Both values should be parameterized
        assert 10 in result.parameters.values()
        assert 100 in result.parameters.values()

    def test_multiple_join_conditions(self):
        """Test query with multiple joins"""
        normalizer = SQLNormalizer()

        sql = """SELECT * FROM orders o
                 JOIN customers c ON o.customer_id = c.id
                 WHERE o.status = 'completed' AND o.amount > 1000"""
        result = normalizer.normalize(sql)

        assert 'completed' in result.parameters.values()
        assert 1000 in result.parameters.values()

    def test_subquery(self):
        """Test query with subquery"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 500)"
        result = normalizer.normalize(sql)

        assert 500 in result.parameters.values()
        assert result.metadata.get('has_subquery') is True

    def test_union_queries(self):
        """Test UNION query"""
        normalizer = SQLNormalizer()

        sql = """SELECT name FROM users WHERE status = 'active'
                 UNION
                 SELECT name FROM customers WHERE status = 'active'"""
        result = normalizer.normalize(sql)

        # Both 'active' values should be parameterized
        assert 'active' in result.parameters.values()


class TestSQLNormalizerMetadata:
    """Test metadata extraction"""

    def test_extract_query_type(self):
        """Test extraction of query type"""
        normalizer = SQLNormalizer()

        queries = [
            ("SELECT * FROM users", "SELECT"),
            ("INSERT INTO users (name) VALUES ('John')", "INSERT"),
            ("UPDATE users SET name = 'Jane' WHERE id = 1", "UPDATE"),
            ("DELETE FROM users WHERE id = 1", "DELETE"),
        ]

        for sql, expected_type in queries:
            result = normalizer.normalize(sql)
            assert result.metadata['query_type'] == expected_type

    def test_extract_tables(self):
        """Test extraction of table names"""
        normalizer = SQLNormalizer()

        sql = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id"
        result = normalizer.normalize(sql)

        tables = result.metadata['tables']
        assert 'orders' in tables
        assert 'customers' in tables

    def test_detect_aggregation(self):
        """Test detection of aggregation functions"""
        normalizer = SQLNormalizer()

        # Query with aggregation
        sql_agg = "SELECT COUNT(*) FROM users WHERE status = 'active'"
        result_agg = normalizer.normalize(sql_agg)
        assert result_agg.metadata['has_aggregation'] is True

        # Query without aggregation
        sql_no_agg = "SELECT * FROM users WHERE status = 'active'"
        result_no_agg = normalizer.normalize(sql_no_agg)
        assert result_no_agg.metadata['has_aggregation'] is False

    def test_detect_join(self):
        """Test detection of JOIN keyword"""
        normalizer = SQLNormalizer()

        sql_join = "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id"
        result_join = normalizer.normalize(sql_join)
        assert result_join.metadata['has_join'] is True

        sql_no_join = "SELECT * FROM users WHERE id = 1"
        result_no_join = normalizer.normalize(sql_no_join)
        assert result_no_join.metadata['has_join'] is False


class TestSQLNormalizerHash:
    """Test hash generation and stability"""

    def test_hash_stability_same_template(self):
        """Test that same template produces same hash"""
        normalizer = SQLNormalizer()

        sql1 = "SELECT * FROM products WHERE category = 'electronics' AND price > 100"
        sql2 = "SELECT * FROM products WHERE category = 'books' AND price > 200"

        result1 = normalizer.normalize(sql1)
        result2 = normalizer.normalize(sql2)

        # Different values, but same template structure and types
        assert result1.template == result2.template
        assert result1.normalization_hash == result2.normalization_hash

    def test_hash_differs_by_template(self):
        """Test that different templates produce different hashes"""
        normalizer = SQLNormalizer()

        sql1 = "SELECT * FROM products WHERE id = 1"
        sql2 = "SELECT * FROM users WHERE id = 1"

        result1 = normalizer.normalize(sql1)
        result2 = normalizer.normalize(sql2)

        assert result1.normalization_hash != result2.normalization_hash

    def test_hash_differs_by_type(self):
        """Test that different parameter types produce different hashes"""
        normalizer = SQLNormalizer()

        sql1 = "SELECT * FROM products WHERE id = 1"
        sql2 = "SELECT * FROM products WHERE id = '1'"

        result1 = normalizer.normalize(sql1)
        result2 = normalizer.normalize(sql2)

        assert result1.parameter_types['p0'] == 'int'
        assert result2.parameter_types['p0'] == 'str'
        assert result1.normalization_hash != result2.normalization_hash

    def test_hash_is_16_chars(self):
        """Test that hash is always 16 characters"""
        normalizer = SQLNormalizer()

        queries = [
            "SELECT * FROM users",
            "SELECT * FROM users WHERE id = 1 AND name = 'John' AND status = 'active'",
            "INSERT INTO logs (event, value) VALUES ('test', 42)",
        ]

        for sql in queries:
            result = normalizer.normalize(sql)
            assert len(result.normalization_hash) == 16
            assert all(c in '0123456789abcdef' for c in result.normalization_hash)


class TestSQLNormalizerErrors:
    """Test error handling"""

    def test_empty_sql_raises_error(self):
        """Test that empty SQL raises ValueError"""
        normalizer = SQLNormalizer()

        with pytest.raises(ValueError):
            normalizer.normalize("")

    def test_whitespace_only_sql_raises_error(self):
        """Test that whitespace-only SQL raises ValueError"""
        normalizer = SQLNormalizer()

        with pytest.raises(ValueError):
            normalizer.normalize("   \n\t  ")

    def test_none_sql_raises_error(self):
        """Test that None SQL raises ValueError"""
        normalizer = SQLNormalizer()

        with pytest.raises(ValueError):
            normalizer.normalize(None)


class TestSQLNormalizerStats:
    """Test statistics tracking"""

    def test_stats_tracking(self):
        """Test that stats are tracked correctly"""
        normalizer = SQLNormalizer()

        # Normalize multiple queries
        sql1 = "SELECT * FROM users WHERE id = 1"
        sql2 = "SELECT * FROM products WHERE category = 'electronics' AND price > 100"

        normalizer.normalize(sql1)
        normalizer.normalize(sql2)

        stats = normalizer.get_stats()

        assert stats['queries_normalized'] == 2
        assert stats['total_parameters_extracted'] >= 3  # At least 1 from sql1, 2 from sql2
        assert stats['avg_parameters_per_query'] > 0


class TestSQLNormalizerSingleton:
    """Test singleton pattern"""

    def test_get_normalizer_returns_singleton(self):
        """Test that get_normalizer returns same instance"""
        normalizer1 = get_normalizer()
        normalizer2 = get_normalizer()

        assert normalizer1 is normalizer2


class TestSQLNormalizerIntegration:
    """Integration tests with realistic SQL patterns"""

    def test_realistic_e_commerce_query(self):
        """Test realistic e-commerce query"""
        normalizer = SQLNormalizer()

        sql = """
            SELECT p.id, p.name, COUNT(o.id) as order_count
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id
            WHERE p.category = 'electronics'
              AND p.price > 100
              AND p.price < 1000
              AND o.status IN ('completed', 'pending')
              AND o.created_at > '2025-01-01'
            GROUP BY p.id, p.name
            LIMIT 50
        """

        result = normalizer.normalize(sql)

        assert len(result.parameters) > 0
        assert result.metadata['has_join'] is True
        assert result.metadata['has_aggregation'] is True
        assert 'electronics' in result.parameters.values()
        assert 100 in result.parameters.values()
        assert 1000 in result.parameters.values()
        assert 'LIMIT 50' in result.template  # LIMIT preserved

    def test_realistic_reporting_query(self):
        """Test realistic reporting query"""
        normalizer = SQLNormalizer()

        sql = """
            SELECT
                DATE(created_at) as date,
                SUM(amount) as total_sales,
                COUNT(*) as order_count
            FROM orders
            WHERE status = 'completed'
              AND created_at >= '2025-01-01'
              AND created_at < '2025-12-31'
              AND amount > 0
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """

        result = normalizer.normalize(sql)

        assert 'completed' in result.parameters.values()
        assert result.metadata['has_aggregation'] is True
        assert result.metadata['query_type'] == 'SELECT'

    def test_case_insensitive_keyword_preservation(self):
        """Test that keyword preservation is case-insensitive"""
        normalizer = SQLNormalizer()

        # Test with lowercase 'null'
        sql_lower = "SELECT * FROM users WHERE email = null"
        result_lower = normalizer.normalize(sql_lower)

        # Test with uppercase 'NULL'
        sql_upper = "SELECT * FROM users WHERE email = NULL"
        result_upper = normalizer.normalize(sql_upper)

        # Both should preserve NULL and not parameterize
        assert len(result_lower.parameters) == 0
        assert len(result_upper.parameters) == 0


class TestSQLNormalizerPerformance:
    """Test performance characteristics"""

    def test_normalization_is_fast(self):
        """Test that normalization completes in reasonable time"""
        import time

        normalizer = SQLNormalizer()

        sql = "SELECT * FROM products WHERE category = 'electronics' AND price > 100"

        start = time.time()
        for _ in range(100):
            normalizer.normalize(sql)
        elapsed = time.time() - start

        # 100 normalizations should complete in < 1 second
        assert elapsed < 1.0, f"Normalization too slow: {elapsed}s for 100 queries"

    def test_large_query_normalization(self):
        """Test normalization of large query"""
        normalizer = SQLNormalizer()

        # Build large IN clause
        sql = "SELECT * FROM products WHERE id IN (" + ",".join(str(i) for i in range(100)) + ")"

        result = normalizer.normalize(sql)

        # Should handle large queries gracefully
        assert len(result.parameters) == 100
        assert result.normalization_hash is not None
