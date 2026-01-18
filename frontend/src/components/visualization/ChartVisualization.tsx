/**
 * Chart Visualization Container
 *
 * Main component that auto-detects the appropriate chart type
 * and renders the corresponding visualization.
 */

import React, { useMemo } from 'react';
import {
  AlertCircle,
  Sparkles,
  Zap,
  TrendingUp,
  AlertTriangle,
  Lightbulb
} from 'lucide-react';
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
import { BubbleChartView } from './BubbleChartView';

interface ChartVisualizationProps {
  data: Record<string, unknown>[];
  statistics: Record<string, unknown>;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
  /** Override the auto-detected chart type */
  overrideChartType?: ChartType | null;
}

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

const ChartInfoBadge: React.FC<{ recommendation: IntelligentChartRecommendation }> = ({
  recommendation,
}) => {
  return (
    <div className="mb-4 p-3 glass-card bg-blue-500/5 dark:bg-blue-500/10 border-blue-500/20 rounded-xl flex items-start gap-3 animate-fadeIn">
      <div className="mt-0.5 p-1 bg-blue-500/10 rounded-lg">
        <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
      </div>
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest bg-blue-500/10 px-1.5 py-0.5 rounded">
            AI Recommendation
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-full font-bold border border-blue-500/30">
              {chartTypeLabels[recommendation.primaryChart]}
            </span>
            <span className="text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded-full font-bold border border-indigo-500/30">
              {Math.round(recommendation.confidence)}% Confidence
            </span>
          </div>
        </div>
        <p className="text-sm text-blue-800 dark:text-blue-300 mt-1.5 font-medium leading-tight">{recommendation.reason}</p>
      </div>
    </div>
  );
};

const InsightsBadge: React.FC<{ insights: DataInsight[] }> = ({ insights }) => {
  if (!insights || insights.length === 0) return null;

  return (
    <div className="mb-4 p-3 glass-card bg-purple-500/5 dark:bg-purple-500/10 border-purple-500/20 rounded-xl animate-fadeIn delay-100">
      <div className="flex items-center gap-2 mb-2.5">
        <div className="p-1 bg-purple-500/10 rounded-lg">
          <Zap className="w-4 h-4 text-purple-600 dark:text-purple-400" />
        </div>
        <span className="text-xs font-black text-purple-600 dark:text-purple-400 uppercase tracking-widest bg-purple-500/10 px-1.5 py-0.5 rounded">
          Data Insights
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {insights.map((insight, index) => (
          <div key={index} className="flex items-center gap-2 px-2.5 py-1 bg-white/50 dark:bg-purple-900/20 text-purple-800 dark:text-purple-200 rounded-full text-xs font-medium border border-purple-200/50 dark:border-purple-800/50">
            {insight.type === 'trend' && <TrendingUp className="w-3.5 h-3.5" />}
            {insight.type === 'outlier' && <AlertTriangle className="w-3.5 h-3.5" />}
            {insight.type === 'pattern' && <Lightbulb className="w-3.5 h-3.5" />}
            <span>{insight.message}</span>
          </div>
        ))}
      </div>
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
        reason: `Manually selected ${chartTypeLabels[overrideChartType]}`,
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
      <div className="glass-card bg-gray-500/5 rounded-2xl border-gray-500/10 p-8 text-center animate-fadeIn">
        <div className="w-12 h-12 bg-gray-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <AlertCircle className="w-6 h-6 text-gray-400 dark:text-gray-500" />
        </div>
        <p className="text-base text-gray-700 dark:text-gray-200 font-bold tracking-tight">
          No Visualization Available
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 max-w-xs mx-auto">{recommendation.reason}</p>
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

      {recommendation.primaryChart === 'bubble' && recommendation.xColumn && recommendation.yColumn && (
        <BubbleChartView
          data={data}
          xColumn={recommendation.xColumn}
          yColumn={recommendation.yColumn}
          zColumn={classifyColumns(data, statistics).numericColumns[2] || recommendation.yColumn}
          title={chartTitle}
          height={height}
          animate={animate}
        />
      )}
    </div>
  );
};

export default ChartVisualization;
