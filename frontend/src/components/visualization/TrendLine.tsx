/**
 * TrendLine Component
 *
 * Renders a trend line overlay on line and scatter charts.
 * Uses linear regression data from trendLineCalculator.
 */

import { Line } from 'recharts';
import { TrendLineResult } from '../../utils/trendLineCalculator';
import { CHART_COLORS } from '../../utils/chartUtils';

export interface TrendLineProps {
  /** Trend line calculation result */
  trendData: TrendLineResult;
  /** Whether the trend line is visible */
  visible?: boolean;
  /** Color of the trend line */
  color?: string;
  /** Stroke width */
  strokeWidth?: number;
  /** Dash pattern for dashed line */
  strokeDasharray?: string;
  /** Data key for X axis (used to format the line) */
  xDataKey?: string;
  /** Data key for Y axis (used for label) */
  yDataKey?: string;
}

/**
 * TrendLine component that renders a regression line on charts.
 *
 * This component is designed to be used inside Recharts Line/Scatter charts.
 * It renders the trend line as a dashed line overlay.
 *
 * Usage:
 * ```tsx
 * <LineChart data={data}>
 *   <Line dataKey="value" />
 *   <TrendLine trendData={trendResult} visible={showTrend} />
 * </LineChart>
 * ```
 */
export function TrendLine({
  trendData,
  visible = true,
  color = CHART_COLORS.secondary,
  strokeWidth = 2,
  strokeDasharray = '8 4',
}: TrendLineProps) {
  if (!visible || !trendData || trendData.points.length < 2) {
    return null;
  }

  // Create the trend line data for Recharts
  const trendLineData = trendData.points.map(point => ({
    x: point.x,
    trendValue: point.y,
  }));

  return (
    <Line
      data={trendLineData}
      dataKey="trendValue"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeDasharray={strokeDasharray}
      dot={false}
      isAnimationActive={false}
      legendType="none"
      name="Trend Line"
    />
  );
}

/**
 * TrendLineInfo Component
 *
 * Displays trend line statistics and direction indicator.
 * Use this alongside TrendLine for user context.
 */
export interface TrendLineInfoProps {
  trendData: TrendLineResult;
  className?: string;
}

export function TrendLineInfo({ trendData, className = '' }: TrendLineInfoProps) {
  const { direction, rSquared } = trendData;

  if (rSquared < 0.1) {
    return null; // No significant trend
  }

  const directionIcon = direction === 'up' ? '\u2197' : direction === 'down' ? '\u2198' : '\u2192';
  const directionColor =
    direction === 'up'
      ? 'text-green-600'
      : direction === 'down'
        ? 'text-red-600'
        : 'text-gray-600';

  const strength = rSquared >= 0.7 ? 'Strong' : rSquared >= 0.4 ? 'Moderate' : 'Weak';

  return (
    <div className={`flex items-center gap-2 text-sm ${className}`}>
      <span className={`text-lg ${directionColor}`}>{directionIcon}</span>
      <span className="text-gray-700">
        {strength} {direction === 'stable' ? '' : direction} trend
      </span>
      <span className="text-gray-500 text-xs">
        (R² = {rSquared.toFixed(2)})
      </span>
    </div>
  );
}

/**
 * TrendLineLegend Component
 *
 * A small legend item for the trend line.
 */
export interface TrendLineLegendProps {
  visible?: boolean;
  color?: string;
  label?: string;
  className?: string;
}

export function TrendLineLegend({
  visible = true,
  color = CHART_COLORS.secondary,
  label = 'Trend Line',
  className = '',
}: TrendLineLegendProps) {
  if (!visible) return null;

  return (
    <div className={`flex items-center gap-2 text-xs text-gray-600 ${className}`}>
      <svg width="24" height="2" className="flex-shrink-0">
        <line
          x1="0"
          y1="1"
          x2="24"
          y2="1"
          stroke={color}
          strokeWidth="2"
          strokeDasharray="6 3"
        />
      </svg>
      <span>{label}</span>
    </div>
  );
}

/**
 * useTrendLineToggle Hook
 *
 * A convenience hook for managing trend line visibility state.
 */
import { useState, useCallback } from 'react';

export function useTrendLineToggle(initialVisible: boolean = false) {
  const [isVisible, setIsVisible] = useState(initialVisible);

  const toggle = useCallback(() => {
    setIsVisible(prev => !prev);
  }, []);

  const show = useCallback(() => {
    setIsVisible(true);
  }, []);

  const hide = useCallback(() => {
    setIsVisible(false);
  }, []);

  return {
    isVisible,
    toggle,
    show,
    hide,
    setIsVisible,
  };
}

export default TrendLine;
