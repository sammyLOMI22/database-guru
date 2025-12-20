/**
 * CrossDatabaseChart Component Tests
 *
 * Tests for the cross-database comparison chart component
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CrossDatabaseChart } from '../src/components/visualization/CrossDatabaseChart';
import type { CrossDbChartConfig } from '../src/utils/crossDbUtils';

// Mock recharts to avoid complex rendering issues in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  ScatterChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="scatter-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  Line: () => <div data-testid="line" />,
  Pie: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie">{children}</div>
  ),
  Cell: () => <div data-testid="cell" />,
  Scatter: () => <div data-testid="scatter" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  ZAxis: () => <div data-testid="z-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

describe('CrossDatabaseChart', () => {
  const mockConfig: CrossDbChartConfig = {
    commonColumns: ['sales', 'revenue'],
    aggregatedData: [
      {
        databaseName: 'Production',
        databaseType: 'postgresql',
        rowCount: 100,
        metrics: { sales: 5000, revenue: 15000 },
        color: '#3b82f6',
      },
      {
        databaseName: 'Staging',
        databaseType: 'mysql',
        rowCount: 50,
        metrics: { sales: 2500, revenue: 8000 },
        color: '#8b5cf6',
      },
    ],
    primaryMetric: 'sales',
    aggregationMethod: 'sum',
  };

  const singleMetricConfig: CrossDbChartConfig = {
    commonColumns: ['total'],
    aggregatedData: [
      {
        databaseName: 'DB1',
        databaseType: 'postgresql',
        rowCount: 10,
        metrics: { total: 1000 },
        color: '#3b82f6',
      },
      {
        databaseName: 'DB2',
        databaseType: 'mysql',
        rowCount: 20,
        metrics: { total: 2000 },
        color: '#8b5cf6',
      },
    ],
    primaryMetric: 'total',
    aggregationMethod: 'sum',
  };

  it('renders chart header', () => {
    render(<CrossDatabaseChart config={mockConfig} />);
    expect(screen.getByText('Cross-Database Comparison')).toBeInTheDocument();
  });

  it('shows database and metric count in header', () => {
    render(<CrossDatabaseChart config={mockConfig} />);
    expect(screen.getByText(/2 databases, 2 metrics/)).toBeInTheDocument();
  });

  it('uses singular form for 1 metric', () => {
    render(<CrossDatabaseChart config={singleMetricConfig} />);
    expect(screen.getByText(/2 databases, 1 metric/)).toBeInTheDocument();
  });

  it('renders expanded by default', () => {
    render(<CrossDatabaseChart config={mockConfig} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('can be collapsed', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    fireEvent.click(screen.getByText('Cross-Database Comparison'));

    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });

  it('can be re-expanded', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    // Collapse
    fireEvent.click(screen.getByText('Cross-Database Comparison'));
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();

    // Expand
    fireEvent.click(screen.getByText('Cross-Database Comparison'));
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('respects defaultExpanded=false', () => {
    render(<CrossDatabaseChart config={mockConfig} defaultExpanded={false} />);
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });

  it('shows metric selector when multiple metrics', () => {
    render(<CrossDatabaseChart config={mockConfig} />);
    expect(screen.getByText('Metric:')).toBeInTheDocument();
    // Should have at least one combobox for metric selection
    expect(screen.getAllByRole('combobox').length).toBeGreaterThanOrEqual(1);
  });

  it('does not show metric selector for single metric', () => {
    render(<CrossDatabaseChart config={singleMetricConfig} />);
    expect(screen.queryByText('Metric:')).not.toBeInTheDocument();
  });

  it('lists all metrics in selector', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    // Find the metric selector (the one with 'sales' value)
    const selects = screen.getAllByRole('combobox');
    const metricSelect = selects.find(s => (s as HTMLSelectElement).value === 'sales');
    expect(metricSelect).toBeDefined();

    // Check options in the metric selector
    const options = metricSelect?.querySelectorAll('option');
    expect(options?.length).toBe(2);
  });

  it('can change selected metric', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    // Find the metric selector
    const selects = screen.getAllByRole('combobox');
    const metricSelect = selects.find(s => (s as HTMLSelectElement).value === 'sales');
    expect(metricSelect).toBeDefined();

    fireEvent.change(metricSelect!, { target: { value: 'revenue' } });
    expect((metricSelect as HTMLSelectElement).value).toBe('revenue');
  });

  it('renders summary stats for each database', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    expect(screen.getByText('Production')).toBeInTheDocument();
    expect(screen.getByText('Staging')).toBeInTheDocument();
  });

  it('shows row count in summary stats', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    expect(screen.getByText('100 rows')).toBeInTheDocument();
    expect(screen.getByText('50 rows')).toBeInTheDocument();
  });

  it('shows singular row for 1 row', () => {
    const singleRowConfig: CrossDbChartConfig = {
      ...mockConfig,
      aggregatedData: [
        { ...mockConfig.aggregatedData[0], rowCount: 1 },
        mockConfig.aggregatedData[1],
      ],
    };

    render(<CrossDatabaseChart config={singleRowConfig} />);
    expect(screen.getByText('1 row')).toBeInTheDocument();
  });

  it('displays metric values', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    // Default metric is 'sales'
    expect(screen.getByText('5.0K')).toBeInTheDocument(); // 5000
    expect(screen.getByText('2.5K')).toBeInTheDocument(); // 2500
  });

  it('updates metric values when changing selection', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    // Switch to revenue
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'revenue' } });

    // Should show revenue values now
    expect(screen.getByText('15.0K')).toBeInTheDocument(); // 15000
    expect(screen.getByText('8.0K')).toBeInTheDocument(); // 8000
  });

  it('renders color indicators for databases', () => {
    render(<CrossDatabaseChart config={mockConfig} />);

    // Check that colored divs are rendered
    const colorIndicators = document.querySelectorAll('.rounded-full');
    expect(colorIndicators.length).toBeGreaterThanOrEqual(2);
  });
});
