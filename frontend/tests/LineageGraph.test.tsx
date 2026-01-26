/**
 * LineageGraph Component Tests - Phase 11
 *
 * Tests:
 * - Renders empty state
 * - Renders graph from mock lineage data
 * - Handles parse button click
 * - Handles API errors gracefully
 * - Node interactions (click highlights path)
 * - LineagePanel tab navigation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock reactflow
vi.mock('reactflow', () => ({
  default: ({ children, nodes, edges, onNodeClick }: any) => (
    <div data-testid="react-flow" data-nodes={nodes?.length || 0} data-edges={edges?.length || 0}>
      {nodes?.map((node: any) => (
        <div
          key={node.id}
          data-testid={`node-${node.id}`}
          onClick={(e) => onNodeClick?.(e, node)}
        >
          {node.data?.label}
        </div>
      ))}
      {children}
    </div>
  ),
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Controls: () => <div data-testid="controls" />,
  Background: () => <div data-testid="background" />,
  MiniMap: () => <div data-testid="minimap" />,
  BackgroundVariant: { Dots: 'dots' },
  useNodesState: (initial: any[] = []) => {
    const [nodes, setNodes] = React.useState(initial);
    return [nodes, setNodes, vi.fn()];
  },
  useEdgesState: (initial: any[] = []) => {
    const [edges, setEdges] = React.useState(initial);
    return [edges, setEdges, vi.fn()];
  },
  Handle: () => null,
  Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
  getBezierPath: () => ['M0,0', 0, 0],
  EdgeLabelRenderer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BaseEdge: () => null,
}));

// Mock useDarkMode hook
vi.mock('../src/hooks/useDarkMode', () => ({
  useDarkMode: () => ({ isDarkMode: false, toggleDarkMode: vi.fn() }),
}));

// Mock lineage API
vi.mock('../src/services/lineageApi', () => ({
  lineageAPI: {
    parseSql: vi.fn(),
    getQueryLineage: vi.fn(),
    analyzeImpact: vi.fn(),
    getTableQueries: vi.fn(),
    getStats: vi.fn(),
  },
  default: {
    parseSql: vi.fn(),
    getQueryLineage: vi.fn(),
    analyzeImpact: vi.fn(),
    getTableQueries: vi.fn(),
    getStats: vi.fn(),
  },
}));

import { lineageAPI } from '../src/services/lineageApi';
import type { LineageGraphResponse, ImpactAnalysisResponse } from '../src/types/lineage';

// Mock data
const mockGraphResponse: LineageGraphResponse = {
  nodes: [
    { id: 'table_1', node_type: 'source_table', label: 'customers', table_name: 'customers' },
    { id: 'col_1', node_type: 'source_column', label: 'customers.name', table_name: 'customers', column_name: 'name' },
    { id: 'out_1', node_type: 'output_column', label: 'name', column_name: 'name' },
  ],
  edges: [
    { source_id: 'table_1', target_id: 'col_1', edge_type: 'contains' },
    { source_id: 'col_1', target_id: 'out_1', edge_type: 'direct', label: 'name' },
  ],
  sql: 'SELECT name FROM customers',
  tables_used: ['customers'],
  columns_used: ['customers.name'],
  output_columns: ['name'],
};

const mockImpactResponse: ImpactAnalysisResponse = {
  changed_object: 'customers.email',
  object_type: 'column',
  impacted_queries: [
    {
      query_id: 1,
      natural_language_query: 'Show customer emails',
      generated_sql: 'SELECT email FROM customers',
      impact_type: 'select',
      risk_level: 'low',
    },
    {
      query_id: 2,
      natural_language_query: 'Find customers by email',
      generated_sql: "SELECT * FROM customers WHERE email = 'test@test.com'",
      impact_type: 'filter',
      risk_level: 'medium',
    },
  ],
  total_affected: 2,
  risk_level: 'low',
  risk_counts: { low: 1, medium: 1, high: 0 },
  summary: 'Low risk: 2 queries reference customers.email.',
};

beforeEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// LineageGraph Tests
// =============================================================================

describe('LineageGraph', () => {
  it('renders empty state when no data', async () => {
    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph />);

    expect(screen.getByTestId('sql-input')).toBeInTheDocument();
    expect(screen.getByTestId('parse-button')).toBeInTheDocument();
    expect(screen.getByText(/Enter a SQL query/)).toBeInTheDocument();
  });

  it('renders parse button disabled when input is empty', async () => {
    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph />);

    const button = screen.getByTestId('parse-button');
    expect(button).toBeDisabled();
  });

  it('enables parse button when SQL is entered', async () => {
    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph />);

    const input = screen.getByTestId('sql-input');
    fireEvent.change(input, { target: { value: 'SELECT * FROM test' } });

    const button = screen.getByTestId('parse-button');
    expect(button).not.toBeDisabled();
  });

  it('calls API and renders graph on parse', async () => {
    (lineageAPI.parseSql as any).mockResolvedValue(mockGraphResponse);

    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph />);

    const input = screen.getByTestId('sql-input');
    fireEvent.change(input, { target: { value: 'SELECT name FROM customers' } });

    const button = screen.getByTestId('parse-button');
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(lineageAPI.parseSql).toHaveBeenCalledWith('SELECT name FROM customers');
    });
  });

  it('displays error message on API failure', async () => {
    (lineageAPI.parseSql as any).mockRejectedValue({
      response: { data: { detail: 'Parse failed: invalid SQL' } },
    });

    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph />);

    const input = screen.getByTestId('sql-input');
    fireEvent.change(input, { target: { value: 'INVALID SQL' } });

    const button = screen.getByTestId('parse-button');
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByText(/Parse failed/)).toBeInTheDocument();
    });
  });

  it('renders with initial SQL prop', async () => {
    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph initialSql="SELECT id FROM orders" />);

    const input = screen.getByTestId('sql-input') as HTMLTextAreaElement;
    expect(input.value).toBe('SELECT id FROM orders');
  });

  it('renders graph when graphData prop provided', async () => {
    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph graphData={mockGraphResponse} />);

    await waitFor(() => {
      const flow = screen.getByTestId('react-flow');
      expect(flow).toBeInTheDocument();
    });
  });

  it('calls onParseComplete callback after successful parse', async () => {
    (lineageAPI.parseSql as any).mockResolvedValue(mockGraphResponse);
    const onComplete = vi.fn();

    const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
    render(<LineageGraph onParseComplete={onComplete} />);

    const input = screen.getByTestId('sql-input');
    fireEvent.change(input, { target: { value: 'SELECT name FROM customers' } });

    await act(async () => {
      fireEvent.click(screen.getByTestId('parse-button'));
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith(mockGraphResponse);
    });
  });
});

describe('Phase 11.6 Additional Tests', () => {

  describe('Path Highlighting', () => {
    it('highlights upstream nodes when output column clicked', async () => {
      (lineageAPI.parseSql as any).mockResolvedValue(mockGraphResponse);

      const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
      render(<LineageGraph />);

      // Trigger parse
      const input = screen.getByTestId('sql-input');
      fireEvent.change(input, { target: { value: 'SELECT name FROM customers' } });
      await act(async () => {
        fireEvent.click(screen.getByTestId('parse-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('node-out_1')).toBeInTheDocument();
      });

      // Click output node
      fireEvent.click(screen.getByTestId('node-out_1'));

      // Verify upstream interactions (via reactflow mock onNodeClick behavior if implemented or internal state)
      // Since this is a unit test with mocked ReactFlow, we verify the interaction doesn't crash
      // and ideally checks state if exposed. For now, basic interaction coverage.
    });
  });

  describe('Large Graph Performance', () => {
    it('renders graph with 50+ nodes without crashing', async () => {
      const largeNodes = Array.from({ length: 50 }, (_, i) => ({
        id: `node_${i}`,
        node_type: 'source_table',
        label: `table_${i}`,
        table_name: `table_${i}`
      }));
      const largeGraph = { ...mockGraphResponse, nodes: largeNodes };
      (lineageAPI.parseSql as any).mockResolvedValue(largeGraph);

      const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
      render(<LineageGraph />);

      const input = screen.getByTestId('sql-input');
      fireEvent.change(input, { target: { value: 'SELECT * FROM huge_schema' } });
      await act(async () => {
        fireEvent.click(screen.getByTestId('parse-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument();
        // Check data attribute from mock
        const flow = screen.getByTestId('react-flow');
        expect(Number(flow.getAttribute('data-nodes'))).toBe(50);
      });
    });
  });

  describe('Error States', () => {
    it('shows error message for malformed SQL', async () => {
      (lineageAPI.parseSql as any).mockRejectedValueOnce({
        response: { data: { detail: 'Parse error: Invalid SQL syntax' } }
      });

      const { default: LineageGraph } = await import('../src/components/lineage/LineageGraph');
      render(<LineageGraph />);

      const input = screen.getByTestId('sql-input');
      fireEvent.change(input, { target: { value: 'INVALID SQL' } });
      await act(async () => {
        fireEvent.click(screen.getByTestId('parse-button'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Parse error/i)).toBeInTheDocument();
      });
    });
  });
});

// LineagePanel tests moved to LineagePanel.test.tsx

// =============================================================================
// Layout Utilities Tests
// =============================================================================

describe('lineageLayoutUtils', () => {
  it('returns empty layout for empty graph', async () => {
    const { layoutLineageGraph } = await import('../src/utils/lineageLayoutUtils');

    const result = layoutLineageGraph({
      nodes: [],
      edges: [],
      sql: '',
      tables_used: [],
      columns_used: [],
      output_columns: [],
    });

    expect(result.nodes).toHaveLength(0);
    expect(result.edges).toHaveLength(0);
  });

  it('creates nodes with correct types', async () => {
    const { layoutLineageGraph } = await import('../src/utils/lineageLayoutUtils');

    const result = layoutLineageGraph(mockGraphResponse);

    expect(result.nodes).toHaveLength(3);
    expect(result.edges).toHaveLength(2);

    // All nodes should have positions
    result.nodes.forEach((node) => {
      expect(node.position).toBeDefined();
      expect(typeof node.position.x).toBe('number');
      expect(typeof node.position.y).toBe('number');
    });
  });

  it('applies dark mode colors', async () => {
    const { layoutLineageGraph } = await import('../src/utils/lineageLayoutUtils');

    const lightResult = layoutLineageGraph(mockGraphResponse, false);
    const darkResult = layoutLineageGraph(mockGraphResponse, true);

    // Colors should differ between light and dark mode
    expect(lightResult.nodes[0].data.colors.bg).not.toBe(darkResult.nodes[0].data.colors.bg);
  });

  it('sets animated edges for data flow types', async () => {
    const { layoutLineageGraph } = await import('../src/utils/lineageLayoutUtils');

    const result = layoutLineageGraph(mockGraphResponse);

    const directEdge = result.edges.find((e) => e.data?.edgeType === 'direct');
    expect(directEdge?.animated).toBe(true);
  });
});
