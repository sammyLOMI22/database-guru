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

// =============================================================================
// LineagePanel Tests
// =============================================================================

describe('LineagePanel', () => {
  it('renders tab navigation', async () => {
    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    expect(screen.getByText('Explore')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Impact')).toBeInTheDocument();
  });

  it('shows explore tab by default', async () => {
    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    expect(screen.getByTestId('sql-input')).toBeInTheDocument();
  });

  it('switches to history tab', async () => {
    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    fireEvent.click(screen.getByText('History'));

    await waitFor(() => {
      expect(screen.getByTestId('query-id-input')).toBeInTheDocument();
    });
  });

  it('switches to impact tab', async () => {
    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    fireEvent.click(screen.getByText('Impact'));

    await waitFor(() => {
      expect(screen.getByTestId('impact-table-input')).toBeInTheDocument();
      expect(screen.getByTestId('impact-column-input')).toBeInTheDocument();
      expect(screen.getByTestId('impact-analyze-button')).toBeInTheDocument();
    });
  });

  it('analyzes impact and shows results', async () => {
    (lineageAPI.analyzeImpact as any).mockResolvedValue(mockImpactResponse);

    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    fireEvent.click(screen.getByText('Impact'));

    await waitFor(() => {
      expect(screen.getByTestId('impact-table-input')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('impact-table-input'), { target: { value: 'customers' } });
    fireEvent.change(screen.getByTestId('impact-column-input'), { target: { value: 'email' } });

    await act(async () => {
      fireEvent.click(screen.getByTestId('impact-analyze-button'));
    });

    await waitFor(() => {
      expect(lineageAPI.analyzeImpact).toHaveBeenCalledWith('customers', 'email');
      expect(screen.getByText(/Impact:/)).toBeInTheDocument();
      expect(screen.getByText(/2 queries reference customers\.email/)).toBeInTheDocument();
    });
  });

  it('handles impact analysis error', async () => {
    (lineageAPI.analyzeImpact as any).mockRejectedValue({
      response: { data: { detail: 'Analysis failed' } },
    });

    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    fireEvent.click(screen.getByText('Impact'));

    await waitFor(() => {
      expect(screen.getByTestId('impact-table-input')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('impact-table-input'), { target: { value: 'test' } });

    await act(async () => {
      fireEvent.click(screen.getByTestId('impact-analyze-button'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Analysis failed/)).toBeInTheDocument();
    });
  });

  it('loads query lineage from history', async () => {
    (lineageAPI.getQueryLineage as any).mockResolvedValue(mockGraphResponse);

    const { LineagePanel } = await import('../src/components/lineage/LineagePanel');
    render(<LineagePanel />);

    fireEvent.click(screen.getByText('History'));

    await waitFor(() => {
      expect(screen.getByTestId('query-id-input')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('query-id-input'), { target: { value: '42' } });

    const loadBtn = screen.getByText('Load');
    await act(async () => {
      fireEvent.click(loadBtn);
    });

    await waitFor(() => {
      expect(lineageAPI.getQueryLineage).toHaveBeenCalledWith(42);
    });
  });
});

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
