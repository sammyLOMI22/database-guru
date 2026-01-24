/**
 * QueryPatternHeatmap Component Tests - Phase 11.5
 *
 * Tests:
 * - Loading state
 * - Empty state when no patterns
 * - Grid rendering with correct cells
 * - View mode toggle
 * - Time range selection
 * - Click cell shows detail panel
 * - Bottlenecks section visibility
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API modules
vi.mock('../src/services/lineageApi', () => ({
  lineageAPI: {
    getHeatmapData: vi.fn(),
  },
}));

vi.mock('../src/services/api', () => ({
  connectionsAPI: {
    listConnections: vi.fn().mockResolvedValue({
      connections: [
        { id: 1, name: 'Test DB', database_type: 'postgresql' },
        { id: 2, name: 'Prod DB', database_type: 'mysql' },
      ],
      count: 2,
    }),
  },
}));

import { QueryPatternHeatmap } from '../src/components/lineage/QueryPatternHeatmap';
import { lineageAPI } from '../src/services/lineageApi';

const mockHeatmapData = {
  table_usage: [
    { table_name: 'orders', query_count: 45, join_count: 20, avg_execution_time_ms: 234, last_used_at: '2026-01-24T10:00:00Z' },
    { table_name: 'customers', query_count: 30, join_count: 18, avg_execution_time_ms: 150, last_used_at: '2026-01-24T09:00:00Z' },
    { table_name: 'products', query_count: 15, join_count: 5, avg_execution_time_ms: 80, last_used_at: '2026-01-23T10:00:00Z' },
    { table_name: 'shipments', query_count: 5, join_count: 2, avg_execution_time_ms: 2500, last_used_at: '2026-01-22T10:00:00Z' },
  ],
  join_patterns: [
    { table_a: 'customers', table_b: 'orders', join_count: 18, sample_sql: 'SELECT * FROM orders JOIN customers...', avg_execution_time_ms: 200 },
    { table_a: 'orders', table_b: 'products', join_count: 12, sample_sql: 'SELECT * FROM orders JOIN products...', avg_execution_time_ms: 180 },
  ],
  bottlenecks: [
    { table_name: 'shipments', query_count: 5, avg_execution_time_ms: 2500, max_execution_time_ms: 5000, bottleneck_score: 0.85 },
    { table_name: 'orders', query_count: 45, avg_execution_time_ms: 234, max_execution_time_ms: 800, bottleneck_score: 0.72 },
  ],
  time_range_days: 30,
  total_queries_analyzed: 95,
  connection_id: null,
};

describe('QueryPatternHeatmap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', async () => {
    (lineageAPI.getHeatmapData as any).mockImplementation(() => new Promise(() => {}));
    render(<QueryPatternHeatmap />);
    expect(screen.getByText('Loading patterns...')).toBeInTheDocument();
  });

  it('shows empty state when no data', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue({
      table_usage: [],
      join_patterns: [],
      bottlenecks: [],
      time_range_days: 30,
      total_queries_analyzed: 0,
      connection_id: null,
    });

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('No query patterns found')).toBeInTheDocument();
    });
  });

  it('renders table cells from data', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('orders')).toBeInTheDocument();
      expect(screen.getByText('customers')).toBeInTheDocument();
      expect(screen.getByText('products')).toBeInTheDocument();
      expect(screen.getByText('shipments')).toBeInTheDocument();
    });
  });

  it('shows query count in frequency mode', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  it('shows total queries analyzed', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('95 queries analyzed')).toBeInTheDocument();
    });
  });

  it('renders view mode toggle buttons', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('Frequency')).toBeInTheDocument();
      expect(screen.getByText('Joins')).toBeInTheDocument();
      expect(screen.getByText('Performance')).toBeInTheDocument();
    });
  });

  it('renders time range buttons', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('7d')).toBeInTheDocument();
      expect(screen.getByText('30d')).toBeInTheDocument();
      expect(screen.getByText('90d')).toBeInTheDocument();
      expect(screen.getByText('All')).toBeInTheDocument();
    });
  });

  it('switches to joins view on toggle click', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('orders')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Joins'));
    // In joins mode, should show join counts
    expect(screen.getByText('20')).toBeInTheDocument(); // orders join_count
  });

  it('clicking a cell shows detail panel', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('orders')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('orders'));
    // Detail panel should show stats
    await waitFor(() => {
      expect(screen.getByText('45 queries')).toBeInTheDocument();
      expect(screen.getByText('20 joins')).toBeInTheDocument();
    });
  });

  it('shows join partners in detail panel', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('orders')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('orders'));
    await waitFor(() => {
      expect(screen.getByText('Common JOINs:')).toBeInTheDocument();
      expect(screen.getByText('customers (18x)')).toBeInTheDocument();
      expect(screen.getByText('products (12x)')).toBeInTheDocument();
    });
  });

  it('shows bottlenecks in performance mode', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('orders')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Performance'));
    await waitFor(() => {
      expect(screen.getByText('Performance Bottlenecks')).toBeInTheDocument();
    });
  });

  it('changes time range and refetches', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('orders')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('7d'));
    await waitFor(() => {
      expect(lineageAPI.getHeatmapData).toHaveBeenCalledWith(0, 7);
    });
  });

  it('handles API errors gracefully', async () => {
    (lineageAPI.getHeatmapData as any).mockRejectedValue(new Error('Network error'));

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('renders connection dropdown with options', async () => {
    (lineageAPI.getHeatmapData as any).mockResolvedValue(mockHeatmapData);

    render(<QueryPatternHeatmap />);
    await waitFor(() => {
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select).toBeInTheDocument();
    });
  });
});
