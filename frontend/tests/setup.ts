import '@testing-library/jest-dom';
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import React from 'react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Make vi globally available as jest
global.jest = vi;

// Mock URL.createObjectURL and revokeObjectURL for export tests
global.URL.createObjectURL = vi.fn(() => 'mock-object-url');
global.URL.revokeObjectURL = vi.fn();

// Mock Recharts components to render simple SVG elements for testing
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children, ...props }: any) =>
    React.createElement('div', { 'data-testid': 'responsive-container', ...props }, children),
  LineChart: ({ children, data, ...props }: any) =>
    React.createElement('svg', { 'data-testid': 'line-chart', 'data-chart-type': 'line', ...props }, children),
  BarChart: ({ children, data, ...props }: any) =>
    React.createElement('svg', { 'data-testid': 'bar-chart', 'data-chart-type': 'bar', ...props }, children),
  PieChart: ({ children, data, ...props }: any) =>
    React.createElement('svg', { 'data-testid': 'pie-chart', 'data-chart-type': 'pie', ...props }, children),
  AreaChart: ({ children, data, ...props }: any) =>
    React.createElement('svg', { 'data-testid': 'area-chart', 'data-chart-type': 'area', ...props }, children),
  Line: (props: any) => React.createElement('path', { 'data-testid': 'chart-line', ...props }),
  Bar: (props: any) => React.createElement('rect', { 'data-testid': 'chart-bar', ...props }),
  Pie: (props: any) => React.createElement('path', { 'data-testid': 'chart-pie', ...props }),
  Area: (props: any) => React.createElement('path', { 'data-testid': 'chart-area', ...props }),
  XAxis: (props: any) => React.createElement('g', { 'data-testid': 'x-axis', ...props }),
  YAxis: (props: any) => React.createElement('g', { 'data-testid': 'y-axis', ...props }),
  CartesianGrid: (props: any) => React.createElement('g', { 'data-testid': 'cartesian-grid', ...props }),
  Tooltip: (props: any) => React.createElement('div', { 'data-testid': 'chart-tooltip', ...props }),
  Legend: (props: any) => React.createElement('div', { 'data-testid': 'chart-legend', ...props }),
  Cell: (props: any) => React.createElement('path', { 'data-testid': 'chart-cell', ...props }),
}));
