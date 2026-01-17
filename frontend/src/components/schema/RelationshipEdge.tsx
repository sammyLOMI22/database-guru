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
  Position,
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
        {/* Source side marker (The "Many" or "One" side with the FK) */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${sourceX}px, ${sourceY + (sourcePosition === Position.Bottom ? 22 : -22)}px)`,
            pointerEvents: 'none',
          }}
          className="transition-all duration-300 z-10"
        >
          <CardinalityBadge
            type={cardinality === 'one-to-many' || cardinality === 'many-to-many' ? 'many' : 'one'}
            isDarkMode={isDarkMode}
            isHighlighted={!!(isHighlighted || selected)}
          />
        </div>

        {/* Target side marker (The "One" side with the PK) */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${targetX}px, ${targetY + (targetPosition === Position.Top ? -22 : 22)}px)`,
            pointerEvents: 'none',
          }}
          className="transition-all duration-300 z-10"
        >
          <CardinalityBadge
            type={cardinality === 'many-to-many' ? 'many' : 'one'}
            isDarkMode={isDarkMode}
            isHighlighted={!!(isHighlighted || selected)}
          />
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
              ${isDarkMode ? 'glass-node text-white border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.2)]' : 'bg-white text-gray-800 shadow-2xl border-blue-200'}
              animate-fadeIn flex items-center gap-2 z-20
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
 * Cardinality Badge component for better visibility.
 */
const CardinalityBadge: React.FC<{
  type: 'one' | 'many';
  isDarkMode: boolean;
  isHighlighted: boolean;
}> = ({ type, isDarkMode, isHighlighted }) => {
  const baseClasses = `
    flex items-center justify-center w-6 h-6 rounded-full border text-[10px] font-black
    transition-all duration-300 shadow-sm
  `;

  const themeClasses = isDarkMode
    ? `${isHighlighted ? 'bg-blue-500 text-white border-blue-400 glow-primary' : 'bg-gray-800/90 text-blue-300 border-gray-700 backdrop-blur-sm'}`
    : `${isHighlighted ? 'bg-blue-600 text-white border-blue-500 shadow-lg' : 'bg-white/90 text-blue-600 border-blue-100 backdrop-blur-sm'}`;

  return (
    <div className={`${baseClasses} ${themeClasses}`}>
      {type === 'one' ? '1' : 'N'}
    </div>
  );
};

export default memo(RelationshipEdge);
