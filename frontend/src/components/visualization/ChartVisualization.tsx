/**
 * Chart Visualization Container
 *
 * Main component that auto-detects the appropriate chart type
 * and renders the corresponding visualization.
 */

import React, { useMemo } from 'react';
import { BarChart2, AlertCircle, Lightbulb, TrendingUp, AlertTriangle } from 'lucide-react';
import {
  ChartType,
  classifyColumns,
} from '../../utils/chartUtils';
import {
  analyzeData,
  IntelligentChartRecommendation,
  DataInsight,
  selectColumnsForChart,
} from '../../utils/chartIntelligence';
import { BarChartView } from './BarChartView';
import { LineChartView } from './LineChartView';
import { PieChartView } from './PieChartView';
import { ScatterChartView } from './ScatterChartView';
// Phase 10: Advanced Charts
import { TreemapView } from './TreemapView';
import { SunburstView } from './SunburstView';
import { HistogramView } from './HistogramView';
import { BoxPlotView } from './BoxPlotView';
import { AreaChartView } from './AreaChartView';

interface ChartVisualizationProps {
  data: Record<string, unknown>[];
  statistics: Record<string, unknown>;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
  /** Override the auto-detected chart type */
  overrideChartType?: ChartType | null;
}

interface ChartInfoBadgeProps {
  recommendation: IntelligentChartRecommendation;
}

const ChartInfoBadge: React.FC<ChartInfoBadgeProps> = ({ recommendation }) => {
  const chartTypeLabels: Record<ChartType, string> = {
    bar: 'Bar Chart',
    line: 'Line Chart',
    pie: 'Pie Chart',
    scatter: 'Scatter Plot',
    table: 'Table',
    // Phase 10: Advanced Charts
    treemap: 'Treemap',
    sunburst: 'Sunburst',
    boxplot: 'Box Plot',
    histogram: 'Histogram',
    bubble: 'Bubble Chart',
    area: 'Area Chart',
  };

  return (
    <div className="flex flex-col gap-2 mb-3">
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          <BarChart2 className="w-3 h-3" />
          {chartTypeLabels[recommendation.primaryChart]}
        </span>
        <span className="text-xs text-gray-500">{recommendation.reason}</span>
        {recommendation.confidence >= 80 && (
          <span className="text-xs text-green-600 font-medium">High confidence</span>
        )}
      </div>
      {recommendation.alternatives.length > 0 && (
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <span>Alternatives:</span>
          {recommendation.alternatives.slice(0, 3).map((alt, i) => (
            <span key={alt.chartType} className="px-1.5 py-0.5 bg-gray-100 rounded">
              {chartTypeLabels[alt.chartType]}{i < Math.min(recommendation.alternatives.length, 3) - 1 ? '' : ''}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

interface InsightsBadgeProps {
  insights: DataInsight[];
}

const InsightsBadge: React.FC<InsightsBadgeProps> = ({ insights }) => {
  if (insights.length === 0) return null;

  const getIcon = (type: DataInsight['type']) => {
    switch (type) {
      case 'trend': return <TrendingUp className="w-3 h-3" />;
      case 'outlier': return <AlertTriangle className="w-3 h-3" />;
      default: return <Lightbulb className="w-3 h-3" />;
    }
  };

  const getColor = (severity: DataInsight['severity']) => {
    switch (severity) {
      case 'warning': return 'bg-amber-100 text-amber-800';
      case 'highlight': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="flex flex-wrap gap-1 mb-2">
      {insights.map((insight, i) => (
        <span
          key={i}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${getColor(insight.severity)}`}
        >
          {getIcon(insight.type)}
          {insight.message}
        </span>
      ))}
    </div>
  );
};

export const ChartVisualization: React.FC<ChartVisualizationProps> = ({
  data,
  statistics,
  height = 300,
  showLegend = true,
  animate = true,
  overrideChartType,
}) => {
  // Use the new Chart Intelligence engine for analysis
  const autoRecommendation = useMemo(
    () => analyzeData(data, statistics),
    [data, statistics]
  );

  // Use override chart type if provided, otherwise use auto-detected
  const recommendation: IntelligentChartRecommendation = useMemo(() => {
    if (overrideChartType && overrideChartType !== 'table') {
      // CRITICAL: Recalculate columns for the overridden chart type
      // Different chart types need different column configurations
      const classification = classifyColumns(data, statistics);
      const { xColumn, yColumn } = selectColumnsForChart(
        overrideChartType,
        classification,
        autoRecommendation.patterns,
        data
      );
      return {
        ...autoRecommendation,
        primaryChart: overrideChartType,
        xColumn,
        yColumn,
        reason: `Manually selected ${overrideChartType} chart`,
      };
    }
    return autoRecommendation;
  }, [autoRecommendation, overrideChartType, data, statistics]);

  // Get correlation value if available for scatter plot
  const correlationValue = useMemo(() => {
    if (recommendation.primaryChart !== 'scatter') return undefined;
    const correlations = statistics.correlations as Record<string, unknown> | undefined;
    const significantCorrelations = correlations?.significant_correlations as Array<Record<string, unknown>> | undefined;
    if (significantCorrelations && significantCorrelations.length > 0) {
      return significantCorrelations[0].correlation as number;
    }
    return undefined;
  }, [recommendation.primaryChart, statistics]);

  // No chart available
  if (recommendation.primaryChart === 'table') {
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
      <InsightsBadge insights={recommendation.insights} />

      {recommendation.primaryChart === 'bar' && recommendation.xColumn && recommendation.yColumn && (
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

      {recommendation.primaryChart === 'line' && recommendation.xColumn && recommendation.yColumn && (
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

      {recommendation.primaryChart === 'pie' && recommendation.xColumn && recommendation.yColumn && (
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

      {recommendation.primaryChart === 'scatter' && recommendation.xColumn && recommendation.yColumn && (
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

      {/* Phase 10: Advanced Charts */}
      {recommendation.primaryChart === 'area' && recommendation.xColumn && recommendation.yColumn && (
        <AreaChartView
          data={data}
          xColumn={recommendation.xColumn}
          yColumns={[recommendation.yColumn]}
          title={chartTitle}
          height={height}
          showLegend={showLegend}
          animate={animate}
        />
      )}

      {recommendation.primaryChart === 'histogram' && recommendation.yColumn && (
        <HistogramView
          data={data}
          valueColumn={recommendation.yColumn}
          title={chartTitle}
          height={height}
          animate={animate}
        />
      )}

      {recommendation.primaryChart === 'boxplot' && recommendation.xColumn && recommendation.yColumn && (
        <BoxPlotView
          data={data}
          categoryColumn={recommendation.xColumn}
          valueColumn={recommendation.yColumn}
          title={chartTitle}
          height={height}
          animate={animate}
        />
      )}

      {recommendation.primaryChart === 'treemap' && (
        <TreemapView
          data={data}
          categoryColumns={
            recommendation.xColumn
              ? [recommendation.xColumn]
              : classifyColumns(data, statistics).categoricalColumns.slice(0, 2)
          }
          valueColumn={recommendation.yColumn || classifyColumns(data, statistics).numericColumns[0] || ''}
          title={chartTitle}
          height={height}
          animate={animate}
        />
      )}

      {recommendation.primaryChart === 'sunburst' && (
        <SunburstView
          data={data}
          categoryColumns={
            recommendation.xColumn
              ? [recommendation.xColumn]
              : classifyColumns(data, statistics).categoricalColumns.slice(0, 2)
          }
          valueColumn={recommendation.yColumn || classifyColumns(data, statistics).numericColumns[0] || ''}
          title={chartTitle}
          height={height}
          animate={animate}
        />
      )}
    </div>
  );
};

export default ChartVisualization;
