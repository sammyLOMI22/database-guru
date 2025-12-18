/**
 * Line Chart Component
 *
 * Displays time-series or trend data as a line chart using Recharts.
 */

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { CHART_COLORS, prepareChartData } from '../../utils/chartUtils';

interface LineChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
}

export const LineChartView: React.FC<LineChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  title,
  height = 300,
  showLegend = false,
  animate = true,
}) => {
  const chartData = useMemo(() => {
    const prepared = prepareChartData(data, xColumn, yColumn, 'line', 100);
    // Sort by x-axis for proper line rendering
    return prepared.sort((a, b) => {
      const aVal = a[xColumn];
      const bVal = b[xColumn];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return aVal.localeCompare(bVal);
      }
      return Number(aVal) - Number(bVal);
    });
  }, [data, xColumn, yColumn]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No data available for line chart
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
          <XAxis
            dataKey={xColumn}
            tick={{ fontSize: 11 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fontSize: 11 }} width={60} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number) => [value.toLocaleString(), yColumn]}
          />
          {showLegend && <Legend />}
          <Line
            type="monotone"
            dataKey={yColumn}
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            dot={{ r: 4, fill: CHART_COLORS.primary }}
            activeDot={{ r: 6, fill: CHART_COLORS.primary }}
            isAnimationActive={animate}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
