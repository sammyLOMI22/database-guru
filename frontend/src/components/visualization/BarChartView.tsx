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
  const chartData = useMemo(() => {
    return prepareChartData(data, xColumn, yColumn, 'bar', 50);
  }, [data, xColumn, yColumn]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No data available for bar chart
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
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
            interval={0}
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
