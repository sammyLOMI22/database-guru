/**
 * Bubble Chart Component
 *
 * Displays three-dimensional data using scatter plot with variable bubble sizes.
 * X and Y for position, Z for bubble size.
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
import { prepareBubbleData, normalizeBubbleSizes, BubblePoint } from '../../utils/statisticalChartUtils';

interface BubbleChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  zColumn: string;
  nameColumn?: string;
  title?: string;
  height?: number;
  animate?: boolean;
}

export const BubbleChartView: React.FC<BubbleChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  zColumn,
  nameColumn,
  title,
  height = 300,
  animate = true,
}) => {
  const chartData = useMemo((): BubblePoint[] => {
    const maxPoints = 100; // Limit for performance with larger bubbles
    const limitedData = data.slice(0, maxPoints);

    const bubbles = prepareBubbleData(limitedData, xColumn, yColumn, zColumn, nameColumn);
    return normalizeBubbleSizes(bubbles, 100, 1000); // Recharts uses area, so larger values
  }, [data, xColumn, yColumn, zColumn, nameColumn]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No numeric data available for bubble chart (requires 3 numeric columns)
      </div>
    );
  }

  // Get z-value range for legend
  const originalZValues = prepareBubbleData(data.slice(0, 100), xColumn, yColumn, zColumn).map(b => b.z);
  const minZ = Math.min(...originalZValues);
  const maxZ = Math.max(...originalZValues);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-1">
          {title}
        </h4>
      )}
      <p className="text-xs text-gray-500 mb-3">
        Bubble size represents {zColumn} ({minZ.toLocaleString()} - {maxZ.toLocaleString()})
      </p>
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
          <ZAxis
            type="number"
            dataKey="z"
            range={[100, 1000]}
            name={zColumn}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
            content={({ active, payload }) => {
              if (active && payload && payload.length > 0) {
                const point = payload[0].payload as BubblePoint;
                return (
                  <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-2">
                    {point.name && (
                      <p className="text-sm font-medium text-gray-900">{point.name}</p>
                    )}
                    <p className="text-xs text-gray-600">{xColumn}: {point.x.toLocaleString()}</p>
                    <p className="text-xs text-gray-600">{yColumn}: {point.y.toLocaleString()}</p>
                    <p className="text-xs text-gray-600">
                      {zColumn}: {point.originalRow?.[zColumn]?.toLocaleString?.() ?? point.z.toLocaleString()}
                    </p>
                  </div>
                );
              }
              return null;
            }}
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
      {data.length > 100 && (
        <p className="text-xs text-gray-400 mt-2 text-center">
          Showing first 100 of {data.length} points
        </p>
      )}
    </div>
  );
};

export default BubbleChartView;
