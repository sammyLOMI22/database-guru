/**
 * LineageEdge - Custom edge with animated flow direction.
 *
 * Shows data flow with animated dashes and optional label on hover.
 */

import React from 'react';
import {
  BaseEdge,
  EdgeProps,
  getBezierPath,
  EdgeLabelRenderer,
} from 'reactflow';

interface LineageEdgeData {
  label?: string | null;
  edgeType: string;
  isDarkMode: boolean;
}

const EDGE_COLORS: Record<string, string> = {
  direct: '#6366f1',    // indigo
  contains: '#3b82f6',  // blue
  feeds: '#a855f7',     // purple
  produces: '#22c55e',  // green
  data_flow: '#6b7280', // gray
};

const LineageEdge: React.FC<EdgeProps<LineageEdgeData>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style = {},
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeColor = EDGE_COLORS[data?.edgeType || 'data_flow'] || EDGE_COLORS.data_flow;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: edgeColor,
          strokeWidth: 2,
          strokeDasharray: '5 3',
          animation: 'dash 1s linear infinite',
        }}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="text-[10px] px-1.5 py-0.5 rounded bg-white/90 dark:bg-gray-800/90 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-mono shadow-sm"
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};

export default LineageEdge;
