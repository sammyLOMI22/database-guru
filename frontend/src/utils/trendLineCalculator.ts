/**
 * Trend Line Calculator
 *
 * Performs linear regression to calculate trend lines for charts.
 * Returns slope, intercept, R-squared, and calculated points.
 */

export interface TrendLineResult {
  /** Slope of the trend line */
  slope: number;
  /** Y-intercept of the trend line */
  intercept: number;
  /** R-squared value (coefficient of determination, 0-1) */
  rSquared: number;
  /** Calculated trend line points */
  points: { x: number; y: number }[];
  /** Direction of the trend */
  direction: 'up' | 'down' | 'stable';
  /** Standard error of the regression */
  standardError: number;
  /** 95% confidence interval width */
  confidenceInterval: number;
}

export interface DataPoint {
  x: number;
  y: number;
}

/**
 * Calculate a linear trend line using ordinary least squares regression
 *
 * @param values - Array of numeric values (y values, x is assumed to be index)
 * @returns TrendLineResult with slope, intercept, R-squared, and points
 */
export function calculateTrendLine(values: number[]): TrendLineResult {
  // Filter out invalid values
  const validValues = values.filter(v => !isNaN(v) && isFinite(v));

  if (validValues.length < 2) {
    return createEmptyResult(values.length);
  }

  // Create data points with x = index
  const dataPoints: DataPoint[] = validValues.map((y, x) => ({ x, y }));

  return calculateTrendLineFromPoints(dataPoints);
}

/**
 * Calculate a linear trend line from x,y data points
 *
 * @param points - Array of {x, y} data points
 * @returns TrendLineResult with slope, intercept, R-squared, and points
 */
export function calculateTrendLineFromPoints(points: DataPoint[]): TrendLineResult {
  if (points.length < 2) {
    return createEmptyResult(points.length);
  }

  const n = points.length;

  // Calculate sums for linear regression
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumX2 = 0;
  let sumY2 = 0;

  for (const { x, y } of points) {
    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumX2 += x * x;
    sumY2 += y * y;
  }

  // Calculate slope and intercept
  const denominator = n * sumX2 - sumX * sumX;

  if (denominator === 0) {
    // All x values are the same, can't calculate trend
    return createEmptyResult(n);
  }

  const slope = (n * sumXY - sumX * sumY) / denominator;
  const intercept = (sumY - slope * sumX) / n;

  // Calculate R-squared
  const meanY = sumY / n;

  let ssTotal = 0; // Total sum of squares
  let ssResidual = 0; // Residual sum of squares

  for (const { x, y } of points) {
    const predicted = slope * x + intercept;
    ssTotal += (y - meanY) ** 2;
    ssResidual += (y - predicted) ** 2;
  }

  const rSquared = ssTotal === 0 ? 0 : Math.max(0, 1 - ssResidual / ssTotal);

  // Calculate standard error
  const standardError = Math.sqrt(ssResidual / (n - 2));

  // Calculate 95% confidence interval width (approximate)
  const tValue = getTValue95(n - 2);
  const meanX = sumX / n;
  const sxx = points.reduce((sum, { x }) => sum + (x - meanX) ** 2, 0);
  const seSlope = standardError / Math.sqrt(sxx);
  const confidenceInterval = tValue * seSlope;

  // Generate trend line points
  const minX = Math.min(...points.map(p => p.x));
  const maxX = Math.max(...points.map(p => p.x));

  const trendPoints: DataPoint[] = [];
  const stepCount = Math.min(points.length, 100);

  for (let i = 0; i < stepCount; i++) {
    const x = minX + (maxX - minX) * (i / (stepCount - 1));
    const y = slope * x + intercept;
    trendPoints.push({ x, y });
  }

  // Determine direction
  let direction: 'up' | 'down' | 'stable' = 'stable';

  // Consider significant if slope creates > 5% change over the data range
  const valueRange = Math.max(...points.map(p => p.y)) - Math.min(...points.map(p => p.y));
  const xRange = maxX - minX;
  const predictedChange = Math.abs(slope * xRange);
  const relativeChange = valueRange === 0 ? 0 : predictedChange / valueRange;

  if (rSquared >= 0.1 && relativeChange >= 0.05) {
    direction = slope > 0 ? 'up' : 'down';
  }

  return {
    slope,
    intercept,
    rSquared,
    points: trendPoints,
    direction,
    standardError,
    confidenceInterval,
  };
}

/**
 * Calculate moving average trend
 *
 * @param values - Array of numeric values
 * @param windowSize - Size of the moving average window
 * @returns Array of smoothed values
 */
export function calculateMovingAverage(
  values: number[],
  windowSize: number = 3
): number[] {
  if (values.length < windowSize) {
    return values;
  }

  const result: number[] = [];
  const halfWindow = Math.floor(windowSize / 2);

  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - halfWindow);
    const end = Math.min(values.length, i + halfWindow + 1);

    const window = values.slice(start, end).filter(v => !isNaN(v) && isFinite(v));
    const avg = window.reduce((a, b) => a + b, 0) / window.length;

    result.push(avg);
  }

  return result;
}

/**
 * Calculate exponential moving average
 *
 * @param values - Array of numeric values
 * @param alpha - Smoothing factor (0 < alpha <= 1), higher = more weight on recent values
 * @returns Array of EMA values
 */
export function calculateEMA(values: number[], alpha: number = 0.3): number[] {
  if (values.length === 0) return [];

  const validValues = values.filter(v => !isNaN(v) && isFinite(v));
  if (validValues.length === 0) return [];

  const result: number[] = [validValues[0]];

  for (let i = 1; i < validValues.length; i++) {
    const ema = alpha * validValues[i] + (1 - alpha) * result[i - 1];
    result.push(ema);
  }

  return result;
}

/**
 * Calculate confidence band points for trend line
 *
 * @param trendResult - Result from calculateTrendLine
 * @param points - Original data points
 * @param level - Confidence level (default 0.95 for 95%)
 * @returns Upper and lower confidence band points
 */
export function calculateConfidenceBand(
  trendResult: TrendLineResult,
  points: DataPoint[],
  level: number = 0.95
): { upper: DataPoint[]; lower: DataPoint[] } {
  const { slope, intercept, standardError } = trendResult;
  const n = points.length;

  if (n < 3) {
    return {
      upper: trendResult.points,
      lower: trendResult.points,
    };
  }

  const tValue = getTValue(n - 2, level);
  const meanX = points.reduce((sum, p) => sum + p.x, 0) / n;
  const sxx = points.reduce((sum, p) => sum + (p.x - meanX) ** 2, 0);

  const upper: DataPoint[] = [];
  const lower: DataPoint[] = [];

  for (const { x } of trendResult.points) {
    const yPredicted = slope * x + intercept;

    // Standard error of prediction
    const sePrediction = standardError * Math.sqrt(
      1 + 1 / n + ((x - meanX) ** 2) / sxx
    );

    const margin = tValue * sePrediction;

    upper.push({ x, y: yPredicted + margin });
    lower.push({ x, y: yPredicted - margin });
  }

  return { upper, lower };
}

/**
 * Get t-value for 95% confidence interval
 */
function getTValue95(degreesOfFreedom: number): number {
  // Common t-values for 95% confidence
  const tTable: Record<number, number> = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    10: 2.228,
    15: 2.131,
    20: 2.086,
    30: 2.042,
    60: 2.000,
    120: 1.980,
  };

  if (degreesOfFreedom <= 0) return 1.96;
  if (degreesOfFreedom >= 120) return 1.96;

  // Find closest value
  const keys = Object.keys(tTable).map(Number).sort((a, b) => a - b);
  for (const key of keys) {
    if (degreesOfFreedom <= key) {
      return tTable[key];
    }
  }

  return 1.96; // Default to z-value for large samples
}

/**
 * Get t-value for given degrees of freedom and confidence level
 */
function getTValue(degreesOfFreedom: number, _level: number): number {
  // For simplicity, just use 95% table
  // A full implementation would include multiple confidence levels
  return getTValue95(degreesOfFreedom);
}

/**
 * Create empty result for edge cases
 */
function createEmptyResult(n: number): TrendLineResult {
  const points: DataPoint[] = n > 0
    ? [{ x: 0, y: 0 }, { x: n - 1, y: 0 }]
    : [];

  return {
    slope: 0,
    intercept: 0,
    rSquared: 0,
    points,
    direction: 'stable',
    standardError: 0,
    confidenceInterval: 0,
  };
}

/**
 * Format trend description for display
 */
export function formatTrendDescription(result: TrendLineResult): string {
  const { direction, rSquared } = result;

  if (rSquared < 0.1) {
    return 'No significant trend detected';
  }

  const strength = rSquared >= 0.7 ? 'strong' : rSquared >= 0.4 ? 'moderate' : 'weak';
  const dir = direction === 'up' ? 'upward' : direction === 'down' ? 'downward' : 'stable';

  if (direction === 'stable') {
    return 'Data shows a stable pattern';
  }

  return `${strength.charAt(0).toUpperCase() + strength.slice(1)} ${dir} trend (R² = ${rSquared.toFixed(2)})`;
}
