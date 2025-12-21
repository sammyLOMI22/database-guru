/**
 * Box Plot Chart Component
 *
 * Displays statistical distribution of data showing quartiles, median, and outliers.
 * Useful for comparing distributions across categories.
 */

import React, { useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ErrorBar,
  Scatter,
  ZAxis,
} from 'recharts';
import { prepareBoxPlotData } from '../../utils/statisticalChartUtils';
import { CHART_COLORS } from '../../utils/chartUtils';

interface BoxPlotViewProps {
  data: Record<string, unknown>[];
  categoryColumn: string;
  valueColumn: string;
  title?: string;
  height?: number;
  showOutliers?: boolean;
  showMean?: boolean;
  animate?: boolean;
}

export const BoxPlotView: React.FC<BoxPlotViewProps> = ({
  data,
  categoryColumn,
  valueColumn,
  title,
  height = 300,
  showOutliers = true,
  showMean = true,
  animate = true,
}) => {
  const boxPlotData = useMemo(() => {
    if (!data || data.length === 0) {
      return [];
    }
    return prepareBoxPlotData(data, categoryColumn, valueColumn);
  }, [data, categoryColumn, valueColumn]);

  // Transform data for Recharts ComposedChart
  const chartData = useMemo(() => {
    return boxPlotData.map(bp => ({
      name: bp.name,
      // For the box (IQR)
      q1: bp.q1,
      q3: bp.q3,
      iqr: bp.q3 - bp.q1,
      median: bp.median,
      mean: bp.mean,
      // For whiskers
      min: bp.min,
      max: bp.max,
      lowerWhisker: bp.q1 - bp.min,
      upperWhisker: bp.max - bp.q3,
      // For outliers
      outliers: bp.outliers,
      // Stats for tooltip
      stdDev: bp.stdDev,
    }));
  }, [boxPlotData]);

  // Flatten outliers for scatter
  const outlierData = useMemo(() => {
    if (!showOutliers) return [];
    return boxPlotData.flatMap((bp, index) =>
      bp.outliers.map(value => ({
        name: bp.name,
        value,
        index,
      }))
    );
  }, [boxPlotData, showOutliers]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No data available for box plot
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-3">{title}</h4>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11 }}
            angle={chartData.length > 5 ? -45 : 0}
            textAnchor={chartData.length > 5 ? 'end' : 'middle'}
            height={chartData.length > 5 ? 60 : 30}
          />
          <YAxis tick={{ fontSize: 11 }} width={60} />
          <ZAxis range={[40, 40]} />

          <Tooltip
            content={({ payload }) => {
              if (!payload || payload.length === 0) return null;
              const item = payload[0].payload;
              return (
                <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
                  <div className="font-medium text-gray-900 mb-2">{item.name}</div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                    <div>Min: {item.min?.toFixed(2)}</div>
                    <div>Max: {item.max?.toFixed(2)}</div>
                    <div>Q1: {item.q1?.toFixed(2)}</div>
                    <div>Q3: {item.q3?.toFixed(2)}</div>
                    <div>Median: {item.median?.toFixed(2)}</div>
                    <div>Mean: {item.mean?.toFixed(2)}</div>
                    <div>IQR: {item.iqr?.toFixed(2)}</div>
                    <div>Std Dev: {item.stdDev?.toFixed(2)}</div>
                  </div>
                  {item.outliers?.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-amber-600">
                      {item.outliers.length} outlier(s)
                    </div>
                  )}
                </div>
              );
            }}
          />

          {/* Box (IQR) */}
          <Bar
            dataKey="iqr"
            fill={CHART_COLORS.primary}
            fillOpacity={0.6}
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            isAnimationActive={animate}
            stackId="box"
          >
            {/* Whiskers as error bars */}
            <ErrorBar
              dataKey="lowerWhisker"
              direction="y"
              width={4}
              strokeWidth={2}
              stroke={CHART_COLORS.primary}
            />
            <ErrorBar
              dataKey="upperWhisker"
              direction="y"
              width={4}
              strokeWidth={2}
              stroke={CHART_COLORS.primary}
            />
          </Bar>

          {/* Median line */}
          <Scatter
            data={chartData.map(d => ({ ...d, medianValue: d.median }))}
            dataKey="median"
            fill={CHART_COLORS.danger}
            shape={(props: unknown) => {
              const { cx, cy } = props as { cx: number; cy: number };
              return (
                <line
                  x1={cx - 15}
                  y1={cy}
                  x2={cx + 15}
                  y2={cy}
                  stroke={CHART_COLORS.danger}
                  strokeWidth={3}
                />
              );
            }}
            isAnimationActive={false}
          />

          {/* Mean marker */}
          {showMean && (
            <Scatter
              data={chartData}
              dataKey="mean"
              fill={CHART_COLORS.success}
              shape="diamond"
              isAnimationActive={false}
            />
          )}

          {/* Outliers */}
          {showOutliers && outlierData.length > 0 && (
            <Scatter
              data={outlierData}
              dataKey="value"
              fill={CHART_COLORS.warning}
              shape="circle"
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-gray-100 text-xs text-gray-600">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded" style={{ backgroundColor: CHART_COLORS.primary, opacity: 0.6 }} />
          <span>IQR (Q1-Q3)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5" style={{ backgroundColor: CHART_COLORS.danger }} />
          <span>Median</span>
        </div>
        {showMean && (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rotate-45" style={{ backgroundColor: CHART_COLORS.success }} />
            <span>Mean</span>
          </div>
        )}
        {showOutliers && (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: CHART_COLORS.warning }} />
            <span>Outliers</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default BoxPlotView;
