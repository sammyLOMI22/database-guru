/**
 * OutlierMarkers Component
 *
 * Renders visual markers for statistical outliers on charts.
 * Outliers are points with z-score >= 2 (or custom threshold).
 */

import { ReferenceDot, Label } from 'recharts';
import { OutlierInfo } from '../../utils/chartIntelligence';

export interface OutlierMarkersProps {
  /** Array of detected outliers */
  outliers: OutlierInfo[];
  /** Whether outlier markers are visible */
  visible?: boolean;
  /** X-axis data key */
  xDataKey: string;
  /** Y-axis data key */
  yDataKey: string;
  /** Color for high outliers */
  highColor?: string;
  /** Color for low outliers */
  lowColor?: string;
  /** Size of the marker */
  markerSize?: number;
  /** Show labels on outliers */
  showLabels?: boolean;
}

/**
 * OutlierMarkers renders reference dots at outlier positions.
 *
 * Usage:
 * ```tsx
 * <LineChart data={data}>
 *   <Line dataKey="value" />
 *   <OutlierMarkers
 *     outliers={detectedOutliers}
 *     xDataKey="date"
 *     yDataKey="value"
 *     visible={showOutliers}
 *   />
 * </LineChart>
 * ```
 */
export function OutlierMarkers({
  outliers,
  visible = true,
  xDataKey,
  yDataKey: _yDataKey,
  highColor = '#ef4444', // red-500
  lowColor = '#3b82f6', // blue-500
  markerSize = 8,
  showLabels = false,
}: OutlierMarkersProps) {
  if (!visible || !outliers || outliers.length === 0) {
    return null;
  }

  return (
    <>
      {outliers.map((outlier, index) => {
        const xValue = outlier.row[xDataKey];
        const yValue = outlier.value;
        const color = outlier.isHigh ? highColor : lowColor;

        return (
          <ReferenceDot
            key={`outlier-${index}`}
            x={xValue as number | string}
            y={yValue}
            r={markerSize}
            fill={color}
            stroke="#fff"
            strokeWidth={2}
          >
            {showLabels && (
              <Label
                value={`z=${outlier.zScore.toFixed(1)}`}
                position="top"
                fill={color}
                fontSize={10}
              />
            )}
          </ReferenceDot>
        );
      })}
    </>
  );
}

/**
 * OutlierSummary Component
 *
 * Displays a summary of detected outliers.
 */
export interface OutlierSummaryProps {
  outliers: OutlierInfo[];
  className?: string;
}

export function OutlierSummary({ outliers, className = '' }: OutlierSummaryProps) {
  if (!outliers || outliers.length === 0) {
    return null;
  }

  const highOutliers = outliers.filter(o => o.isHigh);
  const lowOutliers = outliers.filter(o => !o.isHigh);

  return (
    <div className={`flex items-center gap-3 text-sm ${className}`}>
      <span className="text-gray-600">Outliers detected:</span>
      {highOutliers.length > 0 && (
        <span className="flex items-center gap-1 text-red-600">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          {highOutliers.length} high
        </span>
      )}
      {lowOutliers.length > 0 && (
        <span className="flex items-center gap-1 text-blue-600">
          <span className="w-2 h-2 rounded-full bg-blue-500" />
          {lowOutliers.length} low
        </span>
      )}
    </div>
  );
}

/**
 * OutlierLegend Component
 *
 * Legend items for outlier markers.
 */
export interface OutlierLegendProps {
  visible?: boolean;
  hasHigh?: boolean;
  hasLow?: boolean;
  highColor?: string;
  lowColor?: string;
  className?: string;
}

export function OutlierLegend({
  visible = true,
  hasHigh = true,
  hasLow = true,
  highColor = '#ef4444',
  lowColor = '#3b82f6',
  className = '',
}: OutlierLegendProps) {
  if (!visible || (!hasHigh && !hasLow)) {
    return null;
  }

  return (
    <div className={`flex items-center gap-4 text-xs text-gray-600 ${className}`}>
      {hasHigh && (
        <div className="flex items-center gap-1.5">
          <svg width="10" height="10">
            <circle cx="5" cy="5" r="4" fill={highColor} stroke="#fff" strokeWidth="1" />
          </svg>
          <span>High Outlier</span>
        </div>
      )}
      {hasLow && (
        <div className="flex items-center gap-1.5">
          <svg width="10" height="10">
            <circle cx="5" cy="5" r="4" fill={lowColor} stroke="#fff" strokeWidth="1" />
          </svg>
          <span>Low Outlier</span>
        </div>
      )}
    </div>
  );
}

/**
 * OutlierTooltipContent Component
 *
 * Custom tooltip content for outlier points.
 */
export interface OutlierTooltipContentProps {
  outlier: OutlierInfo | null;
  valueLabel?: string;
}

export function OutlierTooltipContent({
  outlier,
  valueLabel = 'Value',
}: OutlierTooltipContentProps) {
  if (!outlier) return null;

  return (
    <div className="bg-white border border-gray-200 shadow-lg rounded-lg p-2 text-sm">
      <div className="font-medium text-gray-900 mb-1">
        {outlier.isHigh ? 'High' : 'Low'} Outlier
      </div>
      <div className="space-y-0.5 text-gray-600">
        <div>
          {valueLabel}: <span className="font-mono">{outlier.value.toFixed(2)}</span>
        </div>
        <div>
          Z-Score: <span className="font-mono">{outlier.zScore.toFixed(2)}</span>
        </div>
        <div className="text-xs text-gray-500">
          {Math.abs(outlier.zScore).toFixed(1)} standard deviations{' '}
          {outlier.isHigh ? 'above' : 'below'} mean
        </div>
      </div>
    </div>
  );
}

/**
 * useOutlierToggle Hook
 *
 * Convenience hook for managing outlier visibility state.
 */
import { useState, useCallback } from 'react';

export function useOutlierToggle(initialVisible: boolean = true) {
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

export default OutlierMarkers;
