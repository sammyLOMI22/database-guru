/**
 * Area Chart Component
 *
 * Displays time-series data with filled area under the line.
 * Supports stacked areas for multiple series.
 */

import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { CHART_COLORS } from '../../utils/chartUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

interface AreaChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumns: string[];
  title?: string;
  height?: number;
  stacked?: boolean;
  showLegend?: boolean;
  animate?: boolean;
  gradient?: boolean;
}

const AREA_COLORS = [
  CHART_COLORS.primary,
  CHART_COLORS.success,
  CHART_COLORS.warning,
  CHART_COLORS.secondary,
  CHART_COLORS.danger,
  CHART_COLORS.info,
];

export const AreaChartView: React.FC<AreaChartViewProps> = ({
  data,
  xColumn,
  yColumns,
  title,
  height = 300,
  stacked = false,
  showLegend = true,
  animate = true,
  gradient = true,
}) => {
  const { isDarkMode } = useDarkMode();

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Prepare data with all y columns
    return data.slice(0, 100).map(row => {
      const point: Record<string, unknown> = { [xColumn]: row[xColumn] };
      for (const col of yColumns) {
        point[col] = Number(row[col]) || 0;
      }
      return point;
    });
  }, [data, xColumn, yColumns]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        No data available for area chart
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-colors">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{title}</h4>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
        >
          {/* Define gradients */}
          {gradient && (
            <defs>
              {yColumns.map((col, index) => (
                <linearGradient
                  key={`gradient-${col}`}
                  id={`color-${col}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="5%"
                    stopColor={AREA_COLORS[index % AREA_COLORS.length]}
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor={AREA_COLORS[index % AREA_COLORS.length]}
                    stopOpacity={0.1}
                  />
                </linearGradient>
              ))}
            </defs>
          )}

          <CartesianGrid
            strokeDasharray="3 3"
            stroke={isDarkMode ? '#374151' : '#e5e7eb'}
          />
          <XAxis
            dataKey={xColumn}
            tick={{ fontSize: 11, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
            angle={-45}
            textAnchor="end"
            height={60}
            interval="preserveStartEnd"
            stroke={isDarkMode ? '#4b5563' : '#9ca3af'}
          />
          <YAxis
            tick={{ fontSize: 11, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
            width={60}
            stroke={isDarkMode ? '#4b5563' : '#9ca3af'}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: isDarkMode ? '#1f2937' : 'white',
              border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
              borderRadius: '6px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              color: isDarkMode ? '#f3f4f6' : '#111827',
            }}
            itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
            formatter={(value: any, name: any) => [
              value !== undefined ? value.toLocaleString() : '0',
              name ?? '',
            ]}
          />
          {showLegend && <Legend />}

          {yColumns.map((col, index) => (
            <Area
              key={col}
              type="monotone"
              dataKey={col}
              stackId={stacked ? '1' : undefined}
              stroke={AREA_COLORS[index % AREA_COLORS.length]}
              fill={gradient ? `url(#color-${col})` : AREA_COLORS[index % AREA_COLORS.length]}
              fillOpacity={gradient ? 1 : 0.6}
              strokeWidth={2}
              isAnimationActive={animate}
              dot={chartData.length <= 20}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

/**
 * Single-column area chart variant
 */
interface SimpleAreaChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
}

export const SimpleAreaChartView: React.FC<SimpleAreaChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  title,
  height = 300,
  showLegend = false,
  animate = true,
}) => {
  return (
    <AreaChartView
      data={data}
      xColumn={xColumn}
      yColumns={[yColumn]}
      title={title}
      height={height}
      showLegend={showLegend}
      animate={animate}
    />
  );
};

export default AreaChartView;
