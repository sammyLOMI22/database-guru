/**
 * Time Series Pattern Detector
 *
 * Detects periodic patterns (weekly, monthly, yearly) in time-series data.
 * Analyzes temporal columns to identify:
 * - Whether data is time-series
 * - Periodicity (daily, weekly, monthly, yearly)
 * - Trend direction (up, down, stable)
 * - Seasonal patterns
 */

export interface TimeSeriesInfo {
  /** Whether the data appears to be time-series */
  isTimeSeries: boolean;
  /** The temporal column identified */
  temporalColumn: string | null;
  /** Detected periodicity */
  periodicity: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | null;
  /** Average interval between data points in milliseconds */
  avgIntervalMs: number | null;
  /** Trend direction based on linear regression */
  trendDirection: 'up' | 'down' | 'stable' | null;
  /** Trend strength (0-1) */
  trendStrength: number;
  /** Whether trend was detected */
  hasTrend: boolean;
  /** Confidence score for time-series detection (0-1) */
  confidence: number;
}

/**
 * Patterns for detecting date/time columns
 */
const DATE_COLUMN_PATTERNS = [
  /date/i,
  /time/i,
  /timestamp/i,
  /created/i,
  /updated/i,
  /modified/i,
  /_at$/i,
  /_on$/i,
  /^dt_/i,
  /period/i,
  /year/i,
  /month/i,
  /day/i,
  /week/i,
];

/**
 * Patterns for parsing date values
 */
const DATE_VALUE_PATTERNS = [
  /^\d{4}-\d{2}-\d{2}/, // ISO date
  /^\d{2}\/\d{2}\/\d{4}/, // US date MM/DD/YYYY
  /^\d{2}-\d{2}-\d{4}/, // EU date DD-MM-YYYY
  /^\d{4}\/\d{2}\/\d{2}/, // YYYY/MM/DD
  /^\d{4}-\d{2}-\d{2}T/, // ISO datetime
];

/**
 * Interval thresholds for periodicity detection (in milliseconds)
 */
const PERIODICITY_THRESHOLDS = {
  daily: { min: 20 * 60 * 60 * 1000, max: 28 * 60 * 60 * 1000 }, // 20-28 hours
  weekly: { min: 5 * 24 * 60 * 60 * 1000, max: 9 * 24 * 60 * 60 * 1000 }, // 5-9 days
  monthly: { min: 25 * 24 * 60 * 60 * 1000, max: 35 * 24 * 60 * 60 * 1000 }, // 25-35 days
  quarterly: { min: 80 * 24 * 60 * 60 * 1000, max: 100 * 24 * 60 * 60 * 1000 }, // 80-100 days
  yearly: { min: 350 * 24 * 60 * 60 * 1000, max: 380 * 24 * 60 * 60 * 1000 }, // 350-380 days
};

/**
 * Main detection function for time-series patterns
 */
export function detectTimeSeriesPattern(
  results: Record<string, unknown>[],
  temporalColumns: string[],
  numericColumns: string[]
): TimeSeriesInfo {
  // Default: not a time series
  const defaultResult: TimeSeriesInfo = {
    isTimeSeries: false,
    temporalColumn: null,
    periodicity: null,
    avgIntervalMs: null,
    trendDirection: null,
    trendStrength: 0,
    hasTrend: false,
    confidence: 0,
  };

  if (!results || results.length < 3) {
    return defaultResult;
  }

  // Find the best temporal column
  const temporalColumn = findBestTemporalColumn(results, temporalColumns);
  if (!temporalColumn) {
    return defaultResult;
  }

  // Parse dates and sort
  const dateValues = parseDateValues(results, temporalColumn);
  if (dateValues.length < 3) {
    return defaultResult;
  }

  // Calculate intervals
  const intervals = calculateIntervals(dateValues);
  if (intervals.length === 0) {
    return defaultResult;
  }

  // Detect periodicity
  const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
  const periodicity = detectPeriodicity(avgInterval);

  // Calculate interval consistency (for confidence)
  const intervalVariance = calculateVariance(intervals);
  const intervalCV = Math.sqrt(intervalVariance) / avgInterval; // Coefficient of variation
  const intervalConsistency = Math.max(0, 1 - intervalCV);

  // Detect trend if numeric columns exist
  let trendDirection: 'up' | 'down' | 'stable' | null = null;
  let trendStrength = 0;
  let hasTrend = false;

  if (numericColumns.length > 0) {
    const trendResult = detectTrend(results, numericColumns[0]);
    trendDirection = trendResult.direction;
    trendStrength = trendResult.strength;
    hasTrend = trendResult.hasTrend;
  }

  // Calculate overall confidence
  const confidence = calculateConfidence(
    dateValues.length,
    intervalConsistency,
    periodicity !== null
  );

  return {
    isTimeSeries: confidence >= 0.5,
    temporalColumn,
    periodicity,
    avgIntervalMs: avgInterval,
    trendDirection,
    trendStrength,
    hasTrend,
    confidence,
  };
}

/**
 * Find the best temporal column from candidates
 */
function findBestTemporalColumn(
  results: Record<string, unknown>[],
  temporalColumns: string[]
): string | null {
  // First try provided temporal columns
  for (const col of temporalColumns) {
    if (isValidTemporalColumn(results, col)) {
      return col;
    }
  }

  // Then scan all columns for date-like patterns
  const allColumns = Object.keys(results[0] || {});
  for (const col of allColumns) {
    if (DATE_COLUMN_PATTERNS.some(p => p.test(col))) {
      if (isValidTemporalColumn(results, col)) {
        return col;
      }
    }
  }

  // Finally check for date-like values
  for (const col of allColumns) {
    const sample = results[0][col];
    if (typeof sample === 'string' && looksLikeDateValue(sample)) {
      if (isValidTemporalColumn(results, col)) {
        return col;
      }
    }
  }

  return null;
}

/**
 * Check if a column contains valid date values
 */
function isValidTemporalColumn(
  results: Record<string, unknown>[],
  column: string
): boolean {
  const parsedCount = results
    .map(r => parseDate(r[column]))
    .filter(d => d !== null).length;

  // At least 70% of values should be parseable dates
  return parsedCount >= results.length * 0.7;
}

/**
 * Check if a value looks like a date
 */
function looksLikeDateValue(value: string): boolean {
  return DATE_VALUE_PATTERNS.some(p => p.test(value));
}

/**
 * Parse date values from results
 */
function parseDateValues(
  results: Record<string, unknown>[],
  column: string
): Date[] {
  return results
    .map(r => parseDate(r[column]))
    .filter((d): d is Date => d !== null)
    .sort((a, b) => a.getTime() - b.getTime());
}

/**
 * Parse a single date value
 */
function parseDate(value: unknown): Date | null {
  if (value instanceof Date) {
    return isNaN(value.getTime()) ? null : value;
  }

  if (typeof value === 'number') {
    // Unix timestamp (seconds or milliseconds)
    const ts = value > 1e11 ? value : value * 1000;
    const date = new Date(ts);
    return isNaN(date.getTime()) ? null : date;
  }

  if (typeof value === 'string') {
    // Try ISO format first
    let date = new Date(value);
    if (!isNaN(date.getTime())) {
      return date;
    }

    // Try other common formats
    const usMatch = value.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
    if (usMatch) {
      date = new Date(`${usMatch[3]}-${usMatch[1]}-${usMatch[2]}`);
      if (!isNaN(date.getTime())) return date;
    }

    const euMatch = value.match(/^(\d{2})-(\d{2})-(\d{4})/);
    if (euMatch) {
      date = new Date(`${euMatch[3]}-${euMatch[2]}-${euMatch[1]}`);
      if (!isNaN(date.getTime())) return date;
    }
  }

  return null;
}

/**
 * Calculate intervals between consecutive dates
 */
function calculateIntervals(dates: Date[]): number[] {
  const intervals: number[] = [];
  for (let i = 1; i < dates.length; i++) {
    intervals.push(dates[i].getTime() - dates[i - 1].getTime());
  }
  return intervals;
}

/**
 * Detect periodicity from average interval
 */
function detectPeriodicity(
  avgIntervalMs: number
): 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | null {
  for (const [period, { min, max }] of Object.entries(PERIODICITY_THRESHOLDS)) {
    if (avgIntervalMs >= min && avgIntervalMs <= max) {
      return period as 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
    }
  }
  return null;
}

/**
 * Calculate variance for a set of values
 */
function calculateVariance(values: number[]): number {
  if (values.length === 0) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  return values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
}

/**
 * Detect trend in numeric data using simple linear regression
 */
function detectTrend(
  results: Record<string, unknown>[],
  column: string
): { direction: 'up' | 'down' | 'stable'; strength: number; hasTrend: boolean } {
  const values = results
    .map((r, i) => ({ x: i, y: Number(r[column]) }))
    .filter(v => !isNaN(v.y) && isFinite(v.y));

  if (values.length < 3) {
    return { direction: 'stable', strength: 0, hasTrend: false };
  }

  // Simple linear regression
  const n = values.length;
  const sumX = values.reduce((s, v) => s + v.x, 0);
  const sumY = values.reduce((s, v) => s + v.y, 0);
  const sumXY = values.reduce((s, v) => s + v.x * v.y, 0);
  const sumX2 = values.reduce((s, v) => s + v.x * v.x, 0);

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  // Calculate R-squared
  const meanY = sumY / n;
  const ssTotal = values.reduce((s, v) => s + Math.pow(v.y - meanY, 2), 0);
  const ssResidual = values.reduce((s, v) => {
    const predicted = slope * v.x + intercept;
    return s + Math.pow(v.y - predicted, 2);
  }, 0);

  const rSquared = ssTotal === 0 ? 0 : 1 - ssResidual / ssTotal;

  // Determine direction based on slope and R-squared
  const valueRange = Math.max(...values.map(v => v.y)) - Math.min(...values.map(v => v.y));
  const normalizedSlope = valueRange === 0 ? 0 : (slope * n) / valueRange;

  let direction: 'up' | 'down' | 'stable' = 'stable';
  if (rSquared >= 0.3) {
    if (normalizedSlope > 0.1) {
      direction = 'up';
    } else if (normalizedSlope < -0.1) {
      direction = 'down';
    }
  }

  return {
    direction,
    strength: rSquared,
    hasTrend: rSquared >= 0.3 && Math.abs(normalizedSlope) > 0.1,
  };
}

/**
 * Calculate overall confidence in time-series detection
 */
function calculateConfidence(
  dataPoints: number,
  intervalConsistency: number,
  hasRecognizedPeriodicity: boolean
): number {
  let confidence = 0;

  // Data points contribution (more is better, up to 30 points)
  confidence += Math.min(dataPoints / 30, 1) * 0.3;

  // Interval consistency contribution
  confidence += intervalConsistency * 0.4;

  // Periodicity recognition bonus
  if (hasRecognizedPeriodicity) {
    confidence += 0.3;
  }

  return Math.min(confidence, 1);
}
