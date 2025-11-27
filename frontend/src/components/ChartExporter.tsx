/**
 * ChartExporter Utility
 *
 * Provides export functionality for charts (PNG, SVG, CSV).
 * Can be used as a standalone component or utility functions.
 */

import { RefObject } from 'react';

interface ChartExporterProps {
  data: any[];
  chartRef?: RefObject<HTMLDivElement>;
  filename?: string;
}

export default function ChartExporter({
  data,
  chartRef,
  filename = 'chart',
}: ChartExporterProps) {
  const handleExportPNG = async () => {
    if (!chartRef?.current) {
      console.error('Chart ref not available');
      return;
    }

    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(chartRef.current, {
        backgroundColor: '#ffffff',
        scale: 2, // Higher quality
      });

      const link = document.createElement('a');
      link.download = `${filename}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('Failed to export PNG:', error);
      alert('Export failed. Make sure html2canvas is installed.');
    }
  };

  const handleExportSVG = async () => {
    if (!chartRef?.current) {
      console.error('Chart ref not available');
      return;
    }

    // Find SVG element in the chart
    const svgElement = chartRef.current.querySelector('svg');
    if (!svgElement) {
      console.error('No SVG found in chart');
      return;
    }

    const svgData = new XMLSerializer().serializeToString(svgElement);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.download = `${filename}.svg`;
    link.href = url;
    link.click();

    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!data || data.length === 0) {
      console.error('No data to export');
      return;
    }

    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.download = `${filename}.csv`;
    link.href = url;
    link.click();

    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleExportPNG}
        className="px-3 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        title="Export as PNG image"
      >
        PNG
      </button>
      <button
        onClick={handleExportSVG}
        className="px-3 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        title="Export as SVG vector"
      >
        SVG
      </button>
      <button
        onClick={handleExportCSV}
        className="px-3 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        title="Export data as CSV"
      >
        CSV
      </button>
    </div>
  );
}

/**
 * Convert data array to CSV string
 */
function convertToCSV(data: any[]): string {
  if (data.length === 0) return '';

  const headers = Object.keys(data[0]);
  const csvRows = [];

  // Add header row
  csvRows.push(headers.map(escapeCSVValue).join(','));

  // Add data rows
  for (const row of data) {
    const values = headers.map((header) => {
      const value = row[header];
      return escapeCSVValue(value);
    });
    csvRows.push(values.join(','));
  }

  return csvRows.join('\n');
}

/**
 * Escape CSV value (handle quotes, commas, newlines)
 */
function escapeCSVValue(value: any): string {
  if (value === null || value === undefined) return '';

  const stringValue = String(value);

  // If value contains comma, quote, or newline, wrap in quotes and escape quotes
  if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }

  return stringValue;
}

/**
 * Utility functions for programmatic export (can be used without component)
 */
export const exportUtils = {
  exportCSV: (data: any[], filename: string = 'export') => {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${filename}.csv`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  },

  exportJSON: (data: any[], filename: string = 'export') => {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${filename}.json`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  },
};
