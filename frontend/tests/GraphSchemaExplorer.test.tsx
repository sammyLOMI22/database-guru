/**
 * Phase 25.2 — GraphSchemaExplorer vitest coverage.
 *
 * The component is a thin renderer over useGraphSchema(); we mock the hook
 * directly so each test injects its own schema payload and never touches
 * the network.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import GraphSchemaExplorer from '../src/components/graph/GraphSchemaExplorer';
import type { GraphSchemaResponse } from '../src/services/graphApi';

vi.mock('../src/hooks/useGraphSchema', () => ({
  useGraphSchema: vi.fn(),
  useIntrospectGraph: vi.fn(),
  useGraphSchemaSummary: vi.fn(),
}));

import { useGraphSchema } from '../src/hooks/useGraphSchema';

const SAMPLE_SCHEMA: GraphSchemaResponse = {
  connection_id: 1,
  provider: 'neo4j',
  database_name: 'neo4j',
  labels: [
    {
      name: 'User',
      estimated_count: 1234,
      properties: [
        {
          name: 'email',
          types: ['String'],
          indexed: true,
          nullable: false,
          sample_values: null,
        },
        {
          name: 'name',
          types: ['String'],
          indexed: false,
          nullable: true,
          sample_values: null,
        },
      ],
    },
    {
      name: 'Order',
      estimated_count: 5678,
      properties: [
        {
          name: 'total',
          types: ['Float'],
          indexed: false,
          nullable: false,
          sample_values: null,
        },
      ],
    },
  ],
  relationships: [
    {
      name: 'PURCHASED',
      estimated_count: 999,
      properties: [
        {
          name: 'at',
          types: ['DateTime'],
          indexed: false,
          nullable: false,
          sample_values: null,
        },
      ],
    },
  ],
  patterns: [
    {
      source_labels: ['User'],
      relationship_type: 'PURCHASED',
      target_labels: ['Order'],
      estimated_count: 999,
    },
  ],
  indexes: [
    {
      name: 'user_email_idx',
      entity_type: 'NODE',
      labels_or_types: ['User'],
      properties: ['email'],
      type: 'RANGE',
      state: 'ONLINE',
    },
  ],
  constraints: [
    {
      name: 'user_email_unique',
      entity_type: 'NODE',
      labels_or_types: ['User'],
      properties: ['email'],
      type: 'UNIQUENESS',
    },
  ],
  warnings: [],
  collected_at: '2026-05-16T12:00:00+00:00',
  schema_updated_at: '2026-05-16T12:00:00+00:00',
  server_version: '5.18.0',
  edition: 'enterprise',
  label_count: 2,
  relationship_type_count: 1,
  pattern_count: 1,
  index_count: 1,
  constraint_count: 1,
  cached: true,
};

function mockSchemaQuery(overrides: any = {}) {
  (useGraphSchema as any).mockReturnValue({
    data: SAMPLE_SCHEMA,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  });
}

describe('GraphSchemaExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty-state when no connection is selected', () => {
    (useGraphSchema as any).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<GraphSchemaExplorer connectionId={null} />);
    expect(
      screen.getByText(/Select a Neo4j connection/i),
    ).toBeInTheDocument();
  });

  it('renders loading state', () => {
    (useGraphSchema as any).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<GraphSchemaExplorer connectionId={1} />);
    expect(screen.getByText(/Loading schema/i)).toBeInTheDocument();
  });

  it('renders labels view with property table for the first label by default', () => {
    mockSchemaQuery();
    render(<GraphSchemaExplorer connectionId={1} />);
    // Both labels appear in the list. "User" surfaces in both the list
    // button and the detail-panel header, so use getAllByText.
    expect(screen.getAllByText('User').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Order').length).toBeGreaterThan(0);
    // Property table renders for the first label
    expect(screen.getByText('email')).toBeInTheDocument();
    expect(screen.getByText('name')).toBeInTheDocument();
  });

  it('filter input narrows the labels list', () => {
    mockSchemaQuery();
    render(<GraphSchemaExplorer connectionId={1} />);
    const filter = screen.getByLabelText(/Filter schema entries/i);
    // fireEvent.change is synchronous, so React batches the resulting render
    // inside its own act() — keeps the test free of "not wrapped in act"
    // warnings that userEvent's asyncWrapper drains around.
    fireEvent.change(filter, { target: { value: 'Ord' } });
    // "User" should disappear from the list panel
    expect(screen.queryByText('User')).not.toBeInTheDocument();
    // "Order" still surfaces — in the list button and detail header.
    expect(screen.getAllByText('Order').length).toBeGreaterThan(0);
  });

  it('switches to indexes view and renders an index row', () => {
    mockSchemaQuery();
    render(<GraphSchemaExplorer connectionId={1} />);
    fireEvent.click(screen.getByRole('button', { name: /Indexes/i }));
    expect(screen.getByText('user_email_idx')).toBeInTheDocument();
    expect(screen.getByText('RANGE')).toBeInTheDocument();
    expect(screen.getByText('ONLINE')).toBeInTheDocument();
  });

  it('renders patterns view with sampled count', () => {
    mockSchemaQuery();
    render(<GraphSchemaExplorer connectionId={1} />);
    fireEvent.click(screen.getByRole('button', { name: /Patterns/i }));
    // Pattern table shows the rel type cell
    const rows = screen.getAllByRole('row');
    // Header + one pattern row
    expect(rows.length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('PURCHASED').length).toBeGreaterThan(0);
  });

  it('clicking a label updates the detail panel', () => {
    mockSchemaQuery();
    render(<GraphSchemaExplorer connectionId={1} />);
    // Initially shows User properties
    expect(screen.getByText('email')).toBeInTheDocument();
    // Click the Order button in the list panel — there's also an Order
    // header in the (initially empty) detail panel for the default
    // selection, so disambiguate via role+name.
    const orderButton = screen.getAllByRole('button', { name: /Order/i })[0];
    fireEvent.click(orderButton);
    // Order's "total" property surfaces in the detail table
    expect(screen.getByText('total')).toBeInTheDocument();
  });
});
