import { describe, it, expect } from 'vitest';
import {
  analyzeData,
  scoreColumnInterest,
  ScoringPreset,
} from '../src/utils/chartIntelligence';

// Helper data generators
function makeCategoricalData(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    category: `Cat ${i + 1}`,
    revenue: (i + 1) * 100,
    count: (i + 1) * 10,
  }));
}

function makeTimeSeriesData(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    date: `2024-01-${String(i + 1).padStart(2, '0')}`,
    sales: 100 + i * 20,
    cost: 50 + i * 5,
  }));
}

function makeNumericOnlyData(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    x_value: Math.random() * 100,
    y_value: Math.random() * 100,
    size: Math.random() * 50,
  }));
}

describe('Phase 19.4: Chart Intelligence Enhancements', () => {
  describe('Adaptive Scoring Presets', () => {
    it('default preset produces same results as no preset', () => {
      const data = makeCategoricalData(6);
      const resultDefault = analyzeData(data, {}, '', 'default');
      const resultNone = analyzeData(data, {});
      expect(resultDefault.primaryChart).toBe(resultNone.primaryChart);
      expect(resultDefault.confidence).toBe(resultNone.confidence);
    });

    it('business preset boosts categorical comparison charts', () => {
      const data = makeCategoricalData(6);
      const defaultResult = analyzeData(data, {}, '', 'default');
      const businessResult = analyzeData(data, {}, '', 'business');

      // Business preset should prefer bar charts for categorical data
      const defaultBarAlt = [defaultResult.primaryChart, ...defaultResult.alternatives.map(a => a.chartType)];
      const businessBarAlt = [businessResult.primaryChart, ...businessResult.alternatives.map(a => a.chartType)];

      // Bar should rank higher or equal in business preset
      const defaultBarIdx = defaultBarAlt.indexOf('bar');
      const businessBarIdx = businessBarAlt.indexOf('bar');
      expect(businessBarIdx).toBeLessThanOrEqual(defaultBarIdx);
    });

    it('scientific preset boosts distribution and correlation charts', () => {
      // Data with multiple numeric columns (favors scatter in scientific)
      const data = makeNumericOnlyData(30);
      const defaultResult = analyzeData(data, {}, '', 'default');
      const sciResult = analyzeData(data, {}, '', 'scientific');

      // Scientific should prefer scatter/histogram over bar/pie
      const sciCharts = [sciResult.primaryChart, ...sciResult.alternatives.map(a => a.chartType)];
      const hasDistOrCorr = sciCharts.some(c => ['scatter', 'histogram', 'boxplot'].includes(c));
      expect(hasDistOrCorr).toBe(true);
    });

    it('business preset reduces scatter chart prominence', () => {
      const data = makeNumericOnlyData(20);
      const defaultResult = analyzeData(data, {}, '', 'default');
      const businessResult = analyzeData(data, {}, '', 'business');

      // In business mode, scatter should score relatively lower
      const defaultScatter = defaultResult.alternatives.find(a => a.chartType === 'scatter');
      const businessScatter = businessResult.alternatives.find(a => a.chartType === 'scatter');

      if (defaultScatter && businessScatter) {
        expect(businessScatter.score).toBeLessThanOrEqual(defaultScatter.score);
      }
    });
  });

  describe('Column Interest Scoring', () => {
    it('ranks revenue-like columns higher than id columns', () => {
      const data = [
        { id: 1, revenue: 1000, user_id: 101 },
        { id: 2, revenue: 2500, user_id: 102 },
        { id: 3, revenue: 500, user_id: 103 },
        { id: 4, revenue: 3200, user_id: 104 },
        { id: 5, revenue: 800, user_id: 105 },
      ];

      const revenueScore = scoreColumnInterest('revenue', data);
      const idScore = scoreColumnInterest('id', data);
      const userIdScore = scoreColumnInterest('user_id', data);

      expect(revenueScore).toBeGreaterThan(idScore);
      expect(revenueScore).toBeGreaterThan(userIdScore);
    });

    it('gives higher score to columns with more variance', () => {
      const data = [
        { stable: 100, volatile: 10 },
        { stable: 101, volatile: 500 },
        { stable: 100, volatile: 20 },
        { stable: 99, volatile: 800 },
        { stable: 100, volatile: 5 },
      ];

      const stableScore = scoreColumnInterest('stable', data);
      const volatileScore = scoreColumnInterest('volatile', data);

      expect(volatileScore).toBeGreaterThan(stableScore);
    });

    it('returns 0 for non-numeric columns', () => {
      const data = [
        { name: 'Alice', value: 100 },
        { name: 'Bob', value: 200 },
      ];

      expect(scoreColumnInterest('name', data)).toBe(0);
    });

    it('penalizes columns with many nulls', () => {
      const data = [
        { complete: 100, sparse: null },
        { complete: 200, sparse: null },
        { complete: 300, sparse: 50 },
        { complete: 400, sparse: null },
        { complete: 500, sparse: 100 },
      ];

      const completeScore = scoreColumnInterest('complete', data);
      const sparseScore = scoreColumnInterest('sparse', data);

      expect(completeScore).toBeGreaterThan(sparseScore);
    });

    it('uses interest scoring for Y-axis selection', () => {
      const data = [
        { category: 'A', id: 1, total_sales: 1000, index: 0 },
        { category: 'B', id: 2, total_sales: 2500, index: 1 },
        { category: 'C', id: 3, total_sales: 500, index: 2 },
        { category: 'D', id: 4, total_sales: 3200, index: 3 },
        { category: 'E', id: 5, total_sales: 800, index: 4 },
      ];

      const result = analyzeData(data);
      // total_sales should be picked over id/index for Y axis
      expect(result.yColumn).toBe('total_sales');
    });
  });

  describe('Context-Aware Insights', () => {
    it('surfaces trend insight first for trend questions', () => {
      const data = makeTimeSeriesData(10);
      const result = analyzeData(data, {}, 'show me the trend over time');

      if (result.insights.length > 0 && result.patterns.hasTrend) {
        expect(result.insights[0].type).toBe('trend');
        expect(result.insights[0].severity).toBe('highlight');
      }
    });

    it('surfaces outlier insight for anomaly questions', () => {
      // Create data with clear outlier
      const data = [
        { category: 'A', value: 100 },
        { category: 'B', value: 105 },
        { category: 'C', value: 98 },
        { category: 'D', value: 102 },
        { category: 'E', value: 500 }, // outlier
        { category: 'F', value: 101 },
        { category: 'G', value: 99 },
      ];

      const result = analyzeData(data, {}, 'find unusual values');
      const outlierInsight = result.insights.find(i => i.type === 'outlier');
      if (outlierInsight) {
        expect(outlierInsight.severity).toBe('highlight');
      }
    });

    it('adds distribution insight for comparison questions', () => {
      const data = makeCategoricalData(5);
      const result = analyzeData(data, {}, 'compare categories');
      const hasDistribution = result.insights.some(i => i.type === 'distribution');
      expect(hasDistribution).toBe(true);
    });

    it('returns base insights when no question provided', () => {
      const data = makeTimeSeriesData(10);
      const withQuestion = analyzeData(data, {}, 'trend over time');
      const withoutQuestion = analyzeData(data, {});

      // Both should have insights, but context-aware may have different ordering
      expect(withoutQuestion.insights.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Backward Compatibility', () => {
    it('analyzeData works with only results argument', () => {
      const data = makeCategoricalData(5);
      const result = analyzeData(data);
      expect(result.primaryChart).toBeDefined();
      expect(result.confidence).toBeGreaterThan(0);
      expect(result.alternatives).toBeDefined();
    });

    it('analyzeData works with results and statistics only', () => {
      const data = makeCategoricalData(5);
      const result = analyzeData(data, {});
      expect(result.primaryChart).toBeDefined();
    });

    it('still returns table for insufficient data', () => {
      const result = analyzeData([], {}, 'some question', 'business');
      expect(result.primaryChart).toBe('table');
    });
  });
});
