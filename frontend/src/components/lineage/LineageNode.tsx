/**
 * LineageNode - Custom React Flow node for lineage graph.
 *
 * Node types:
 * - Source table: blue, table icon
 * - Source column: indigo, column reference
 * - Transformation: purple, function name
 * - Output column: green, result column
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import type { LineageNodeType, TransformationType } from '../../types/lineage';

interface LineageNodeData {
  id: string;
  node_type: LineageNodeType;
  label: string;
  table_name?: string | null;
  column_name?: string | null;
  expression?: string | null;
  transformation_type?: TransformationType | null;
  colors: { bg: string; border: string; text: string };
  isDarkMode: boolean;
}

const NODE_ICONS: Record<LineageNodeType, string> = {
  source_table: '🗂️',
  source_column: '📋',
  transformation: '⚙️',
  output_column: '📊',
};

const LineageNode: React.FC<NodeProps<LineageNodeData>> = ({ data, selected }) => {
  const { node_type, label, expression, transformation_type, colors, isDarkMode } = data;

  const icon = NODE_ICONS[node_type];
  const isTransform = node_type === 'transformation';

  return (
    <div
      className={`
        rounded-xl shadow-lg border-2 px-3 py-2 transition-all duration-300 min-w-[140px]
        ${selected ? 'ring-2 ring-indigo-400 ring-offset-2 scale-105' : ''}
        ${isDarkMode ? 'backdrop-blur-md' : ''}
        ${isTransform ? 'rotate-0' : ''}
      `}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: colors.border,
          width: 8,
          height: 8,
          border: '2px solid white',
        }}
      />

      {/* Content */}
      <div className="flex items-center gap-2">
        <span className="text-sm flex-shrink-0">{icon}</span>
        <div className="flex flex-col min-w-0">
          <span className="text-xs font-bold truncate max-w-[120px]" title={label}>
            {label}
          </span>
          {isTransform && transformation_type && (
            <span className="text-[10px] opacity-70 uppercase">
              {transformation_type}
            </span>
          )}
          {expression && !isTransform && (
            <span className="text-[10px] opacity-60 truncate max-w-[120px]" title={expression}>
              {expression}
            </span>
          )}
        </div>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: colors.border,
          width: 8,
          height: 8,
          border: '2px solid white',
        }}
      />
    </div>
  );
};

export default memo(LineageNode);
