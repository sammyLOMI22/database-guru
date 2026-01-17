
import pytest
from datetime import datetime
import time
from src.core.query_compiler import QueryCompiler, CompiledQuery


@pytest.fixture
def compiler():
    # Reset singleton for fresh tests
    QueryCompiler._instance = None
    return QueryCompiler(max_cache_size=3)


class TestQueryCompiler:

    def test_normalize_simple_integers(self, compiler):
        sql = "SELECT * FROM users WHERE id = 123"
        template, params = compiler.normalize_query(sql)

        assert template == "SELECT * FROM users WHERE id = :p0"
        assert params == {"p0": 123}

    def test_normalize_strings(self, compiler):
        sql = "SELECT * FROM products WHERE category = 'electronics'"
        template, params = compiler.normalize_query(sql)

        assert template == "SELECT * FROM products WHERE category = :p0"
        assert params == {"p0": "electronics"}

    def test_normalize_mixed_types(self, compiler):
        sql = "SELECT * FROM orders WHERE user_id = 42 AND status = 'shipped' AND total > 99.99"
        template, params = compiler.normalize_query(sql)

        assert template == "SELECT * FROM orders WHERE user_id = :p0 AND status = :p1 AND total > :p2"
        assert params == {"p0": 42, "p1": "shipped", "p2": 99.99}

    def test_normalize_escaped_quotes(self, compiler):
        # Should unescape 'O''Reilly' to "O'Reilly"
        sql = "SELECT * FROM users WHERE name = 'O''Reilly'"
        template, params = compiler.normalize_query(sql)

        assert template == "SELECT * FROM users WHERE name = :p0"
        assert params == {"p0": "O'Reilly"}

    def test_normalize_double_quotes_ignored(self, compiler):
        # "Order 1" is an identifier, should NOT be parameterized
        # 'active' is a string literal, SHOULD be parameterized
        sql = 'SELECT * FROM "Order 1" WHERE status = \'active\''
        template, params = compiler.normalize_query(sql)

        assert template == 'SELECT * FROM "Order 1" WHERE status = :p0'
        assert params == {"p0": "active"}

    def test_cache_miss_on_first_query(self, compiler):
        sql = "SELECT * FROM items WHERE id = 1"
        compiled, params = compiler.get_compiled_query(sql)

        assert compiled is None
        assert params == {"p0": 1}

        stats = compiler.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    def test_compile_and_cache_hit(self, compiler):
        sql1 = "SELECT * FROM items WHERE id = 1"

        # First attempt: miss
        compiled, _ = compiler.get_compiled_query(sql1)
        assert compiled is None

        # Compile
        compiled_new, _ = compiler.compile_query(sql1)
        assert isinstance(compiled_new, CompiledQuery)
        assert compiled_new.execution_count == 0

        # Second attempt (same query): hit
        sql2 = "SELECT * FROM items WHERE id = 1"
        compiled_hit, params_hit = compiler.get_compiled_query(sql2)

        assert compiled_hit is not None
        assert compiled_hit.query_hash == compiled_new.query_hash
        assert params_hit == {"p0": 1}
        assert compiled_hit.execution_count == 1

        stats = compiler.get_stats()
        assert stats["hits"] == 1

    def test_parameter_variation_hit(self, compiler):
        sql1 = "SELECT * FROM items WHERE id = 1"
        compiler.compile_query(sql1)

        # Same structure, different value -> should hit same template
        sql2 = "SELECT * FROM items WHERE id = 999"
        compiled, params = compiler.get_compiled_query(sql2)

        assert compiled is not None
        assert params == {"p0": 999}
        assert compiled.sql_template == "SELECT * FROM items WHERE id = :p0"

    def test_lru_eviction(self, compiler):
        # Clear singleton state for test
        compiler.compiled_queries.clear()

        # Fill cache (size 3)
        compiler.compile_query("SELECT * FROM t1 WHERE id = 1")  # 1st (oldest)
        compiler.compile_query("SELECT * FROM t2 WHERE id = 1")  # 2nd
        compiler.compile_query("SELECT * FROM t3 WHERE id = 1")  # 3rd (newest)

        assert len(compiler.compiled_queries) == 3

        # Access t1 to update recency (moves t1 to end/newest)
        # Order becomes: t2, t3, t1
        compiler.get_compiled_query("SELECT * FROM t1 WHERE id = 2")

        # Add 4th item - should evict oldest (t2)
        compiler.compile_query("SELECT * FROM t4 WHERE id = 1")

        # Check size maintained
        assert len(compiler.compiled_queries) == 3

        # t2 should be gone (sqlparse preserves whitespace: "= :p0")
        template_t2 = "SELECT * FROM t2 WHERE id = :p0"
        hash_t2 = compiler._generate_hash(template_t2)
        assert hash_t2 not in compiler.compiled_queries

        # t1 should be present
        template_t1 = "SELECT * FROM t1 WHERE id = :p0"
        hash_t1 = compiler._generate_hash(template_t1)
        assert hash_t1 in compiler.compiled_queries

    def test_stats_tracking(self, compiler):
        sql = "SELECT * FROM test WHERE id = 1"
        compiled, _ = compiler.compile_query(sql)

        compiler.update_stats(compiled, 100.0)  # 100ms
        assert compiled.avg_execution_ms == 100.0

        # Manually increment execution count as get_compiled_query does
        compiled.execution_count = 2
        compiler.update_stats(compiled, 50.0)  # 50ms

        # (100 * 1 + 50) / 2 = 75
        assert compiled.avg_execution_ms == 75.0

    # ============ NEW EDGE CASE TESTS ============

    def test_normalize_negative_numbers(self, compiler):
        """Critical fix: negative numbers should be parameterized correctly"""
        sql = "SELECT * FROM accounts WHERE balance < -100"
        template, params = compiler.normalize_query(sql)

        assert params == {"p0": -100}
        assert "<:p0" in template or "< :p0" in template

    def test_normalize_negative_decimals(self, compiler):
        """Negative decimal numbers should work"""
        sql = "SELECT * FROM t WHERE val <= -99.99"
        template, params = compiler.normalize_query(sql)

        assert params == {"p0": -99.99}

    def test_strip_single_line_comments(self, compiler):
        """Numbers in single-line comments should NOT be parameterized"""
        sql = "SELECT * FROM t WHERE id = 1 -- this is 1"
        template, params = compiler.normalize_query(sql)

        # Should only have 1 parameter (the WHERE value), not 2
        assert len(params) == 1
        assert params == {"p0": 1}

    def test_strip_multi_line_comments(self, compiler):
        """Numbers in multi-line comments should NOT be parameterized"""
        sql = "SELECT * FROM t WHERE id = 5 /* comment with 123 */ AND x = 10"
        template, params = compiler.normalize_query(sql)

        # Should only have 2 parameters (5 and 10), not 3
        assert len(params) == 2
        assert params == {"p0": 5, "p1": 10}

    def test_preserve_array_literals(self, compiler):
        """DuckDB/PostgreSQL array literals should be preserved"""
        sql = "SELECT * FROM t WHERE tags @> ['tag1', 'tag2']"
        template, params = compiler.normalize_query(sql)

        # Array should be preserved as-is
        assert "['tag1', 'tag2']" in template
        # No params extracted from array
        assert len(params) == 0

    def test_scientific_notation(self, compiler):
        """Scientific notation should be parameterized"""
        sql = "SELECT * FROM t WHERE val > 1e10"
        template, params = compiler.normalize_query(sql)

        assert params == {"p0": 1e10}

    def test_preserve_identifiers_with_numbers(self, compiler):
        """Column names like col1, table2 should NOT be parameterized"""
        sql = "SELECT col1, col2 FROM table1 WHERE id = 123"
        template, params = compiler.normalize_query(sql)

        assert "col1" in template
        assert "col2" in template
        assert "table1" in template
        assert params == {"p0": 123}

    def test_in_clause_values(self, compiler):
        """Values in IN clause should be parameterized"""
        sql = "SELECT * FROM t WHERE status IN ('a', 'b', 'c')"
        template, params = compiler.normalize_query(sql)

        assert params == {"p0": "a", "p1": "b", "p2": "c"}

    def test_between_clause_values(self, compiler):
        """Values in BETWEEN clause should be parameterized"""
        sql = "SELECT * FROM t WHERE id BETWEEN 1 AND 100"
        template, params = compiler.normalize_query(sql)

        assert params.get("p0") == 1
        assert params.get("p1") == 100

    def test_limit_offset_values(self, compiler):
        """LIMIT and OFFSET values should be parameterized"""
        sql = "SELECT * FROM t LIMIT 10 OFFSET 20"
        template, params = compiler.normalize_query(sql)

        # Standalone numbers should be captured
        assert 10 in params.values()
        assert 20 in params.values()

    def test_comment_inside_string_preserved(self, compiler):
        """Comment-like content inside strings should be preserved"""
        sql = "SELECT * FROM t WHERE note = '-- this is not a comment'"
        template, params = compiler.normalize_query(sql)

        # The string content should be captured as-is
        assert params == {"p0": "-- this is not a comment"}
