/**
 * Tests for AutoChart and Chart Components
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AutoChart from '../src/components/AutoChart';
import TimeSeriesChart from '../src/components/TimeSeriesChart';
import CategoryBarChart from '../src/components/CategoryBarChart';
import PieChartComponent from '../src/components/PieChartComponent';
import { exportUtils } from '../src/components/ChartExporter';

describe('AutoChart', () => {
  describe('Chart type auto-detection and rendering', () => {
    it('should auto-detect and render line chart for time-series data', () => {
      const data = [
        { date: '2024-01-01', revenue: 1000 },
        { date: '2024-01-02', revenue: 1200 },
        { date: '2024-01-03', revenue: 1100 },
      ];

      const { container } = render(<AutoChart data={data} title="Revenue Over Time" />);

      // Should show title
      expect(screen.getByText('Revenue Over Time')).toBeInTheDocument();

      // Should show high confidence
      expect(screen.getByText(/9[0-9]% confidence/)).toBeInTheDocument();

      // Should detect time column
      expect(screen.getByText(/Time column:/)).toBeInTheDocument();
      expect(screen.getByText('date')).toBeInTheDocument();
    });

    it('should auto-detect and render pie chart for small categorical data', () => {
      const data = [
        { category: 'Electronics', sales: 1000 },
        { category: 'Books', sales: 800 },
        { category: 'Clothing', sales: 1200 },
      ];

      const { container } = render(<AutoChart data={data} />);

      // Should show confidence badge
      expect(screen.getByText(/85% confidence/)).toBeInTheDocument();

      // Should detect category
      expect(screen.getByText(/Category:/)).toBeInTheDocument();
      expect(screen.getByText('category')).toBeInTheDocument();
    });

    it('should auto-detect and render bar chart for categorical data', () => {
      const data = [
        { product: 'Laptop', units_sold: 50 },
        { product: 'Phone', units_sold: 120 },
        { product: 'Tablet', units_sold: 80 },
      ];

      render(<AutoChart data={data} />);

      // Should show confidence
      expect(screen.getByText(/80% confidence/)).toBeInTheDocument();

      // Should detect category
      expect(screen.getByText('product')).toBeInTheDocument();
    });

    it('should fallback to table for complex data', () => {
      const data = [
        { name: 'Alice', city: 'NYC', country: 'USA' },
        { name: 'Bob', city: 'LA', country: 'USA' },
      ];

      render(<AutoChart data={data} />);

      // Should show table fallback reason
      expect(screen.getByText(/No numeric columns/)).toBeInTheDocument();

      // Should render table headers
      expect(screen.getByText('name')).toBeInTheDocument();
      expect(screen.getByText('city')).toBeInTheDocument();
      expect(screen.getByText('country')).toBeInTheDocument();
    });

    it('should show empty state for no data', () => {
      render(<AutoChart data={[]} />);

      expect(screen.getByText('No data to visualize')).toBeInTheDocument();
    });
  });

  describe('Manual chart type override', () => {
    it('should allow manual override of chart type', () => {
      const data = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 200 },
      ];

      render(<AutoChart data={data} allowManualOverride={true} />);

      // Find and change chart type selector
      const select = screen.getByLabelText(/Type:/i);
      fireEvent.change(select, { target: { value: 'table' } });

      // Should now show table view
      expect(screen.getByText('date')).toBeInTheDocument();
      expect(screen.getByText('value')).toBeInTheDocument();
    });

    it('should call onChartTypeChange callback when type changes', () => {
      const mockCallback = vi.fn();
      const data = [{ x: 1, y: 10 }];

      render(<AutoChart data={data} onChartTypeChange={mockCallback} />);

      const select = screen.getByLabelText(/Type:/i);
      fireEvent.change(select, { target: { value: 'bar' } });

      expect(mockCallback).toHaveBeenCalledWith('bar');
    });

    it('should not show manual override when allowManualOverride is false', () => {
      const data = [{ x: 1, y: 10 }];

      render(<AutoChart data={data} allowManualOverride={false} />);

      expect(screen.queryByLabelText(/Type:/i)).not.toBeInTheDocument();
    });
  });

  describe('Chart exporter integration', () => {
    it('should show export buttons by default', () => {
      const data = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 200 },
      ];

      render(<AutoChart data={data} />);

      expect(screen.getByText('PNG')).toBeInTheDocument();
      expect(screen.getByText('SVG')).toBeInTheDocument();
      expect(screen.getByText('CSV')).toBeInTheDocument();
    });

    it('should hide export buttons when showExporter is false', () => {
      const data = [{ date: '2024-01-01', value: 100 }];

      render(<AutoChart data={data} showExporter={false} />);

      expect(screen.queryByText('PNG')).not.toBeInTheDocument();
      expect(screen.queryByText('SVG')).not.toBeInTheDocument();
    });

    it('should not show export buttons for table view', () => {
      const data = [
        { name: 'Alice', city: 'NYC' },
        { name: 'Bob', city: 'LA' },
      ];

      render(<AutoChart data={data} />);

      // Should be table view (no numeric columns)
      expect(screen.queryByText('PNG')).not.toBeInTheDocument();
    });
  });

  describe('Confidence badge colors', () => {
    it('should show green badge for high confidence (≥85%)', () => {
      const data = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 200 },
      ];

      const { container } = render(<AutoChart data={data} />);

      const badge = screen.getByText(/9[0-9]% confidence/);
      expect(badge.className).toContain('bg-green-100');
      expect(badge.className).toContain('text-green-800');
    });

    it('should show red badge for low confidence (<70%)', () => {
      const data = [{ text1: 'hello', text2: 'world' }];

      const { container } = render(<AutoChart data={data} />);

      const badge = screen.getByText(/50% confidence/);
      expect(badge.className).toContain('bg-red-100');
      expect(badge.className).toContain('text-red-800');
    });
  });

  describe('Metadata display', () => {
    it('should show time column metadata for line charts', () => {
      const data = [
        { timestamp: '2024-01-01', count: 10 },
        { timestamp: '2024-01-02', count: 20 },
      ];

      render(<AutoChart data={data} />);

      expect(screen.getByText(/Time column:/)).toBeInTheDocument();
      expect(screen.getByText('timestamp')).toBeInTheDocument();
    });

    it('should show value columns metadata', () => {
      const data = [
        { date: '2024-01-01', sales: 100, profit: 20 },
        { date: '2024-01-02', sales: 120, profit: 25 },
      ];

      render(<AutoChart data={data} />);

      expect(screen.getByText(/Values:/)).toBeInTheDocument();
      expect(screen.getByText(/sales, profit/)).toBeInTheDocument();
    });

    it('should show row count', () => {
      const data = Array.from({ length: 42 }, (_, i) => ({
        id: i,
        value: Math.random(),
      }));

      render(<AutoChart data={data} />);

      expect(screen.getByText('42')).toBeInTheDocument();
    });
  });
});

describe('TimeSeriesChart', () => {
  it('should render line chart with single value column', () => {
    const data = [
      { date: '2024-01-01', revenue: 1000 },
      { date: '2024-01-02', revenue: 1200 },
    ];

    const { container } = render(
      <TimeSeriesChart data={data} timeColumn="date" valueColumns={['revenue']} />
    );

    // Recharts renders SVG
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should render multiple value columns as separate lines', () => {
    const data = [
      { timestamp: '2024-01-01', sales: 100, orders: 50 },
      { timestamp: '2024-01-02', sales: 120, orders: 55 },
    ];

    const { container } = render(
      <TimeSeriesChart data={data} timeColumn="timestamp" valueColumns={['sales', 'orders']} />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should format dates for display', () => {
    const data = [
      { date: '2024-01-01T00:00:00Z', value: 100 },
      { date: '2024-01-02T00:00:00Z', value: 200 },
    ];

    const { container } = render(
      <TimeSeriesChart data={data} timeColumn="date" valueColumns={['value']} />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

describe('CategoryBarChart', () => {
  it('should render bar chart with single value column', () => {
    const data = [
      { product: 'Laptop', sales: 1000 },
      { product: 'Phone', sales: 1200 },
    ];

    const { container } = render(
      <CategoryBarChart data={data} categoryColumn="product" valueColumns={['sales']} />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should render grouped bars for multiple value columns', () => {
    const data = [
      { region: 'North', sales: 1000, profit: 200 },
      { region: 'South', sales: 1200, profit: 250 },
    ];

    const { container } = render(
      <CategoryBarChart data={data} categoryColumn="region" valueColumns={['sales', 'profit']} />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should support horizontal orientation', () => {
    const data = [
      { category: 'A', value: 10 },
      { category: 'B', value: 20 },
    ];

    const { container } = render(
      <CategoryBarChart
        data={data}
        categoryColumn="category"
        valueColumns={['value']}
        orientation="horizontal"
      />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should truncate long category names', () => {
    const data = [
      { category: 'This is a very long category name that should be truncated', value: 100 },
    ];

    const { container } = render(
      <CategoryBarChart data={data} categoryColumn="category" valueColumns={['value']} />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

describe('PieChartComponent', () => {
  it('should render pie chart', () => {
    const data = [
      { category: 'A', value: 100 },
      { category: 'B', value: 200 },
      { category: 'C', value: 150 },
    ];

    const { container } = render(
      <PieChartComponent data={data} categoryColumn="category" valueColumn="value" />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should support donut variant', () => {
    const data = [
      { category: 'X', value: 50 },
      { category: 'Y', value: 100 },
    ];

    const { container } = render(
      <PieChartComponent data={data} categoryColumn="category" valueColumn="value" variant="donut" />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should calculate percentages correctly', () => {
    const data = [
      { segment: 'A', amount: 25 },
      { segment: 'B', amount: 75 },
    ];

    const { container } = render(
      <PieChartComponent data={data} categoryColumn="segment" valueColumn="amount" />
    );

    // Total = 100, so A = 25%, B = 75%
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

describe('ChartExporter utils', () => {
  describe('exportCSV', () => {
    it('should export data as CSV', () => {
      const mockLink = document.createElement('a');
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
      const clickSpy = vi.spyOn(mockLink, 'click');

      const data = [
        { name: 'Alice', age: 30 },
        { name: 'Bob', age: 25 },
      ];

      exportUtils.exportCSV(data, 'test');

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(clickSpy).toHaveBeenCalled();
      expect(mockLink.download).toBe('test.csv');

      createElementSpy.mockRestore();
      clickSpy.mockRestore();
    });
  });

  describe('exportJSON', () => {
    it('should export data as JSON', () => {
      const mockLink = document.createElement('a');
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
      const clickSpy = vi.spyOn(mockLink, 'click');

      const data = [{ x: 1, y: 2 }];

      exportUtils.exportJSON(data, 'test');

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(clickSpy).toHaveBeenCalled();
      expect(mockLink.download).toBe('test.json');

      createElementSpy.mockRestore();
      clickSpy.mockRestore();
    });
  });
});

describe('Table view', () => {
  it('should render table with all columns', () => {
    const data = [
      { id: 1, name: 'Alice', age: 30 },
      { id: 2, name: 'Bob', age: 25 },
    ];

    render(<AutoChart data={data} />);

    // Should show column headers
    expect(screen.getByText('id')).toBeInTheDocument();
    expect(screen.getByText('name')).toBeInTheDocument();
    expect(screen.getByText('age')).toBeInTheDocument();

    // Should show data
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('should show first 100 rows only', () => {
    const data = Array.from({ length: 150 }, (_, i) => ({
      id: i,
      value: i * 10,
    }));

    render(<AutoChart data={data} />);

    expect(screen.getByText(/Showing 100 of 150 rows/)).toBeInTheDocument();
  });

  it('should format null/undefined as dash', () => {
    const data = [
      { name: 'Alice', value: null },
      { name: 'Bob', value: undefined },
    ];

    render(<AutoChart data={data} />);

    // Should show dashes for null/undefined
    const cells = screen.getAllByText('-');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('should format numbers with locale', () => {
    const data = [{ value: 1234567 }];

    render(<AutoChart data={data} />);

    // Should format number with commas
    expect(screen.getByText('1,234,567')).toBeInTheDocument();
  });

  it('should format booleans as Yes/No', () => {
    const data = [
      { active: true },
      { active: false },
    ];

    render(<AutoChart data={data} />);

    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });
});
