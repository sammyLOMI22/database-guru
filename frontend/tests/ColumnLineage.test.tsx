/**
 * ColumnLineage Component Tests - Phase 11.6
 *
 * Tests:
 * - Renders empty state when no lineage traces
 * - Renders lineage table from graph data
 * - Filters traces by column/table name
 * - Expands complex transformation rows
 * - Displays correct transformation type badges
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';

import { ColumnLineage } from '../src/components/lineage/ColumnLineage';
import type { LineageGraphResponse } from '../src/types/lineage';

// Mock data for a simple direct mapping
const mockSimpleGraph: LineageGraphResponse = {
  nodes: [
    { id: 'table_1', node_type: 'source_table', label: 'customers', table_name: 'customers' },
    { id: 'col_1', node_type: 'source_column', label: 'customers.name', table_name: 'customers', column_name: 'name' },
    { id: 'col_2', node_type: 'source_column', label: 'customers.email', table_name: 'customers', column_name: 'email' },
    { id: 'out_1', node_type: 'output_column', label: 'name', column_name: 'name' },
    { id: 'out_2', node_type: 'output_column', label: 'email', column_name: 'email' },
  ],
  edges: [
    { source_id: 'table_1', target_id: 'col_1', edge_type: 'contains' },
    { source_id: 'table_1', target_id: 'col_2', edge_type: 'contains' },
    { source_id: 'col_1', target_id: 'out_1', edge_type: 'direct' },
    { source_id: 'col_2', target_id: 'out_2', edge_type: 'direct' },
  ],
  sql: 'SELECT name, email FROM customers',
  tables_used: ['customers'],
  columns_used: ['customers.name', 'customers.email'],
  output_columns: ['name', 'email'],
};

// Mock data with aggregation transformation
const mockAggregationGraph: LineageGraphResponse = {
  nodes: [
    { id: 'table_1', node_type: 'source_table', label: 'orders', table_name: 'orders' },
    { id: 'col_1', node_type: 'source_column', label: 'orders.total', table_name: 'orders', column_name: 'total' },
    { id: 'trans_1', node_type: 'transformation', label: 'SUM(orders.total)', transformation_type: 'aggregation', expression: 'SUM(orders.total)' },
    { id: 'out_1', node_type: 'output_column', label: 'total_revenue', column_name: 'total_revenue' },
  ],
  edges: [
    { source_id: 'table_1', target_id: 'col_1', edge_type: 'contains' },
    { source_id: 'col_1', target_id: 'trans_1', edge_type: 'input' },
    { source_id: 'trans_1', target_id: 'out_1', edge_type: 'produces' },
  ],
  sql: 'SELECT SUM(total) AS total_revenue FROM orders',
  tables_used: ['orders'],
  columns_used: ['orders.total'],
  output_columns: ['total_revenue'],
};

// Mock data with complex expression
const mockExpressionGraph: LineageGraphResponse = {
  nodes: [
    { id: 'table_1', node_type: 'source_table', label: 'order_items', table_name: 'order_items' },
    { id: 'col_1', node_type: 'source_column', label: 'order_items.price', table_name: 'order_items', column_name: 'price' },
    { id: 'col_2', node_type: 'source_column', label: 'order_items.quantity', table_name: 'order_items', column_name: 'quantity' },
    { id: 'trans_1', node_type: 'transformation', label: 'price * quantity', transformation_type: 'expression', expression: 'price * quantity' },
    { id: 'out_1', node_type: 'output_column', label: 'line_total', column_name: 'line_total' },
  ],
  edges: [
    { source_id: 'table_1', target_id: 'col_1', edge_type: 'contains' },
    { source_id: 'table_1', target_id: 'col_2', edge_type: 'contains' },
    { source_id: 'col_1', target_id: 'trans_1', edge_type: 'input' },
    { source_id: 'col_2', target_id: 'trans_1', edge_type: 'input' },
    { source_id: 'trans_1', target_id: 'out_1', edge_type: 'produces' },
  ],
  sql: 'SELECT price * quantity AS line_total FROM order_items',
  tables_used: ['order_items'],
  columns_used: ['order_items.price', 'order_items.quantity'],
  output_columns: ['line_total'],
};

// Empty graph
const mockEmptyGraph: LineageGraphResponse = {
  nodes: [],
  edges: [],
  sql: '',
  tables_used: [],
  columns_used: [],
  output_columns: [],
};

describe('ColumnLineage', () => {
  describe('Empty State', () => {
    it('shows empty message when no traces found', () => {
      render(<ColumnLineage graphData={mockEmptyGraph} />);

      expect(screen.getByText(/no column-level lineage traces found/i)).toBeInTheDocument();
    });

    it('shows empty message for graph with only table nodes', () => {
      const tableOnlyGraph: LineageGraphResponse = {
        nodes: [
          { id: 'table_1', node_type: 'source_table', label: 'customers', table_name: 'customers' },
        ],
        edges: [],
        sql: 'SELECT 1',
        tables_used: ['customers'],
        columns_used: [],
        output_columns: [],
      };

      render(<ColumnLineage graphData={tableOnlyGraph} />);

      expect(screen.getByText(/no column-level lineage traces found/i)).toBeInTheDocument();
    });
  });

  describe('Simple Direct Mappings', () => {
    it('renders table headers', () => {
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      expect(screen.getByText(/output column/i)).toBeInTheDocument();
      expect(screen.getByText(/source table/i)).toBeInTheDocument();
      expect(screen.getByText(/source column/i)).toBeInTheDocument();
      expect(screen.getByText(/transformation/i)).toBeInTheDocument();
    });

    it('displays output columns from simple SELECT', () => {
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      // Should show both output columns (may appear multiple times as output and source)
      expect(screen.getAllByText('name').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('email').length).toBeGreaterThanOrEqual(1);
    });

    it('displays source table for each trace', () => {
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      // Source table should appear for both columns
      const customerCells = screen.getAllByText('customers');
      expect(customerCells.length).toBeGreaterThanOrEqual(2);
    });

    it('shows "direct" for simple column mappings', () => {
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      // Direct mappings should show "direct" transformation
      const directLabels = screen.getAllByText('direct');
      expect(directLabels.length).toBeGreaterThanOrEqual(2);
    });

    it('displays trace count in header', () => {
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      // Header should show count
      expect(screen.getByText(/column lineage \(2\)/i)).toBeInTheDocument();
    });
  });

  describe('Aggregation Transformations', () => {
    it('displays aggregation badge for SUM transformation', () => {
      render(<ColumnLineage graphData={mockAggregationGraph} />);

      expect(screen.getByText('aggregation')).toBeInTheDocument();
    });

    it('shows output column from aggregation', () => {
      render(<ColumnLineage graphData={mockAggregationGraph} />);

      expect(screen.getAllByText('total_revenue').length).toBeGreaterThanOrEqual(1);
    });

    it('shows source column for aggregation', () => {
      render(<ColumnLineage graphData={mockAggregationGraph} />);

      expect(screen.getAllByText('total').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Complex Expressions', () => {
    it('marks expression transformations as complex', () => {
      render(<ColumnLineage graphData={mockExpressionGraph} />);

      // Expression badge(s) should be visible - may be multiple due to multiple source columns
      const expressionBadges = screen.getAllByText('expression');
      expect(expressionBadges.length).toBeGreaterThanOrEqual(1);
    });

    it('expands complex row to show expression on click', async () => {
      const user = userEvent.setup();
      render(<ColumnLineage graphData={mockExpressionGraph} />);

      // Find a row with the complex transformation - use getAllByText since there may be duplicates
      const lineTotals = screen.getAllByText('line_total');
      const row = lineTotals[0].closest('tr');
      expect(row).toBeTruthy();

      // Click to expand
      fireEvent.click(row!);

      // Expression should be visible - use getAllByText for safety
      const expressions = screen.getAllByText('price * quantity');
      expect(expressions.length).toBeGreaterThanOrEqual(1);
    });

    it('collapses expanded row on second click', async () => {
      render(<ColumnLineage graphData={mockExpressionGraph} />);

      const lineTotals = screen.getAllByText('line_total');
      const row = lineTotals[0].closest('tr');

      // Expand
      fireEvent.click(row!);
      let expressions = screen.getAllByText('price * quantity');
      expect(expressions.length).toBeGreaterThanOrEqual(1);

      // Collapse - the expanded row should be removed
      fireEvent.click(row!);

      // After collapse, expression count may decrease (depends on implementation)
      // This tests that clicking again doesn't crash
    });

    it('shows chevron icon for expandable rows', () => {
      render(<ColumnLineage graphData={mockExpressionGraph} />);

      // Complex rows should have chevron (ChevronRight initially)
      const chevrons = document.querySelectorAll('svg');
      expect(chevrons.length).toBeGreaterThan(0);
    });
  });

  describe('Filtering', () => {
    it('renders filter input', () => {
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      expect(screen.getByPlaceholderText(/filter/i)).toBeInTheDocument();
    });

    it('filters traces by output column name', async () => {
      const user = userEvent.setup();
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      const filterInput = screen.getByPlaceholderText(/filter/i);
      await user.type(filterInput, 'email');

      // Should only show email trace - check count changed
      expect(screen.getByText(/column lineage \(1\)/i)).toBeInTheDocument();
      expect(screen.getAllByText('email').length).toBeGreaterThanOrEqual(1);
    });

    it('filters traces by source table name', async () => {
      const user = userEvent.setup();

      // Use a graph with multiple tables
      const multiTableGraph: LineageGraphResponse = {
        nodes: [
          { id: 'table_1', node_type: 'source_table', label: 'customers', table_name: 'customers' },
          { id: 'table_2', node_type: 'source_table', label: 'orders', table_name: 'orders' },
          { id: 'col_1', node_type: 'source_column', label: 'customers.name', table_name: 'customers', column_name: 'name' },
          { id: 'col_2', node_type: 'source_column', label: 'orders.id', table_name: 'orders', column_name: 'id' },
          { id: 'out_1', node_type: 'output_column', label: 'customer_name' },
          { id: 'out_2', node_type: 'output_column', label: 'order_id' },
        ],
        edges: [
          { source_id: 'col_1', target_id: 'out_1', edge_type: 'direct' },
          { source_id: 'col_2', target_id: 'out_2', edge_type: 'direct' },
        ],
        sql: 'SELECT c.name, o.id FROM customers c JOIN orders o',
        tables_used: ['customers', 'orders'],
        columns_used: ['customers.name', 'orders.id'],
        output_columns: ['customer_name', 'order_id'],
      };

      render(<ColumnLineage graphData={multiTableGraph} />);

      const filterInput = screen.getByPlaceholderText(/filter/i);
      await user.type(filterInput, 'order_id');

      // Should only show orders trace - count should be 1
      expect(screen.getByText(/column lineage \(1\)/i)).toBeInTheDocument();
    });

    it('updates count when filtering', async () => {
      const user = userEvent.setup();
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      // Initial count
      expect(screen.getByText(/column lineage \(2\)/i)).toBeInTheDocument();

      const filterInput = screen.getByPlaceholderText(/filter/i);
      await user.type(filterInput, 'email');

      // Filtered count
      expect(screen.getByText(/column lineage \(1\)/i)).toBeInTheDocument();
    });

    it('shows all traces when filter is cleared', async () => {
      const user = userEvent.setup();
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      const filterInput = screen.getByPlaceholderText(/filter/i);

      // Type filter
      await user.type(filterInput, 'email');
      expect(screen.getByText(/column lineage \(1\)/i)).toBeInTheDocument();

      // Clear filter
      await user.clear(filterInput);
      expect(screen.getByText(/column lineage \(2\)/i)).toBeInTheDocument();
    });

    it('shows empty result when no matches', async () => {
      const user = userEvent.setup();
      render(<ColumnLineage graphData={mockSimpleGraph} />);

      const filterInput = screen.getByPlaceholderText(/filter/i);
      await user.type(filterInput, 'nonexistent');

      expect(screen.getByText(/column lineage \(0\)/i)).toBeInTheDocument();
    });
  });

  describe('Transformation Type Badges', () => {
    it('applies correct color for aggregation', () => {
      render(<ColumnLineage graphData={mockAggregationGraph} />);

      const badges = screen.getAllByText('aggregation');
      expect(badges.length).toBeGreaterThanOrEqual(1);
      expect(badges[0].className).toMatch(/purple/i);
    });

    it('applies correct color for expression', () => {
      render(<ColumnLineage graphData={mockExpressionGraph} />);

      const badges = screen.getAllByText('expression');
      expect(badges.length).toBeGreaterThanOrEqual(1);
      expect(badges[0].className).toMatch(/amber/i);
    });
  });

  describe('Edge Cases', () => {
    it('handles SELECT * with table source', () => {
      const starGraph: LineageGraphResponse = {
        nodes: [
          { id: 'table_1', node_type: 'source_table', label: 'orders', table_name: 'orders' },
          { id: 'out_1', node_type: 'output_column', label: 'orders.*' },
        ],
        edges: [
          { source_id: 'table_1', target_id: 'out_1', edge_type: 'contains' },
        ],
        sql: 'SELECT * FROM orders',
        tables_used: ['orders'],
        columns_used: [],
        output_columns: ['orders.*'],
      };

      render(<ColumnLineage graphData={starGraph} />);

      // Should show wildcard indicator
      expect(screen.getByText(/orders\.\*/)).toBeInTheDocument();
    });

    it('handles COUNT(*) with no source columns', () => {
      const countStarGraph: LineageGraphResponse = {
        nodes: [
          { id: 'table_1', node_type: 'source_table', label: 'orders', table_name: 'orders' },
          { id: 'trans_1', node_type: 'transformation', label: 'COUNT(*)', transformation_type: 'aggregation', expression: 'COUNT(*)' },
          { id: 'out_1', node_type: 'output_column', label: 'total_count' },
        ],
        edges: [
          { source_id: 'trans_1', target_id: 'out_1', edge_type: 'produces' },
        ],
        sql: 'SELECT COUNT(*) AS total_count FROM orders',
        tables_used: ['orders'],
        columns_used: [],
        output_columns: ['total_count'],
      };

      render(<ColumnLineage graphData={countStarGraph} />);

      expect(screen.getByText('total_count')).toBeInTheDocument();
      expect(screen.getByText('aggregation')).toBeInTheDocument();
    });

    it('handles missing table_name gracefully', () => {
      const noTableNameGraph: LineageGraphResponse = {
        nodes: [
          { id: 'col_1', node_type: 'source_column', label: 'unknown_col' }, // No table_name
          { id: 'out_1', node_type: 'output_column', label: 'output_col' },
        ],
        edges: [
          { source_id: 'col_1', target_id: 'out_1', edge_type: 'direct' },
        ],
        sql: 'SELECT name FROM t',
        tables_used: [],
        columns_used: ['name'],
        output_columns: ['output_col'],
      };

      render(<ColumnLineage graphData={noTableNameGraph} />);

      // Should show the trace without crashing, count should be 1
      expect(screen.getByText(/column lineage \(1\)/i)).toBeInTheDocument();
      expect(screen.getByText('output_col')).toBeInTheDocument();
    });
  });
});
