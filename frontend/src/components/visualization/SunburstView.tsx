/**
 * Sunburst Chart Component
 *
 * Displays hierarchical data as a sunburst (radial treemap).
 * The center represents the root, with rings expanding outward for each level.
 */

import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import {
  prepareSunburstData,
  HIERARCHICAL_COLORS,
  SunburstNode,
} from '../../utils/hierarchicalChartUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

interface SunburstViewProps {
  data: Record<string, unknown>[];
  categoryColumns: string[];
  valueColumn: string;
  title?: string;
  height?: number;
  animate?: boolean;
}

interface FlattenedNode {
  name: string;
  value: number;
  depth: number;
  color: string;
  path: string[];
  parent: string;
  [key: string]: unknown; // Index signature for Recharts compatibility
}

/**
 * Flattens hierarchical sunburst data into rings for Pie charts
 */
function flattenToRings(
  node: SunburstNode,
  depth: number = 0,
  path: string[] = [],
  parent: string = '',
  colorIndex: number = 0
): FlattenedNode[][] {
  const rings: FlattenedNode[][] = [];

  // Skip root node for display
  if (depth > 0) {
    if (!rings[depth - 1]) rings[depth - 1] = [];
    rings[depth - 1].push({
      name: node.name,
      value: node.value || 0,
      depth,
      color: HIERARCHICAL_COLORS[colorIndex % HIERARCHICAL_COLORS.length],
      path: [...path, node.name],
      parent,
    });
  }

  if (node.children) {
    node.children.forEach((child, index) => {
      const childRings = flattenToRings(
        child,
        depth + 1,
        depth > 0 ? [...path, node.name] : path,
        node.name,
        depth === 0 ? index : colorIndex
      );
      childRings.forEach((ring, ringIndex) => {
        if (!rings[ringIndex]) rings[ringIndex] = [];
        rings[ringIndex].push(...ring);
      });
    });
  }

  return rings;
}

export const SunburstView: React.FC<SunburstViewProps> = ({
  data,
  categoryColumns,
  valueColumn,
  title,
  height = 350,
  animate = true,
}) => {
  const { isDarkMode } = useDarkMode();
  const { rings, maxDepth } = useMemo(() => {
    if (!data || data.length === 0 || categoryColumns.length === 0) {
      return { rings: [], maxDepth: 0 };
    }

    const sunburstData = prepareSunburstData(data, categoryColumns, valueColumn);
    const flatRings = flattenToRings(sunburstData);

    return {
      rings: flatRings,
      maxDepth: flatRings.length,
    };
  }, [data, categoryColumns, valueColumn]);

  if (!rings || rings.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400">
        No hierarchical data available for sunburst chart
      </div>
    );
  }

  // Calculate radius for each ring
  const baseRadius = 40;
  const ringWidth = Math.min(35, (height / 2 - baseRadius - 30) / maxDepth);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-colors">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{title}</h4>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          {rings.map((ringData, ringIndex) => (
            <Pie
              key={`ring-${ringIndex}`}
              data={ringData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={baseRadius + ringIndex * ringWidth}
              outerRadius={baseRadius + (ringIndex + 1) * ringWidth - 2}
              paddingAngle={1}
              isAnimationActive={animate}
            >
              {ringData.map((entry, index) => (
                <Cell
                  key={`cell-${ringIndex}-${index}`}
                  fill={entry.color}
                  stroke={isDarkMode ? '#374151' : '#fff'}
                  strokeWidth={1}
                  style={{ cursor: 'pointer' }}
                />
              ))}
            </Pie>
          ))}

          <Tooltip
            content={({ payload }) => {
              if (!payload || payload.length === 0) return null;
              const item = payload[0].payload as FlattenedNode;
              return (
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-sm">
                  <div className="font-medium text-gray-900 dark:text-gray-100">{item.name}</div>
                  <div className="text-gray-600 dark:text-gray-400 mt-1">
                    {valueColumn}: {item.value?.toLocaleString()}
                  </div>
                  {item.path && item.path.length > 1 && (
                    <div className="text-gray-500 dark:text-gray-400 text-xs mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                      {item.path.join(' → ')}
                    </div>
                  )}
                </div>
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend - show first ring items */}
      {rings[0] && (
        <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          {rings[0].slice(0, 8).map((item) => (
            <div key={item.name} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: item.color }}
              />
              <span>{item.name}</span>
            </div>
          ))}
          {rings[0].length > 8 && (
            <span className="text-xs text-gray-400 dark:text-gray-400">+{rings[0].length - 8} more</span>
          )}
        </div>
      )}

      {/* Depth indicator */}
      <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
        <span>Hierarchy depth: {maxDepth} level{maxDepth !== 1 ? 's' : ''}</span>
        <span className="text-gray-300 dark:text-gray-700">|</span>
        <span>Inner ring = top level, outer rings = sub-categories</span>
      </div>
    </div>
  );
};

export default SunburstView;
