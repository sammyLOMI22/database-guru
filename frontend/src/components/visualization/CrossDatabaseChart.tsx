/**
 * Cross-Database Comparison Chart Component
 *
 * Displays a comparison chart (bar, line, pie, or scatter) comparing metrics across multiple databases.
 * Auto-detects the best chart type based on data characteristics.
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { ChevronDown, ChevronRight, BarChart3, TrendingUp, PieChart as PieChartIcon, ScatterChart as ScatterChartIcon } from 'lucide-react';
import { CrossDbChartConfig, formatMetricValue } from '../../utils/crossDbUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

type CrossDbChartType = 'bar' | 'line' | 'pie' | 'scatter';

interface ChartTypeRecommendation {
  type: CrossDbChartType;
  reason: string;
}

/**
 * Detect the best chart type for cross-database comparison
 */
function detectBestChartType(config: CrossDbChartConfig): ChartTypeRecommendation {
  const dbCount = config.aggregatedData.length;
  const metricCount = config.commonColumns.length;

  // Scatter plot: Best for 2+ metrics to show relationships between metrics across databases
  if (metricCount >= 2 && dbCount >= 3) {
    return {
      type: 'scatter',
      reason: 'Scatter plot shows relationships between metrics across databases',
    };
  }

  // Pie chart: Best for single metric with 2-6 databases (shows proportional distribution)
  if (metricCount === 1 && dbCount >= 2 && dbCount <= 6) {
    return {
      type: 'pie',
      reason: 'Pie chart shows metric distribution across databases',
    };
  }

  // Bar chart: Default for comparisons
  return {
    type: 'bar',
    reason: 'Bar chart for comparing values across databases',
  };
}

const chartTypeOptions: { type: CrossDbChartType; label: string; icon: React.ReactNode }[] = [
  { type: 'bar', label: 'Bar', icon: <BarChart3 className="w-4 h-4" /> },
  { type: 'line', label: 'Line', icon: <TrendingUp className="w-4 h-4" /> },
  { type: 'pie', label: 'Pie', icon: <PieChartIcon className="w-4 h-4" /> },
  { type: 'scatter', label: 'Scatter', icon: <ScatterChartIcon className="w-4 h-4" /> },
];

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
  const [showChartTypeDropdown, setShowChartTypeDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { isDarkMode } = useDarkMode();

  // Auto-detect best chart type
  const recommendation = useMemo(() => detectBestChartType(config), [config]);
  const [selectedChartType, setSelectedChartType] = useState<CrossDbChartType | null>(null);
  const chartType = selectedChartType || recommendation.type;

  // For scatter plot, allow selecting which metrics to compare
  const [scatterXMetric, setScatterXMetric] = useState(config.commonColumns[0] || '');
  const [scatterYMetric, setScatterYMetric] = useState(config.commonColumns[1] || config.commonColumns[0] || '');

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowChartTypeDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

  // Data for pie chart - shows distribution of selected metric across databases
  const pieData = config.aggregatedData.map((db) => ({
    name: db.databaseName,
    value: db.metrics[selectedMetric] || 0,
    color: db.color,
  }));

  // Data for scatter plot - each database is a point with x and y metrics
  const scatterData = config.aggregatedData.map((db) => ({
    name: db.databaseName,
    x: db.metrics[scatterXMetric] || 0,
    y: db.metrics[scatterYMetric] || 0,
    color: db.color,
    rowCount: db.rowCount,
  }));

  // Data for line chart - databases on x-axis with selected metric values
  const lineData = config.aggregatedData.map((db) => ({
    database: db.databaseName,
    value: db.metrics[selectedMetric] || 0,
  }));

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden transition-colors">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 hover:from-purple-100 hover:to-indigo-100 dark:hover:from-purple-900/30 dark:hover:to-indigo-900/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          <span className="font-semibold text-gray-900 dark:text-white">Cross-Database Comparison</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
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
        <div className="p-4 bg-white dark:bg-gray-800 transition-colors">
          {/* Chart controls row */}
          <div className="mb-4 flex flex-wrap items-center gap-4">
            {/* Chart type selector */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setShowChartTypeDropdown(!showChartTypeDropdown)}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-200"
              >
                {chartTypeOptions.find((o) => o.type === chartType)?.icon}
                <span>{chartTypeOptions.find((o) => o.type === chartType)?.label}</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showChartTypeDropdown ? 'rotate-180' : ''}`} />
              </button>

              {showChartTypeDropdown && (
                <div className="absolute left-0 mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50">
                  <div className="py-1">
                    <div className="px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Chart Type
                    </div>
                    {chartTypeOptions.map((option) => (
                      <button
                        key={option.type}
                        onClick={() => {
                          setSelectedChartType(option.type);
                          setShowChartTypeDropdown(false);
                        }}
                        className={`
                          w-full flex items-center gap-2 px-3 py-2 text-sm text-left
                          ${chartType === option.type
                            ? 'bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}
                        `}
                      >
                        {option.icon}
                        <span className="flex-1">{option.label}</span>
                        {recommendation.type === option.type && (
                          <span className="text-xs text-purple-500 font-medium">(recommended)</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Metric selector for bar/line/pie (if multiple metrics) */}
            {chartType !== 'scatter' && config.commonColumns.length > 1 && (
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 dark:text-gray-400">Metric:</label>
                <select
                  value={selectedMetric}
                  onChange={(e) => setSelectedMetric(e.target.value)}
                  className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200"
                >
                  {config.commonColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Axis selectors for scatter plot */}
            {chartType === 'scatter' && config.commonColumns.length >= 2 && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600 dark:text-gray-400">X-Axis:</label>
                  <select
                    value={scatterXMetric}
                    onChange={(e) => setScatterXMetric(e.target.value)}
                    className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200"
                  >
                    {config.commonColumns.map((col) => (
                      <option key={col} value={col}>
                        {col}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600 dark:text-gray-400">Y-Axis:</label>
                  <select
                    value={scatterYMetric}
                    onChange={(e) => setScatterYMetric(e.target.value)}
                    className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200"
                  >
                    {config.commonColumns.map((col) => (
                      <option key={col} value={col}>
                        {col}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Chart */}
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              {/* Bar Chart */}
              {chartType === 'bar' && (
                singleMetricData ? (
                  <BarChart data={singleMetricData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? '#374151' : '#e5e7eb'} />
                    <XAxis dataKey="database" tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }} tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }} />
                    <YAxis
                      tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                      tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }}
                      tickFormatter={(value) => formatMetricValue(value)}
                    />
                    <Tooltip
                      formatter={(value: any) => [formatMetricValue(Number(value)), config.primaryMetric]}
                      contentStyle={{
                        backgroundColor: isDarkMode ? '#1f2937' : 'white',
                        border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
                        borderRadius: '0.375rem',
                        color: isDarkMode ? '#f3f4f6' : '#111827',
                      }}
                      itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
                    />
                    <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} name={config.primaryMetric} />
                  </BarChart>
                ) : (
                  <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? '#374151' : '#e5e7eb'} />
                    <XAxis dataKey="metric" tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }} tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }} />
                    <YAxis
                      tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                      tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }}
                      tickFormatter={(value) => formatMetricValue(value)}
                    />
                    <Tooltip
                      formatter={(value: any, name: any) => [formatMetricValue(Number(value)), String(name)]}
                      contentStyle={{
                        backgroundColor: isDarkMode ? '#1f2937' : 'white',
                        border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
                        borderRadius: '0.375rem',
                        color: isDarkMode ? '#f3f4f6' : '#111827',
                      }}
                      itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
                    />
                    <Legend
                      wrapperStyle={{
                        paddingTop: '20px',
                        color: isDarkMode ? '#9ca3af' : '#4b5563',
                        fontSize: '12px',
                      }}
                    />
                    {config.aggregatedData.map((db) => (
                      <Bar key={db.databaseName} dataKey={db.databaseName} fill={db.color} radius={[4, 4, 0, 0]} />
                    ))}
                  </BarChart>
                )
              )}

              {/* Line Chart */}
              {chartType === 'line' && (
                <LineChart data={lineData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? '#374151' : '#e5e7eb'} />
                  <XAxis dataKey="database" tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }} tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                    tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }}
                    tickFormatter={(value) => formatMetricValue(value)}
                  />
                  <Tooltip
                    formatter={(value: any) => [formatMetricValue(Number(value)), selectedMetric]}
                    contentStyle={{
                      backgroundColor: isDarkMode ? '#1f2937' : 'white',
                      border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
                      borderRadius: '0.375rem',
                      color: isDarkMode ? '#f3f4f6' : '#111827',
                    }}
                    itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
                  />
                  <Legend
                    wrapperStyle={{
                      paddingTop: '20px',
                      color: isDarkMode ? '#9ca3af' : '#4b5563',
                      fontSize: '12px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 4 }}
                    name={selectedMetric}
                  />
                </LineChart>
              )}

              {/* Pie Chart */}
              {chartType === 'pie' && (
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                    outerRadius={100}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: any) => [formatMetricValue(Number(value)), selectedMetric]}
                    contentStyle={{
                      backgroundColor: isDarkMode ? '#1f2937' : 'white',
                      border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
                      borderRadius: '0.375rem',
                      color: isDarkMode ? '#f3f4f6' : '#111827',
                    }}
                    itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
                  />
                  <Legend
                    wrapperStyle={{
                      paddingTop: '20px',
                      color: isDarkMode ? '#9ca3af' : '#4b5563',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              )}

              {/* Scatter Plot */}
              {chartType === 'scatter' && (
                <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? '#374151' : '#e5e7eb'} />
                  <XAxis
                    type="number"
                    dataKey="x"
                    name={scatterXMetric}
                    tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                    tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }}
                    tickFormatter={(value) => formatMetricValue(value)}
                    label={{ value: scatterXMetric, position: 'bottom', offset: -5, fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name={scatterYMetric}
                    tick={{ fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                    tickLine={{ stroke: isDarkMode ? '#4b5563' : '#9ca3af' }}
                    tickFormatter={(value) => formatMetricValue(value)}
                    label={{ value: scatterYMetric, angle: -90, position: 'insideLeft', fontSize: 12, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
                  />
                  <ZAxis type="number" dataKey="rowCount" range={[100, 500]} name="Rows" />
                  <Tooltip
                    cursor={{ strokeDasharray: '3 3' }}
                    formatter={(value: any, name: any) => [formatMetricValue(Number(value)), String(name)]}
                    contentStyle={{
                      backgroundColor: isDarkMode ? '#1f2937' : 'white',
                      border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
                      borderRadius: '0.375rem',
                      color: isDarkMode ? '#f3f4f6' : '#111827',
                    }}
                    itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
                  />
                  <Legend
                    wrapperStyle={{
                      paddingTop: '20px',
                      color: isDarkMode ? '#9ca3af' : '#4b5563',
                      fontSize: '12px',
                    }}
                  />
                  {config.aggregatedData.map((db) => (
                    <Scatter
                      key={db.databaseName}
                      name={db.databaseName}
                      data={[scatterData.find((d) => d.name === db.databaseName)]}
                      fill={db.color}
                    />
                  ))}
                </ScatterChart>
              )}
            </ResponsiveContainer>
          </div>

          {/* Summary stats */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {config.aggregatedData.map((db) => (
              <div
                key={db.databaseName}
                className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-100 dark:border-gray-700"
              >
                <div className="flex items-center gap-2 mb-1">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: db.color }}
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">
                    {db.databaseName}
                  </span>
                </div>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatMetricValue(db.metrics[selectedMetric] || 0)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
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
