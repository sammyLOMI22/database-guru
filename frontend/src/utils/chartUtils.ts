/**
 * Chart Detection Utilities
 *
 * Automatically determines the best chart type based on query results
 * and statistics from the ResultNarrator.
 */

/**
 * Chart types supported by the visualization system
 *
 * Basic charts: bar, line, pie, scatter, table
 * Hierarchical charts: treemap, sunburst
 * Statistical charts: boxplot, histogram, bubble
 * Time-series charts: area
 */
export type ChartType =
  // Basic charts
  | 'bar'
  | 'line'
  | 'pie'
  | 'scatter'
  | 'table'
  // Hierarchical charts (Phase 10)
  | 'treemap'
  | 'sunburst'
  // Statistical charts (Phase 10)
  | 'boxplot'
  | 'histogram'
  | 'bubble'
  // Time-series charts (Phase 10)
  | 'area';

export interface ChartRecommendation {
  chartType: ChartType;
  confidence: number;
  xColumn: string | null;
  yColumn: string | null;
  reason: string;
}

interface ColumnClassification {
  numericColumns: string[];
  categoricalColumns: string[];
  temporalColumns: string[];
  idColumns: string[];
}

// Patterns that indicate a temporal/date column
const TEMPORAL_PATTERNS = [
  /date/i,
  /time/i,
  /year/i,
  /month/i,
  /day/i,
  /created_at/i,
  /updated_at/i,
  /timestamp/i,
  /_at$/i,
  /_on$/i,
];

// Patterns that indicate an ID column (should be excluded from charts)
const ID_PATTERNS = [
  /^id$/i,
  /_id$/i,
  /^pk$/i,
  /^key$/i,
  /uuid/i,
];

/**
 * Checks if a column name matches temporal patterns
 */
function isTemporalColumn(columnName: string): boolean {
  return TEMPORAL_PATTERNS.some(pattern => pattern.test(columnName));
}

/**
 * Checks if a column name matches ID patterns
 */
function isIdColumn(columnName: string): boolean {
  return ID_PATTERNS.some(pattern => pattern.test(columnName));
}

/**
 * Checks if a value looks like a date
 */
function looksLikeDate(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  // Check for common date formats
  const datePatterns = [
    /^\d{4}-\d{2}-\d{2}/, // ISO date
    /^\d{2}\/\d{2}\/\d{4}/, // US date
    /^\d{2}-\d{2}-\d{4}/, // Other date
  ];
  return datePatterns.some(pattern => pattern.test(value));
}

/**
 * Classifies columns based on their data types and names
 */
export function classifyColumns(
  results: Record<string, unknown>[],
  statistics: Record<string, unknown>
): ColumnClassification {
  if (!results || results.length === 0) {
    return {
      numericColumns: [],
      categoricalColumns: [],
      temporalColumns: [],
      idColumns: [],
    };
  }

  const columns = Object.keys(results[0]);
  const classification: ColumnClassification = {
    numericColumns: [],
    categoricalColumns: [],
    temporalColumns: [],
    idColumns: [],
  };

  for (const column of columns) {
    // Skip ID columns
    if (isIdColumn(column)) {
      classification.idColumns.push(column);
      continue;
    }

    // Check if statistics has type info
    const columnStats = statistics[column] as Record<string, unknown> | undefined;

    // Check for temporal columns first (by name or value pattern)
    if (isTemporalColumn(column) || looksLikeDate(results[0][column])) {
      classification.temporalColumns.push(column);
      continue;
    }

    // Use statistics type if available
    if (columnStats?.type === 'numeric') {
      classification.numericColumns.push(column);
    } else if (columnStats?.type === 'string') {
      classification.categoricalColumns.push(column);
    } else {
      // Fallback: inspect first non-null value
      const firstValue = results.find(r => r[column] != null)?.[column];
      if (typeof firstValue === 'number') {
        classification.numericColumns.push(column);
      } else if (typeof firstValue === 'string') {
        // Check if it's numeric string
        if (!isNaN(Number(firstValue)) && firstValue.trim() !== '') {
          classification.numericColumns.push(column);
        } else {
          classification.categoricalColumns.push(column);
        }
      }
    }
  }

  return classification;
}

/**
 * Gets the unique count for a categorical column
 */
function getUniqueCount(
  column: string,
  results: Record<string, unknown>[],
  statistics: Record<string, unknown>
): number {
  const columnStats = statistics[column] as Record<string, unknown> | undefined;
  if (columnStats?.unique_count !== undefined) {
    return columnStats.unique_count as number;
  }
  // Fallback: calculate from data
  const uniqueValues = new Set(results.map(r => r[column]));
  return uniqueValues.size;
}

/**
 * Main chart detection function
 *
 * Algorithm priority:
 * 1. Line Chart - temporal column + numeric (time-series)
 * 2. Scatter Plot - correlations detected
 * 3. Pie Chart - few categories (<=8) + numeric
 * 4. Bar Chart - moderate categories (<=15) + numeric
 * 5. Table - default fallback
 */
export function detectChartType(
  results: Record<string, unknown>[],
  statistics: Record<string, unknown>
): ChartRecommendation {
  // Default response
  const tableResult: ChartRecommendation = {
    chartType: 'table',
    confidence: 1.0,
    xColumn: null,
    yColumn: null,
    reason: 'Default table view',
  };

  // Insufficient data
  if (!results || results.length < 2) {
    return {
      ...tableResult,
      reason: 'Insufficient data for visualization (need at least 2 rows)',
    };
  }

  const classification = classifyColumns(results, statistics);
  const { numericColumns, categoricalColumns, temporalColumns } = classification;

  // Check for trends (from ResultNarrator)
  const trendsData = statistics.trends as Record<string, unknown> | undefined;
  const hasTrends = trendsData?.found === true;

  // Check for correlations (from ResultNarrator)
  const correlationsData = statistics.correlations as Record<string, unknown> | undefined;
  const hasCorrelations = correlationsData?.found === true;

  // 1. LINE CHART - Time-series data
  if (temporalColumns.length > 0 && numericColumns.length > 0) {
    return {
      chartType: 'line',
      confidence: hasTrends ? 0.95 : 0.85,
      xColumn: temporalColumns[0],
      yColumn: numericColumns[0],
      reason: hasTrends
        ? 'Time-series data with detected trends'
        : 'Time-series data detected (temporal + numeric columns)',
    };
  }

  // Also check if trends were detected even without obvious temporal column
  if (hasTrends && numericColumns.length >= 1) {
    const detectedTrends = trendsData?.detected_trends as Array<Record<string, unknown>> | undefined;
    if (detectedTrends && detectedTrends.length > 0) {
      const trendInfo = detectedTrends[0];
      return {
        chartType: 'line',
        confidence: 0.9,
        xColumn: (trendInfo.temporal_column as string) || categoricalColumns[0] || null,
        yColumn: (trendInfo.column as string) || numericColumns[0],
        reason: 'Trend detected in data',
      };
    }
  }

  // 2. SCATTER PLOT - Correlations detected
  if (hasCorrelations && numericColumns.length >= 2) {
    const significantCorrelations = correlationsData?.significant_correlations as Array<Record<string, unknown>> | undefined;
    if (significantCorrelations && significantCorrelations.length > 0) {
      const corr = significantCorrelations[0];
      return {
        chartType: 'scatter',
        confidence: 0.9,
        xColumn: corr.column1 as string,
        yColumn: corr.column2 as string,
        reason: `Strong correlation detected (r=${(corr.correlation as number)?.toFixed(2)})`,
      };
    }
  }

  // 3 & 4. PIE or BAR CHART - Categorical + Numeric
  if (categoricalColumns.length > 0 && numericColumns.length > 0) {
    const catColumn = categoricalColumns[0];
    const uniqueCount = getUniqueCount(catColumn, results, statistics);

    // PIE CHART - Few categories
    if (uniqueCount <= 8 && uniqueCount >= 2) {
      return {
        chartType: 'pie',
        confidence: 0.85,
        xColumn: catColumn,
        yColumn: numericColumns[0],
        reason: `Categorical distribution with ${uniqueCount} categories`,
      };
    }

    // BAR CHART - Moderate categories
    if (uniqueCount <= 15) {
      return {
        chartType: 'bar',
        confidence: 0.8,
        xColumn: catColumn,
        yColumn: numericColumns[0],
        reason: `Categorical comparison with ${uniqueCount} categories`,
      };
    }
  }

  // 5. Check for simple numeric comparison (bar chart)
  if (numericColumns.length >= 1 && results.length <= 20) {
    // If we have row labels or can use index
    const labelColumn = categoricalColumns[0] || Object.keys(results[0])[0];
    return {
      chartType: 'bar',
      confidence: 0.6,
      xColumn: labelColumn,
      yColumn: numericColumns[0],
      reason: 'Numeric values suitable for comparison',
    };
  }

  // Default to table
  return {
    ...tableResult,
    reason: categoricalColumns.length === 0 && numericColumns.length === 0
      ? 'No suitable columns for visualization'
      : 'Too many unique values for effective visualization',
  };
}

/**
 * Prepares data for a specific chart type
 */
export function prepareChartData(
  results: Record<string, unknown>[],
  xColumn: string,
  yColumn: string,
  chartType: ChartType,
  maxItems: number = 100
): Record<string, unknown>[] {
  // Limit data for performance
  const limitedResults = results.slice(0, maxItems);

  // For pie charts, aggregate by category
  if (chartType === 'pie') {
    const aggregated = new Map<string, number>();
    for (const row of limitedResults) {
      const key = String(row[xColumn] ?? 'Unknown');
      const value = Number(row[yColumn]) || 0;
      aggregated.set(key, (aggregated.get(key) || 0) + value);
    }
    return Array.from(aggregated.entries()).map(([name, value]) => ({
      name,
      value,
    }));
  }

  // For other charts, return filtered data
  return limitedResults.map(row => ({
    [xColumn]: row[xColumn],
    [yColumn]: Number(row[yColumn]) || 0,
    // Include original row for tooltips
    _original: row,
  }));
}

/**
 * Chart color palette (Tailwind-aligned)
 */
export const CHART_COLORS = {
  primary: '#3b82f6',    // blue-500
  secondary: '#8b5cf6',  // violet-500
  success: '#10b981',    // emerald-500
  warning: '#f59e0b',    // amber-500
  danger: '#ef4444',     // red-500
  info: '#06b6d4',       // cyan-500
  pink: '#ec4899',       // pink-500
  lime: '#84cc16',       // lime-500
};

export const PIE_PALETTE = [
  CHART_COLORS.primary,
  CHART_COLORS.secondary,
  CHART_COLORS.success,
  CHART_COLORS.warning,
  CHART_COLORS.danger,
  CHART_COLORS.info,
  CHART_COLORS.pink,
  CHART_COLORS.lime,
];
