/**
 * Chart Auto-Detection Service
 *
 * Analyzes query result data and automatically detects the optimal chart type
 * with confidence scoring.
 */

export type ChartType = 'line' | 'bar' | 'pie' | 'table';

export interface ChartDetectionResult {
  type: ChartType;
  confidence: number; // 0.0-1.0
  reason: string;
  timeColumn?: string;
  categoryColumn?: string;
  valueColumns?: string[];
}

interface ColumnMetadata {
  name: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'unknown';
  distinctCount: number;
  hasNulls: boolean;
  sampleValues: any[];
}

/**
 * Detect the optimal chart type for the given data
 */
export function detectChartType(data: any[]): ChartDetectionResult {
  if (!data || data.length === 0) {
    return {
      type: 'table',
      confidence: 1.0,
      reason: 'No data to visualize',
    };
  }

  // Analyze columns
  const columns = analyzeColumns(data);
  const dateColumns = columns.filter(c => c.type === 'date');
  const numericColumns = columns.filter(c => c.type === 'number');
  const stringColumns = columns.filter(c => c.type === 'string');

  // Rule 1: Time-series line chart (highest priority)
  if (dateColumns.length > 0 && numericColumns.length >= 1 && numericColumns.length <= 5) {
    // Check if data is ordered by time column
    const timeCol = dateColumns[0];
    const isOrdered = isDataOrdered(data, timeCol.name);

    return {
      type: 'line',
      confidence: isOrdered ? 0.95 : 0.85,
      reason: `Detected time column '${timeCol.name}' with ${numericColumns.length} numeric value(s)`,
      timeColumn: timeCol.name,
      valueColumns: numericColumns.map(c => c.name),
    };
  }

  // Rule 2: Pie chart ONLY for 3-5 categories with exactly matching row count
  // Very restrictive: only when data.length == distinctCount (one row per category)
  // This ensures pie charts are only for summary data, not detailed listings
  if (
    stringColumns.length === 1 &&
    numericColumns.length === 1 &&
    stringColumns[0].distinctCount >= 3 &&
    stringColumns[0].distinctCount <= 5 &&
    data.length === stringColumns[0].distinctCount &&
    data.length <= 8
  ) {
    return {
      type: 'pie',
      confidence: 0.85,
      reason: `Small categorical data (${stringColumns[0].distinctCount} categories)`,
      categoryColumn: stringColumns[0].name,
      valueColumns: [numericColumns[0].name],
    };
  }

  // Rule 3: Bar chart for categorical data
  if (
    stringColumns.length === 1 &&
    numericColumns.length >= 1 &&
    numericColumns.length <= 3 &&
    data.length >= 2 &&
    data.length <= 50 &&
    stringColumns[0].distinctCount >= 2
  ) {
    return {
      type: 'bar',
      confidence: 0.80,
      reason: `Categorical data with ${numericColumns.length} numeric value(s)`,
      categoryColumn: stringColumns[0].name,
      valueColumns: numericColumns.map(c => c.name),
    };
  }

  // Rule 4: Fallback to table for complex/large datasets
  const reasons: string[] = [];
  if (data.length > 50) {
    reasons.push('Large dataset (>50 rows)');
  }
  if (columns.length > 10) {
    reasons.push('Many columns (>10)');
  }
  if (numericColumns.length === 0) {
    reasons.push('No numeric columns for visualization');
  }
  if (stringColumns.length === 0 && dateColumns.length === 0) {
    reasons.push('No categorical or time columns');
  }

  return {
    type: 'table',
    confidence: 0.5,
    reason: reasons.length > 0 ? reasons.join(', ') : 'Complex data structure',
  };
}

/**
 * Analyze columns in the dataset to determine types and metadata
 */
function analyzeColumns(data: any[]): ColumnMetadata[] {
  if (data.length === 0) return [];

  const firstRow = data[0];
  const columnNames = Object.keys(firstRow);

  return columnNames.map(name => {
    const values = data.map(row => row[name]);
    const nonNullValues = values.filter(v => v !== null && v !== undefined);
    const distinctValues = [...new Set(nonNullValues)];

    return {
      name,
      type: inferColumnType(nonNullValues),
      distinctCount: distinctValues.length,
      hasNulls: values.length !== nonNullValues.length,
      sampleValues: distinctValues.slice(0, 10),
    };
  });
}

/**
 * Infer column type from sample values
 */
function inferColumnType(values: any[]): ColumnMetadata['type'] {
  if (values.length === 0) return 'unknown';

  const sample = values.slice(0, Math.min(100, values.length));

  // Check for dates
  const dateCount = sample.filter(v => isDateValue(v)).length;
  if (dateCount / sample.length > 0.8) return 'date';

  // Check for numbers
  const numberCount = sample.filter(v => typeof v === 'number' && !isNaN(v)).length;
  if (numberCount / sample.length > 0.8) return 'number';

  // Check for booleans
  const boolCount = sample.filter(v => typeof v === 'boolean').length;
  if (boolCount / sample.length > 0.8) return 'boolean';

  // Default to string
  return 'string';
}

/**
 * Check if a value represents a date
 */
function isDateValue(value: any): boolean {
  if (value instanceof Date) return true;
  if (typeof value !== 'string') return false;

  // Check for ISO date format (YYYY-MM-DD)
  const isoDateRegex = /^\d{4}-\d{2}-\d{2}/;
  if (isoDateRegex.test(value)) return true;

  // Check for common date formats
  const dateFormats = [
    /^\d{1,2}\/\d{1,2}\/\d{2,4}/, // MM/DD/YYYY or DD/MM/YYYY
    /^\d{4}\/\d{2}\/\d{2}/,       // YYYY/MM/DD
    /^\d{2}-\d{2}-\d{4}/,         // DD-MM-YYYY
  ];

  return dateFormats.some(regex => regex.test(value));
}

/**
 * Check if data is ordered by a specific column
 */
function isDataOrdered(data: any[], columnName: string): boolean {
  if (data.length < 2) return true;

  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1][columnName];
    const curr = data[i][columnName];

    if (prev === null || prev === undefined || curr === null || curr === undefined) {
      continue;
    }

    // Convert to comparable values
    const prevTime = new Date(prev).getTime();
    const currTime = new Date(curr).getTime();

    if (!isNaN(prevTime) && !isNaN(currTime) && prevTime > currTime) {
      return false; // Found descending order
    }
  }

  return true;
}
