/**
 * Treemap Chart Component
 *
 * Displays hierarchical data as a treemap using Recharts.
 * Each rectangle's size represents the value, and color represents category.
 */

import React, { useMemo } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import {
  prepareTreemapData,
  assignColors,
  HIERARCHICAL_COLORS,
} from '../../utils/hierarchicalChartUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

interface TreemapViewProps {
  data: Record<string, unknown>[];
  categoryColumns: string[];
  valueColumn: string;
  title?: string;
  height?: number;
  animate?: boolean;
}

interface CustomContentProps {
  root?: unknown;
  depth?: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  index?: number;
  name?: string;
  value?: number;
  color?: string;
}

const CustomContent: React.FC<CustomContentProps> = ({
  depth = 0,
  x = 0,
  y = 0,
  width = 0,
  height = 0,
  name,
  value,
  color,
}) => {
  // Only render leaf nodes and first level
  if (depth === 0) return null;

  const fontSize = Math.min(12, Math.max(8, width / 10));
  const showLabel = width > 40 && height > 20;
  const showValue = width > 60 && height > 35;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color || HIERARCHICAL_COLORS[0]}
        stroke="#fff"
        strokeWidth={1}
        rx={1}
        style={{ cursor: 'pointer' }}
      />
      {showLabel && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showValue ? 6 : 0)}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={fontSize}
          fontWeight={500}
          style={{ pointerEvents: 'none' }}
        >
          {name && name.length > 15 ? name.substring(0, 12) + '...' : name}
        </text>
      )}
      {showValue && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 10}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={fontSize - 1}
          style={{ pointerEvents: 'none', opacity: 0.9 }}
        >
          {value?.toLocaleString()}
        </text>
      )}
    </g>
  );
};

export const TreemapView: React.FC<TreemapViewProps> = ({
  data,
  categoryColumns,
  valueColumn,
  title,
  height = 300,
  animate = true,
}) => {
  const { isDarkMode } = useDarkMode();
  const treemapData = useMemo(() => {
    if (!data || data.length === 0 || categoryColumns.length === 0) {
      return null;
    }
    const prepared = prepareTreemapData(data, categoryColumns, valueColumn);
    return assignColors(prepared);
  }, [data, categoryColumns, valueColumn]);

  if (!treemapData || !treemapData.children || treemapData.children.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        No hierarchical data available for treemap
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-colors">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <Treemap
          data={treemapData.children}
          dataKey="value"
          aspectRatio={4 / 3}
          stroke={isDarkMode ? '#374151' : '#fff'}
          fill={HIERARCHICAL_COLORS[0]}
          isAnimationActive={animate}
          content={<CustomContent />}
        >
          <Tooltip
            content={({ payload }) => {
              if (!payload || payload.length === 0) return null;
              const item = payload[0].payload;
              return (
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-2 text-sm">
                  <div className="font-medium text-gray-900 dark:text-gray-100">{item.name}</div>
                  <div className="text-gray-600 dark:text-gray-400">
                    {valueColumn}: {item.value?.toLocaleString()}
                  </div>
                  {item.path && item.path.length > 1 && (
                    <div className="text-gray-500 dark:text-gray-400 text-xs mt-1">
                      {item.path.join(' > ')}
                    </div>
                  )}
                </div>
              );
            }}
          />
        </Treemap>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
        {treemapData.children.slice(0, 8).map((child, index) => (
          <div key={child.name} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
            <div
              className="w-3 h-3 rounded"
              style={{ backgroundColor: HIERARCHICAL_COLORS[index % HIERARCHICAL_COLORS.length] }}
            />
            <span>{child.name}</span>
          </div>
        ))}
        {treemapData.children.length > 8 && (
          <span className="text-xs text-gray-400 dark:text-gray-400">+{treemapData.children.length - 8} more</span>
        )}
      </div>
    </div>
  );
};

export default TreemapView;
