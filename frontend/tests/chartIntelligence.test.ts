import { describe, it, expect } from 'vitest';
import { analyzeData, detectOutliers } from '../src/utils/chartIntelligence';
import { detectTimeSeriesPattern } from '../src/utils/timeSeriesDetector';
import { detectHierarchy } from '../src/utils/hierarchyDetector';
import { detectGeoData } from '../src/utils/geoDetector';
import { calculateTrendLine, calculateMovingAverage } from '../src/utils/trendLineCalculator';

describe('chartIntelligence', () => {
  describe('analyzeData', () => {
    it('returns table for insufficient data', () => {
      const result = analyzeData([]);
      expect(result.primaryChart).toBe('table');
      expect(result.reason).toContain('Insufficient data');
    });

    it('returns table for single row', () => {
      const result = analyzeData([{ name: 'Test', value: 100 }]);
      expect(result.primaryChart).toBe('table');
    });

    it('recommends line chart for time-series data', () => {
      const data = [
        { date: '2024-01-01', sales: 100 },
        { date: '2024-01-02', sales: 120 },
        { date: '2024-01-03', sales: 140 },
        { date: '2024-01-04', sales: 160 },
        { date: '2024-01-05', sales: 180 },
      ];
      const result = analyzeData(data);
      expect(result.primaryChart).toBe('line');
      expect(result.xColumn).toBe('date');
      expect(result.yColumn).toBe('sales');
    });

    it('recommends pie chart for few categories', () => {
      const data = [
        { category: 'A', count: 30 },
        { category: 'B', count: 25 },
        { category: 'C', count: 20 },
        { category: 'D', count: 15 },
        { category: 'E', count: 10 },
      ];
      const result = analyzeData(data);
      expect(['pie', 'bar']).toContain(result.primaryChart);
    });

    it('recommends bar chart for moderate categories', () => {
      const data = Array.from({ length: 12 }, (_, i) => ({
        region: `Region ${i + 1}`,
        revenue: Math.random() * 1000,
      }));
      const result = analyzeData(data);
      expect(result.primaryChart).toBe('bar');
    });

    it('recommends scatter for two numeric columns', () => {
      const data = Array.from({ length: 20 }, (_, i) => ({
        x: i * 10,
        y: i * 15 + Math.random() * 10,
      }));
      const result = analyzeData(data);
      expect(result.primaryChart).toBe('scatter');
    });

    it('provides alternatives', () => {
      const data = [
        { category: 'A', value: 100, quantity: 50 },
        { category: 'B', value: 200, quantity: 100 },
        { category: 'C', value: 150, quantity: 75 },
      ];
      const result = analyzeData(data);
      expect(result.alternatives.length).toBeGreaterThan(0);
      expect(result.alternatives[0]).toHaveProperty('chartType');
      expect(result.alternatives[0]).toHaveProperty('score');
      expect(result.alternatives[0]).toHaveProperty('reason');
    });

    it('generates natural language explanation', () => {
      const data = [
        { month: 'Jan', sales: 100 },
        { month: 'Feb', sales: 150 },
        { month: 'Mar', sales: 200 },
      ];
      const result = analyzeData(data);
      expect(result.nlExplanation).toBeTruthy();
      expect(result.nlExplanation.length).toBeGreaterThan(20);
    });

    it('detects outliers in data', () => {
      const data = [
        { name: 'A', value: 10 },
        { name: 'B', value: 12 },
        { name: 'C', value: 11 },
        { name: 'D', value: 100 }, // Outlier
        { name: 'E', value: 13 },
        { name: 'F', value: 9 },
      ];
      const result = analyzeData(data);
      expect(result.patterns.hasOutliers).toBe(true);
    });
  });

  describe('detectOutliers', () => {
    it('detects high outliers', () => {
      const data = [
        { value: 10 },
        { value: 12 },
        { value: 11 },
        { value: 100 }, // High outlier
        { value: 13 },
        { value: 9 },
      ];
      const outliers = detectOutliers(data, ['value']);
      expect(outliers.length).toBeGreaterThan(0);
      expect(outliers.some(o => o.value === 100)).toBe(true);
      expect(outliers.find(o => o.value === 100)?.isHigh).toBe(true);
    });

    it('detects low outliers', () => {
      const data = [
        { value: 100 },
        { value: 102 },
        { value: 98 },
        { value: 1 }, // Low outlier
        { value: 99 },
        { value: 101 },
      ];
      const outliers = detectOutliers(data, ['value']);
      expect(outliers.length).toBeGreaterThan(0);
      expect(outliers.some(o => o.value === 1)).toBe(true);
      expect(outliers.find(o => o.value === 1)?.isHigh).toBe(false);
    });

    it('returns empty array for uniform data', () => {
      const data = [
        { value: 10 },
        { value: 10 },
        { value: 10 },
        { value: 10 },
        { value: 10 },
      ];
      const outliers = detectOutliers(data, ['value']);
      expect(outliers.length).toBe(0);
    });

    it('ignores non-numeric values', () => {
      const data = [
        { value: 'text' },
        { value: null },
        { value: undefined },
      ] as any[];
      const outliers = detectOutliers(data, ['value']);
      expect(outliers.length).toBe(0);
    });
  });
});

describe('timeSeriesDetector', () => {
  it('detects ISO date format', () => {
    const data = [
      { date: '2024-01-01', value: 100 },
      { date: '2024-01-08', value: 120 },
      { date: '2024-01-15', value: 140 },
      { date: '2024-01-22', value: 160 },
      { date: '2024-01-29', value: 180 },
    ];
    const result = detectTimeSeriesPattern(data, ['date'], ['value']);
    expect(result.isTimeSeries).toBe(true);
    expect(result.temporalColumn).toBe('date');
  });

  it('detects upward trend', () => {
    const data = [
      { date: '2024-01-01', value: 100 },
      { date: '2024-02-01', value: 150 },
      { date: '2024-03-01', value: 200 },
      { date: '2024-04-01', value: 250 },
      { date: '2024-05-01', value: 300 },
    ];
    const result = detectTimeSeriesPattern(data, ['date'], ['value']);
    expect(result.hasTrend).toBe(true);
    expect(result.trendDirection).toBe('up');
  });

  it('detects downward trend', () => {
    const data = [
      { date: '2024-01-01', value: 300 },
      { date: '2024-02-01', value: 250 },
      { date: '2024-03-01', value: 200 },
      { date: '2024-04-01', value: 150 },
      { date: '2024-05-01', value: 100 },
    ];
    const result = detectTimeSeriesPattern(data, ['date'], ['value']);
    expect(result.hasTrend).toBe(true);
    expect(result.trendDirection).toBe('down');
  });

  it('detects weekly periodicity', () => {
    const data = [
      { date: '2024-01-01', value: 100 },
      { date: '2024-01-08', value: 110 },
      { date: '2024-01-15', value: 120 },
      { date: '2024-01-22', value: 130 },
    ];
    const result = detectTimeSeriesPattern(data, ['date'], ['value']);
    expect(result.periodicity).toBe('weekly');
  });

  it('returns false for non-time-series data', () => {
    const data = [
      { name: 'Product A', price: 100 },
      { name: 'Product B', price: 150 },
      { name: 'Product C', price: 200 },
    ];
    const result = detectTimeSeriesPattern(data, [], ['price']);
    expect(result.isTimeSeries).toBe(false);
  });
});

describe('hierarchyDetector', () => {
  it('detects parent-child relationships', () => {
    const data = [
      { id: 1, parent_id: null, name: 'Root' },
      { id: 2, parent_id: 1, name: 'Child 1' },
      { id: 3, parent_id: 1, name: 'Child 2' },
      { id: 4, parent_id: 2, name: 'Grandchild' },
    ];
    const result = detectHierarchy(data, ['name']);
    expect(result.isHierarchical).toBe(true);
    expect(result.type).toBe('parent-child');
    expect(result.parentColumn).toBe('parent_id');
    expect(result.maxDepth).toBeGreaterThanOrEqual(2);
  });

  it('detects nested categories (region > country)', () => {
    const data = [
      { region: 'Americas', country: 'USA', city: 'New York' },
      { region: 'Americas', country: 'USA', city: 'Los Angeles' },
      { region: 'Americas', country: 'Canada', city: 'Toronto' },
      { region: 'Europe', country: 'UK', city: 'London' },
      { region: 'Europe', country: 'France', city: 'Paris' },
    ];
    const result = detectHierarchy(data, ['region', 'country', 'city']);
    expect(result.isHierarchical).toBe(true);
    expect(result.type).toBe('nested-categories');
  });

  it('returns false for flat data', () => {
    const data = [
      { name: 'A', value: 100 },
      { name: 'B', value: 200 },
      { name: 'C', value: 300 },
    ];
    const result = detectHierarchy(data, ['name']);
    expect(result.isHierarchical).toBe(false);
  });
});

describe('geoDetector', () => {
  it('detects latitude/longitude coordinates', () => {
    const data = [
      { lat: 40.7128, lon: -74.0060, name: 'New York' },
      { lat: 34.0522, lon: -118.2437, name: 'Los Angeles' },
      { lat: 51.5074, lon: -0.1278, name: 'London' },
    ];
    const result = detectGeoData(data, Object.keys(data[0]));
    expect(result.isGeographic).toBe(true);
    expect(result.type).toBe('coordinates');
    expect(result.latColumn).toBe('lat');
    expect(result.lonColumn).toBe('lon');
  });

  it('detects country codes', () => {
    const data = [
      { country: 'US', sales: 1000 },
      { country: 'CA', sales: 800 },
      { country: 'GB', sales: 600 },
      { country: 'DE', sales: 500 },
    ];
    const result = detectGeoData(data, Object.keys(data[0]));
    expect(result.isGeographic).toBe(true);
    expect(result.type).toBe('country-codes');
    expect(result.geoColumn).toBe('country');
  });

  it('detects US state codes', () => {
    const data = [
      { state: 'CA', population: 39000000 },
      { state: 'TX', population: 29000000 },
      { state: 'NY', population: 19000000 },
      { state: 'FL', population: 21000000 },
    ];
    const result = detectGeoData(data, Object.keys(data[0]));
    expect(result.isGeographic).toBe(true);
    expect(result.type).toBe('us-states');
  });

  it('returns false for non-geographic data', () => {
    const data = [
      { product: 'Widget', price: 10 },
      { product: 'Gadget', price: 20 },
    ];
    const result = detectGeoData(data, Object.keys(data[0]));
    expect(result.isGeographic).toBe(false);
  });
});

describe('trendLineCalculator', () => {
  it('calculates slope for increasing values', () => {
    const values = [10, 20, 30, 40, 50];
    const result = calculateTrendLine(values);
    expect(result.slope).toBeGreaterThan(0);
    expect(result.direction).toBe('up');
  });

  it('calculates slope for decreasing values', () => {
    const values = [50, 40, 30, 20, 10];
    const result = calculateTrendLine(values);
    expect(result.slope).toBeLessThan(0);
    expect(result.direction).toBe('down');
  });

  it('calculates R-squared for perfect linear data', () => {
    const values = [10, 20, 30, 40, 50];
    const result = calculateTrendLine(values);
    expect(result.rSquared).toBeGreaterThan(0.99);
  });

  it('calculates lower R-squared for noisy data', () => {
    const values = [10, 25, 15, 35, 20, 40, 30];
    const result = calculateTrendLine(values);
    expect(result.rSquared).toBeLessThan(0.9);
  });

  it('returns stable direction for flat data', () => {
    const values = [100, 101, 99, 100, 100];
    const result = calculateTrendLine(values);
    expect(result.direction).toBe('stable');
  });

  it('generates correct number of trend points', () => {
    const values = [10, 20, 30, 40, 50];
    const result = calculateTrendLine(values);
    expect(result.points.length).toBeGreaterThanOrEqual(2);
  });

  it('handles empty array', () => {
    const result = calculateTrendLine([]);
    expect(result.slope).toBe(0);
    expect(result.rSquared).toBe(0);
  });

  it('handles single value', () => {
    const result = calculateTrendLine([42]);
    expect(result.slope).toBe(0);
  });
});

describe('calculateMovingAverage', () => {
  it('smooths data with window size 3', () => {
    const values = [10, 20, 30, 40, 50];
    const smoothed = calculateMovingAverage(values, 3);
    expect(smoothed.length).toBe(5);
    // Middle values should be averaged
    expect(smoothed[2]).toBeCloseTo(30, 0);
  });

  it('returns original for small arrays', () => {
    const values = [10, 20];
    const smoothed = calculateMovingAverage(values, 5);
    expect(smoothed).toEqual(values);
  });

  it('handles window larger than data', () => {
    const values = [10, 20, 30];
    const smoothed = calculateMovingAverage(values, 10);
    expect(smoothed).toEqual(values);
  });
});
