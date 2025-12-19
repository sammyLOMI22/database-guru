/**
 * Data Export Utilities
 *
 * Functions for exporting query results to CSV and JSON formats.
 */

export interface ExportOptions {
  filename?: string;
  includeHeaders?: boolean;
  delimiter?: string;
}

export interface JSONExportMetadata {
  query?: string;
  sql?: string;
  timestamp?: string;
  rowCount: number;
  connectionName?: string;
  databaseType?: string;
}

/**
 * Escapes a CSV field to handle special characters
 */
function escapeCSVField(field: string): string {
  if (field === null || field === undefined) {
    return '';
  }
  const str = String(field);
  // Escape if contains comma, quote, or newline
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Triggers a file download in the browser
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Generates a default filename with timestamp
 */
function generateFilename(prefix: string = 'query-results'): string {
  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-');
  return `${prefix}-${dateStr}-${timeStr}`;
}

/**
 * Exports data to CSV format
 *
 * @param data - Array of records to export
 * @param options - Export configuration options
 */
export function exportToCSV(
  data: Record<string, unknown>[],
  options: ExportOptions = {}
): void {
  const {
    filename,
    includeHeaders = true,
    delimiter = ','
  } = options;

  if (!data || data.length === 0) {
    console.warn('No data to export');
    return;
  }

  const headers = Object.keys(data[0]);
  const rows: string[] = [];

  // Add header row
  if (includeHeaders) {
    rows.push(headers.map(h => escapeCSVField(h)).join(delimiter));
  }

  // Add data rows
  for (const row of data) {
    const values = headers.map(h => escapeCSVField(String(row[h] ?? '')));
    rows.push(values.join(delimiter));
  }

  const csvContent = rows.join('\n');
  const finalFilename = filename || generateFilename();
  downloadFile(csvContent, `${finalFilename}.csv`, 'text/csv;charset=utf-8;');
}

/**
 * Exports data to JSON format with metadata
 *
 * @param data - Array of records to export
 * @param metadata - Additional metadata to include in export
 * @param filename - Optional custom filename
 */
export function exportToJSON(
  data: Record<string, unknown>[],
  metadata: JSONExportMetadata,
  filename?: string
): void {
  if (!data || data.length === 0) {
    console.warn('No data to export');
    return;
  }

  const exportData = {
    metadata: {
      ...metadata,
      exportedAt: new Date().toISOString(),
      totalRows: data.length,
    },
    columns: Object.keys(data[0]),
    data,
  };

  const jsonContent = JSON.stringify(exportData, null, 2);
  const finalFilename = filename || generateFilename();
  downloadFile(jsonContent, `${finalFilename}.json`, 'application/json');
}

/**
 * Copies data to clipboard as tab-separated values (for pasting into spreadsheets)
 */
export async function copyToClipboard(
  data: Record<string, unknown>[]
): Promise<boolean> {
  if (!data || data.length === 0) {
    return false;
  }

  try {
    const headers = Object.keys(data[0]);
    const rows: string[] = [];

    // Header row
    rows.push(headers.join('\t'));

    // Data rows
    for (const row of data) {
      const values = headers.map(h => String(row[h] ?? ''));
      rows.push(values.join('\t'));
    }

    const tsvContent = rows.join('\n');
    await navigator.clipboard.writeText(tsvContent);
    return true;
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
}

/**
 * Formats a number for display (handles large numbers, decimals)
 */
export function formatNumber(value: number): string {
  if (Number.isInteger(value)) {
    return value.toLocaleString();
  }
  // Limit decimal places for floating point
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

/**
 * Truncates a string for display
 */
export function truncateString(str: string, maxLength: number = 50): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength - 3) + '...';
}

/**
 * Database result type for combined exports
 */
export interface DatabaseResultForExport {
  connection_id: number;
  connection_name: string;
  database_type: string;
  results?: Record<string, unknown>[] | null;
  success: boolean;
  sql: string;
}

/**
 * Exports combined data from multiple databases as stacked CSV
 * Adds a 'database_name' column to identify the source database
 *
 * @param results - Array of database query results
 * @param filename - Optional custom filename
 */
export function exportCombinedCSV(
  results: DatabaseResultForExport[],
  filename?: string
): void {
  // Filter successful results with data
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );

  if (successfulResults.length === 0) {
    console.warn('No data to export');
    return;
  }

  // Get all unique columns across all databases
  const allColumns = new Set<string>();
  allColumns.add('database_name'); // Add source column first

  for (const result of successfulResults) {
    if (result.results && result.results.length > 0) {
      Object.keys(result.results[0]).forEach((col) => allColumns.add(col));
    }
  }

  const headers = Array.from(allColumns);
  const rows: string[] = [];

  // Add header row
  rows.push(headers.map((h) => escapeCSVField(h)).join(','));

  // Add data rows from all databases
  for (const result of successfulResults) {
    if (result.results) {
      for (const row of result.results) {
        const values = headers.map((h) => {
          if (h === 'database_name') {
            return escapeCSVField(result.connection_name);
          }
          return escapeCSVField(String(row[h] ?? ''));
        });
        rows.push(values.join(','));
      }
    }
  }

  const csvContent = rows.join('\n');
  const finalFilename = filename || generateFilename('multi-db-results');
  downloadFile(csvContent, `${finalFilename}.csv`, 'text/csv;charset=utf-8;');
}

/**
 * Exports combined data from multiple databases as stacked JSON
 *
 * @param results - Array of database query results
 * @param question - Original query question
 * @param filename - Optional custom filename
 */
export function exportCombinedJSON(
  results: DatabaseResultForExport[],
  question?: string,
  filename?: string
): void {
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );

  if (successfulResults.length === 0) {
    console.warn('No data to export');
    return;
  }

  const exportData = {
    metadata: {
      question,
      exportedAt: new Date().toISOString(),
      databaseCount: successfulResults.length,
      totalRows: successfulResults.reduce(
        (sum, r) => sum + (r.results?.length || 0),
        0
      ),
    },
    databases: successfulResults.map((r) => ({
      name: r.connection_name,
      type: r.database_type,
      sql: r.sql,
      rowCount: r.results?.length || 0,
      columns: r.results && r.results.length > 0 ? Object.keys(r.results[0]) : [],
      data: r.results,
    })),
  };

  const jsonContent = JSON.stringify(exportData, null, 2);
  const finalFilename = filename || generateFilename('multi-db-results');
  downloadFile(jsonContent, `${finalFilename}.json`, 'application/json');
}

/**
 * Exports each database's results as separate files in a ZIP archive
 *
 * @param results - Array of database query results
 * @param format - Export format ('csv' or 'json')
 * @param filename - Optional custom filename for ZIP
 */
export async function exportSeparateFiles(
  results: DatabaseResultForExport[],
  format: 'csv' | 'json' = 'csv',
  filename?: string
): Promise<void> {
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );

  if (successfulResults.length === 0) {
    console.warn('No data to export');
    return;
  }

  // Dynamic import of jszip
  const JSZip = (await import('jszip')).default;
  const zip = new JSZip();

  for (const result of successfulResults) {
    if (!result.results || result.results.length === 0) continue;

    const safeName = result.connection_name.replace(/[^a-zA-Z0-9-_]/g, '_');

    if (format === 'csv') {
      const headers = Object.keys(result.results[0]);
      const rows: string[] = [];
      rows.push(headers.map((h) => escapeCSVField(h)).join(','));

      for (const row of result.results) {
        const values = headers.map((h) => escapeCSVField(String(row[h] ?? '')));
        rows.push(values.join(','));
      }

      zip.file(`${safeName}.csv`, rows.join('\n'));
    } else {
      const jsonData = {
        metadata: {
          database: result.connection_name,
          type: result.database_type,
          sql: result.sql,
          exportedAt: new Date().toISOString(),
          rowCount: result.results.length,
        },
        columns: Object.keys(result.results[0]),
        data: result.results,
      };
      zip.file(`${safeName}.json`, JSON.stringify(jsonData, null, 2));
    }
  }

  // Generate and download ZIP
  const zipBlob = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(zipBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename || generateFilename('multi-db-export')}.zip`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
