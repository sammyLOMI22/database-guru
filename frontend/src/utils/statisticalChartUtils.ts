/**
 * Statistical Chart Utilities
 *
 * Data preparation and calculations for statistical charts:
 * - Box Plot (quartiles, whiskers, outliers)
 * - Histogram (binning)
 * - Violin Plot (density estimation)
 * - Bubble Chart (3-variable scatter)
 */

export interface BoxPlotData {
  name: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers: number[];
  mean: number;
  stdDev: number;
}

export interface HistogramBin {
  x0: number;
  x1: number;
  count: number;
  frequency: number;
}

export interface ViolinData {
  name: string;
  values: number[];
  density: { x: number; y: number }[];
  boxPlot: BoxPlotData;
}

export interface BubblePoint {
  x: number;
  y: number;
  z: number;
  name?: string;
  originalRow?: Record<string, unknown>;
}

/**
 * Calculates box plot statistics for a set of values
 */
export function calculateBoxPlot(
  values: number[],
  name: string = 'Data'
): BoxPlotData {
  // Filter and sort values
  const sorted = values
    .filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v))
    .sort((a, b) => a - b);

  if (sorted.length === 0) {
    return {
      name,
      min: 0,
      q1: 0,
      median: 0,
      q3: 0,
      max: 0,
      outliers: [],
      mean: 0,
      stdDev: 0,
    };
  }

  const n = sorted.length;

  // Calculate quartiles
  const q1 = percentile(sorted, 25);
  const median = percentile(sorted, 50);
  const q3 = percentile(sorted, 75);
  const iqr = q3 - q1;

  // Calculate whisker bounds (1.5 * IQR)
  const lowerBound = q1 - 1.5 * iqr;
  const upperBound = q3 + 1.5 * iqr;

  // Find whisker endpoints (actual data points within bounds)
  const min = sorted.find(v => v >= lowerBound) ?? sorted[0];
  const max = [...sorted].reverse().find(v => v <= upperBound) ?? sorted[n - 1];

  // Identify outliers
  const outliers = sorted.filter(v => v < lowerBound || v > upperBound);

  // Calculate mean and standard deviation
  const mean = sorted.reduce((a, b) => a + b, 0) / n;
  const variance = sorted.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n;
  const stdDev = Math.sqrt(variance);

  return {
    name,
    min,
    q1,
    median,
    q3,
    max,
    outliers,
    mean,
    stdDev,
  };
}

/**
 * Calculates percentile value from sorted array
 */
function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  if (sorted.length === 1) return sorted[0];

  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;

  if (upper >= sorted.length) return sorted[sorted.length - 1];
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

/**
 * Prepares box plot data from grouped data
 */
export function prepareBoxPlotData(
  data: Record<string, unknown>[],
  categoryColumn: string,
  valueColumn: string
): BoxPlotData[] {
  // Group values by category
  const grouped = new Map<string, number[]>();

  for (const row of data) {
    const category = String(row[categoryColumn] ?? 'Unknown');
    const value = Number(row[valueColumn]);

    if (!isNaN(value) && isFinite(value)) {
      if (!grouped.has(category)) {
        grouped.set(category, []);
      }
      grouped.get(category)!.push(value);
    }
  }

  // Calculate box plot for each group
  return Array.from(grouped.entries()).map(([name, values]) =>
    calculateBoxPlot(values, name)
  );
}

/**
 * Creates histogram bins from numeric data
 */
export function createHistogram(
  values: number[],
  binCount?: number
): HistogramBin[] {
  // Filter valid values
  const valid = values.filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v));

  if (valid.length === 0) return [];

  const min = Math.min(...valid);
  const max = Math.max(...valid);

  // Determine bin count using Sturges' formula if not specified
  const numBins = binCount ?? Math.ceil(Math.log2(valid.length) + 1);
  const binWidth = (max - min) / numBins || 1;

  // Create bins
  const bins: HistogramBin[] = [];
  for (let i = 0; i < numBins; i++) {
    const x0 = min + i * binWidth;
    const x1 = min + (i + 1) * binWidth;
    bins.push({
      x0,
      x1,
      count: 0,
      frequency: 0,
    });
  }

  // Count values in each bin
  for (const value of valid) {
    const binIndex = Math.min(
      Math.floor((value - min) / binWidth),
      numBins - 1
    );
    bins[binIndex].count++;
  }

  // Calculate frequencies
  const total = valid.length;
  for (const bin of bins) {
    bin.frequency = bin.count / total;
  }

  return bins;
}

/**
 * Prepares histogram data from a column
 */
export function prepareHistogramData(
  data: Record<string, unknown>[],
  valueColumn: string,
  binCount?: number
): HistogramBin[] {
  const values = data
    .map(row => Number(row[valueColumn]))
    .filter(v => !isNaN(v) && isFinite(v));

  return createHistogram(values, binCount);
}

/**
 * Estimates kernel density for violin plot
 * Uses Gaussian kernel density estimation
 */
export function estimateDensity(
  values: number[],
  points: number = 50
): { x: number; y: number }[] {
  const valid = values.filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v));

  if (valid.length < 2) return [];

  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const range = max - min || 1;

  // Silverman's rule of thumb for bandwidth
  const n = valid.length;
  const stdDev = Math.sqrt(
    valid.reduce((sum, v) => sum + Math.pow(v - valid.reduce((a, b) => a + b, 0) / n, 2), 0) / n
  );
  const bandwidth = 1.06 * stdDev * Math.pow(n, -0.2);

  // Generate density points
  const density: { x: number; y: number }[] = [];
  const step = range / (points - 1);

  for (let i = 0; i < points; i++) {
    const x = min + i * step;
    let y = 0;

    // Gaussian kernel
    for (const v of valid) {
      const u = (x - v) / bandwidth;
      y += Math.exp(-0.5 * u * u) / Math.sqrt(2 * Math.PI);
    }

    y /= n * bandwidth;
    density.push({ x, y });
  }

  return density;
}

/**
 * Prepares violin plot data
 */
export function prepareViolinData(
  data: Record<string, unknown>[],
  categoryColumn: string,
  valueColumn: string
): ViolinData[] {
  // Group values by category
  const grouped = new Map<string, number[]>();

  for (const row of data) {
    const category = String(row[categoryColumn] ?? 'Unknown');
    const value = Number(row[valueColumn]);

    if (!isNaN(value) && isFinite(value)) {
      if (!grouped.has(category)) {
        grouped.set(category, []);
      }
      grouped.get(category)!.push(value);
    }
  }

  // Calculate violin data for each group
  return Array.from(grouped.entries()).map(([name, values]) => ({
    name,
    values,
    density: estimateDensity(values),
    boxPlot: calculateBoxPlot(values, name),
  }));
}

/**
 * Prepares bubble chart data
 */
export function prepareBubbleData(
  data: Record<string, unknown>[],
  xColumn: string,
  yColumn: string,
  zColumn: string,
  nameColumn?: string
): BubblePoint[] {
  const result: BubblePoint[] = [];

  for (const row of data) {
    const x = Number(row[xColumn]);
    const y = Number(row[yColumn]);
    const z = Number(row[zColumn]);

    if (isNaN(x) || isNaN(y) || isNaN(z)) continue;

    const point: BubblePoint = {
      x,
      y,
      z: Math.abs(z), // Size should be positive
      originalRow: row,
    };

    if (nameColumn) {
      point.name = String(row[nameColumn]);
    }

    result.push(point);
  }

  return result;
}

/**
 * Normalizes bubble sizes for display
 */
export function normalizeBubbleSizes(
  bubbles: BubblePoint[],
  minSize: number = 20,
  maxSize: number = 100
): BubblePoint[] {
  if (bubbles.length === 0) return [];

  const zValues = bubbles.map(b => b.z);
  const minZ = Math.min(...zValues);
  const maxZ = Math.max(...zValues);
  const range = maxZ - minZ || 1;

  return bubbles.map(b => ({
    ...b,
    z: minSize + ((b.z - minZ) / range) * (maxSize - minSize),
  }));
}

/**
 * Calculates summary statistics for a numeric array
 */
export function calculateSummaryStats(values: number[]): {
  count: number;
  sum: number;
  mean: number;
  median: number;
  mode: number | null;
  min: number;
  max: number;
  range: number;
  variance: number;
  stdDev: number;
  skewness: number;
} {
  const valid = values.filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v));

  if (valid.length === 0) {
    return {
      count: 0,
      sum: 0,
      mean: 0,
      median: 0,
      mode: null,
      min: 0,
      max: 0,
      range: 0,
      variance: 0,
      stdDev: 0,
      skewness: 0,
    };
  }

  const sorted = [...valid].sort((a, b) => a - b);
  const n = valid.length;
  const sum = valid.reduce((a, b) => a + b, 0);
  const mean = sum / n;
  const median = percentile(sorted, 50);

  // Calculate mode
  const counts = new Map<number, number>();
  let maxCount = 0;
  let mode: number | null = null;
  for (const v of valid) {
    const count = (counts.get(v) || 0) + 1;
    counts.set(v, count);
    if (count > maxCount) {
      maxCount = count;
      mode = v;
    }
  }
  if (maxCount === 1) mode = null; // No mode if all values unique

  const min = sorted[0];
  const max = sorted[n - 1];
  const range = max - min;

  const variance = valid.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / n;
  const stdDev = Math.sqrt(variance);

  // Calculate skewness
  const skewness = stdDev === 0
    ? 0
    : valid.reduce((sum, v) => sum + Math.pow((v - mean) / stdDev, 3), 0) / n;

  return {
    count: n,
    sum,
    mean,
    median,
    mode,
    min,
    max,
    range,
    variance,
    stdDev,
    skewness,
  };
}
