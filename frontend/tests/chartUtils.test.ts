/**
 * Chart Utilities Tests
 *
 * Tests for chart detection and data preparation utilities
 */

import { describe, it, expect } from 'vitest';
import {
  detectChartType,
  classifyColumns,
  prepareChartData,
  ChartRecommendation,
  CHART_COLORS,
  PIE_PALETTE,
} from '../src/utils/chartUtils';

describe('classifyColumns', () => {
  it('classifies numeric columns correctly', () => {
    const results = [
      { name: 'Alice', age: 30, salary: 50000 },
      { name: 'Bob', age: 25, salary: 45000 },
    ];
    const classification = classifyColumns(results, {});

    expect(classification.numericColumns).toContain('age');
    expect(classification.numericColumns).toContain('salary');
  });

  it('classifies categorical columns correctly', () => {
    const results = [
      { name: 'Alice', department: 'Engineering' },
      { name: 'Bob', department: 'Marketing' },
    ];
    const classification = classifyColumns(results, {});

    expect(classification.categoricalColumns).toContain('name');
    expect(classification.categoricalColumns).toContain('department');
  });

  it('classifies temporal columns by name pattern', () => {
    const results = [
      { created_at: '2024-01-01', updated_on: '2024-01-02', value: 100 },
    ];
    const classification = classifyColumns(results, {});

    expect(classification.temporalColumns).toContain('created_at');
    expect(classification.temporalColumns).toContain('updated_on');
  });

  it('classifies ID columns correctly', () => {
    const results = [
      { id: 1, user_id: 100, name: 'Test' },
    ];
    const classification = classifyColumns(results, {});

    expect(classification.idColumns).toContain('id');
    expect(classification.idColumns).toContain('user_id');
    expect(classification.categoricalColumns).toContain('name');
  });

  it('returns empty arrays for empty results', () => {
    const classification = classifyColumns([], {});

    expect(classification.numericColumns).toHaveLength(0);
    expect(classification.categoricalColumns).toHaveLength(0);
    expect(classification.temporalColumns).toHaveLength(0);
    expect(classification.idColumns).toHaveLength(0);
  });

  it('uses statistics type info when available', () => {
    const results = [
      { value: '100', category: 'A' },
    ];
    const statistics = {
      value: { type: 'numeric' },
      category: { type: 'string' },
    };
    const classification = classifyColumns(results, statistics);

    expect(classification.numericColumns).toContain('value');
    expect(classification.categoricalColumns).toContain('category');
  });

  it('classifies numeric strings as numeric', () => {
    const results = [
      { amount: '1234.56', name: 'Test' },
    ];
    const classification = classifyColumns(results, {});

    expect(classification.numericColumns).toContain('amount');
  });

  it('detects date values in string columns', () => {
    const results = [
      { event_date: '2024-01-15', value: 100 },
    ];
    const classification = classifyColumns(results, {});

    expect(classification.temporalColumns).toContain('event_date');
  });
});

describe('detectChartType', () => {
  it('returns table for insufficient data', () => {
    const results = [{ value: 1 }]; // Only 1 row
    const recommendation = detectChartType(results, {});

    expect(recommendation.chartType).toBe('table');
    expect(recommendation.reason).toContain('Insufficient data');
  });

  it('returns table for empty data', () => {
    const recommendation = detectChartType([], {});

    expect(recommendation.chartType).toBe('table');
  });

  it('recommends line chart for temporal + numeric data', () => {
    const results = [
      { date: '2024-01-01', sales: 100 },
      { date: '2024-01-02', sales: 150 },
      { date: '2024-01-03', sales: 120 },
    ];
    const recommendation = detectChartType(results, {});

    expect(recommendation.chartType).toBe('line');
    expect(recommendation.xColumn).toBe('date');
    expect(recommendation.yColumn).toBe('sales');
  });

  it('recommends line chart when trends are detected', () => {
    const results = [
      { month: 'Jan', revenue: 100 },
      { month: 'Feb', revenue: 150 },
    ];
    const statistics = {
      trends: {
        found: true,
        detected_trends: [
          { column: 'revenue', temporal_column: 'month' },
        ],
      },
    };
    const recommendation = detectChartType(results, statistics);

    expect(recommendation.chartType).toBe('line');
    expect(recommendation.confidence).toBeGreaterThanOrEqual(0.9);
  });

  it('recommends scatter plot when correlations are detected', () => {
    const results = [
      { price: 10, quantity: 100 },
      { price: 20, quantity: 80 },
      { price: 30, quantity: 60 },
    ];
    const statistics = {
      correlations: {
        found: true,
        significant_correlations: [
          { column1: 'price', column2: 'quantity', correlation: -0.95 },
        ],
      },
    };
    const recommendation = detectChartType(results, statistics);

    expect(recommendation.chartType).toBe('scatter');
    expect(recommendation.xColumn).toBe('price');
    expect(recommendation.yColumn).toBe('quantity');
  });

  it('recommends pie chart for few categories', () => {
    const results = [
      { region: 'North', sales: 100 },
      { region: 'South', sales: 150 },
      { region: 'East', sales: 120 },
      { region: 'West', sales: 80 },
    ];
    const recommendation = detectChartType(results, {});

    expect(recommendation.chartType).toBe('pie');
    expect(recommendation.xColumn).toBe('region');
    expect(recommendation.yColumn).toBe('sales');
  });

  it('recommends bar chart for moderate categories', () => {
    const results = Array.from({ length: 12 }, (_, i) => ({
      category: `Category ${i + 1}`,
      value: Math.random() * 100,
    }));
    const recommendation = detectChartType(results, {});

    expect(recommendation.chartType).toBe('bar');
  });

  it('returns table for too many categories', () => {
    const results = Array.from({ length: 50 }, (_, i) => ({
      category: `Category ${i + 1}`,
      value: Math.random() * 100,
    }));
    const recommendation = detectChartType(results, {});

    expect(recommendation.chartType).toBe('table');
  });

  it('includes confidence score in recommendation', () => {
    const results = [
      { date: '2024-01-01', value: 100 },
      { date: '2024-01-02', value: 150 },
    ];
    const recommendation = detectChartType(results, {});

    expect(recommendation.confidence).toBeGreaterThan(0);
    expect(recommendation.confidence).toBeLessThanOrEqual(1);
  });

  it('includes reason in recommendation', () => {
    const results = [
      { category: 'A', value: 100 },
      { category: 'B', value: 150 },
    ];
    const recommendation = detectChartType(results, {});

    expect(recommendation.reason).toBeTruthy();
    expect(typeof recommendation.reason).toBe('string');
  });
});

describe('prepareChartData', () => {
  it('prepares data for bar chart', () => {
    const results = [
      { name: 'A', value: 100 },
      { name: 'B', value: 200 },
    ];
    const prepared = prepareChartData(results, 'name', 'value', 'bar');

    expect(prepared).toHaveLength(2);
    expect(prepared[0].name).toBe('A');
    expect(prepared[0].value).toBe(100);
  });

  it('aggregates data for pie chart', () => {
    const results = [
      { region: 'North', sales: 100 },
      { region: 'North', sales: 50 },
      { region: 'South', sales: 200 },
    ];
    const prepared = prepareChartData(results, 'region', 'sales', 'pie');

    expect(prepared).toHaveLength(2);
    const north = prepared.find((d) => d.name === 'North');
    const south = prepared.find((d) => d.name === 'South');
    expect(north?.value).toBe(150); // 100 + 50
    expect(south?.value).toBe(200);
  });

  it('limits data to maxItems', () => {
    const results = Array.from({ length: 100 }, (_, i) => ({
      id: i,
      value: i * 10,
    }));
    const prepared = prepareChartData(results, 'id', 'value', 'bar', 50);

    expect(prepared).toHaveLength(50);
  });

  it('handles null values', () => {
    const results = [
      { name: 'A', value: 100 },
      { name: null, value: 200 },
    ];
    const prepared = prepareChartData(results, 'name', 'value', 'pie');

    const unknown = prepared.find((d) => d.name === 'Unknown');
    expect(unknown).toBeDefined();
  });

  it('handles non-numeric values as zero', () => {
    const results = [
      { name: 'A', value: 'not a number' },
    ];
    const prepared = prepareChartData(results, 'name', 'value', 'bar');

    expect(prepared[0].value).toBe(0);
  });
});

describe('Chart Colors', () => {
  it('exports CHART_COLORS constant', () => {
    expect(CHART_COLORS).toBeDefined();
    expect(CHART_COLORS.primary).toBe('#3b82f6');
    expect(CHART_COLORS.secondary).toBe('#8b5cf6');
    expect(CHART_COLORS.success).toBe('#10b981');
  });

  it('exports PIE_PALETTE array', () => {
    expect(PIE_PALETTE).toBeDefined();
    expect(Array.isArray(PIE_PALETTE)).toBe(true);
    expect(PIE_PALETTE.length).toBeGreaterThan(0);
  });

  it('PIE_PALETTE contains valid hex colors', () => {
    const hexPattern = /^#[0-9a-f]{6}$/i;
    PIE_PALETTE.forEach((color) => {
      expect(color).toMatch(hexPattern);
    });
  });
});
