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
        ? 'rgba(96, 165, 250, 0.4)'
        : 'rgba(59, 130, 246, 0.3)';

  const strokeWidth = selected || isHighlighted ? 3 : 2;

  // Determine animation
  const edgeClassName = (selected || isHighlighted) ? 'edge-animate' : '';

  // Cardinality marker size
  const markerSize = 12;

  return (
    <>
      {/* Background interaction path (wider for easier clicking) */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        className="cursor-pointer"
      />

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
          filter: isHighlighted || selected
            ? `drop-shadow(0 0 12px ${selected ? 'rgba(59, 130, 246, 0.6)' : 'rgba(251, 191, 36, 0.6)'})`
            : 'none',
          transition: 'stroke 0.5s, stroke-width 0.5s, filter 0.5s',
        }}
      />

      {/* Cardinality markers */}
      <EdgeLabelRenderer>
        {/* Source side marker */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${sourceX}px, ${sourceY + 18}px)`,
            pointerEvents: 'none',
          }}
          className="transition-opacity duration-300"
        >
          {cardinality === 'one-to-many' || cardinality === 'many-to-many' ? (
            <ManyMarker size={markerSize} color={strokeColor} />
          ) : (
            <OneMarker size={markerSize} color={strokeColor} />
          )}
        </div>

        {/* Target side marker */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${targetX}px, ${targetY - 18}px)`,
            pointerEvents: 'none',
          }}
          className="transition-opacity duration-300"
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
              px-3 py-1.5 rounded-xl text-[10px] font-extrabold tracking-wider uppercase
              ${isDarkMode ? 'glass-node text-white border-blue-500/50' : 'bg-white text-gray-800 shadow-2xl border-blue-200'}
              animate-fadeIn flex items-center gap-2
            `}
          >
            <span className="text-blue-500">{sourceColumn}</span>
            <span className="opacity-40">→</span>
            <span className="text-indigo-500">{targetColumn}</span>
            {isInferred && (
              <span className="ml-1 px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-500 text-[8px]" title="Inferred relationship">
                AI INFERRED
              </span>
            )}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
};

/**
 * "One" side cardinality marker.
 */
const OneMarker: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="drop-shadow-sm">
    <circle cx="12" cy="12" r="4" fill={color} />
    <circle cx="12" cy="12" r="8" stroke={color} strokeWidth="2" strokeOpacity="0.3" />
  </svg>
);

/**
 * "Many" side cardinality marker.
 */
const ManyMarker: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="drop-shadow-sm">
    <path d="M12 4L12 20M4 12L20 12" stroke={color} strokeWidth="3" strokeLinecap="round" />
    <path d="M7 7L17 17M17 7L7 17" stroke={color} strokeWidth="3" strokeLinecap="round" />
  </svg>
);

export default memo(RelationshipEdge);
