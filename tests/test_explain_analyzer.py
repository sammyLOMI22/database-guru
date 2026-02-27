"""Tests for Phase 22.1: Explain Analyzer"""

import pytest
from src.guru.explain_analyzer import ExplainAnalyzer, PlanNode, ExecutionPlan


@pytest.fixture
def analyzer():
    return ExplainAnalyzer()


# ============================================================================
# build_explain_sql tests
# ============================================================================

class TestBuildExplainSQL:
    def test_postgresql_no_analyze(self, analyzer):
        result = analyzer.build_explain_sql("SELECT * FROM orders", "postgresql")
        assert result == "EXPLAIN SELECT * FROM orders"

    def test_postgresql_with_analyze(self, analyzer):
        result = analyzer.build_explain_sql("SELECT * FROM orders", "postgresql", analyze=True)
        assert result == "EXPLAIN (ANALYZE, FORMAT TEXT) SELECT * FROM orders"

    def test_postgres_alias(self, analyzer):
        result = analyzer.build_explain_sql("SELECT 1", "postgres")
        assert result == "EXPLAIN SELECT 1"

    def test_mysql_no_analyze(self, analyzer):
        result = analyzer.build_explain_sql("SELECT * FROM users", "mysql")
        assert result == "EXPLAIN SELECT * FROM users"

    def test_mysql_analyze_ignored(self, analyzer):
        """MySQL EXPLAIN doesn't support ANALYZE in all versions."""
        result = analyzer.build_explain_sql("SELECT * FROM users", "mysql", analyze=True)
        assert result == "EXPLAIN SELECT * FROM users"

    def test_sqlite(self, analyzer):
        result = analyzer.build_explain_sql("SELECT * FROM t", "sqlite")
        assert result == "EXPLAIN QUERY PLAN SELECT * FROM t"

    def test_sqlite_analyze_ignored(self, analyzer):
        result = analyzer.build_explain_sql("SELECT * FROM t", "sqlite", analyze=True)
        assert result == "EXPLAIN QUERY PLAN SELECT * FROM t"

    def test_duckdb_no_analyze(self, analyzer):
        result = analyzer.build_explain_sql("SELECT 1", "duckdb")
        assert result == "EXPLAIN SELECT 1"

    def test_duckdb_with_analyze(self, analyzer):
        result = analyzer.build_explain_sql("SELECT 1", "duckdb", analyze=True)
        assert result == "EXPLAIN ANALYZE SELECT 1"

    def test_unknown_dialect(self, analyzer):
        result = analyzer.build_explain_sql("SELECT 1", "oracle")
        assert result == "EXPLAIN SELECT 1"


# ============================================================================
# PostgreSQL plan parsing tests
# ============================================================================

class TestParsePostgreSQL:
    def test_seq_scan(self, analyzer):
        rows = [
            ("Seq Scan on orders  (cost=0.00..1823.00 rows=10000 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders", False)

        assert plan.has_seq_scans is True
        assert "orders" in plan.seq_scan_tables
        assert plan.node_count == 1
        assert plan.root_node.node_type == "Seq Scan"
        assert plan.root_node.relation == "orders"
        assert plan.root_node.cost_total == 1823.00
        assert plan.root_node.rows_estimated == 10000

    def test_index_scan(self, analyzer):
        rows = [
            ("Index Scan using idx_orders_id on orders  (cost=0.28..8.30 rows=1 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders WHERE id=1", False)

        assert plan.has_seq_scans is False
        assert plan.node_count == 1
        assert plan.root_node.node_type == "Index Scan"
        assert plan.root_node.index_name == "idx_orders_id"
        assert plan.root_node.relation == "orders"

    def test_analyze_output(self, analyzer):
        rows = [
            ("Seq Scan on orders  (cost=0.00..1823.00 rows=10000 width=8) (actual time=0.041..15.234 rows=847 loops=1)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders", True)

        assert plan.analyzed is True
        assert plan.root_node.actual_time_ms == 15.234
        assert plan.root_node.rows_actual == 847
        assert plan.root_node.loops == 1
        assert plan.total_actual_time_ms == 15.234

    def test_hash_join_tree(self, analyzer):
        rows = [
            ("Hash Join  (cost=24.00..2847.00 rows=1000 width=16)",),
            ("  Hash Cond: (o.customer_id = c.id)",),
            ("  ->  Seq Scan on orders o  (cost=0.00..1823.00 rows=15000 width=8)",),
            ("        Filter: (status = 'pending')",),
            ("  ->  Hash  (cost=24.00..24.00 rows=1000 width=8)",),
            ("        ->  Seq Scan on customers c  (cost=0.00..24.00 rows=1000 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.status='pending'", False)

        assert plan.node_count >= 2
        assert plan.has_seq_scans is True
        assert "orders" in plan.seq_scan_tables or any("order" in t for t in plan.seq_scan_tables)
        assert plan.root_node.node_type == "Hash Join"
        assert plan.root_node.join_type == "Hash Join"

    def test_disk_spill_sort(self, analyzer):
        rows = [
            ("Sort  (cost=1000.00..1050.00 rows=10000 width=8)",),
            ("  Sort Key: created_at",),
            ("  Sort Method: external merge  Disk: 4096kB",),
            ("  ->  Seq Scan on orders  (cost=0.00..800.00 rows=10000 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders ORDER BY created_at", False)

        assert plan.has_disk_spill is True

    def test_disk_spill_batches(self, analyzer):
        rows = [
            ("Hash Join  (cost=100.00..500.00 rows=1000 width=16)",),
            ("  Buckets: 1024  Batches: 4  Memory Usage: 50kB",),
            ("  ->  Seq Scan on a  (cost=0.00..300.00 rows=5000 width=8)",),
            ("  ->  Hash  (cost=50.00..50.00 rows=1000 width=8)",),
            ("        ->  Seq Scan on b  (cost=0.00..50.00 rows=1000 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM a JOIN b ON a.id=b.id", False)

        # The batches annotation should mark the Hash Join node as disk_spill
        assert any(n.disk_spill for n in plan.all_nodes)

    def test_seq_scan_with_filter_and_rows_removed(self, analyzer):
        rows = [
            ("Seq Scan on orders  (cost=0.00..1823.00 rows=1000 width=8)",),
            ("  Filter: (status = 'pending')",),
            ("  Rows Removed by Filter: 14000",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders WHERE status='pending'", False)

        assert plan.has_seq_scans is True
        assert plan.root_node.filter == "(status = 'pending')"
        # Check that warnings mention the rows removed
        assert any("14,000" in w for w in plan.warnings)

    def test_empty_plan(self, analyzer):
        plan = analyzer.parse_plan([], "postgresql", "SELECT 1", False)
        assert plan.node_count == 0
        assert plan.root_node is None


# ============================================================================
# MySQL plan parsing tests
# ============================================================================

class TestParseMySQL:
    def _make_mysql_row(self, **kwargs):
        """Create a mock MySQL EXPLAIN row with _mapping."""
        defaults = {
            "id": 1, "select_type": "SIMPLE", "table": "orders",
            "partitions": None, "type": "ALL", "possible_keys": None,
            "key": None, "key_len": None, "ref": None,
            "rows": 10000, "filtered": 100.0, "Extra": "",
        }
        defaults.update(kwargs)

        class MockRow:
            pass

        row = MockRow()
        row._mapping = defaults
        return row

    def test_full_table_scan(self, analyzer):
        rows = [self._make_mysql_row(table="orders", type="ALL", rows=10000)]
        plan = analyzer.parse_plan(rows, "mysql", "SELECT * FROM orders", False)

        assert plan.has_seq_scans is True
        assert "orders" in plan.seq_scan_tables
        assert plan.all_nodes[0].node_type == "Full Table Scan"

    def test_index_lookup(self, analyzer):
        rows = [self._make_mysql_row(table="users", type="REF", key="idx_email", rows=1)]
        plan = analyzer.parse_plan(rows, "mysql", "SELECT * FROM users WHERE email='a@b.com'", False)

        assert plan.has_seq_scans is False
        assert plan.all_nodes[0].index_name == "idx_email"

    def test_using_filesort(self, analyzer):
        rows = [self._make_mysql_row(table="orders", type="ALL", Extra="Using filesort")]
        plan = analyzer.parse_plan(rows, "mysql", "SELECT * FROM orders ORDER BY created_at", False)

        assert plan.has_disk_spill is True
        assert any("Filesort" in w for w in plan.warnings)

    def test_using_temporary(self, analyzer):
        rows = [self._make_mysql_row(table="orders", type="ALL", Extra="Using temporary; Using filesort")]
        plan = analyzer.parse_plan(rows, "mysql", "SELECT status, COUNT(*) FROM orders GROUP BY status", False)

        assert plan.has_disk_spill is True
        assert any("Temporary" in w or "temporary" in w.lower() for w in plan.warnings)


# ============================================================================
# SQLite plan parsing tests
# ============================================================================

class TestParseSQLite:
    def test_scan_table(self, analyzer):
        rows = [(0, 0, 0, "SCAN TABLE orders")]
        plan = analyzer.parse_plan(rows, "sqlite", "SELECT * FROM orders", False)

        assert plan.has_seq_scans is True
        assert "orders" in plan.seq_scan_tables
        assert plan.all_nodes[0].node_type == "SCAN"
        assert plan.all_nodes[0].relation == "orders"

    def test_search_using_index(self, analyzer):
        rows = [(0, 0, 0, "SEARCH TABLE orders USING INDEX idx_status (status=?)")]
        plan = analyzer.parse_plan(rows, "sqlite", "SELECT * FROM orders WHERE status='pending'", False)

        assert plan.has_seq_scans is False
        assert plan.all_nodes[0].node_type == "SEARCH"
        assert plan.all_nodes[0].relation == "orders"
        assert plan.all_nodes[0].index_name == "idx_status"

    def test_search_using_covering_index(self, analyzer):
        rows = [(0, 0, 0, "SEARCH TABLE orders USING COVERING INDEX idx_status (status=?)")]
        plan = analyzer.parse_plan(rows, "sqlite", "SELECT status FROM orders WHERE status='pending'", False)

        assert plan.all_nodes[0].node_type == "SEARCH"
        assert plan.all_nodes[0].index_name == "idx_status"

    def test_search_using_primary_key(self, analyzer):
        rows = [(0, 0, 0, "SEARCH TABLE orders USING INTEGER PRIMARY KEY (rowid=?)")]
        plan = analyzer.parse_plan(rows, "sqlite", "SELECT * FROM orders WHERE rowid=1", False)

        assert plan.all_nodes[0].node_type == "SEARCH"
        assert plan.all_nodes[0].index_name == "PRIMARY KEY"

    def test_temp_btree(self, analyzer):
        rows = [
            (0, 0, 0, "SCAN TABLE orders"),
            (0, 0, 0, "USE TEMP B-TREE FOR ORDER BY"),
        ]
        plan = analyzer.parse_plan(rows, "sqlite", "SELECT * FROM orders ORDER BY created_at", False)

        assert any(n.node_type == "TEMP B-TREE" for n in plan.all_nodes)
        assert any("Temporary B-tree" in w for w in plan.warnings)


# ============================================================================
# DuckDB plan parsing tests
# ============================================================================

class TestParseDuckDB:
    def test_seq_scan(self, analyzer):
        rows = [
            ("┌───────────────────────────┐",),
            ("│      SEQ_SCAN orders      │",),
            ("└───────────────────────────┘",),
        ]
        plan = analyzer.parse_plan(rows, "duckdb", "SELECT * FROM orders", False)

        assert plan.has_seq_scans is True
        assert "orders" in plan.seq_scan_tables

    def test_filter_and_scan(self, analyzer):
        rows = [
            ("FILTER",),
            ("  SEQ_SCAN orders",),
        ]
        plan = analyzer.parse_plan(rows, "duckdb", "SELECT * FROM orders WHERE status='pending'", False)

        assert plan.node_count >= 1


# ============================================================================
# Deterministic warnings tests
# ============================================================================

class TestDeterministicWarnings:
    def test_seq_scan_with_filter_generates_warning(self, analyzer):
        rows = [
            ("Seq Scan on orders  (cost=0.00..1823.00 rows=10000 width=8)",),
            ("  Filter: (status = 'pending')",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders WHERE status='pending'", False)

        assert len(plan.warnings) > 0
        assert any("orders" in w for w in plan.warnings)
        assert any("index" in w.lower() for w in plan.warnings)

    def test_no_warnings_for_index_scan(self, analyzer):
        rows = [
            ("Index Scan using idx_orders_id on orders  (cost=0.28..8.30 rows=1 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT * FROM orders WHERE id=1", False)

        # Index scan should not generate seq scan warnings
        assert not any("Sequential scan" in w for w in plan.warnings)

    def test_sqlite_scan_warning(self, analyzer):
        rows = [(0, 0, 0, "SCAN TABLE orders")]
        plan = analyzer.parse_plan(rows, "sqlite", "SELECT * FROM orders", False)

        assert any("Full table scan" in w for w in plan.warnings)

    def test_mysql_filesort_warning(self, analyzer):
        class MockRow:
            _mapping = {
                "id": 1, "select_type": "SIMPLE", "table": "orders",
                "partitions": None, "type": "ALL", "possible_keys": None,
                "key": None, "key_len": None, "ref": None,
                "rows": 10000, "filtered": 100.0, "Extra": "Using filesort",
            }
        plan = analyzer.parse_plan([MockRow()], "mysql", "SELECT * FROM orders ORDER BY x", False)

        assert any("Filesort" in w for w in plan.warnings)


# ============================================================================
# ExecutionPlan.to_dict tests
# ============================================================================

class TestToDictSerialization:
    def test_plan_to_dict(self, analyzer):
        rows = [
            ("Seq Scan on orders  (cost=0.00..100.00 rows=100 width=8)",),
        ]
        plan = analyzer.parse_plan(rows, "postgresql", "SELECT 1", False)
        d = plan.to_dict()

        assert isinstance(d, dict)
        assert d["dialect"] == "postgresql"
        assert d["has_seq_scans"] is True
        assert isinstance(d["root_node"], dict)
        assert d["root_node"]["node_type"] == "Seq Scan"

    def test_empty_plan_to_dict(self, analyzer):
        plan = ExecutionPlan(dialect="postgresql", sql="SELECT 1", analyzed=False)
        d = plan.to_dict()
        assert d["root_node"] is None
        assert d["all_nodes"] == []
