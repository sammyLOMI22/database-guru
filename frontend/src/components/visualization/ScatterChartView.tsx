/**
 * Scatter Chart Component
 *
 * Displays correlation between two numeric columns using Recharts.
 */

import React, { useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
} from 'recharts';
import { CHART_COLORS } from '../../utils/chartUtils';

interface ScatterChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  title?: string;
  height?: number;
  animate?: boolean;
  correlationValue?: number;
}

interface ScatterDataPoint {
  x: number;
  y: number;
  name?: string;
}

export const ScatterChartView: React.FC<ScatterChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  title,
  height = 300,
  animate = true,
  correlationValue,
}) => {
  const chartData = useMemo((): ScatterDataPoint[] => {
    const maxPoints = 200; // Limit for performance
    const limitedData = data.slice(0, maxPoints);

    return limitedData
      .map((row, idx) => {
        const x = Number(row[xColumn]);
        const y = Number(row[yColumn]);
        if (isNaN(x) || isNaN(y)) return null;
        return { x, y, name: `Point ${idx + 1}` };
      })
      .filter((point): point is ScatterDataPoint => point !== null);
  }, [data, xColumn, yColumn]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No numeric data available for scatter chart
      </div>
    );
  }

  const correlationLabel = correlationValue !== undefined
    ? ` (r = ${correlationValue.toFixed(2)})`
    : '';

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-1">
          {title}
          {correlationLabel && (
            <span className="text-gray-500 font-normal">{correlationLabel}</span>
          )}
        </h4>
      )}
      {correlationValue !== undefined && (
        <p className="text-xs text-gray-500 mb-3">
          {Math.abs(correlationValue) > 0.7
            ? 'Strong correlation detected'
            : Math.abs(correlationValue) > 0.4
            ? 'Moderate correlation'
            : 'Weak correlation'}
        </p>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
          <XAxis
            type="number"
            dataKey="x"
            name={xColumn}
            tick={{ fontSize: 11 }}
            label={{
              value: xColumn,
              position: 'bottom',
              fontSize: 11,
              fill: '#6b7280',
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name={yColumn}
            tick={{ fontSize: 11 }}
            width={60}
            label={{
              value: yColumn,
              angle: -90,
              position: 'insideLeft',
              fontSize: 11,
              fill: '#6b7280',
            }}
          />
          <ZAxis range={[50, 50]} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number, name: string) => [
              value.toLocaleString(),
              name === 'x' ? xColumn : yColumn,
            ]}
            cursor={{ strokeDasharray: '3 3' }}
          />
          <Scatter
            name="Data Points"
            data={chartData}
            fill={CHART_COLORS.primary}
            fillOpacity={0.6}
            isAnimationActive={animate}
          />
        </ScatterChart>
      </ResponsiveContainer>
      {data.length > 200 && (
        <p className="text-xs text-gray-400 mt-2 text-center">
          Showing first 200 of {data.length} points
        </p>
      )}
    </div>
  );
};
