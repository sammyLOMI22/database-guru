/**
 * Cross-Database Comparison Chart Component
 *
 * Displays a grouped bar chart comparing the same metrics across multiple databases.
 */

import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { ChevronDown, ChevronRight, BarChart3 } from 'lucide-react';
import { CrossDbChartConfig, formatMetricValue } from '../../utils/crossDbUtils';

interface CrossDatabaseChartProps {
  config: CrossDbChartConfig;
  defaultExpanded?: boolean;
}

export function CrossDatabaseChart({
  config,
  defaultExpanded = true,
}: CrossDatabaseChartProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [selectedMetric, setSelectedMetric] = useState(config.primaryMetric);

  // Transform data for Recharts - one entry per metric with bars for each database
  const chartData = config.commonColumns.map((column) => {
    const entry: Record<string, string | number> = { metric: column };
    for (const db of config.aggregatedData) {
      entry[db.databaseName] = db.metrics[column];
    }
    return entry;
  });

  // If only one metric, show databases on x-axis instead
  const singleMetricData =
    config.commonColumns.length === 1
      ? config.aggregatedData.map((db) => ({
          database: db.databaseName,
          value: db.metrics[config.primaryMetric],
          color: db.color,
        }))
      : null;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-600" />
          <span className="font-semibold text-gray-900">Cross-Database Comparison</span>
          <span className="text-sm text-gray-500">
            ({config.aggregatedData.length} databases, {config.commonColumns.length} metric
            {config.commonColumns.length !== 1 ? 's' : ''})
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {/* Chart Content */}
      {isExpanded && (
        <div className="p-4 bg-white">
          {/* Metric selector (if multiple metrics) */}
          {config.commonColumns.length > 1 && (
            <div className="mb-4">
              <label className="text-sm text-gray-600 mr-2">Compare:</label>
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                {config.commonColumns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Chart */}
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              {singleMetricData ? (
                // Single metric: show databases on x-axis
                <BarChart data={singleMetricData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="database"
                    tick={{ fontSize: 12 }}
                    tickLine={{ stroke: '#9ca3af' }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={{ stroke: '#9ca3af' }}
                    tickFormatter={(value) => formatMetricValue(value)}
                  />
                  <Tooltip
                    formatter={(value) => [formatMetricValue(Number(value)), config.primaryMetric]}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.375rem',
                    }}
                  />
                  <Bar
                    dataKey="value"
                    fill="#8b5cf6"
                    radius={[4, 4, 0, 0]}
                    name={config.primaryMetric}
                  />
                </BarChart>
              ) : (
                // Multiple metrics: show metrics on x-axis with grouped bars per database
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="metric"
                    tick={{ fontSize: 12 }}
                    tickLine={{ stroke: '#9ca3af' }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={{ stroke: '#9ca3af' }}
                    tickFormatter={(value) => formatMetricValue(value)}
                  />
                  <Tooltip
                    formatter={(value, name) => [formatMetricValue(Number(value)), String(name)]}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.375rem',
                    }}
                  />
                  <Legend />
                  {config.aggregatedData.map((db) => (
                    <Bar
                      key={db.databaseName}
                      dataKey={db.databaseName}
                      fill={db.color}
                      radius={[4, 4, 0, 0]}
                    />
                  ))}
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>

          {/* Summary stats */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {config.aggregatedData.map((db) => (
              <div
                key={db.databaseName}
                className="p-3 bg-gray-50 rounded-lg border border-gray-100"
              >
                <div className="flex items-center gap-2 mb-1">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: db.color }}
                  />
                  <span className="text-sm font-medium text-gray-700 truncate">
                    {db.databaseName}
                  </span>
                </div>
                <p className="text-lg font-semibold text-gray-900">
                  {formatMetricValue(db.metrics[selectedMetric] || 0)}
                </p>
                <p className="text-xs text-gray-500">
                  {db.rowCount} row{db.rowCount !== 1 ? 's' : ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
