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
import { useDarkMode } from '../../hooks/useDarkMode';

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
  const { isDarkMode } = useDarkMode();
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
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400">
        No data available for box plot
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-colors">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{title}</h4>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? '#374151' : '#e5e7eb'} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
            angle={chartData.length > 5 ? -45 : 0}
            textAnchor={chartData.length > 5 ? 'end' : 'middle'}
            height={chartData.length > 5 ? 60 : 30}
            stroke={isDarkMode ? '#4b5563' : '#9ca3af'}
          />
          <YAxis
            tick={{ fontSize: 11, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
            width={60}
            stroke={isDarkMode ? '#4b5563' : '#9ca3af'}
          />
          <ZAxis range={[40, 40]} />

          <Tooltip
            content={({ payload }) => {
              if (!payload || payload.length === 0) return null;
              const item = payload[0].payload;
              return (
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-sm">
                  <div className="font-medium text-gray-900 dark:text-gray-100 mb-2">{item.name}</div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600 dark:text-gray-400">
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Min:</span> {item.min?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Max:</span> {item.max?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Q1:</span> {item.q1?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Q3:</span> {item.q3?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Median:</span> {item.median?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Mean:</span> {item.mean?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">IQR:</span> {item.iqr?.toFixed(2)}</div>
                    <div><span className="font-medium text-gray-500 dark:text-gray-500">Std Dev:</span> {item.stdDev?.toFixed(2)}</div>
                  </div>
                  {item.outliers?.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 text-xs text-amber-600 dark:text-amber-500">
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
      <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
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
