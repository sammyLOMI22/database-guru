/**
 * Advanced Charts Tests (Phase 10)
 *
 * Tests for advanced chart components: Treemap, Sunburst, Histogram, BoxPlot, Area
 * Tests for utility functions: hierarchicalChartUtils, statisticalChartUtils
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Import chart components
import { TreemapView } from '../src/components/visualization/TreemapView';
import { SunburstView } from '../src/components/visualization/SunburstView';
import { HistogramView } from '../src/components/visualization/HistogramView';
import { BoxPlotView } from '../src/components/visualization/BoxPlotView';
import { AreaChartView } from '../src/components/visualization/AreaChartView';
import { BubbleChartView } from '../src/components/visualization/BubbleChartView';
import { ChartToggle } from '../src/components/visualization/ChartToggle';

// Import utility functions
import {
  prepareTreemapData,
  prepareSunburstData,
  prepareSankeyData,
  assignColors,
  isHierarchicalData,
  HIERARCHICAL_COLORS,
} from '../src/utils/hierarchicalChartUtils';

import {
  calculateBoxPlot,
  prepareBoxPlotData,
  prepareHistogramData,
  prepareBubbleData,
  calculateSummaryStats,
} from '../src/utils/statisticalChartUtils';

// Mock recharts components
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Treemap: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="treemap">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="pie">{children}</div>
  ),
  Cell: () => <div data-testid="cell" />,
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="bar">{children}</div>
  ),
  AreaChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => <div data-testid="area" />,
  ComposedChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="composed-chart">{children}</div>
  ),
  ScatterChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="scatter-chart">{children}</div>
  ),
  Scatter: () => <div data-testid="scatter" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  ZAxis: () => <div data-testid="z-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
  ErrorBar: () => <div data-testid="error-bar" />,
  Sector: () => <div data-testid="sector" />,
}));

// =============================================================================
// TREEMAP VIEW TESTS
// =============================================================================

describe('TreemapView', () => {
  const mockHierarchicalData = [
    { category: 'Electronics', subcategory: 'Phones', value: 1000 },
    { category: 'Electronics', subcategory: 'Laptops', value: 800 },
    { category: 'Clothing', subcategory: 'Shirts', value: 500 },
    { category: 'Clothing', subcategory: 'Pants', value: 400 },
    { category: 'Food', subcategory: 'Fruits', value: 300 },
  ];

  it('renders without crashing', () => {
    render(
      <TreemapView
        data={mockHierarchicalData}
        categoryColumns={['category']}
        valueColumn="value"
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays title when provided', () => {
    render(
      <TreemapView
        data={mockHierarchicalData}
        categoryColumns={['category']}
        valueColumn="value"
        title="Sales by Category"
      />
    );
    expect(screen.getByText('Sales by Category')).toBeInTheDocument();
  });

  it('shows no data message for empty data', () => {
    render(
      <TreemapView
        data={[]}
        categoryColumns={['category']}
        valueColumn="value"
      />
    );
    expect(screen.getByText(/No hierarchical data available/)).toBeInTheDocument();
  });

  it('renders treemap component', () => {
    render(
      <TreemapView
        data={mockHierarchicalData}
        categoryColumns={['category']}
        valueColumn="value"
      />
    );
    expect(screen.getByTestId('treemap')).toBeInTheDocument();
  });

  it('renders with multiple category columns', () => {
    render(
      <TreemapView
        data={mockHierarchicalData}
        categoryColumns={['category', 'subcategory']}
        valueColumn="value"
      />
    );
    expect(screen.getByTestId('treemap')).toBeInTheDocument();
  });
});

// =============================================================================
// SUNBURST VIEW TESTS
// =============================================================================

describe('SunburstView', () => {
  const mockHierarchicalData = [
    { region: 'North', state: 'NY', sales: 500 },
    { region: 'North', state: 'MA', sales: 400 },
    { region: 'South', state: 'TX', sales: 600 },
    { region: 'South', state: 'FL', sales: 450 },
  ];

  it('renders without crashing', () => {
    render(
      <SunburstView
        data={mockHierarchicalData}
        categoryColumns={['region', 'state']}
        valueColumn="sales"
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays title when provided', () => {
    render(
      <SunburstView
        data={mockHierarchicalData}
        categoryColumns={['region', 'state']}
        valueColumn="sales"
        title="Sales Distribution"
      />
    );
    expect(screen.getByText('Sales Distribution')).toBeInTheDocument();
  });

  it('shows no data message for empty data', () => {
    render(
      <SunburstView
        data={[]}
        categoryColumns={['region']}
        valueColumn="sales"
      />
    );
    expect(screen.getByText(/No hierarchical data available/)).toBeInTheDocument();
  });

  it('renders pie chart (sunburst rings)', () => {
    render(
      <SunburstView
        data={mockHierarchicalData}
        categoryColumns={['region', 'state']}
        valueColumn="sales"
      />
    );
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('shows depth indicator', () => {
    render(
      <SunburstView
        data={mockHierarchicalData}
        categoryColumns={['region', 'state']}
        valueColumn="sales"
      />
    );
    expect(screen.getByText(/Hierarchy depth:/)).toBeInTheDocument();
  });
});

// =============================================================================
// HISTOGRAM VIEW TESTS
// =============================================================================

describe('HistogramView', () => {
  const mockNumericData = [
    { id: 1, score: 85 },
    { id: 2, score: 92 },
    { id: 3, score: 78 },
    { id: 4, score: 88 },
    { id: 5, score: 95 },
    { id: 6, score: 72 },
    { id: 7, score: 81 },
    { id: 8, score: 90 },
  ];

  it('renders without crashing', () => {
    render(
      <HistogramView
        data={mockNumericData}
        valueColumn="score"
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays title when provided', () => {
    render(
      <HistogramView
        data={mockNumericData}
        valueColumn="score"
        title="Score Distribution"
      />
    );
    expect(screen.getByText('Score Distribution')).toBeInTheDocument();
  });

  it('shows no data message for empty data', () => {
    render(
      <HistogramView
        data={[]}
        valueColumn="score"
      />
    );
    expect(screen.getByText(/No numeric data available/)).toBeInTheDocument();
  });

  it('renders bar chart for histogram', () => {
    render(
      <HistogramView
        data={mockNumericData}
        valueColumn="score"
      />
    );
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('shows statistics summary', () => {
    render(
      <HistogramView
        data={mockNumericData}
        valueColumn="score"
      />
    );
    expect(screen.getByText(/Mean:/)).toBeInTheDocument();
    expect(screen.getByText(/Median:/)).toBeInTheDocument();
    expect(screen.getByText(/Std Dev:/)).toBeInTheDocument();
  });
});

// =============================================================================
// BOXPLOT VIEW TESTS
// =============================================================================

describe('BoxPlotView', () => {
  const mockCategoryData = [
    { category: 'A', value: 10 },
    { category: 'A', value: 15 },
    { category: 'A', value: 12 },
    { category: 'B', value: 20 },
    { category: 'B', value: 25 },
    { category: 'B', value: 22 },
    { category: 'C', value: 8 },
    { category: 'C', value: 10 },
    { category: 'C', value: 9 },
  ];

  it('renders without crashing', () => {
    render(
      <BoxPlotView
        data={mockCategoryData}
        categoryColumn="category"
        valueColumn="value"
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays title when provided', () => {
    render(
      <BoxPlotView
        data={mockCategoryData}
        categoryColumn="category"
        valueColumn="value"
        title="Value Distribution"
      />
    );
    expect(screen.getByText('Value Distribution')).toBeInTheDocument();
  });

  it('shows no data message for empty data', () => {
    render(
      <BoxPlotView
        data={[]}
        categoryColumn="category"
        valueColumn="value"
      />
    );
    expect(screen.getByText(/No data available/)).toBeInTheDocument();
  });

  it('renders composed chart for box plot', () => {
    render(
      <BoxPlotView
        data={mockCategoryData}
        categoryColumn="category"
        valueColumn="value"
      />
    );
    expect(screen.getByTestId('composed-chart')).toBeInTheDocument();
  });

  it('shows legend for chart elements', () => {
    render(
      <BoxPlotView
        data={mockCategoryData}
        categoryColumn="category"
        valueColumn="value"
      />
    );
    expect(screen.getByText(/IQR/)).toBeInTheDocument();
    expect(screen.getByText(/Median/)).toBeInTheDocument();
  });
});

// =============================================================================
// AREA CHART VIEW TESTS
// =============================================================================

describe('AreaChartView', () => {
  const mockTimeSeriesData = [
    { month: 'Jan', sales: 100, profit: 20 },
    { month: 'Feb', sales: 120, profit: 25 },
    { month: 'Mar', sales: 140, profit: 30 },
    { month: 'Apr', sales: 130, profit: 28 },
    { month: 'May', sales: 160, profit: 35 },
  ];

  it('renders without crashing', () => {
    render(
      <AreaChartView
        data={mockTimeSeriesData}
        xColumn="month"
        yColumns={['sales']}
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays title when provided', () => {
    render(
      <AreaChartView
        data={mockTimeSeriesData}
        xColumn="month"
        yColumns={['sales']}
        title="Monthly Sales"
      />
    );
    expect(screen.getByText('Monthly Sales')).toBeInTheDocument();
  });

  it('shows no data message for empty data', () => {
    render(
      <AreaChartView
        data={[]}
        xColumn="month"
        yColumns={['sales']}
      />
    );
    expect(screen.getByText(/No data available/)).toBeInTheDocument();
  });

  it('renders area chart', () => {
    render(
      <AreaChartView
        data={mockTimeSeriesData}
        xColumn="month"
        yColumns={['sales']}
      />
    );
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
  });

  it('supports multiple y columns', () => {
    render(
      <AreaChartView
        data={mockTimeSeriesData}
        xColumn="month"
        yColumns={['sales', 'profit']}
      />
    );
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
  });
});

// =============================================================================
// BUBBLE CHART VIEW TESTS
// =============================================================================

describe('BubbleChartView', () => {
  const mockBubbleData = [
    { x: 10, y: 20, size: 100, name: 'A' },
    { x: 20, y: 30, size: 200, name: 'B' },
    { x: 30, y: 40, size: 150, name: 'C' },
    { x: 40, y: 50, size: 300, name: 'D' },
    { x: 50, y: 60, size: 250, name: 'E' },
  ];

  it('renders without crashing', () => {
    render(
      <BubbleChartView
        data={mockBubbleData}
        xColumn="x"
        yColumn="y"
        zColumn="size"
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('displays title when provided', () => {
    render(
      <BubbleChartView
        data={mockBubbleData}
        xColumn="x"
        yColumn="y"
        zColumn="size"
        title="Sales by Region"
      />
    );
    expect(screen.getByText('Sales by Region')).toBeInTheDocument();
  });

  it('shows no data message for empty data', () => {
    render(
      <BubbleChartView
        data={[]}
        xColumn="x"
        yColumn="y"
        zColumn="size"
      />
    );
    expect(screen.getByText(/No numeric data available for bubble chart/)).toBeInTheDocument();
  });

  it('shows bubble size legend', () => {
    render(
      <BubbleChartView
        data={mockBubbleData}
        xColumn="x"
        yColumn="y"
        zColumn="size"
      />
    );
    expect(screen.getByText(/Bubble size represents size/)).toBeInTheDocument();
  });

  it('renders scatter chart for bubbles', () => {
    render(
      <BubbleChartView
        data={mockBubbleData}
        xColumn="x"
        yColumn="y"
        zColumn="size"
      />
    );
    expect(screen.getByTestId('scatter')).toBeInTheDocument();
  });

  it('handles data with name column', () => {
    render(
      <BubbleChartView
        data={mockBubbleData}
        xColumn="x"
        yColumn="y"
        zColumn="size"
        nameColumn="name"
      />
    );
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('shows truncation message for large datasets', () => {
    const largeData = Array.from({ length: 150 }, (_, i) => ({
      x: i,
      y: i * 2,
      size: i * 10,
    }));
    render(
      <BubbleChartView
        data={largeData}
        xColumn="x"
        yColumn="y"
        zColumn="size"
      />
    );
    expect(screen.getByText(/Showing first 100 of 150 points/)).toBeInTheDocument();
  });
});

// =============================================================================
// HIERARCHICAL CHART UTILS TESTS
// =============================================================================

describe('hierarchicalChartUtils', () => {
  describe('prepareTreemapData', () => {
    it('creates hierarchical structure from flat data', () => {
      const data = [
        { category: 'A', value: 100 },
        { category: 'B', value: 200 },
      ];
      const result = prepareTreemapData(data, ['category'], 'value');
      expect(result.name).toBe('root');
      expect(result.children).toHaveLength(2);
    });

    it('handles nested categories', () => {
      const data = [
        { cat1: 'A', cat2: 'X', value: 100 },
        { cat1: 'A', cat2: 'Y', value: 200 },
        { cat1: 'B', cat2: 'X', value: 150 },
      ];
      const result = prepareTreemapData(data, ['cat1', 'cat2'], 'value');
      expect(result.children).toHaveLength(2);
      expect(result.children![0].children).toHaveLength(2);
    });

    it('aggregates values correctly', () => {
      const data = [
        { category: 'A', value: 100 },
        { category: 'A', value: 200 },
      ];
      const result = prepareTreemapData(data, ['category'], 'value');
      expect(result.children![0].value).toBe(300);
    });

    it('handles empty data', () => {
      const result = prepareTreemapData([], ['category'], 'value');
      expect(result.children).toEqual([]);
    });
  });

  describe('prepareSunburstData', () => {
    it('adds depth information to nodes', () => {
      const data = [
        { cat1: 'A', cat2: 'X', value: 100 },
      ];
      const result = prepareSunburstData(data, ['cat1', 'cat2'], 'value');
      expect(result.depth).toBe(0);
      expect(result.children![0].depth).toBe(1);
    });
  });

  describe('prepareSankeyData', () => {
    it('creates nodes and links', () => {
      const data = [
        { source: 'A', target: 'B', value: 100 },
        { source: 'B', target: 'C', value: 80 },
      ];
      const result = prepareSankeyData(data, 'source', 'target', 'value');
      expect(result.nodes.length).toBeGreaterThan(0);
      expect(result.links.length).toBe(2);
    });

    it('aggregates duplicate links', () => {
      const data = [
        { source: 'A', target: 'B', value: 50 },
        { source: 'A', target: 'B', value: 50 },
      ];
      const result = prepareSankeyData(data, 'source', 'target', 'value');
      expect(result.links).toHaveLength(1);
      expect(result.links[0].value).toBe(100);
    });
  });

  describe('assignColors', () => {
    it('assigns colors to nodes', () => {
      const node = { name: 'root', children: [{ name: 'A' }, { name: 'B' }] };
      const result = assignColors(node);
      expect(result.children![0].color).toBe(HIERARCHICAL_COLORS[0]);
      expect(result.children![1].color).toBe(HIERARCHICAL_COLORS[1]);
    });
  });

  describe('isHierarchicalData', () => {
    it('returns true for hierarchical data', () => {
      const data = [
        { cat1: 'A', cat2: 'X', value: 100 },
        { cat1: 'A', cat2: 'Y', value: 200 },
        { cat1: 'B', cat2: 'Z', value: 150 },
      ];
      expect(isHierarchicalData(data, ['cat1', 'cat2'])).toBe(true);
    });

    it('returns false for flat data', () => {
      const data = [{ cat1: 'A', value: 100 }];
      expect(isHierarchicalData(data, ['cat1'])).toBe(false);
    });
  });
});

// =============================================================================
// STATISTICAL CHART UTILS TESTS
// =============================================================================

describe('statisticalChartUtils', () => {
  describe('calculateBoxPlot', () => {
    it('calculates quartiles correctly', () => {
      const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
      const result = calculateBoxPlot(values, 'Test');
      expect(result.min).toBe(1);
      expect(result.max).toBe(10);
      expect(result.median).toBe(5.5);
      // Q1 and Q3 can vary by interpolation method (exclusive vs inclusive)
      expect(result.q1).toBeGreaterThanOrEqual(2.5);
      expect(result.q1).toBeLessThanOrEqual(3.5);
      expect(result.q3).toBeGreaterThanOrEqual(7.5);
      expect(result.q3).toBeLessThanOrEqual(8.5);
    });

    it('identifies outliers', () => {
      const values = [1, 2, 3, 4, 5, 50]; // 50 is an outlier
      const result = calculateBoxPlot(values, 'Test');
      expect(result.outliers).toContain(50);
    });

    it('handles empty array', () => {
      const result = calculateBoxPlot([], 'Test');
      expect(result.min).toBe(0);
      expect(result.max).toBe(0);
      expect(result.median).toBe(0);
    });

    it('calculates mean and standard deviation', () => {
      const values = [10, 20, 30];
      const result = calculateBoxPlot(values, 'Test');
      expect(result.mean).toBe(20);
      expect(result.stdDev).toBeCloseTo(8.165, 2);
    });
  });

  describe('prepareBoxPlotData', () => {
    it('groups data by category', () => {
      const data = [
        { category: 'A', value: 10 },
        { category: 'A', value: 20 },
        { category: 'B', value: 15 },
        { category: 'B', value: 25 },
      ];
      const result = prepareBoxPlotData(data, 'category', 'value');
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('A');
      expect(result[1].name).toBe('B');
    });
  });

  describe('prepareHistogramData', () => {
    it('creates bins from numeric data', () => {
      const data = [
        { value: 10 },
        { value: 20 },
        { value: 30 },
        { value: 40 },
        { value: 50 },
      ];
      const result = prepareHistogramData(data, 'value', 5);
      expect(result.length).toBeLessThanOrEqual(5);
      expect(result[0]).toHaveProperty('count');
      expect(result[0]).toHaveProperty('x0');
      expect(result[0]).toHaveProperty('x1');
    });

    it('calculates frequencies', () => {
      const data = [
        { value: 10 },
        { value: 10 },
        { value: 20 },
      ];
      const result = prepareHistogramData(data, 'value', 2);
      const totalCount = result.reduce((sum, bin) => sum + bin.count, 0);
      expect(totalCount).toBe(3);
    });
  });

  describe('prepareBubbleData', () => {
    it('creates bubble points from data', () => {
      const data = [
        { x: 1, y: 2, z: 3, name: 'A' },
        { x: 4, y: 5, z: 6, name: 'B' },
      ];
      const result = prepareBubbleData(data, 'x', 'y', 'z', 'name');
      expect(result).toHaveLength(2);
      expect(result[0].x).toBe(1);
      expect(result[0].y).toBe(2);
      expect(result[0].z).toBe(3);
      expect(result[0].name).toBe('A');
    });

    it('filters invalid values', () => {
      const data = [
        { x: 1, y: 2, z: 3 },
        { x: 'invalid', y: 2, z: 3 },
      ];
      const result = prepareBubbleData(data, 'x', 'y', 'z');
      expect(result).toHaveLength(1);
    });

    it('makes z values absolute', () => {
      const data = [{ x: 1, y: 2, z: -5 }];
      const result = prepareBubbleData(data, 'x', 'y', 'z');
      expect(result[0].z).toBe(5);
    });
  });

  describe('calculateSummaryStats', () => {
    it('calculates basic statistics', () => {
      const values = [1, 2, 3, 4, 5];
      const result = calculateSummaryStats(values);
      expect(result.count).toBe(5);
      expect(result.mean).toBe(3);
      expect(result.median).toBe(3);
      expect(result.min).toBe(1);
      expect(result.max).toBe(5);
    });

    it('handles single value', () => {
      const result = calculateSummaryStats([42]);
      expect(result.count).toBe(1);
      expect(result.mean).toBe(42);
      expect(result.median).toBe(42);
      expect(result.stdDev).toBe(0);
    });

    it('handles empty array', () => {
      const result = calculateSummaryStats([]);
      expect(result.count).toBe(0);
      expect(result.mean).toBe(0);
    });
  });
});

// =============================================================================
// CHART TOGGLE WITH ADVANCED CHART TYPES
// =============================================================================

describe('ChartToggle with Advanced Chart Types', () => {
  const mockOnModeChange = vi.fn();

  it('shows treemap label', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="treemap"
      />
    );
    expect(screen.getByTitle('View as Treemap')).toBeInTheDocument();
  });

  it('shows histogram label', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="histogram"
      />
    );
    expect(screen.getByTitle('View as Histogram')).toBeInTheDocument();
  });

  it('shows boxplot label', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="boxplot"
      />
    );
    expect(screen.getByTitle('View as Box Plot')).toBeInTheDocument();
  });

  it('shows area chart label', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="area"
      />
    );
    expect(screen.getByTitle('View as Area Chart')).toBeInTheDocument();
  });

  it('shows sunburst label', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="sunburst"
      />
    );
    expect(screen.getByTitle('View as Sunburst')).toBeInTheDocument();
  });

  it('shows bubble chart label', () => {
    render(
      <ChartToggle
        mode="chart"
        onModeChange={mockOnModeChange}
        chartAvailable={true}
        chartType="bubble"
      />
    );
    expect(screen.getByTitle('View as Bubble Chart')).toBeInTheDocument();
  });
});
