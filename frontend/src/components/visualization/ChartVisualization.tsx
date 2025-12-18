/**
 * Chart Visualization Container
 *
 * Main component that auto-detects the appropriate chart type
 * and renders the corresponding visualization.
 */

import React, { useMemo } from 'react';
import { BarChart2, AlertCircle } from 'lucide-react';
import {
  detectChartType,
  ChartRecommendation,
  ChartType,
} from '../../utils/chartUtils';
import { BarChartView } from './BarChartView';
import { LineChartView } from './LineChartView';
import { PieChartView } from './PieChartView';
import { ScatterChartView } from './ScatterChartView';

interface ChartVisualizationProps {
  data: Record<string, unknown>[];
  statistics: Record<string, unknown>;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
}

interface ChartInfoBadgeProps {
  recommendation: ChartRecommendation;
}

const ChartInfoBadge: React.FC<ChartInfoBadgeProps> = ({ recommendation }) => {
  const chartTypeLabels: Record<ChartType, string> = {
    bar: 'Bar Chart',
    line: 'Line Chart',
    pie: 'Pie Chart',
    scatter: 'Scatter Plot',
    table: 'Table',
  };

  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
        <BarChart2 className="w-3 h-3" />
        {chartTypeLabels[recommendation.chartType]}
      </span>
      <span className="text-xs text-gray-500">{recommendation.reason}</span>
    </div>
  );
};

export const ChartVisualization: React.FC<ChartVisualizationProps> = ({
  data,
  statistics,
  height = 300,
  showLegend = true,
  animate = true,
}) => {
  const recommendation = useMemo(
    () => detectChartType(data, statistics),
    [data, statistics]
  );

  // Get correlation value if available for scatter plot
  const correlationValue = useMemo(() => {
    if (recommendation.chartType !== 'scatter') return undefined;
    const correlations = statistics.correlations as Record<string, unknown> | undefined;
    const significantCorrelations = correlations?.significant_correlations as Array<Record<string, unknown>> | undefined;
    if (significantCorrelations && significantCorrelations.length > 0) {
      return significantCorrelations[0].correlation as number;
    }
    return undefined;
  }, [recommendation.chartType, statistics]);

  // No chart available
  if (recommendation.chartType === 'table') {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
        <AlertCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-600 font-medium">
          No Visualization Available
        </p>
        <p className="text-xs text-gray-500 mt-1">{recommendation.reason}</p>
      </div>
    );
  }

  // Generate title based on columns
  const chartTitle =
    recommendation.xColumn && recommendation.yColumn
      ? `${recommendation.yColumn} by ${recommendation.xColumn}`
      : undefined;

  return (
    <div>
      <ChartInfoBadge recommendation={recommendation} />

      {recommendation.chartType === 'bar' && recommendation.xColumn && recommendation.yColumn && (
        <BarChartView
          data={data}
          xColumn={recommendation.xColumn}
          yColumn={recommendation.yColumn}
          title={chartTitle}
          height={height}
          showLegend={showLegend}
          animate={animate}
        />
      )}

      {recommendation.chartType === 'line' && recommendation.xColumn && recommendation.yColumn && (
        <LineChartView
          data={data}
          xColumn={recommendation.xColumn}
          yColumn={recommendation.yColumn}
          title={chartTitle}
          height={height}
          showLegend={showLegend}
          animate={animate}
        />
      )}

      {recommendation.chartType === 'pie' && recommendation.xColumn && recommendation.yColumn && (
        <PieChartView
          data={data}
          xColumn={recommendation.xColumn}
          yColumn={recommendation.yColumn}
          title={chartTitle}
          height={height}
          showLegend={showLegend}
          animate={animate}
        />
      )}

      {recommendation.chartType === 'scatter' && recommendation.xColumn && recommendation.yColumn && (
        <ScatterChartView
          data={data}
          xColumn={recommendation.xColumn}
          yColumn={recommendation.yColumn}
          title={chartTitle}
          height={height}
          animate={animate}
          correlationValue={correlationValue}
        />
      )}
    </div>
  );
};

export default ChartVisualization;
