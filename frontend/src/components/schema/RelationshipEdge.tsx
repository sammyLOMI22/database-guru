/**
 * RelationshipEdge - Custom React Flow edge for FK relationships.
 *
 * Displays cardinality markers and relationship details.
 * Supports explicit (solid) and inferred (dashed) relationship styles.
 */

import React, { memo } from 'react';
import {
  EdgeProps,
  getBezierPath,
  EdgeLabelRenderer,
} from 'reactflow';
import type { RelationshipEdgeData } from '../../types/erDiagram';

interface RelationshipEdgeProps extends EdgeProps<RelationshipEdgeData> { }

const RelationshipEdge: React.FC<RelationshipEdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  style,
}) => {
  const {
    sourceColumn,
    targetColumn,
    cardinality,
    source: relationshipSource,
    isHighlighted,
    isDarkMode,
  } = data || {
    sourceColumn: '',
    targetColumn: '',
    cardinality: 'one-to-many',
    source: 'explicit',
    isHighlighted: false,
    isDarkMode: false,
  };

  // Calculate the bezier path
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Determine stroke style based on relationship type
  const isInferred = relationshipSource === 'inferred';
  const strokeDasharray = isInferred ? '5,5' : undefined;

  // Determine color based on state
  const strokeColor = isHighlighted
    ? '#FBBF24'
    : selected
      ? '#3B82F6'
      : isDarkMode
        ? 'rgba(107, 114, 128, 0.4)'
        : '#9CA3AF';

  const strokeWidth = selected || isHighlighted ? 2.5 : 1.5;

  // Determine animation
  const edgeClassName = isHighlighted ? 'edge-animate' : '';

  // Cardinality marker size
  const markerSize = 8;

  return (
    <>
      {/* Main edge path */}
      <path
        id={id}
        d={edgePath}
        fill="none"
        className={edgeClassName}
        style={{
          ...style,
          stroke: strokeColor,
          strokeWidth,
          strokeDasharray,
          filter: isHighlighted ? 'drop-shadow(0 0 8px rgba(251, 191, 36, 0.4))' : 'none',
          transition: 'stroke 0.3s, stroke-width 0.3s',
        }}
      />

      {/* Cardinality markers */}
      <EdgeLabelRenderer>
        {/* Source side marker (many side for one-to-many) */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${sourceX}px, ${sourceY + 15}px)`,
            pointerEvents: 'none',
          }}
        >
          {cardinality === 'one-to-many' || cardinality === 'many-to-many' ? (
            <ManyMarker size={markerSize} color={strokeColor} />
          ) : (
            <OneMarker size={markerSize} color={strokeColor} />
          )}
        </div>

        {/* Target side marker (one side for one-to-many) */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${targetX}px, ${targetY - 15}px)`,
            pointerEvents: 'none',
          }}
        >
          {cardinality === 'many-to-many' ? (
            <ManyMarker size={markerSize} color={strokeColor} />
          ) : (
            <OneMarker size={markerSize} color={strokeColor} />
          )}
        </div>

        {/* Relationship label (shown on hover/select) */}
        {(selected || isHighlighted) && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
            }}
            className={`
              px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-tight
              ${isDarkMode ? 'glass-panel text-gray-200' : 'bg-white text-gray-700 shadow-lg'}
              border border-blue-500/30
              flex items-center gap-1.5
            `}
          >
            <span className="text-blue-400 opacity-80">{sourceColumn}</span>
            <span className="text-gray-500">→</span>
            <span className="text-indigo-400 opacity-80">{targetColumn}</span>
            {isInferred && (
              <span className="ml-0.5 text-yellow-500" title="Inferred relationship">
                ✧
              </span>
            )}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
};

/**
 * "One" side cardinality marker (single line).
 */
const OneMarker: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 10 10">
    <line
      x1="5"
      y1="0"
      x2="5"
      y2="10"
      stroke={color}
      strokeWidth="2"
    />
  </svg>
);

/**
 * "Many" side cardinality marker (crow's foot).
 */
const ManyMarker: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 10 10">
    {/* Crow's foot shape */}
    <line x1="5" y1="5" x2="0" y2="0" stroke={color} strokeWidth="1.5" />
    <line x1="5" y1="5" x2="10" y2="0" stroke={color} strokeWidth="1.5" />
    <line x1="5" y1="5" x2="5" y2="10" stroke={color} strokeWidth="1.5" />
  </svg>
);

export default memo(RelationshipEdge);
