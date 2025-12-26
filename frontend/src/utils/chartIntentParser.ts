/**
 * Chart Intent Parser
 *
 * Parses natural language queries to extract chart type preferences.
 * Allows users to request specific visualizations like:
 * - "Create a bar chart of inventory"
 * - "Show me a pie chart of sales by region"
 * - "Graph inventory levels as a line chart"
 */

import { ChartType } from './chartUtils';

export interface ChartIntentResult {
  /** The detected chart type, or null if no chart intent found */
  chartType: ChartType | null;
  /** The question with chart-related keywords removed */
  cleanedQuestion: string;
  /** The original matched phrase (for debugging/display) */
  matchedPhrase: string | null;
  /** Confidence level: 'high' if explicit chart type, 'medium' if inferred */
  confidence: 'high' | 'medium' | 'low' | null;
}

interface ChartPattern {
  pattern: RegExp;
  type: ChartType | 'dynamic';
  confidence: 'high' | 'medium';
}

/**
 * Patterns for detecting chart type requests in natural language.
 * Ordered by specificity - more specific patterns first.
 */
const CHART_PATTERNS: ChartPattern[] = [
  // Explicit chart type mentions (high confidence)
  // Supports: "bar chart", "bar graph", "barchart", "bargraph", "bar plot", etc.
  { pattern: /\b(?:bar\s*(?:chart|graph|plot)?|barchart|bargraph)\b/i, type: 'bar', confidence: 'high' },
  { pattern: /\b(?:pie\s*(?:chart|graph)?|piechart|piegraph)\b/i, type: 'pie', confidence: 'high' },
  { pattern: /\b(?:line\s*(?:chart|graph|plot)?|linechart|linegraph)\b/i, type: 'line', confidence: 'high' },
  { pattern: /\b(?:scatter\s*(?:plot|chart|graph)?|scatterplot|scatterchart)\b/i, type: 'scatter', confidence: 'high' },
  { pattern: /\b(?:area\s*(?:chart|graph)?|areachart)\b/i, type: 'area', confidence: 'high' },
  // Phase 10: Advanced chart patterns
  { pattern: /\b(?:histogram|frequency\s*(?:chart|graph)?)\b/i, type: 'histogram', confidence: 'high' },
  { pattern: /\b(?:box\s*(?:plot|and\s*whisker)?|boxplot|whisker\s*(?:plot|chart)?)\b/i, type: 'boxplot', confidence: 'high' },
  { pattern: /\b(?:tree\s*map|treemap)\b/i, type: 'treemap', confidence: 'high' },
  { pattern: /\b(?:sunburst|radial\s*(?:chart|graph)?)\b/i, type: 'sunburst', confidence: 'high' },
  { pattern: /\b(?:bubble\s*(?:chart|graph|plot)?|bubblechart)\b/i, type: 'bubble', confidence: 'high' },

  // "Create a X chart" pattern
  { pattern: /\bcreate\s+(?:a\s+)?(\w+)\s+(?:chart|graph|plot)\b/i, type: 'dynamic', confidence: 'high' },

  // "Show as X" pattern
  { pattern: /\bshow\s+(?:as\s+)?(?:a\s+)?(\w+)\s+(?:chart|graph|plot)?\b/i, type: 'dynamic', confidence: 'high' },

  // "Visualize as X" pattern
  { pattern: /\bvisualize\s+(?:as\s+)?(?:a\s+)?(\w+)\b/i, type: 'dynamic', confidence: 'medium' },

  // "Graph of" or "Chart of" (medium confidence - defaults to bar/line)
  { pattern: /\bgraph\s+(?:of|showing|for)\b/i, type: 'line', confidence: 'medium' },
  { pattern: /\bchart\s+(?:of|showing|for)\b/i, type: 'bar', confidence: 'medium' },

  // "Plot X" pattern
  { pattern: /\bplot\s+(?:the\s+)?(?:\w+\s+){0,2}(?:vs|versus|against)\b/i, type: 'scatter', confidence: 'medium' },

  // Distribution-related keywords
  { pattern: /\b(?:distribution|breakdown|proportion|percentage)\s+(?:of|for|by)\b/i, type: 'pie', confidence: 'medium' },

  // Trend-related keywords
  { pattern: /\b(?:trend|over\s+time|timeline|progression)\b/i, type: 'line', confidence: 'medium' },

  // Comparison-related keywords
  { pattern: /\b(?:compare|comparison|versus|vs)\b/i, type: 'bar', confidence: 'medium' },

  // Correlation-related keywords
  { pattern: /\b(?:correlation|relationship\s+between|scatter)\b/i, type: 'scatter', confidence: 'medium' },
];

/**
 * Map of chart type synonyms to canonical types
 */
const CHART_TYPE_SYNONYMS: Record<string, ChartType> = {
  // Basic charts
  'bar': 'bar',
  'bars': 'bar',
  'column': 'bar',
  'columns': 'bar',

  'line': 'line',
  'lines': 'line',
  'trend': 'line',
  'timeline': 'line',

  'pie': 'pie',
  'donut': 'pie',
  'doughnut': 'pie',
  'circle': 'pie',

  'scatter': 'scatter',
  'scatterplot': 'scatter',
  'dot': 'scatter',
  'dots': 'scatter',
  'point': 'scatter',
  'points': 'scatter',
  'xy': 'scatter',

  // Phase 10: Advanced charts
  'area': 'area',
  'areachart': 'area',
  'filled': 'area',

  'histogram': 'histogram',
  'distribution': 'histogram',
  'frequency': 'histogram',

  'boxplot': 'boxplot',
  'box': 'boxplot',
  'whisker': 'boxplot',
  'quartile': 'boxplot',

  'treemap': 'treemap',
  'tree': 'treemap',
  'heatmap': 'treemap',

  'sunburst': 'sunburst',
  'radial': 'sunburst',
  'ring': 'sunburst',

  'bubble': 'bubble',
  'bubbles': 'bubble',
};

/**
 * Validates and normalizes a chart type string to a valid ChartType.
 * Returns null if the string doesn't match any known chart type.
 */
function normalizeChartType(typeStr: string): ChartType | null {
  const normalized = typeStr.toLowerCase().trim();
  return CHART_TYPE_SYNONYMS[normalized] || null;
}

/**
 * Parses a natural language question to extract chart type preferences.
 *
 * @param question - The user's natural language query
 * @returns ChartIntentResult with detected chart type and cleaned question
 *
 * @example
 * parseChartIntent("Create a bar chart of inventory by category")
 * // Returns: { chartType: 'bar', cleanedQuestion: 'inventory by category', ... }
 *
 * @example
 * parseChartIntent("Show me sales by region")
 * // Returns: { chartType: null, cleanedQuestion: 'Show me sales by region', ... }
 */
export function parseChartIntent(question: string): ChartIntentResult {
  const trimmedQuestion = question.trim();

  for (const { pattern, type, confidence } of CHART_PATTERNS) {
    const match = trimmedQuestion.match(pattern);

    if (match) {
      let chartType: ChartType | null = null;

      if (type === 'dynamic') {
        // Extract the chart type from the capture group
        const capturedType = match[1];
        if (capturedType) {
          chartType = normalizeChartType(capturedType);
        }
      } else {
        chartType = type;
      }

      // If we found a valid chart type, clean the question
      if (chartType) {
        // Remove the matched phrase from the question
        let cleanedQuestion = trimmedQuestion.replace(pattern, '').trim();

        // Clean up common prefix phrases (Create a, Show me, Make a, etc.)
        cleanedQuestion = cleanedQuestion
          .replace(/^(?:create|show|make|display|generate|give\s+me|build)\s+(?:a|an|me|the)?\s*/i, '')
          .trim();

        // Clean up common connecting words left at the start or end
        cleanedQuestion = cleanedQuestion
          .replace(/^(?:of|for|showing|with|the)\s+/i, '')
          .replace(/\s+(?:of|for|showing|with|the)$/i, '')
          .trim();

        // If the cleaned question is empty, use the original
        if (!cleanedQuestion) {
          cleanedQuestion = trimmedQuestion;
        }

        return {
          chartType,
          cleanedQuestion,
          matchedPhrase: match[0],
          confidence,
        };
      }
    }
  }

  // No chart intent found
  return {
    chartType: null,
    cleanedQuestion: trimmedQuestion,
    matchedPhrase: null,
    confidence: null,
  };
}

/**
 * Checks if a question contains any chart-related keywords.
 * Useful for UI hints without full parsing.
 */
export function hasChartIntent(question: string): boolean {
  const result = parseChartIntent(question);
  return result.chartType !== null;
}

/**
 * Returns a list of supported chart type keywords for autocomplete/suggestions.
 */
export function getChartTypeKeywords(): string[] {
  return [
    'bar chart',
    'pie chart',
    'line chart',
    'scatter plot',
    'area chart',
    'histogram',
    'trend',
    'distribution',
    'comparison',
  ];
}

/**
 * Generates a hint message based on the detected chart intent.
 */
export function getChartIntentHint(result: ChartIntentResult): string | null {
  if (!result.chartType) {
    return null;
  }

  const typeLabels: Record<ChartType, string> = {
    bar: 'bar chart',
    line: 'line chart',
    pie: 'pie chart',
    scatter: 'scatter plot',
    table: 'table',
    // Phase 10: Advanced Charts
    treemap: 'treemap',
    sunburst: 'sunburst chart',
    boxplot: 'box plot',
    histogram: 'histogram',
    bubble: 'bubble chart',
    area: 'area chart',
  };

  const label = typeLabels[result.chartType];

  if (result.confidence === 'high') {
    return `Will display results as a ${label}`;
  } else {
    return `Suggested visualization: ${label}`;
  }
}
