/**
 * Tests for Chart Auto-Detection Service
 */

import { describe, it, expect } from 'vitest';
import { detectChartType, ChartType } from '../src/services/chartDetector';

describe('chartDetector', () => {
  describe('Time-series detection (Line charts)', () => {
    it('should detect line chart for time-series data with single value column', () => {
      const data = [
        { date: '2024-01-01', revenue: 1000 },
        { date: '2024-01-02', revenue: 1200 },
        { date: '2024-01-03', revenue: 1100 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('line');
      expect(result.confidence).toBeGreaterThanOrEqual(0.85);
      expect(result.timeColumn).toBe('date');
      expect(result.valueColumns).toEqual(['revenue']);
      expect(result.reason).toContain('time column');
    });

    it('should detect line chart for time-series with multiple value columns', () => {
      const data = [
        { timestamp: '2024-01-01T00:00:00', sales: 100, orders: 50 },
        { timestamp: '2024-01-02T00:00:00', sales: 120, orders: 55 },
        { timestamp: '2024-01-03T00:00:00', sales: 110, orders: 52 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('line');
      expect(result.confidence).toBeGreaterThanOrEqual(0.85);
      expect(result.timeColumn).toBe('timestamp');
      expect(result.valueColumns).toContain('sales');
      expect(result.valueColumns).toContain('orders');
    });

    it('should have higher confidence for ordered time-series data', () => {
      const orderedData = [
        { created_at: '2024-01-01', count: 10 },
        { created_at: '2024-01-02', count: 20 },
        { created_at: '2024-01-03', count: 30 },
      ];

      const unorderedData = [
        { created_at: '2024-01-03', count: 30 },
        { created_at: '2024-01-01', count: 10 },
        { created_at: '2024-01-02', count: 20 },
      ];

      const orderedResult = detectChartType(orderedData);
      const unorderedResult = detectChartType(unorderedData);

      expect(orderedResult.confidence).toBeGreaterThan(unorderedResult.confidence);
      expect(orderedResult.confidence).toBeCloseTo(0.95);
      expect(unorderedResult.confidence).toBeCloseTo(0.85);
    });

    it('should detect various date formats', () => {
      const formats = [
        [{ date: '2024-01-01', val: 1 }, { date: '2024-01-02', val: 2 }], // ISO
        [{ date: '01/01/2024', val: 1 }, { date: '01/02/2024', val: 2 }], // MM/DD/YYYY
        [{ date: '2024/01/01', val: 1 }, { date: '2024/01/02', val: 2 }], // YYYY/MM/DD
      ];

      formats.forEach(data => {
        const result = detectChartType(data);
        expect(result.type).toBe('line');
      });
    });

    it('should not detect line chart if too many value columns (>5)', () => {
      const data = [
        { date: '2024-01-01', v1: 1, v2: 2, v3: 3, v4: 4, v5: 5, v6: 6 },
        { date: '2024-01-02', v1: 2, v2: 3, v3: 4, v4: 5, v5: 6, v6: 7 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('table');
    });
  });

  describe('Pie chart detection', () => {
    it('should detect pie chart for small categorical data (≤12 categories)', () => {
      const data = [
        { category: 'Electronics', sales: 1000 },
        { category: 'Books', sales: 800 },
        { category: 'Clothing', sales: 1200 },
        { category: 'Food', sales: 600 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('pie');
      expect(result.confidence).toBeCloseTo(0.85);
      expect(result.categoryColumn).toBe('category');
      expect(result.valueColumns).toEqual(['sales']);
    });

    it('should not detect pie chart if >12 categories', () => {
      const data = Array.from({ length: 15 }, (_, i) => ({
        category: `Category ${i + 1}`,
        value: Math.random() * 100,
      }));

      const result = detectChartType(data);

      expect(result.type).not.toBe('pie');
    });

    it('should not detect pie chart if >20 rows', () => {
      const data = Array.from({ length: 25 }, (_, i) => ({
        category: `Cat ${i % 5}`, // Only 5 categories but 25 rows
        value: 100,
      }));

      const result = detectChartType(data);

      expect(result.type).not.toBe('pie');
    });

    it('should require exactly 1 categorical and 1 numeric column for pie', () => {
      const twoNumeric = [
        { category: 'A', val1: 10, val2: 20 },
        { category: 'B', val1: 30, val2: 40 },
      ];

      const twoCategorical = [
        { cat1: 'A', cat2: 'X', value: 10 },
        { cat1: 'B', cat2: 'Y', value: 20 },
      ];

      expect(detectChartType(twoNumeric).type).not.toBe('pie');
      expect(detectChartType(twoCategorical).type).not.toBe('pie');
    });
  });

  describe('Bar chart detection', () => {
    it('should detect bar chart for categorical data with numeric values', () => {
      const data = [
        { product: 'Laptop', units_sold: 50 },
        { product: 'Phone', units_sold: 120 },
        { product: 'Tablet', units_sold: 80 },
        { product: 'Monitor', units_sold: 45 },
        { product: 'Keyboard', units_sold: 95 },
        { product: 'Mouse', units_sold: 110 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('bar');
      expect(result.confidence).toBeCloseTo(0.80);
      expect(result.categoryColumn).toBe('product');
      expect(result.valueColumns).toEqual(['units_sold']);
    });

    it('should detect bar chart with multiple value columns (2-3)', () => {
      const data = [
        { region: 'North', sales: 1000, profit: 200 },
        { region: 'South', sales: 1200, profit: 250 },
        { region: 'East', sales: 900, profit: 180 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('bar');
      expect(result.valueColumns).toHaveLength(2);
      expect(result.valueColumns).toContain('sales');
      expect(result.valueColumns).toContain('profit');
    });

    it('should work for data within 2-50 rows', () => {
      const minData = [
        { cat: 'A', val: 10 },
        { cat: 'B', val: 20 },
      ];

      const maxData = Array.from({ length: 50 }, (_, i) => ({
        cat: `Category ${i}`,
        val: Math.random() * 100,
      }));

      expect(detectChartType(minData).type).toBe('bar');
      expect(detectChartType(maxData).type).toBe('bar');
    });

    it('should not detect bar chart if >50 rows', () => {
      const data = Array.from({ length: 55 }, (_, i) => ({
        category: `Cat ${i}`,
        value: 100,
      }));

      const result = detectChartType(data);

      expect(result.type).toBe('table');
      expect(result.reason).toContain('Large dataset');
    });

    it('should not detect bar chart if >3 value columns', () => {
      const data = [
        { cat: 'A', v1: 1, v2: 2, v3: 3, v4: 4 },
        { cat: 'B', v1: 5, v2: 6, v3: 7, v4: 8 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('table');
    });
  });

  describe('Table fallback', () => {
    it('should fallback to table for empty data', () => {
      const result = detectChartType([]);

      expect(result.type).toBe('table');
      expect(result.confidence).toBe(1.0);
      expect(result.reason).toBe('No data to visualize');
    });

    it('should fallback to table for large datasets (>50 rows)', () => {
      const data = Array.from({ length: 100 }, (_, i) => ({
        id: i,
        value: Math.random(),
      }));

      const result = detectChartType(data);

      expect(result.type).toBe('table');
      expect(result.reason).toContain('Large dataset');
    });

    it('should fallback to table for many columns (>10)', () => {
      const data = [
        {
          c1: 1, c2: 2, c3: 3, c4: 4, c5: 5,
          c6: 6, c7: 7, c8: 8, c9: 9, c10: 10,
          c11: 11, c12: 12,
        },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('table');
      expect(result.reason).toContain('Many columns');
    });

    it('should fallback to table if no numeric columns', () => {
      const data = [
        { name: 'Alice', city: 'NYC', country: 'USA' },
        { name: 'Bob', city: 'LA', country: 'USA' },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('table');
      expect(result.reason).toContain('No numeric columns');
    });

    it('should have low confidence (0.5) for table fallback', () => {
      const data = [
        { col1: 'text', col2: 'more text' },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('table');
      expect(result.confidence).toBe(0.5);
    });
  });

  describe('Edge cases', () => {
    it('should handle null values gracefully', () => {
      const data = [
        { date: '2024-01-01', value: 100 },
        { date: null, value: null },
        { date: '2024-01-03', value: 120 },
      ];

      const result = detectChartType(data);

      expect(result.type).toBe('line');
    });

    it('should handle undefined values', () => {
      const data = [
        { category: 'A', value: 10 },
        { category: undefined, value: undefined },
        { category: 'B', value: 20 },
      ];

      const result = detectChartType(data);

      // Should still detect a chart type
      expect(['line', 'bar', 'pie', 'table']).toContain(result.type);
    });

    it('should handle mixed data types in same column', () => {
      const data = [
        { id: 1, value: 100 },
        { id: '2', value: '200' }, // Mixed types
        { id: 3, value: 300 },
      ];

      const result = detectChartType(data);

      // Should not crash
      expect(result).toBeDefined();
      expect(result.type).toBeDefined();
    });

    it('should handle single row dataset', () => {
      const data = [{ category: 'A', value: 100 }];

      const result = detectChartType(data);

      // Should fallback to table (not enough data for meaningful chart)
      expect(result.type).toBe('table');
    });

    it('should handle boolean columns correctly', () => {
      const data = [
        { is_active: true, count: 10 },
        { is_active: false, count: 5 },
      ];

      const result = detectChartType(data);

      // Boolean is not treated as string/number, should fallback
      expect(result).toBeDefined();
    });
  });

  describe('Confidence scoring', () => {
    it('should return confidence between 0.0 and 1.0', () => {
      const testCases = [
        [{ date: '2024-01-01', val: 1 }], // line
        [{ cat: 'A', val: 1 }], // bar/pie
        [], // empty
      ];

      testCases.forEach(data => {
        const result = detectChartType(data);
        expect(result.confidence).toBeGreaterThanOrEqual(0.0);
        expect(result.confidence).toBeLessThanOrEqual(1.0);
      });
    });

    it('should prioritize line chart over bar chart for time data', () => {
      const timeData = [
        { created_at: '2024-01-01', category: 'A', value: 10 },
        { created_at: '2024-01-02', category: 'B', value: 20 },
      ];

      const result = detectChartType(timeData);

      // Time-series should take priority
      expect(result.type).toBe('line');
      expect(result.timeColumn).toBe('created_at');
    });
  });
});
