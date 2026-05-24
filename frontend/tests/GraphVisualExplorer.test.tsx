/**
 * Phase 25.5 — GraphVisualExplorer + GraphCanvas vitest coverage.
 *
 * The canvas itself is a thin wrapper over React Flow + dagre — we don't
 * need to render real coordinates. We stub `reactflow` (same pattern as
 * `LineageGraph.test.tsx`) so we can assert on:
 *   - Form state transitions (label → property → value → explore).
 *   - Truncation banner appearing when the backend flags it.
 *   - Node click → property panel surfaces.
 *   - "Expand from here" reuses the clicked node's primary key.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from '@testing-library/react';

// ── Mock reactflow ───────────────────────────────────────────────────────
vi.mock('reactflow', () => ({
  default: ({ nodes, onNodeClick }: any) => (
    <div data-testid="react-flow" data-nodes={nodes?.length || 0}>
      {nodes?.map((node: any) => (
        <button
          key={node.id}
          data-testid={`node-${node.id}`}
          onClick={(e) => onNodeClick?.(e, node)}
        >
          {node.id}
        </button>
      ))}
    </div>
  ),
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Controls: () => null,
  Background: () => null,
  MiniMap: () => null,
  BackgroundVariant: { Dots: 'dots' },
  useNodesState: (initial: any[] = []) => {
    const [nodes, setNodes] = React.useState(initial);
    return [nodes, setNodes, vi.fn()];
  },
  useEdgesState: (initial: any[] = []) => {
    const [edges, setEdges] = React.useState(initial);
    return [edges, setEdges, vi.fn()];
  },
  Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
}));

// dagre's layout doesn't matter for these tests — short-circuit it.
vi.mock('dagre', () => ({
  default: {
    graphlib: {
      Graph: class {
        _nodes = new Map<string, any>();
        setDefaultEdgeLabel() {}
        setGraph() {}
        setNode(id: string, attrs: any) {
          this._nodes.set(id, { ...attrs, x: 0, y: 0 });
        }
        setEdge() {}
        node(id: string) {
          return this._nodes.get(id) || { x: 0, y: 0 };
        }
      },
    },
    layout: () => {},
  },
}));

// ── Mock graphAPI ────────────────────────────────────────────────────────
vi.mock('../src/services/graphApi', () => ({
  graphAPI: {
    getSchema: vi.fn(),
    explore: vi.fn(),
  },
}));

import { graphAPI } from '../src/services/graphApi';
import type {
  GraphExploreResponse,
  GraphSchemaResponse,
} from '../src/services/graphApi';
import GraphVisualExplorer from '../src/components/graph/GraphVisualExplorer';

// ── Fixtures ─────────────────────────────────────────────────────────────

const SAMPLE_SCHEMA: GraphSchemaResponse = {
  connection_id: 1,
  provider: 'neo4j',
  database_name: 'neo4j',
  labels: [
    {
      name: 'User',
      estimated_count: 100,
      properties: [
        { name: 'email', types: ['String'], indexed: true, nullable: false, sample_values: null },
        { name: 'name', types: ['String'], indexed: false, nullable: true, sample_values: null },
      ],
    },
    {
      name: 'Order',
      estimated_count: 200,
      properties: [
        { name: 'id', types: ['String'], indexed: true, nullable: false, sample_values: null },
      ],
    },
  ],
  relationships: [],
  patterns: [
    {
      source_labels: ['User'],
      relationship_type: 'PURCHASED',
      target_labels: ['Order'],
      estimated_count: 50,
    },
    {
      source_labels: ['User'],
      relationship_type: 'FOLLOWS',
      target_labels: ['User'],
      estimated_count: 10,
    },
  ],
  indexes: [],
  constraints: [],
  warnings: [],
  collected_at: null,
  schema_updated_at: null,
  server_version: null,
  edition: null,
  label_count: 2,
  relationship_type_count: 2,
  pattern_count: 2,
  index_count: 0,
  constraint_count: 0,
  cached: true,
};

function makeExploreResponse(overrides: Partial<GraphExploreResponse> = {}): GraphExploreResponse {
  return {
    connection_id: 1,
    start_label: 'User',
    depth: 1,
    direction: 'any',
    rel_types: [],
    safety_level: 'read_only',
    success: true,
    record_count: 2,
    execution_time_ms: 12.3,
    truncated: false,
    table: { columns: ['p'], rows: [] },
    graph_viz: {
      nodes: [
        { id: 'n1', labels: ['User'], displayName: 'alice@b.com', properties: { email: 'alice@b.com' } },
        { id: 'n2', labels: ['Order'], displayName: '42', properties: { id: '42' } },
      ],
      edges: [],
      has_graph: true,
    },
    warnings: [],
    server_warnings: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  (graphAPI.getSchema as any).mockResolvedValue(SAMPLE_SCHEMA);
});

// ── Tests ────────────────────────────────────────────────────────────────

describe('GraphVisualExplorer', () => {
  it('auto-populates the form with the first label + best-guess property', async () => {
    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => {
      expect((screen.getByTestId('start-label') as HTMLSelectElement).value).toBe('User');
    });
    // Among User's properties, `email` is the preferred anchor (preferred list).
    expect((screen.getByTestId('start-property') as HTMLSelectElement).value).toBe('email');
  });

  it('shows rel-type chips sourced from the cached schema patterns', async () => {
    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => expect(screen.getByTestId('rel-chip-PURCHASED')).toBeInTheDocument());
    expect(screen.getByTestId('rel-chip-FOLLOWS')).toBeInTheDocument();
  });

  it('refuses Explore when no value is entered', async () => {
    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => screen.getByTestId('explore-btn'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('explore-btn'));
    });
    expect(screen.getByTestId('explore-error')).toHaveTextContent(
      /pick a label, property, and value/i,
    );
    expect(graphAPI.explore as any).not.toHaveBeenCalled();
  });

  it('explore call carries selected rel-type chips through', async () => {
    (graphAPI.explore as any).mockResolvedValue(makeExploreResponse());
    render(<GraphVisualExplorer connectionId={1} />);

    await waitFor(() => screen.getByTestId('rel-chip-FOLLOWS'));
    fireEvent.change(screen.getByTestId('start-value'), {
      target: { value: 'alice@b.com' },
    });
    fireEvent.click(screen.getByTestId('rel-chip-FOLLOWS'));

    await act(async () => {
      fireEvent.click(screen.getByTestId('explore-btn'));
    });

    expect(graphAPI.explore as any).toHaveBeenCalledWith(1, expect.objectContaining({
      start_label: 'User',
      start_property: 'email',
      start_value: 'alice@b.com',
      rel_types: ['FOLLOWS'],
    }));
  });

  it('renders the truncation banner when backend flags truncated=true', async () => {
    (graphAPI.explore as any).mockResolvedValue(
      makeExploreResponse({
        truncated: true,
        warnings: ['Visualization truncated — only 2 node(s) shown.'],
      }),
    );

    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => screen.getByTestId('explore-btn'));

    fireEvent.change(screen.getByTestId('start-value'), {
      target: { value: 'alice@b.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('explore-btn'));
    });

    await waitFor(() =>
      expect(screen.getByTestId('graph-canvas-warnings')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('graph-canvas-warnings')).toHaveTextContent(/truncated/i);
    expect(screen.getByTestId('explore-summary')).toHaveTextContent(/truncated/i);
  });

  it('opens the property panel when a canvas node is clicked', async () => {
    (graphAPI.explore as any).mockResolvedValue(makeExploreResponse());

    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => screen.getByTestId('explore-btn'));

    fireEvent.change(screen.getByTestId('start-value'), {
      target: { value: 'alice@b.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('explore-btn'));
    });

    // The mocked reactflow renders one button per node.
    await waitFor(() => screen.getByTestId('node-n1'));
    fireEvent.click(screen.getByTestId('node-n1'));

    await waitFor(() => screen.getByTestId('property-panel'));
    expect(screen.getByTestId('property-panel')).toHaveTextContent('alice@b.com');
  });

  it('"Expand from here" re-issues the explore call with the clicked node as anchor', async () => {
    (graphAPI.explore as any)
      .mockResolvedValueOnce(makeExploreResponse())
      .mockResolvedValueOnce(makeExploreResponse({ record_count: 5 }));

    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => screen.getByTestId('explore-btn'));

    fireEvent.change(screen.getByTestId('start-value'), {
      target: { value: 'alice@b.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('explore-btn'));
    });
    await waitFor(() => screen.getByTestId('node-n2'));

    // Click the Order node, then "Expand from here".
    fireEvent.click(screen.getByTestId('node-n2'));
    await waitFor(() => screen.getByTestId('expand-from-selected'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('expand-from-selected'));
    });

    // Second call: Order's anchor property is `id` (the only one), value '42'.
    expect((graphAPI.explore as any).mock.calls.length).toBe(2);
    expect((graphAPI.explore as any).mock.calls[1][1]).toMatchObject({
      start_label: 'Order',
      start_property: 'id',
      start_value: '42',
    });
  });

  it('surfaces backend error_message + error_hint on 502', async () => {
    (graphAPI.explore as any).mockRejectedValue({
      response: {
        data: {
          detail: {
            error_message: 'Syntax error in Cypher',
            error_hint: 'Check label spelling',
            error_category: 'syntax',
          },
        },
      },
    });

    render(<GraphVisualExplorer connectionId={1} />);
    await waitFor(() => screen.getByTestId('explore-btn'));

    fireEvent.change(screen.getByTestId('start-value'), {
      target: { value: 'alice@b.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('explore-btn'));
    });

    await waitFor(() => screen.getByTestId('explore-error'));
    expect(screen.getByTestId('explore-error')).toHaveTextContent('Syntax error in Cypher');
    expect(screen.getByTestId('explore-error')).toHaveTextContent('Check label spelling');
  });
});
