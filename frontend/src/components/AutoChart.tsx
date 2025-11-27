/**
 * AutoChart Component
 *
 * Smart chart wrapper that automatically detects and renders the optimal chart type
 * for query result data using confidence-based detection.
 */

import { useState, useMemo, useRef } from 'react';
import { detectChartType, ChartType } from '../services/chartDetector';
import TimeSeriesChart from './TimeSeriesChart';
import CategoryBarChart from './CategoryBarChart';
import PieChartComponent from './PieChartComponent';
import ChartExporter from './ChartExporter';

interface AutoChartProps {
  data: any[];
  title?: string;
  allowManualOverride?: boolean;
  showExporter?: boolean;
  onChartTypeChange?: (chartType: ChartType) => void;
}

export default function AutoChart({
  data,
  title,
  allowManualOverride = true,
  showExporter = true,
  onChartTypeChange,
}: AutoChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  // Auto-detect optimal chart type
  const detection = useMemo(() => detectChartType(data), [data]);

  // Allow manual override of chart type
  const [manualChartType, setManualChartType] = useState<ChartType | null>(null);
  const activeChartType = manualChartType || detection.type;

  const handleChartTypeChange = (newType: ChartType) => {
    setManualChartType(newType);
    onChartTypeChange?.(newType);
  };

  // Confidence badge color
  const confidenceBadgeColor =
    detection.confidence >= 0.85
      ? 'bg-green-100 text-green-800'
      : detection.confidence >= 0.7
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Header with title and controls */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          {title && <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2 py-1 rounded text-xs font-medium ${confidenceBadgeColor}`}>
              {(detection.confidence * 100).toFixed(0)}% confidence
            </span>
            <span className="text-xs text-gray-500">{detection.reason}</span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 ml-4">
          {/* Manual chart type selector */}
          {allowManualOverride && (
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-600">Type:</label>
              <select
                value={activeChartType}
                onChange={(e) => handleChartTypeChange(e.target.value as ChartType)}
                className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="line">Line</option>
                <option value="bar">Bar</option>
                <option value="pie">Pie</option>
                <option value="table">Table</option>
              </select>
            </div>
          )}

          {/* Export buttons */}
          {showExporter && activeChartType !== 'table' && (
            <ChartExporter
              data={data}
              chartRef={chartRef}
              filename={title?.toLowerCase().replace(/\s+/g, '_') || 'chart'}
            />
          )}
        </div>
      </div>

      {/* Chart rendering area */}
      <div ref={chartRef} className="min-h-[300px]">
        {renderChart(activeChartType, data, detection)}
      </div>

      {/* Detection metadata (for debugging/transparency) */}
      <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap gap-4 text-xs text-gray-500">
        {detection.timeColumn && (
          <div>
            Time column: <span className="font-mono text-gray-700">{detection.timeColumn}</span>
          </div>
        )}
        {detection.categoryColumn && (
          <div>
            Category: <span className="font-mono text-gray-700">{detection.categoryColumn}</span>
          </div>
        )}
        {detection.valueColumns && detection.valueColumns.length > 0 && (
          <div>
            Values: <span className="font-mono text-gray-700">{detection.valueColumns.join(', ')}</span>
          </div>
        )}
        <div>
          Rows: <span className="font-mono text-gray-700">{data.length.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Render the appropriate chart component based on chart type
 */
function renderChart(chartType: ChartType, data: any[], detection: any) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-500 py-12">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <p className="mt-2">No data to visualize</p>
      </div>
    );
  }

  switch (chartType) {
    case 'line':
      if (!detection.timeColumn || !detection.valueColumns || detection.valueColumns.length === 0) {
        return <EmptyChartMessage message="Time-series data requires a time column and at least one value column" />;
      }
      return (
        <TimeSeriesChart
          data={data}
          timeColumn={detection.timeColumn}
          valueColumns={detection.valueColumns}
        />
      );

    case 'bar':
      if (!detection.categoryColumn || !detection.valueColumns || detection.valueColumns.length === 0) {
        return <EmptyChartMessage message="Bar chart requires a category column and at least one value column" />;
      }
      return (
        <CategoryBarChart
          data={data}
          categoryColumn={detection.categoryColumn}
          valueColumns={detection.valueColumns}
        />
      );

    case 'pie':
      if (!detection.categoryColumn || !detection.valueColumns || detection.valueColumns.length === 0) {
        return <EmptyChartMessage message="Pie chart requires a category column and exactly one value column" />;
      }
      return (
        <PieChartComponent
          data={data}
          categoryColumn={detection.categoryColumn}
          valueColumn={detection.valueColumns[0]}
        />
      );

    case 'table':
    default:
      return <TableView data={data} />;
  }
}

/**
 * Empty chart message component
 */
function EmptyChartMessage({ message }: { message: string }) {
  return (
    <div className="text-center text-gray-500 py-12">
      <svg
        className="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <p className="mt-2 text-sm">{message}</p>
    </div>
  );
}

/**
 * Table view component for fallback display
 */
function TableView({ data }: { data: any[] }) {
  if (data.length === 0) return null;

  const columns = Object.keys(data[0]);
  const displayRows = data.slice(0, 100); // Show first 100 rows

  return (
    <div className="w-full overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {displayRows.map((row, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={col} className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">
                  {formatCellValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <div className="text-center text-xs text-gray-500 mt-3 py-2 bg-gray-50 rounded">
          Showing 100 of {data.length.toLocaleString()} rows
        </div>
      )}
    </div>
  );
}

/**
 * Format cell value for display in table
 */
function formatCellValue(value: any): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}
