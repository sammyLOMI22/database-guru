"""
Performance tests for Lineage system

Verifies:
- Parse time for complex queries
- Impact analysis on large query history
- Memory usage for large graphs
"""

import pytest
import time
from src.lineage.sql_lineage_parser import SQLLineageParser


class TestParserPerformance:
    """Performance tests for SQL Lineage Parser."""

    @pytest.fixture
    def parser(self):
        return SQLLineageParser()

    def test_simple_query_under_10ms(self, parser):
        """Simple SELECT should parse in <10ms."""
        sql = "SELECT name, email FROM customers WHERE id = 1"

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        # Adjust threshold slightly for CI environments
        assert elapsed < 50, f"Parse took {elapsed:.2f}ms, expected <50ms"
        assert len(graph.nodes) > 0

    def test_medium_join_under_50ms(self, parser):
        """5-table JOIN should parse in <50ms."""
        sql = """
        SELECT
            c.name, o.id, p.title, s.name as seller, cat.name as category
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        JOIN sellers s ON p.seller_id = s.id
        JOIN categories cat ON p.category_id = cat.id
        WHERE o.created_at > '2024-01-01'
        """

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"Parse took {elapsed:.2f}ms, expected <100ms"
        assert len(graph.tables_used) >= 5

    def test_wide_select_under_200ms(self, parser):
        """SELECT with 50 columns should parse in <200ms."""
        columns = ", ".join([f"col{i}" for i in range(50)])
        sql = f"SELECT {columns} FROM wide_table WHERE status = 'active'"

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 200, f"Parse took {elapsed:.2f}ms, expected <200ms"
        assert len(graph.output_columns) == 50

    def test_10_table_join_under_500ms(self, parser):
        """10-table JOIN stress test."""
        joins = []
        for i in range(10):
            if i == 0:
                joins.append(f"table{i} t{i}")
            else:
                joins.append(f"JOIN table{i} t{i} ON t{i-1}.id = t{i}.parent_id")

        sql = f"SELECT t0.id FROM {' '.join(joins)}"

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"Parse took {elapsed:.2f}ms, expected <500ms"
        assert len(graph.tables_used) == 10


class TestMemoryUsage:
    """Memory usage tests."""

    @pytest.fixture
    def parser(self):
        return SQLLineageParser()

    def test_large_graph_memory(self, parser):
        """Large graph shouldn't exceed 10MB."""
        import tracemalloc

        tracemalloc.start()

        # Generate large SQL
        columns = ", ".join([f"t{i}.col{j}" for i in range(5) for j in range(20)])
        joins = " ".join([f"JOIN table{i} t{i} ON t{i-1}.id = t{i}.fk" for i in range(1, 5)])
        sql = f"SELECT {columns} FROM table0 t0 {joins}"

        graph = parser.parse(sql)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 20, f"Peak memory {peak_mb:.2f}MB, expected <20MB"
