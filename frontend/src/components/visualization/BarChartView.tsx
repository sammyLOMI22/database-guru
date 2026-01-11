/**
 * Bar Chart Component
 *
 * Displays categorical data as a bar chart using Recharts.
 */

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts';
import { CHART_COLORS, prepareChartData } from '../../utils/chartUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

interface BarChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
}

export const BarChartView: React.FC<BarChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  title,
  height = 300,
  showLegend = false,
  animate = true,
}) => {
  const { isDarkMode } = useDarkMode();

  const chartData = useMemo(() => {
    return prepareChartData(data, xColumn, yColumn, 'bar', 50);
  }, [data, xColumn, yColumn]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        No data available for bar chart
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-colors">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
        >
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
            interval={0}
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
              borderRadius: '8px',
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
              color: isDarkMode ? '#f3f4f6' : '#111827',
            }}
            itemStyle={{ color: isDarkMode ? '#f3f4f6' : '#111827' }}
            formatter={(value: any) => [
              value !== undefined ? value.toLocaleString() : '0',
              yColumn,
            ]}
          />
          {showLegend && (
            <Legend
              wrapperStyle={{
                paddingTop: '10px',
                color: isDarkMode ? '#9ca3af' : '#4b5563',
                fontSize: '12px',
              }}
            />
          )}
          <Bar
            dataKey={yColumn}
            fill={CHART_COLORS.primary}
            radius={[4, 4, 0, 0]}
            isAnimationActive={animate}
          >
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={CHART_COLORS.primary}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
