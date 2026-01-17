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
  BaseEdge,
} from 'reactflow';
import type { RelationshipEdgeData } from '../../types/erDiagram';
import { useDarkMode } from '../../hooks/useDarkMode';

interface RelationshipEdgeProps extends EdgeProps<RelationshipEdgeData> {}

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
  const { isDarkMode } = useDarkMode();

  const {
    sourceColumn,
    targetColumn,
    cardinality,
    source: relationshipSource,
    isHighlighted,
  } = data || {
    sourceColumn: '',
    targetColumn: '',
    cardinality: 'one-to-many',
    source: 'explicit',
    isHighlighted: false,
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
    ? '#FBBF24' // yellow for highlighted
    : selected
    ? '#3B82F6' // blue for selected
    : isDarkMode
    ? '#6B7280' // gray-500 for dark mode
    : '#9CA3AF'; // gray-400 for light mode

  const strokeWidth = selected || isHighlighted ? 2 : 1.5;

  // Cardinality marker size
  const markerSize = 8;

  return (
    <>
      {/* Main edge path */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: strokeColor,
          strokeWidth,
          strokeDasharray,
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
              px-2 py-1 rounded text-xs font-mono
              ${isDarkMode ? 'bg-gray-800 text-gray-200' : 'bg-white text-gray-700'}
              border ${isDarkMode ? 'border-gray-600' : 'border-gray-300'}
              shadow-sm
            `}
          >
            <span className="text-purple-500">{sourceColumn}</span>
            <span className="mx-1">→</span>
            <span className="text-blue-500">{targetColumn}</span>
            {isInferred && (
              <span className="ml-1 text-gray-400" title="Inferred relationship">
                *
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
