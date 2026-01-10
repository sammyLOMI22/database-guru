/**
 * Pie Chart Component
 *
 * Displays categorical distribution as a pie chart using Recharts.
 */

import React, { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { CHART_COLORS, prepareChartData } from '../../utils/chartUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

interface PieChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
}

interface PieDataItem {
  name: string;
  value: number;
  [key: string]: unknown;
}

const RADIAN = Math.PI / 180;

interface LabelProps {
  cx?: number;
  cy?: number;
  midAngle?: number;
  innerRadius?: number;
  outerRadius?: number;
  percent?: number;
}

const renderCustomizedLabel = ({
  cx = 0,
  cy = 0,
  midAngle = 0,
  innerRadius = 0,
  outerRadius = 0,
  percent = 0,
}: LabelProps) => {
  // Only show label if percentage is significant
  if (percent < 0.05) return null;

  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={500}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export const PieChartView: React.FC<PieChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  title,
  height = 300,
  showLegend = true,
  animate = true,
}) => {
  const { isDarkMode } = useDarkMode();

  const chartData = useMemo((): PieDataItem[] => {
    const prepared = prepareChartData(data, xColumn, yColumn, 'pie', 20);
    // Transform to pie chart format with name and value
    return prepared.map((item) => ({
      ...item,
      name: String(item[xColumn] ?? 'Unknown'),
      value: Number(item[yColumn]) || 0,
    }));
  }, [data, xColumn, yColumn]);

  const total = useMemo(() => data.reduce((sum, row) => sum + Number(row[yColumn] || 0), 0), [data, yColumn]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        No data available for pie chart
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-colors">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomizedLabel}
            outerRadius={Math.min(height / 2 - 40, 120)}
            fill="#8884d8"
            dataKey="value"
            isAnimationActive={animate}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color as string || CHART_COLORS.primary}
                stroke={isDarkMode ? '#374151' : '#fff'}
                strokeWidth={2}
              />
            ))}
          </Pie>
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
              value !== undefined
                ? `${value.toLocaleString()} (${((value / total) * 100).toFixed(1)}%)`
                : '0',
              name ?? '',
            ]}
          />
          {showLegend && (
            <Legend
              layout="vertical"
              verticalAlign="middle"
              align="right"
              wrapperStyle={{
                fontSize: 12,
                color: isDarkMode ? '#9ca3af' : '#4b5563',
                paddingLeft: '20px',
              }}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
