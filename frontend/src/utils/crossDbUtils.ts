/**
 * Cross-Database Analysis Utilities
 *
 * Functions for analyzing and comparing data across multiple databases.
 */

import { PIE_PALETTE } from './chartUtils';

/**
 * Configuration for cross-database comparison chart
 */
export interface CrossDbChartConfig {
  /** Common numeric columns found across all databases */
  commonColumns: string[];
  /** Aggregated data for each database */
  aggregatedData: CrossDbAggregatedData[];
  /** The metric column to compare */
  primaryMetric: string;
  /** Aggregation method used */
  aggregationMethod: 'sum' | 'avg' | 'count';
}

/**
 * Aggregated data for a single database
 */
export interface CrossDbAggregatedData {
  databaseName: string;
  databaseType: string;
  rowCount: number;
  metrics: Record<string, number>;
  color: string;
}

/**
 * Database result type for cross-database analysis
 */
export interface DatabaseResultForCrossDb {
  connection_id: number;
  connection_name: string;
  database_type: string;
  results?: Record<string, unknown>[] | null;
  success: boolean;
  row_count?: number;
}

/**
 * Finds numeric columns that are common across all successful database results
 */
export function findCommonNumericColumns(
  results: DatabaseResultForCrossDb[]
): string[] {
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );

  if (successfulResults.length < 2) {
    return []; // Need at least 2 databases to compare
  }

  // Get numeric columns from first result
  const firstResult = successfulResults[0].results![0];
  const numericColumns = Object.entries(firstResult)
    .filter(([key, value]) => {
      // Skip ID-like columns
      if (/^id$|_id$|^pk$|^key$|uuid/i.test(key)) return false;
      // Check if value is numeric
      return typeof value === 'number' || !isNaN(Number(value));
    })
    .map(([key]) => key);

  // Filter to columns present in ALL databases
  const commonColumns = numericColumns.filter((col) =>
    successfulResults.every((r) => {
      if (!r.results || r.results.length === 0) return false;
      const firstRow = r.results[0];
      const value = firstRow[col];
      return (
        col in firstRow &&
        (typeof value === 'number' || !isNaN(Number(value)))
      );
    })
  );

  return commonColumns;
}

/**
 * Aggregates numeric columns by database
 */
export function aggregateByDatabase(
  results: DatabaseResultForCrossDb[],
  columns: string[],
  method: 'sum' | 'avg' | 'count' = 'sum'
): CrossDbAggregatedData[] {
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );

  return successfulResults.map((result, index) => {
    const metrics: Record<string, number> = {};

    for (const col of columns) {
      let value = 0;

      if (method === 'count') {
        value = result.results?.length || 0;
      } else {
        const sum = result.results?.reduce((acc, row) => {
          const numValue = Number(row[col]);
          return acc + (isNaN(numValue) ? 0 : numValue);
        }, 0) || 0;

        if (method === 'avg' && result.results && result.results.length > 0) {
          value = sum / result.results.length;
        } else {
          value = sum;
        }
      }

      metrics[col] = Math.round(value * 100) / 100; // Round to 2 decimals
    }

    return {
      databaseName: result.connection_name,
      databaseType: result.database_type,
      rowCount: result.results?.length || 0,
      metrics,
      color: PIE_PALETTE[index % PIE_PALETTE.length],
    };
  });
}

/**
 * Detects if cross-database comparison is possible and returns configuration
 */
export function detectCrossDbComparison(
  results: DatabaseResultForCrossDb[]
): CrossDbChartConfig | null {
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );

  // Need at least 2 successful databases to compare
  if (successfulResults.length < 2) {
    return null;
  }

  const commonColumns = findCommonNumericColumns(results);

  // Need at least 1 common numeric column
  if (commonColumns.length === 0) {
    return null;
  }

  // Choose first common column as primary metric
  const primaryMetric = commonColumns[0];

  // Aggregate data
  const aggregatedData = aggregateByDatabase(results, commonColumns, 'sum');

  return {
    commonColumns,
    aggregatedData,
    primaryMetric,
    aggregationMethod: 'sum',
  };
}

/**
 * Formats a metric value for display
 */
export function formatMetricValue(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}
