import { describe, it, expect } from 'vitest';
import {
  parseChartIntent,
  hasChartIntent,
  getChartTypeKeywords,
  getChartIntentHint,
} from '../src/utils/chartIntentParser';

describe('chartIntentParser', () => {
  describe('parseChartIntent', () => {
    // Bar chart detection
    describe('bar chart detection', () => {
      it('detects "bar chart" keyword', () => {
        const result = parseChartIntent('Create a bar chart of sales by region');
        expect(result.chartType).toBe('bar');
        expect(result.confidence).toBe('high');
        expect(result.cleanedQuestion).toBe('sales by region');
      });

      it('detects "bar graph" keyword', () => {
        const result = parseChartIntent('Show me a bar graph of inventory');
        expect(result.chartType).toBe('bar');
        expect(result.confidence).toBe('high');
      });

      it('detects "bargraph" without space', () => {
        const result = parseChartIntent('Create a bargraph of revenue');
        expect(result.chartType).toBe('bar');
      });

      it('detects "barchart" without space', () => {
        const result = parseChartIntent('Show barchart of products');
        expect(result.chartType).toBe('bar');
      });

      it('detects comparison keywords as bar chart', () => {
        const result = parseChartIntent('Compare sales across regions');
        expect(result.chartType).toBe('bar');
        expect(result.confidence).toBe('medium');
      });
    });

    // Pie chart detection
    describe('pie chart detection', () => {
      it('detects "pie chart" keyword', () => {
        const result = parseChartIntent('Show a pie chart of market share');
        expect(result.chartType).toBe('pie');
        expect(result.confidence).toBe('high');
      });

      it('detects "piechart" without space', () => {
        const result = parseChartIntent('Create piechart of expenses');
        expect(result.chartType).toBe('pie');
      });

      it('detects distribution keywords as pie chart', () => {
        const result = parseChartIntent('Show the distribution of categories');
        expect(result.chartType).toBe('pie');
        expect(result.confidence).toBe('medium');
      });

      it('detects breakdown keywords as pie chart', () => {
        const result = parseChartIntent('Show breakdown of revenue by product');
        expect(result.chartType).toBe('pie');
      });
    });

    // Line chart detection
    describe('line chart detection', () => {
      it('detects "line chart" keyword', () => {
        const result = parseChartIntent('Create a line chart of sales over time');
        expect(result.chartType).toBe('line');
        expect(result.confidence).toBe('high');
      });

      it('detects "line graph" keyword', () => {
        const result = parseChartIntent('Show line graph of revenue');
        expect(result.chartType).toBe('line');
      });

      it('detects "linechart" without space', () => {
        const result = parseChartIntent('Create linechart of trends');
        expect(result.chartType).toBe('line');
      });

      it('detects trend keywords as line chart', () => {
        const result = parseChartIntent('Show the trend of user signups');
        expect(result.chartType).toBe('line');
        expect(result.confidence).toBe('medium');
      });

      it('detects "over time" as line chart', () => {
        const result = parseChartIntent('Show sales over time');
        expect(result.chartType).toBe('line');
      });

      it('detects "graph of" as line chart', () => {
        const result = parseChartIntent('Graph of monthly revenue');
        expect(result.chartType).toBe('line');
      });
    });

    // Scatter plot detection
    describe('scatter plot detection', () => {
      it('detects "scatter plot" keyword', () => {
        const result = parseChartIntent('Create a scatter plot of price vs quantity');
        expect(result.chartType).toBe('scatter');
        expect(result.confidence).toBe('high');
      });

      it('detects "scatterplot" without space', () => {
        const result = parseChartIntent('Show scatterplot of correlation');
        expect(result.chartType).toBe('scatter');
      });

      it('detects "scatter chart" keyword', () => {
        const result = parseChartIntent('Show scatter chart of data points');
        expect(result.chartType).toBe('scatter');
      });

      it('detects correlation keywords as scatter', () => {
        const result = parseChartIntent('Show the correlation between price and sales');
        expect(result.chartType).toBe('scatter');
        expect(result.confidence).toBe('medium');
      });

      it('detects "plot X vs Y" as scatter', () => {
        const result = parseChartIntent('Plot price vs quantity');
        expect(result.chartType).toBe('scatter');
      });
    });

    // Dynamic chart type detection
    describe('dynamic chart type detection', () => {
      it('detects "create a X chart" pattern', () => {
        const result = parseChartIntent('Create a bar chart of inventory');
        expect(result.chartType).toBe('bar');
      });

      it('handles unknown chart type gracefully', () => {
        // "chart of" pattern triggers bar chart detection (medium confidence)
        const result = parseChartIntent('Create a unknown chart of data');
        // The "chart of" pattern matches, so it returns bar with medium confidence
        expect(result.chartType).toBe('bar');
        expect(result.confidence).toBe('medium');
      });

      it('detects "visualize as X" pattern', () => {
        const result = parseChartIntent('Visualize as pie the data');
        expect(result.chartType).toBe('pie');
      });
    });

    // No chart intent
    describe('no chart intent', () => {
      it('returns null for plain questions', () => {
        const result = parseChartIntent('Show me all customers from California');
        expect(result.chartType).toBeNull();
        expect(result.cleanedQuestion).toBe('Show me all customers from California');
      });

      it('returns null for SQL-like questions', () => {
        const result = parseChartIntent('What are the top 10 products by sales?');
        expect(result.chartType).toBeNull();
      });

      it('returns null for empty question', () => {
        const result = parseChartIntent('');
        expect(result.chartType).toBeNull();
      });
    });

    // Question cleaning
    describe('question cleaning', () => {
      it('removes chart keywords from question', () => {
        const result = parseChartIntent('Create a bar chart of inventory levels');
        expect(result.cleanedQuestion).not.toContain('bar chart');
        // The parser removes the matched pattern and cleans up connectors
        expect(result.cleanedQuestion).toContain('inventory levels');
      });

      it('preserves question when no chart intent', () => {
        const result = parseChartIntent('Show all orders');
        expect(result.cleanedQuestion).toBe('Show all orders');
      });

      it('handles simple chart keyword at start', () => {
        const result = parseChartIntent('bar chart of sales data');
        // The parser removes "bar chart" and cleans "of" connector
        expect(result.cleanedQuestion).toBe('sales data');
      });
    });
  });

  describe('hasChartIntent', () => {
    it('returns true for chart keywords', () => {
      expect(hasChartIntent('Create a bar chart')).toBe(true);
      expect(hasChartIntent('pie chart of data')).toBe(true);
      expect(hasChartIntent('line graph showing trends')).toBe(true);
    });

    it('returns false for plain questions', () => {
      expect(hasChartIntent('Show me all customers')).toBe(false);
      expect(hasChartIntent('How many orders?')).toBe(false);
    });
  });

  describe('getChartTypeKeywords', () => {
    it('returns list of chart keywords', () => {
      const keywords = getChartTypeKeywords();
      expect(keywords).toContain('bar chart');
      expect(keywords).toContain('pie chart');
      expect(keywords).toContain('line chart');
      expect(keywords).toContain('scatter plot');
    });
  });

  describe('getChartIntentHint', () => {
    it('returns hint for high confidence detection', () => {
      const result = parseChartIntent('Create a bar chart');
      const hint = getChartIntentHint(result);
      expect(hint).toContain('bar chart');
      expect(hint).toContain('Will display');
    });

    it('returns hint for medium confidence detection', () => {
      const result = parseChartIntent('Show the trend of data');
      const hint = getChartIntentHint(result);
      expect(hint).toContain('Suggested');
    });

    it('returns null for no chart intent', () => {
      const result = parseChartIntent('Show all data');
      const hint = getChartIntentHint(result);
      expect(hint).toBeNull();
    });
  });
});
