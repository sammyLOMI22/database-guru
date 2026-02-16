/**
 * Chart Intelligence Engine
 *
 * Advanced pattern detection and multi-chart recommendation system.
 * Extends basic chart detection with:
 * - Multi-chart scoring (returns top alternatives)
 * - Pattern detection (time-series, hierarchy, geo)
 * - Natural language explanations
 * - Trend and outlier detection
 * - Chart overlay suggestions (trend lines, confidence intervals)
 */

import { ChartType, classifyColumns } from './chartUtils';
import { detectTimeSeriesPattern, TimeSeriesInfo } from './timeSeriesDetector';
import { detectHierarchy, HierarchyInfo } from './hierarchyDetector';
import { detectGeoData, GeoInfo } from './geoDetector';
import { calculateTrendLine } from './trendLineCalculator';

/**
 * Extended chart recommendation with alternatives and NL explanations
 */
export interface IntelligentChartRecommendation {
  /** Primary recommended chart type */
  primaryChart: ChartType;
  /** Confidence score 0-100 */
  confidence: number;
  /** X-axis column */
  xColumn: string | null;
  /** Y-axis column */
  yColumn: string | null;
  /** Human-readable reason */
  reason: string;
  /** Natural language explanation for the user */
  nlExplanation: string;
  /** Alternative chart types with scores */
  alternatives: ChartAlternative[];
  /** Detected patterns in the data */
  patterns: DetectedPatterns;
  /** Suggested visual overlays */
  overlays: ChartOverlay[];
  /** Data insights for display */
  insights: DataInsight[];
}

export interface ChartAlternative {
  chartType: ChartType;
  score: number;
  reason: string;
}

export interface DetectedPatterns {
  timeSeries: TimeSeriesInfo | null;
  hierarchy: HierarchyInfo | null;
  geo: GeoInfo | null;
  hasOutliers: boolean;
  hasTrend: boolean;
  hasCorrelation: boolean;
}

export interface ChartOverlay {
  type: 'trendLine' | 'outlierMarker' | 'confidenceInterval' | 'average';
  enabled: boolean;
  data: Record<string, unknown>;
}

export interface DataInsight {
  type: 'trend' | 'outlier' | 'pattern' | 'correlation' | 'distribution';
  message: string;
  severity: 'info' | 'warning' | 'highlight';
}

export interface OutlierInfo {
  row: Record<string, unknown>;
  column: string;
  value: number;
  zScore: number;
  isHigh: boolean;
}

/**
 * Z-score threshold for outlier detection
 */
const OUTLIER_THRESHOLD = 2.0;

// ========== Phase 19.4: Adaptive Scoring Presets ==========

export type ScoringPreset = 'default' | 'business' | 'scientific';

interface ChartWeights {
  timeSeries: number;
  categoricalComparison: number;
  proportional: number;
  correlation: number;
  distribution: number;
  hierarchical: number;
}

const SCORING_PRESETS: Record<ScoringPreset, ChartWeights> = {
  default: {
    timeSeries: 1.0,
    categoricalComparison: 1.0,
    proportional: 1.0,
    correlation: 1.0,
    distribution: 1.0,
    hierarchical: 1.0,
  },
  business: {
    timeSeries: 1.2,
    categoricalComparison: 1.3,
    proportional: 1.2,
    correlation: 0.7,
    distribution: 0.5,
    hierarchical: 0.8,
  },
  scientific: {
    timeSeries: 1.0,
    categoricalComparison: 0.7,
    proportional: 0.6,
    correlation: 1.5,
    distribution: 1.5,
    hierarchical: 1.0,
  },
};

/**
 * Main analysis function - orchestrates all detection
 */
export function analyzeData(
  results: Record<string, unknown>[],
  statistics: Record<string, unknown> = {},
  question: string = '',
  preset: ScoringPreset = 'default'
): IntelligentChartRecommendation {
  // Default response for insufficient data
  if (!results || results.length < 2) {
    return createDefaultRecommendation(
      'Insufficient data for visualization (need at least 2 rows)'
    );
  }

  // Classify columns
  const classification = classifyColumns(results, statistics);
  const { numericColumns } = classification;

  // Detect patterns in parallel conceptually
  const patterns = detectPatterns(results, classification, statistics);

  // Score all chart types (with adaptive preset weights)
  const scores = scoreChartTypes(results, classification, patterns, statistics, preset);

  // Get the best chart type
  const sortedScores = Object.entries(scores)
    .map(([type, score]) => ({ type: type as ChartType, score }))
    .sort((a, b) => b.score - a.score);

  const primaryType = sortedScores[0].type;
  const primaryScore = sortedScores[0].score;

  // Determine columns for the primary chart (with interest scoring)
  const { xColumn, yColumn } = selectColumnsForChart(
    primaryType,
    classification,
    patterns,
    results
  );

  // Generate alternatives (top 3, excluding table if score is very low)
  const alternatives = sortedScores
    .slice(1, 4)
    .filter(s => s.score >= 20)
    .map(s => ({
      chartType: s.type,
      score: s.score,
      reason: generateChartReason(s.type, classification, patterns),
    }));

  // Generate natural language explanation
  const nlExplanation = generateNLExplanation(
    primaryType,
    primaryScore,
    classification,
    patterns,
    results.length
  );

  // Detect outliers and calculate overlays
  const outliers = detectOutliers(results, numericColumns);
  const overlays = generateOverlays(patterns, outliers, numericColumns, results);

  // Generate insights (context-aware if question provided)
  const insights = question
    ? generateContextAwareInsights(question, patterns, outliers, classification, results.length)
    : generateInsights(patterns, outliers, classification, results.length);

  return {
    primaryChart: primaryType,
    confidence: primaryScore,
    xColumn,
    yColumn,
    reason: generateChartReason(primaryType, classification, patterns),
    nlExplanation,
    alternatives,
    patterns,
    overlays,
    insights,
  };
}

/**
 * Detect various patterns in the data
 */
function detectPatterns(
  results: Record<string, unknown>[],
  classification: ReturnType<typeof classifyColumns>,
  statistics: Record<string, unknown>
): DetectedPatterns {
  const { numericColumns, categoricalColumns, temporalColumns } = classification;

  // Detect time-series patterns
  let timeSeries: TimeSeriesInfo | null = null;
  if (temporalColumns.length > 0 || results.length >= 5) {
    timeSeries = detectTimeSeriesPattern(results, temporalColumns, numericColumns);
  }

  // Detect hierarchical patterns
  let hierarchy: HierarchyInfo | null = null;
  if (categoricalColumns.length >= 2) {
    hierarchy = detectHierarchy(results, categoricalColumns);
  }

  // Detect geographic data
  let geo: GeoInfo | null = null;
  geo = detectGeoData(results, Object.keys(results[0] || {}));

  // Check for trends from statistics or calculate
  const hasTrend = !!(
    (statistics.trends as Record<string, unknown>)?.found ||
    (timeSeries?.hasTrend)
  );

  // Check for correlations
  const hasCorrelation = !!(
    (statistics.correlations as Record<string, unknown>)?.found
  );

  // Detect outliers
  const outliers = detectOutliers(results, numericColumns);
  const hasOutliers = outliers.length > 0;

  return {
    timeSeries,
    hierarchy,
    geo,
    hasOutliers,
    hasTrend,
    hasCorrelation,
  };
}

/**
 * Score each chart type based on data characteristics
 */
function scoreChartTypes(
  results: Record<string, unknown>[],
  classification: ReturnType<typeof classifyColumns>,
  patterns: DetectedPatterns,
  _statistics: Record<string, unknown>,
  preset: ScoringPreset = 'default'
): Record<ChartType, number> {
  const { numericColumns, categoricalColumns, temporalColumns } = classification;
  const rowCount = results.length;
  const w = SCORING_PRESETS[preset];

  const scores: Record<ChartType, number> = {
    bar: 0,
    line: 0,
    pie: 0,
    scatter: 0,
    table: 30, // Base score for table
    // Phase 10: Advanced Charts
    treemap: 0,
    sunburst: 0,
    boxplot: 0,
    histogram: 0,
    bubble: 0,
    area: 0,
  };

  // LINE CHART scoring
  if (patterns.timeSeries?.isTimeSeries) {
    scores.line += 40 * w.timeSeries;
    if (patterns.hasTrend) scores.line += 20 * w.timeSeries;
    if (patterns.timeSeries.periodicity) scores.line += 15 * w.timeSeries;
  }
  if (temporalColumns.length > 0 && numericColumns.length > 0) {
    scores.line += 25 * w.timeSeries;
  }
  // Penalize line for few data points
  if (rowCount < 5) scores.line -= 20;

  // BAR CHART scoring
  if (categoricalColumns.length > 0 && numericColumns.length > 0) {
    const uniqueCategories = getUniqueCount(categoricalColumns[0], results);
    if (uniqueCategories >= 2 && uniqueCategories <= 30) {
      scores.bar += 45 * w.categoricalComparison;
      if (uniqueCategories >= 3 && uniqueCategories <= 12) {
        scores.bar += 15 * w.categoricalComparison;
      }
    }
  }
  if (rowCount >= 2 && rowCount <= 20 && numericColumns.length > 0) {
    scores.bar += 15 * w.categoricalComparison;
  }

  // PIE CHART scoring
  if (categoricalColumns.length > 0 && numericColumns.length > 0) {
    const uniqueCategories = getUniqueCount(categoricalColumns[0], results);
    if (uniqueCategories >= 2 && uniqueCategories <= 12) {
      scores.pie += 45 * w.proportional;
      if (isProbablyProportional(results, numericColumns[0])) {
        scores.pie += 25 * w.proportional;
      }
    }
    if (uniqueCategories > 12) {
      scores.pie -= 30;
    }
  }

  // SCATTER PLOT scoring
  if (numericColumns.length >= 2) {
    scores.scatter += 40 * w.correlation;
    if (patterns.hasCorrelation) {
      scores.scatter += 25 * w.correlation;
    }
    if (rowCount >= 10) {
      scores.scatter += 15 * w.correlation;
    }
    if (numericColumns.length === 2 && categoricalColumns.length === 0) {
      scores.scatter += 25 * w.correlation;
    }
  }

  // TABLE scoring (fallback, not weighted)
  if (Object.keys(results[0] || {}).length > 5) {
    scores.table += 15;
  }
  if (rowCount > 50) {
    scores.table += 10;
  }

  // ========== PHASE 10: Advanced Chart Scoring ==========

  // AREA CHART scoring (time-series alternative to line)
  if (patterns.timeSeries?.isTimeSeries) {
    scores.area += 35 * w.timeSeries;
    if (patterns.hasTrend) scores.area += 15 * w.timeSeries;
    if (numericColumns.length === 1) scores.area += 10 * w.timeSeries;
  }
  if (temporalColumns.length > 0 && numericColumns.length > 0) {
    scores.area += 20 * w.timeSeries;
  }
  if (rowCount < 5) scores.area -= 20;

  // HISTOGRAM scoring (distribution analysis)
  if (numericColumns.length >= 1 && categoricalColumns.length === 0) {
    scores.histogram += 30 * w.distribution;
    if (rowCount >= 20) scores.histogram += 25 * w.distribution;
    if (rowCount >= 50) scores.histogram += 10 * w.distribution;
    if (numericColumns.length === 1) scores.histogram += 15 * w.distribution;
  }
  if (rowCount < 10) scores.histogram -= 30;

  // BOXPLOT scoring (statistical distribution by category)
  if (categoricalColumns.length >= 1 && numericColumns.length >= 1) {
    const uniqueCategories = getUniqueCount(categoricalColumns[0], results);
    if (uniqueCategories >= 2 && uniqueCategories <= 10) {
      scores.boxplot += 35 * w.distribution;
      if (rowCount >= uniqueCategories * 5) scores.boxplot += 20 * w.distribution;
    }
    if (uniqueCategories > 15) scores.boxplot -= 20;
  }
  if (rowCount < 10) scores.boxplot -= 25;

  // TREEMAP scoring (hierarchical data)
  if (patterns.hierarchy?.isHierarchical) {
    scores.treemap += 50 * w.hierarchical;
    if (patterns.hierarchy.maxDepth >= 2) scores.treemap += 15 * w.hierarchical;
  }
  if (categoricalColumns.length >= 2 && numericColumns.length >= 1) {
    scores.treemap += 25 * w.hierarchical;
    const uniqueCat1 = getUniqueCount(categoricalColumns[0], results);
    const uniqueCat2 = getUniqueCount(categoricalColumns[1], results);
    if (uniqueCat1 >= 2 && uniqueCat2 >= 2) scores.treemap += 15 * w.hierarchical;
  }

  // SUNBURST scoring (hierarchical data, radial alternative to treemap)
  if (patterns.hierarchy?.isHierarchical) {
    scores.sunburst += 45 * w.hierarchical;
    if (patterns.hierarchy.maxDepth >= 2) scores.sunburst += 20 * w.hierarchical;
  }
  if (categoricalColumns.length >= 2 && numericColumns.length >= 1) {
    scores.sunburst += 20 * w.hierarchical;
    const uniqueCat1 = getUniqueCount(categoricalColumns[0], results);
    if (uniqueCat1 >= 3 && uniqueCat1 <= 8) scores.sunburst += 15 * w.hierarchical;
  }

  // BUBBLE CHART scoring (three-dimensional scatter)
  if (numericColumns.length >= 3) {
    scores.bubble += 40 * w.correlation;
    if (patterns.hasCorrelation) scores.bubble += 20 * w.correlation;
    if (rowCount >= 5 && rowCount <= 50) scores.bubble += 15 * w.correlation;
  } else if (numericColumns.length >= 2 && categoricalColumns.length >= 1) {
    scores.bubble += 25 * w.correlation;
  }

  // Normalize scores to 0-100
  const maxScore = Math.max(...Object.values(scores), 1);
  for (const type of Object.keys(scores) as ChartType[]) {
    scores[type] = Math.round((scores[type] / maxScore) * 100);
  }

  return scores;
}

// ========== Phase 19.4: Column Interest Scoring ==========

const INTERESTING_KEYWORDS = ['revenue', 'amount', 'total', 'count', 'sales', 'profit', 'rate', 'price', 'cost', 'value'];
const BORING_KEYWORDS = ['id', 'key', 'uuid', 'guid', 'index', '_id', 'pk'];

export function scoreColumnInterest(
  column: string,
  results: Record<string, unknown>[]
): number {
  let score = 50; // Base score

  const values = results
    .map(r => Number(r[column]))
    .filter(v => !isNaN(v) && isFinite(v));

  if (values.length === 0) return 0;

  // Coefficient of variation: high variance = interesting
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  if (mean !== 0) {
    const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
    const cv = Math.sqrt(variance) / Math.abs(mean);
    score += Math.min(cv * 30, 25);
  }

  // Name heuristics
  const colLower = column.toLowerCase();
  if (INTERESTING_KEYWORDS.some(kw => colLower.includes(kw))) score += 20;
  if (BORING_KEYWORDS.some(kw => colLower === kw || colLower.endsWith('_' + kw))) score -= 40;

  // Null penalty
  const nullCount = results.filter(r => r[column] == null).length;
  const nullRate = nullCount / results.length;
  score -= nullRate * 20;

  return Math.max(0, Math.min(100, score));
}

function pickBestNumericColumn(
  numericColumns: string[],
  results: Record<string, unknown>[]
): string | null {
  if (numericColumns.length === 0) return null;
  if (numericColumns.length === 1) return numericColumns[0];

  return numericColumns
    .map(col => ({ col, score: scoreColumnInterest(col, results) }))
    .sort((a, b) => b.score - a.score)[0].col;
}

/**
 * Select optimal columns for the given chart type
 */
export function selectColumnsForChart(
  chartType: ChartType,
  classification: ReturnType<typeof classifyColumns>,
  _patterns: DetectedPatterns,
  results: Record<string, unknown>[]
): { xColumn: string | null; yColumn: string | null } {
  const { numericColumns, categoricalColumns, temporalColumns } = classification;
  const bestNumeric = pickBestNumericColumn(numericColumns, results);

  switch (chartType) {
    case 'line':
      return {
        xColumn: temporalColumns[0] || categoricalColumns[0] || null,
        yColumn: bestNumeric,
      };

    case 'scatter': {
      // Pick two most interesting numeric columns
      const ranked = numericColumns
        .map(col => ({ col, score: scoreColumnInterest(col, results) }))
        .sort((a, b) => b.score - a.score);
      return {
        xColumn: ranked[0]?.col || null,
        yColumn: ranked[1]?.col || ranked[0]?.col || null,
      };
    }

    case 'pie':
    case 'bar':
      return {
        xColumn: categoricalColumns[0] || Object.keys(results[0] || {})[0] || null,
        yColumn: bestNumeric,
      };

    case 'area':
      return {
        xColumn: temporalColumns[0] || categoricalColumns[0] || null,
        yColumn: bestNumeric,
      };

    case 'histogram':
      return {
        xColumn: null,
        yColumn: bestNumeric,
      };

    case 'boxplot':
      return {
        xColumn: categoricalColumns[0] || null,
        yColumn: bestNumeric,
      };

    case 'treemap':
    case 'sunburst':
      return {
        xColumn: categoricalColumns[0] || null,
        yColumn: bestNumeric,
      };

    case 'bubble': {
      const ranked = numericColumns
        .map(col => ({ col, score: scoreColumnInterest(col, results) }))
        .sort((a, b) => b.score - a.score);
      return {
        xColumn: ranked[0]?.col || null,
        yColumn: ranked[1]?.col || ranked[0]?.col || null,
      };
    }

    default:
      return { xColumn: null, yColumn: null };
  }
}

/**
 * Generate human-readable reason for chart selection
 */
function generateChartReason(
  chartType: ChartType,
  classification: ReturnType<typeof classifyColumns>,
  patterns: DetectedPatterns
): string {
  const { categoricalColumns } = classification;

  switch (chartType) {
    case 'line':
      if (patterns.timeSeries?.isTimeSeries) {
        return patterns.hasTrend
          ? 'Time-series data with detected trend'
          : 'Time-series data detected';
      }
      return 'Sequential data suitable for line chart';

    case 'bar':
      if (categoricalColumns.length > 0) {
        return `Categorical comparison across ${categoricalColumns[0]}`;
      }
      return 'Data suitable for categorical comparison';

    case 'pie':
      return 'Distribution data ideal for pie chart';

    case 'scatter':
      if (patterns.hasCorrelation) {
        return 'Correlation detected between numeric columns';
      }
      return 'Two numeric columns suitable for scatter plot';

    case 'table':
      return 'Data best viewed as table';

    // Phase 10: Advanced Charts
    case 'area':
      if (patterns.timeSeries?.isTimeSeries) {
        return 'Time-series data ideal for area chart';
      }
      return 'Sequential data suitable for area visualization';

    case 'histogram':
      return 'Numeric distribution ideal for histogram';

    case 'boxplot':
      return 'Statistical distribution comparison across categories';

    case 'treemap':
      if (patterns.hierarchy?.isHierarchical) {
        return 'Hierarchical data detected - treemap shows nested proportions';
      }
      return 'Categorical breakdown suitable for treemap';

    case 'sunburst':
      if (patterns.hierarchy?.isHierarchical) {
        return 'Hierarchical data detected - sunburst shows radial breakdown';
      }
      return 'Nested categories ideal for sunburst chart';

    case 'bubble':
      if (patterns.hasCorrelation) {
        return 'Multi-dimensional correlation shown with bubble sizes';
      }
      return 'Three numeric dimensions suitable for bubble chart';

    default:
      return 'Default visualization';
  }
}

/**
 * Generate natural language explanation for the user
 */
function generateNLExplanation(
  chartType: ChartType,
  confidence: number,
  classification: ReturnType<typeof classifyColumns>,
  patterns: DetectedPatterns,
  rowCount: number
): string {
  const parts: string[] = [];

  // Describe the data
  const numCols = classification.numericColumns.length;
  const catCols = classification.categoricalColumns.length;
  const tempCols = classification.temporalColumns.length;

  parts.push(`Your data has ${rowCount} rows`);

  if (tempCols > 0) {
    parts.push('with time-based columns');
  } else if (catCols > 0 && numCols > 0) {
    parts.push('with categorical and numeric data');
  } else if (numCols >= 2) {
    parts.push('with multiple numeric columns');
  }

  // Explain the recommendation
  switch (chartType) {
    case 'line':
      if (patterns.hasTrend) {
        parts.push('- I detected an upward/downward trend, making a line chart ideal');
      } else {
        parts.push('- a line chart works well for showing changes over time');
      }
      break;

    case 'bar':
      parts.push('- a bar chart is great for comparing values across categories');
      break;

    case 'pie':
      parts.push('- a pie chart shows how parts make up a whole');
      break;

    case 'scatter':
      if (patterns.hasCorrelation) {
        parts.push('- I found a correlation between columns, scatter plot will show the relationship');
      } else {
        parts.push('- a scatter plot reveals patterns between two numeric values');
      }
      break;

    case 'table':
      parts.push('- the data is best viewed as a table for detailed inspection');
      break;

    // Phase 10: Advanced Charts
    case 'area':
      if (patterns.hasTrend) {
        parts.push('- an area chart emphasizes the magnitude of change over time');
      } else {
        parts.push('- an area chart shows cumulative values effectively');
      }
      break;

    case 'histogram':
      parts.push('- a histogram shows the distribution of values across ranges');
      break;

    case 'boxplot':
      parts.push('- a box plot compares statistical distributions across categories');
      break;

    case 'treemap':
      parts.push('- a treemap shows hierarchical proportions in nested rectangles');
      break;

    case 'sunburst':
      parts.push('- a sunburst chart displays hierarchy as concentric rings');
      break;

    case 'bubble':
      parts.push('- a bubble chart shows relationships between three numeric values');
      break;
  }

  // Add confidence note
  if (confidence >= 80) {
    parts.push('(high confidence)');
  } else if (confidence >= 50) {
    parts.push('(try the alternatives if this doesn\'t look right)');
  }

  return parts.join(' ');
}

/**
 * Detect statistical outliers using z-score
 */
export function detectOutliers(
  results: Record<string, unknown>[],
  numericColumns: string[]
): OutlierInfo[] {
  const outliers: OutlierInfo[] = [];

  for (const column of numericColumns) {
    const values = results
      .map(r => Number(r[column]))
      .filter(v => !isNaN(v) && isFinite(v));

    if (values.length < 5) continue;

    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
    const stdDev = Math.sqrt(variance);

    if (stdDev === 0) continue;

    results.forEach((row) => {
      const value = Number(row[column]);
      if (isNaN(value) || !isFinite(value)) return;

      const zScore = (value - mean) / stdDev;
      if (Math.abs(zScore) >= OUTLIER_THRESHOLD) {
        outliers.push({
          row,
          column,
          value,
          zScore,
          isHigh: zScore > 0,
        });
      }
    });
  }

  return outliers;
}

/**
 * Generate chart overlays based on patterns
 */
function generateOverlays(
  patterns: DetectedPatterns,
  outliers: OutlierInfo[],
  numericColumns: string[],
  results: Record<string, unknown>[]
): ChartOverlay[] {
  const overlays: ChartOverlay[] = [];

  // Trend line overlay
  if (patterns.hasTrend && numericColumns.length > 0) {
    const values = results.map((r, i) => ({
      x: i,
      y: Number(r[numericColumns[0]]) || 0,
    }));

    const trendLine = calculateTrendLine(values.map(v => v.y));

    overlays.push({
      type: 'trendLine',
      enabled: true,
      data: {
        slope: trendLine.slope,
        intercept: trendLine.intercept,
        rSquared: trendLine.rSquared,
        points: trendLine.points,
      },
    });
  }

  // Outlier markers
  if (outliers.length > 0) {
    overlays.push({
      type: 'outlierMarker',
      enabled: true,
      data: {
        outliers: outliers.map(o => ({
          column: o.column,
          value: o.value,
          zScore: o.zScore,
          isHigh: o.isHigh,
        })),
      },
    });
  }

  // Average line
  if (numericColumns.length > 0) {
    const values = results.map(r => Number(r[numericColumns[0]])).filter(v => !isNaN(v));
    const avg = values.reduce((a, b) => a + b, 0) / values.length;

    overlays.push({
      type: 'average',
      enabled: false, // Disabled by default
      data: { value: avg, column: numericColumns[0] },
    });
  }

  return overlays;
}

// ========== Phase 19.4: Context-Aware Insights ==========

function generateContextAwareInsights(
  question: string,
  patterns: DetectedPatterns,
  outliers: OutlierInfo[],
  classification: ReturnType<typeof classifyColumns>,
  rowCount: number
): DataInsight[] {
  const baseInsights = generateInsights(patterns, outliers, classification, rowCount);
  if (!question) return baseInsights;

  const q = question.toLowerCase();
  const reordered = [...baseInsights];

  // Prioritize trend insights for trend-related questions
  if (/trend|over time|growth|decline|change/.test(q)) {
    const trendIdx = reordered.findIndex(i => i.type === 'trend');
    if (trendIdx > 0) {
      const [trend] = reordered.splice(trendIdx, 1);
      trend.severity = 'highlight';
      reordered.unshift(trend);
    } else if (trendIdx === 0) {
      reordered[0].severity = 'highlight';
    } else if (trendIdx === -1 && patterns.hasTrend) {
      reordered.unshift({
        type: 'trend',
        message: 'Trend detected in the data matching your question',
        severity: 'highlight',
      });
    }
  }

  // Prioritize outlier insights for anomaly-related questions
  if (/outlier|unusual|anomal|extreme|spike/.test(q)) {
    const outlierIdx = reordered.findIndex(i => i.type === 'outlier');
    if (outlierIdx > 0) {
      const [outlierInsight] = reordered.splice(outlierIdx, 1);
      outlierInsight.severity = 'highlight';
      reordered.unshift(outlierInsight);
    } else if (outlierIdx === 0) {
      reordered[0].severity = 'highlight';
    } else if (outlierIdx === -1 && outliers.length > 0) {
      reordered.unshift({
        type: 'outlier',
        message: `${outliers.length} outlier(s) found relevant to your query`,
        severity: 'highlight',
      });
    }
  }

  // Add distribution insight for comparison questions
  if (/compar|vs|versus|difference|between/.test(q)) {
    const hasDistribution = reordered.some(i => i.type === 'distribution');
    if (!hasDistribution) {
      reordered.push({
        type: 'distribution',
        message: 'Data shows variation across categories relevant for comparison',
        severity: 'info',
      });
    }
  }

  // Add correlation insight for relationship questions
  if (/correlat|relat|affect|impact|depend/.test(q)) {
    const corrIdx = reordered.findIndex(i => i.type === 'correlation');
    if (corrIdx > 0) {
      const [corr] = reordered.splice(corrIdx, 1);
      corr.severity = 'highlight';
      reordered.unshift(corr);
    }
  }

  return reordered;
}

/**
 * Generate data insights for display
 */
function generateInsights(
  patterns: DetectedPatterns,
  outliers: OutlierInfo[],
  _classification: ReturnType<typeof classifyColumns>,
  _rowCount: number
): DataInsight[] {
  const insights: DataInsight[] = [];

  // Trend insight
  if (patterns.hasTrend && patterns.timeSeries) {
    const direction = patterns.timeSeries.trendDirection || 'detected';
    insights.push({
      type: 'trend',
      message: `${direction.charAt(0).toUpperCase() + direction.slice(1)} trend detected in the data`,
      severity: 'highlight',
    });
  }

  // Outlier insight
  if (outliers.length > 0) {
    const highCount = outliers.filter(o => o.isHigh).length;
    const lowCount = outliers.filter(o => !o.isHigh).length;

    let message = `Found ${outliers.length} outlier(s)`;
    if (highCount > 0 && lowCount > 0) {
      message += ` (${highCount} high, ${lowCount} low)`;
    } else if (highCount > 0) {
      message += ' above the norm';
    } else {
      message += ' below the norm';
    }

    insights.push({
      type: 'outlier',
      message,
      severity: 'warning',
    });
  }

  // Periodicity insight
  if (patterns.timeSeries?.periodicity) {
    insights.push({
      type: 'pattern',
      message: `Data shows ${patterns.timeSeries.periodicity} periodicity`,
      severity: 'info',
    });
  }

  // Correlation insight
  if (patterns.hasCorrelation) {
    insights.push({
      type: 'correlation',
      message: 'Strong correlation detected between numeric columns',
      severity: 'highlight',
    });
  }

  // Geographic insight
  if (patterns.geo?.isGeographic) {
    insights.push({
      type: 'pattern',
      message: `Geographic data detected (${patterns.geo.type})`,
      severity: 'info',
    });
  }

  return insights;
}

/**
 * Helper: Get unique count for a column
 */
function getUniqueCount(column: string, results: Record<string, unknown>[]): number {
  const uniqueValues = new Set(results.map(r => r[column]));
  return uniqueValues.size;
}

/**
 * Helper: Check if values might be proportional (for pie charts)
 */
function isProbablyProportional(results: Record<string, unknown>[], column: string): boolean {
  const values = results.map(r => Number(r[column])).filter(v => !isNaN(v) && v >= 0);
  if (values.length === 0) return false;

  const sum = values.reduce((a, b) => a + b, 0);

  // Check if sum is close to 100 (percentages) or 1 (fractions)
  return (
    (sum >= 99 && sum <= 101) ||
    (sum >= 0.99 && sum <= 1.01)
  );
}

/**
 * Create default recommendation for edge cases
 */
function createDefaultRecommendation(reason: string): IntelligentChartRecommendation {
  return {
    primaryChart: 'table',
    confidence: 100,
    xColumn: null,
    yColumn: null,
    reason,
    nlExplanation: reason,
    alternatives: [],
    patterns: {
      timeSeries: null,
      hierarchy: null,
      geo: null,
      hasOutliers: false,
      hasTrend: false,
      hasCorrelation: false,
    },
    overlays: [],
    insights: [],
  };
}
