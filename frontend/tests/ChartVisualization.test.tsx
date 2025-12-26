/**
 * ChartVisualization Component Tests
 *
 * Tests for the main chart visualization container and individual chart components
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ChartVisualization } from '../src/components/visualization/ChartVisualization';
import { ChartToggle } from '../src/components/visualization/ChartToggle';
import { ExportDropdown } from '../src/components/visualization/ExportDropdown';

// Mock recharts to avoid complex rendering issues in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  ScatterChart: ({ children }: { children: React.ReactNode }) => <div data-testid="scatter-chart">{children}</div>,
  Scatter: () => <div data-testid="scatter" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  ZAxis: () => <div data-testid="z-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  Cell: () => <div data-testid="cell" />,
}));

describe('ChartVisualization', () => {
  // 10 categories to trigger bar chart (9-15 = bar, 2-8 = pie)
  const mockBarData = [
    { category: 'Cat1', value: 100 },
    { category: 'Cat2', value: 200 },
    { category: 'Cat3', value: 150 },
    { category: 'Cat4', value: 180 },
    { category: 'Cat5', value: 120 },
    { category: 'Cat6', value: 190 },
    { category: 'Cat7', value: 110 },
    { category: 'Cat8', value: 170 },
    { category: 'Cat9', value: 130 },
    { category: 'Cat10', value: 160 },
  ];

  const mockTimeSeriesData = [
    { date: '2024-01-01', sales: 100 },
    { date: '2024-01-02', sales: 150 },
    { date: '2024-01-03', sales: 120 },
  ];

  const mockPieData = [
    { region: 'North', sales: 100 },
    { region: 'South', sales: 150 },
    { region: 'East', sales: 120 },
    { region: 'West', sales: 80 },
  ];

  it('renders without crashing', () => {
    render(<ChartVisualization data={mockBarData} statistics={{}} />);
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays chart type badge', () => {
    render(<ChartVisualization data={mockBarData} statistics={{}} />);
    // Should show either Bar Chart, Pie Chart, etc. (may have alternatives too)
    const badges = screen.getAllByText(/Chart|Plot/);
    expect(badges.length).toBeGreaterThan(0);
    expect(badges[0]).toBeInTheDocument();
  });

  it('displays reason for chart selection', () => {
    render(<ChartVisualization data={mockBarData} statistics={{}} />);
    // Should show a reason text
    const reasonText = screen.getByText(/categories|distribution|comparison|visualization/i);
    expect(reasonText).toBeInTheDocument();
  });

  it('renders bar chart for categorical data', () => {
    render(<ChartVisualization data={mockBarData} statistics={{}} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders line chart for time-series data', () => {
    render(<ChartVisualization data={mockTimeSeriesData} statistics={{}} />);
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('shows "No Visualization Available" for insufficient data', () => {
    const singleRow = [{ value: 100 }];
    render(<ChartVisualization data={singleRow} statistics={{}} />);
    expect(screen.getByText('No Visualization Available')).toBeInTheDocument();
  });

  it('shows reason when no visualization available', () => {
    const singleRow = [{ value: 100 }];
    render(<ChartVisualization data={singleRow} statistics={{}} />);
    expect(screen.getByText(/Insufficient data/i)).toBeInTheDocument();
  });

  it('respects custom height prop', () => {
    render(<ChartVisualization data={mockBarData} statistics={{}} height={500} />);
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('handles empty data array', () => {
    render(<ChartVisualization data={[]} statistics={{}} />);
    expect(screen.getByText('No Visualization Available')).toBeInTheDocument();
  });

  it('renders with detected correlations', () => {
    const numericData = [
      { price: 10, quantity: 100 },
      { price: 20, quantity: 80 },
    ];
    const statistics = {
      correlations: {
        found: true,
        significant_correlations: [
          { column1: 'price', column2: 'quantity', correlation: -0.9 },
        ],
      },
    };
    render(<ChartVisualization data={numericData} statistics={statistics} />);
    expect(screen.getByTestId('scatter-chart')).toBeInTheDocument();
  });

  it('renders with detected trends', () => {
    const statistics = {
      trends: {
        found: true,
        detected_trends: [
          { column: 'sales', temporal_column: 'date' },
        ],
      },
    };
    render(<ChartVisualization data={mockTimeSeriesData} statistics={statistics} />);
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});

describe('ChartToggle', () => {
  const mockOnModeChange = vi.fn();

  beforeEach(() => {
    mockOnModeChange.mockClear();
  });

  it('renders table and chart toggle buttons', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="bar"
      />
    );

    expect(screen.getByTitle('View as table')).toBeInTheDocument();
    expect(screen.getByTitle(/View as Bar Chart/)).toBeInTheDocument();
  });

  it('highlights active mode', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="bar"
      />
    );

    const tableButton = screen.getByTitle('View as table');
    expect(tableButton.className).toContain('bg-white');
  });

  it('calls onModeChange when clicking table', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="bar"
      />
    );

    fireEvent.click(screen.getByTitle('View as table'));
    expect(mockOnModeChange).toHaveBeenCalledWith('table');
  });

  it('calls onModeChange when clicking chart', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="bar"
      />
    );

    fireEvent.click(screen.getByTitle(/View as Bar Chart/));
    expect(mockOnModeChange).toHaveBeenCalledWith('chart');
  });

  it('disables chart button when chart not available', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={false}
        chartType="table"
      />
    );

    const chartButton = screen.getByTitle('No chart available for this data');
    expect(chartButton).toBeDisabled();
    expect(chartButton.className).toContain('cursor-not-allowed');
  });

  it('does not call onModeChange when clicking disabled chart button', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={false}
        chartType="table"
      />
    );

    fireEvent.click(screen.getByTitle('No chart available for this data'));
    expect(mockOnModeChange).not.toHaveBeenCalled();
  });

  it('shows correct chart type in tooltip', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="line"
      />
    );

    expect(screen.getByTitle('View as Line Chart')).toBeInTheDocument();
  });

  it('shows correct tooltip for scatter plot', () => {
    render(
      <ChartToggle
        mode="table"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="scatter"
      />
    );

    expect(screen.getByTitle('View as Scatter Plot')).toBeInTheDocument();
  });
});

describe('ExportDropdown', () => {
  const mockData = [
    { name: 'Alice', age: 30 },
    { name: 'Bob', age: 25 },
  ];

  it('renders export button', () => {
    render(<ExportDropdown data={mockData} sql="SELECT * FROM users" />);
    expect(screen.getByTitle('Export data')).toBeInTheDocument();
  });

  it('disables button when no data', () => {
    render(<ExportDropdown data={[]} sql="SELECT * FROM users" />);
    expect(screen.getByTitle('No data to export')).toBeDisabled();
  });

  it('disables button when disabled prop is true', () => {
    render(<ExportDropdown data={mockData} sql="SELECT * FROM users" disabled={true} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('opens dropdown on click', () => {
    render(<ExportDropdown data={mockData} sql="SELECT * FROM users" />);

    fireEvent.click(screen.getByTitle('Export data'));

    expect(screen.getByText('Export as CSV')).toBeInTheDocument();
    expect(screen.getByText('Export as JSON')).toBeInTheDocument();
    expect(screen.getByText('Copy to Clipboard')).toBeInTheDocument();
  });

  it('shows row count in dropdown', () => {
    render(<ExportDropdown data={mockData} sql="SELECT * FROM users" />);

    fireEvent.click(screen.getByTitle('Export data'));

    expect(screen.getByText('2 rows')).toBeInTheDocument();
  });

  it('shows singular "row" for single item', () => {
    render(<ExportDropdown data={[mockData[0]]} sql="SELECT * FROM users" />);

    fireEvent.click(screen.getByTitle('Export data'));

    expect(screen.getByText('1 row')).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', () => {
    render(
      <div>
        <ExportDropdown data={mockData} sql="SELECT * FROM users" />
        <button>Outside</button>
      </div>
    );

    // Open dropdown
    fireEvent.click(screen.getByTitle('Export data'));
    expect(screen.getByText('Export as CSV')).toBeInTheDocument();

    // Click outside
    fireEvent.mouseDown(screen.getByText('Outside'));

    // Dropdown should close
    expect(screen.queryByText('Export as CSV')).not.toBeInTheDocument();
  });

  it('closes dropdown after clicking export option', () => {
    // Mock URL methods to prevent errors
    global.URL.createObjectURL = vi.fn(() => 'blob:mock');
    global.URL.revokeObjectURL = vi.fn();

    render(<ExportDropdown data={mockData} sql="SELECT * FROM users" />);

    fireEvent.click(screen.getByTitle('Export data'));
    fireEvent.click(screen.getByText('Export as CSV'));

    // Dropdown should close
    expect(screen.queryByText('Export as JSON')).not.toBeInTheDocument();
  });
});
