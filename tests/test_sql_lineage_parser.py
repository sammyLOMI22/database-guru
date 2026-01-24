"""
Tests for SQL Lineage Parser

Covers:
- Simple SELECT single table
- Multi-table JOINs (INNER, LEFT, RIGHT)
- Aggregations (COUNT, SUM, AVG with GROUP BY)
- Aliased tables and columns
- Complex expressions (CASE, arithmetic)
- SELECT * handling
- Subqueries (basic)
- Invalid/empty SQL error handling
"""

import pytest
from src.lineage.sql_lineage_parser import (
    SQLLineageParser,
    LineageNodeType,
    TransformationType,
    LineageGraph,
)


@pytest.fixture
def parser():
    return SQLLineageParser()


# =============================================================================
# Simple SELECT Tests
# =============================================================================

class TestSimpleSelect:
    def test_single_table_single_column(self, parser):
        sql = "SELECT name FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert len(graph.output_columns) == 1
        assert "name" in graph.output_columns

    def test_single_table_multiple_columns(self, parser):
        sql = "SELECT name, email, phone FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert len(graph.output_columns) == 3
        assert "name" in graph.output_columns
        assert "email" in graph.output_columns
        assert "phone" in graph.output_columns

    def test_single_table_qualified_columns(self, parser):
        sql = "SELECT customers.name, customers.email FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert len(graph.output_columns) == 2

        # Should have source column nodes
        source_cols = [n for n in graph.nodes if n.node_type == LineageNodeType.SOURCE_COLUMN]
        assert len(source_cols) >= 2

    def test_select_star(self, parser):
        sql = "SELECT * FROM orders"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert any("*" in col for col in graph.output_columns)

    def test_table_dot_star(self, parser):
        sql = "SELECT o.* FROM orders o"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert any("*" in col for col in graph.output_columns)

    def test_column_alias(self, parser):
        sql = "SELECT name AS customer_name FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "customer_name" in graph.output_columns

    def test_distinct_keyword(self, parser):
        sql = "SELECT DISTINCT city FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert len(graph.output_columns) >= 1


# =============================================================================
# JOIN Tests
# =============================================================================

class TestJoins:
    def test_inner_join(self, parser):
        sql = """
        SELECT o.id, c.name
        FROM orders o
        INNER JOIN customers c ON o.customer_id = c.id
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "customers" in graph.tables_used
        assert len(graph.output_columns) == 2

    def test_left_join(self, parser):
        sql = """
        SELECT p.name, c.category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        """
        graph = parser.parse(sql)

        assert "products" in graph.tables_used
        assert "categories" in graph.tables_used

    def test_multiple_joins(self, parser):
        sql = """
        SELECT o.id, c.name, p.product_name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "customers" in graph.tables_used
        assert "products" in graph.tables_used
        assert len(graph.output_columns) == 3

    def test_right_join(self, parser):
        sql = """
        SELECT c.name, o.total
        FROM customers c
        RIGHT JOIN orders o ON c.id = o.customer_id
        """
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "orders" in graph.tables_used

    def test_comma_join(self, parser):
        sql = "SELECT a.name, b.value FROM table_a a, table_b b"
        graph = parser.parse(sql)

        assert "table_a" in graph.tables_used
        assert "table_b" in graph.tables_used


# =============================================================================
# Aggregation Tests
# =============================================================================

class TestAggregations:
    def test_count_star(self, parser):
        sql = "SELECT COUNT(*) FROM orders"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        # Should have a transformation node for COUNT
        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert len(trans_nodes) >= 1
        assert any(n.transformation_type == TransformationType.AGGREGATION for n in trans_nodes)

    def test_count_column(self, parser):
        sql = "SELECT COUNT(id) AS total FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "total" in graph.output_columns
        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert len(trans_nodes) >= 1

    def test_sum_aggregation(self, parser):
        sql = "SELECT SUM(amount) AS total_amount FROM orders"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "total_amount" in graph.output_columns
        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert any(n.label == "SUM" for n in trans_nodes)

    def test_avg_aggregation(self, parser):
        sql = "SELECT AVG(price) AS avg_price FROM products"
        graph = parser.parse(sql)

        assert "products" in graph.tables_used
        assert "avg_price" in graph.output_columns

    def test_group_by_with_aggregation(self, parser):
        sql = """
        SELECT category, COUNT(*) AS cnt, SUM(price) AS total
        FROM products
        GROUP BY category
        """
        graph = parser.parse(sql)

        assert "products" in graph.tables_used
        assert "category" in graph.output_columns
        assert "cnt" in graph.output_columns
        assert "total" in graph.output_columns

    def test_min_max(self, parser):
        sql = "SELECT MIN(price) AS lowest, MAX(price) AS highest FROM products"
        graph = parser.parse(sql)

        assert "products" in graph.tables_used
        assert "lowest" in graph.output_columns
        assert "highest" in graph.output_columns


# =============================================================================
# Alias Tests
# =============================================================================

class TestAliases:
    def test_table_alias(self, parser):
        sql = "SELECT o.id, o.total FROM orders o"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert len(graph.output_columns) == 2

    def test_table_alias_as(self, parser):
        sql = "SELECT o.id FROM orders AS o"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used

    def test_column_alias_expression(self, parser):
        sql = "SELECT price * quantity AS line_total FROM order_items"
        graph = parser.parse(sql)

        assert "order_items" in graph.tables_used
        assert "line_total" in graph.output_columns

    def test_schema_qualified_table(self, parser):
        sql = "SELECT id FROM public.customers"
        graph = parser.parse(sql)

        # Should extract just "customers" from "public.customers"
        assert "customers" in graph.tables_used


# =============================================================================
# Complex Expression Tests
# =============================================================================

class TestExpressions:
    def test_arithmetic_expression(self, parser):
        sql = "SELECT price * quantity AS total FROM order_items"
        graph = parser.parse(sql)

        assert "order_items" in graph.tables_used
        assert "total" in graph.output_columns

    def test_case_expression(self, parser):
        sql = """
        SELECT
            CASE WHEN status = 'active' THEN 'Active' ELSE 'Inactive' END AS status_label
        FROM customers
        """
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "status_label" in graph.output_columns
        # Should detect CASE as expression/function
        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert len(trans_nodes) >= 1

    def test_function_call(self, parser):
        sql = "SELECT UPPER(name) AS upper_name FROM customers"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "upper_name" in graph.output_columns
        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert len(trans_nodes) >= 1

    def test_coalesce_function(self, parser):
        sql = "SELECT COALESCE(nickname, name) AS display_name FROM users"
        graph = parser.parse(sql)

        assert "users" in graph.tables_used
        assert "display_name" in graph.output_columns


# =============================================================================
# Graph Structure Tests
# =============================================================================

class TestGraphStructure:
    def test_nodes_have_correct_types(self, parser):
        sql = "SELECT name FROM customers"
        graph = parser.parse(sql)

        table_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.SOURCE_TABLE]
        output_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.OUTPUT_COLUMN]

        assert len(table_nodes) == 1
        assert table_nodes[0].table_name == "customers"
        assert len(output_nodes) == 1

    def test_edges_connect_source_to_output(self, parser):
        sql = "SELECT name FROM customers"
        graph = parser.parse(sql)

        assert len(graph.edges) >= 1
        # Should have path from table to output
        node_ids = {n.id for n in graph.nodes}
        for edge in graph.edges:
            assert edge.source_id in node_ids
            assert edge.target_id in node_ids

    def test_aggregation_has_transformation_node(self, parser):
        sql = "SELECT COUNT(*) AS total FROM orders"
        graph = parser.parse(sql)

        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert len(trans_nodes) >= 1

        # Transformation should connect to output
        trans_id = trans_nodes[0].id
        out_edges = [e for e in graph.edges if e.source_id == trans_id]
        assert len(out_edges) >= 1

    def test_unique_node_ids(self, parser):
        sql = """
        SELECT o.id, c.name, SUM(o.total) AS sum_total
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        GROUP BY o.id, c.name
        """
        graph = parser.parse(sql)

        ids = [n.id for n in graph.nodes]
        assert len(ids) == len(set(ids)), "Node IDs should be unique"

    def test_to_dict_serialization(self, parser):
        sql = "SELECT name FROM customers"
        graph = parser.parse(sql)

        result = graph.to_dict()
        assert "nodes" in result
        assert "edges" in result
        assert "sql" in result
        assert "tables_used" in result
        assert "output_columns" in result

        for node in result["nodes"]:
            assert "id" in node
            assert "node_type" in node
            assert "label" in node


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    def test_empty_sql(self, parser):
        graph = parser.parse("")
        assert graph.nodes == []
        assert graph.edges == []

    def test_none_sql(self, parser):
        graph = parser.parse(None)
        assert graph.nodes == []

    def test_whitespace_only(self, parser):
        graph = parser.parse("   ")
        assert graph.nodes == []

    def test_non_select_statement(self, parser):
        graph = parser.parse("INSERT INTO customers (name) VALUES ('test')")
        assert graph.nodes == []
        assert graph.tables_used == []

    def test_update_statement(self, parser):
        graph = parser.parse("UPDATE customers SET name = 'test' WHERE id = 1")
        assert graph.nodes == []

    def test_delete_statement(self, parser):
        graph = parser.parse("DELETE FROM customers WHERE id = 1")
        assert graph.nodes == []

    def test_malformed_sql(self, parser):
        graph = parser.parse("SELECT FROM WHERE")
        # Should not crash, may return partial or empty results
        assert isinstance(graph, LineageGraph)

    def test_very_long_sql(self, parser):
        # Generate a long but valid SQL
        columns = ", ".join([f"col_{i}" for i in range(50)])
        sql = f"SELECT {columns} FROM big_table"
        graph = parser.parse(sql)

        assert "big_table" in graph.tables_used
        assert len(graph.output_columns) == 50

    def test_sql_with_where_clause(self, parser):
        sql = "SELECT name, email FROM customers WHERE status = 'active'"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "name" in graph.output_columns
        assert "email" in graph.output_columns

    def test_sql_with_order_by(self, parser):
        sql = "SELECT name FROM customers ORDER BY name ASC"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used
        assert "name" in graph.output_columns

    def test_sql_with_limit(self, parser):
        sql = "SELECT name FROM customers LIMIT 10"
        graph = parser.parse(sql)

        assert "customers" in graph.tables_used

    def test_multiple_statements_uses_first(self, parser):
        sql = "SELECT id FROM a; SELECT name FROM b"
        graph = parser.parse(sql)

        # Should parse first statement
        assert "a" in graph.tables_used

    def test_subquery_in_from(self, parser):
        sql = """
        SELECT sub.total
        FROM (SELECT SUM(amount) AS total FROM orders) sub
        """
        graph = parser.parse(sql)

        # Should at least recognize the subquery alias as a table
        assert len(graph.tables_used) >= 1


class TestWhereSubqueries:
    """Tests for subquery extraction in WHERE clauses."""

    @pytest.fixture
    def parser(self):
        return SQLLineageParser()

    def test_where_in_subquery(self, parser):
        sql = """
        SELECT * FROM orders
        WHERE customer_id IN (SELECT customer_id FROM customers WHERE state = 'TX')
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "customers" in graph.tables_used
        assert len(graph.tables_used) == 2

    def test_where_in_subquery_with_schema_prefix(self, parser):
        sql = """
        SELECT * FROM orders
        WHERE customer_id IN (
            SELECT customers.customer_id FROM customers WHERE state = 'TX'
        ) AND status = 'shipped' LIMIT 100
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "customers" in graph.tables_used

    def test_where_exists_subquery(self, parser):
        sql = """
        SELECT o.id, o.total FROM orders o
        WHERE EXISTS (
            SELECT 1 FROM payments p WHERE p.order_id = o.id
        )
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "payments" in graph.tables_used

    def test_where_scalar_subquery(self, parser):
        sql = """
        SELECT name, salary FROM employees
        WHERE salary > (SELECT AVG(salary) FROM employees)
        """
        graph = parser.parse(sql)

        assert "employees" in graph.tables_used

    def test_where_not_in_subquery(self, parser):
        sql = """
        SELECT * FROM products
        WHERE category_id NOT IN (
            SELECT id FROM categories WHERE deprecated = true
        )
        """
        graph = parser.parse(sql)

        assert "products" in graph.tables_used
        assert "categories" in graph.tables_used

    def test_nested_subqueries_in_where(self, parser):
        sql = """
        SELECT * FROM orders
        WHERE customer_id IN (
            SELECT id FROM customers
            WHERE region_id IN (
                SELECT id FROM regions WHERE country = 'US'
            )
        )
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "customers" in graph.tables_used
        assert "regions" in graph.tables_used

    def test_multiple_subqueries_in_where(self, parser):
        sql = """
        SELECT * FROM orders
        WHERE customer_id IN (SELECT id FROM customers)
        AND product_id IN (SELECT id FROM products WHERE active = true)
        """
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        assert "customers" in graph.tables_used
        assert "products" in graph.tables_used

    def test_subquery_table_not_expanded_in_star(self, parser):
        sql = """
        SELECT * FROM orders
        WHERE customer_id IN (SELECT id FROM customers)
        """
        graph = parser.parse(sql)

        # SELECT * should only expand the primary table (orders), not customers
        output_labels = [n.label for n in graph.nodes if n.node_type.value == "output_column"]
        assert "orders.*" in output_labels
        assert "customers.*" not in output_labels

    def test_subquery_creates_filter_edge(self, parser):
        sql = """
        SELECT * FROM orders
        WHERE customer_id IN (SELECT id FROM customers)
        """
        graph = parser.parse(sql)

        # Should have a filter edge from customers table to output
        filter_edges = [e for e in graph.edges if e.edge_type == "filter"]
        assert len(filter_edges) == 1
        assert filter_edges[0].label == "filters via subquery"

        # The filter edge source should be the customers table node
        customers_node = next(n for n in graph.nodes if n.table_name == "customers")
        assert filter_edges[0].source_id == customers_node.id

    def test_subquery_shared_table_not_duplicated(self, parser):
        """When subquery references same table as FROM, don't add it as subquery table."""
        sql = """
        SELECT * FROM employees
        WHERE salary > (SELECT AVG(salary) FROM employees)
        """
        graph = parser.parse(sql)

        # employees should appear only once in tables_used
        assert graph.tables_used.count("employees") == 1
        # Only one SOURCE_TABLE node for employees
        source_nodes = [
            n for n in graph.nodes
            if n.table_name == "employees" and n.node_type.value == "source_table"
        ]
        assert len(source_nodes) == 1
        # No filter edge since it's the same table
        filter_edges = [e for e in graph.edges if e.edge_type == "filter"]
        assert len(filter_edges) == 0
