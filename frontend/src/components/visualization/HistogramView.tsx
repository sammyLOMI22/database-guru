/**
 * Histogram Chart Component
 *
 * Displays the distribution of numeric data as a histogram.
 * Shows frequency/count of values within bins.
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
  ReferenceLine,
} from 'recharts';
import { prepareHistogramData, calculateSummaryStats } from '../../utils/statisticalChartUtils';
import { CHART_COLORS } from '../../utils/chartUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

interface HistogramViewProps {
  data: Record<string, unknown>[];
  valueColumn: string;
  binCount?: number;
  title?: string;
  height?: number;
  showMean?: boolean;
  showMedian?: boolean;
  animate?: boolean;
}

export const HistogramView: React.FC<HistogramViewProps> = ({
  data,
  valueColumn,
  binCount,
  title,
  height = 300,
  showMean = true,
  showMedian = false,
  animate = true,
}) => {
  const { isDarkMode } = useDarkMode();
  const { histogramData, stats } = useMemo(() => {
    if (!data || data.length === 0) {
      return { histogramData: [], stats: null };
    }

    const values = data
      .map(row => Number(row[valueColumn]))
      .filter(v => !isNaN(v) && isFinite(v));

    const bins = prepareHistogramData(data, valueColumn, binCount);
    const statistics = calculateSummaryStats(values);

    // Format bins for chart display
    const formattedBins = bins.map(bin => ({
      range: `${bin.x0.toFixed(1)} - ${bin.x1.toFixed(1)}`,
      rangeStart: bin.x0,
      rangeEnd: bin.x1,
      count: bin.count,
      frequency: bin.frequency,
      midpoint: (bin.x0 + bin.x1) / 2,
    }));

    return {
      histogramData: formattedBins,
      stats: statistics,
    };
  }, [data, valueColumn, binCount]);

  if (!histogramData || histogramData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400">
        No numeric data available for histogram
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
          data={histogramData}
          margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
          barCategoryGap={1}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? '#374151' : '#e5e7eb'} />
          <XAxis
            dataKey="range"
            tick={{ fontSize: 10, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
            angle={-45}
            textAnchor="end"
            height={60}
            stroke={isDarkMode ? '#4b5563' : '#9ca3af'}
            interval={Math.floor(histogramData.length / 8)}
          />
          <YAxis
            tick={{ fontSize: 11, fill: isDarkMode ? '#9ca3af' : '#6b7280' }}
            width={50}
            stroke={isDarkMode ? '#4b5563' : '#9ca3af'}
            label={{
              value: 'Count',
              angle: -90,
              position: 'insideLeft',
              style: { textAnchor: 'middle', fontSize: 11, fill: isDarkMode ? '#9ca3af' : '#6b7280' },
            }}
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
            formatter={(value: any) => [value !== undefined ? value.toLocaleString() : '0', 'Count']}
            labelFormatter={(label) => `Range: ${label}`}
          />

          {/* Mean line */}
          {showMean && stats && (
            <ReferenceLine
              x={histogramData.find(d =>
                stats.mean >= d.rangeStart && stats.mean < d.rangeEnd
              )?.range}
              stroke={CHART_COLORS.danger}
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{
                value: `Mean: ${stats.mean.toFixed(2)}`,
                position: 'top',
                fill: CHART_COLORS.danger,
                fontSize: 10,
              }}
            />
          )}

          {/* Median line */}
          {showMedian && stats && (
            <ReferenceLine
              x={histogramData.find(d =>
                stats.median >= d.rangeStart && stats.median < d.rangeEnd
              )?.range}
              stroke={CHART_COLORS.success}
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{
                value: `Median: ${stats.median.toFixed(2)}`,
                position: 'top',
                fill: CHART_COLORS.success,
                fontSize: 10,
              }}
            />
          )}

          <Bar
            dataKey="count"
            fill={CHART_COLORS.primary}
            radius={[2, 2, 0, 0]}
            isAnimationActive={animate}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Statistics summary */}
      {stats && (
        <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Count:</span> {stats.count}
          </div>
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Mean:</span> {stats.mean.toFixed(2)}
          </div>
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Median:</span> {stats.median.toFixed(2)}
          </div>
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Std Dev:</span> {stats.stdDev.toFixed(2)}
          </div>
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-300">Range:</span> {stats.min.toFixed(2)} - {stats.max.toFixed(2)}
          </div>
        </div>
      )}
    </div>
  );
};

export default HistogramView;
