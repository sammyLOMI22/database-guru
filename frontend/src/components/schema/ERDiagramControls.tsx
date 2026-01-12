/**
 * ERDiagramControls - Toolbar for ER diagram controls.
 *
 * Provides layout direction, expand/collapse, and view controls.
 */

import React from 'react';
import {
  ArrowDown,
  ArrowRight,
  Maximize2,
  Minimize2,
  Focus,
  Link2,
  Link2Off,
} from 'lucide-react';
import type { LayoutDirection } from '../../types/erDiagram';
import { useDarkMode } from '../../hooks/useDarkMode';

interface ERDiagramControlsProps {
  /** Current layout direction */
  layoutDirection: LayoutDirection;
  /** Callback when layout direction changes */
  onLayoutChange: (direction: LayoutDirection) => void;
  /** Whether to show inferred relationships */
  showInferred: boolean;
  /** Callback when show inferred changes */
  onShowInferredChange: (show: boolean) => void;
  /** Expand all nodes */
  onExpandAll: () => void;
  /** Collapse all nodes */
  onCollapseAll: () => void;
  /** Fit diagram to view */
  onFitView: () => void;
}

const ERDiagramControls: React.FC<ERDiagramControlsProps> = ({
  layoutDirection,
  onLayoutChange,
  showInferred,
  onShowInferredChange,
  onExpandAll,
  onCollapseAll,
  onFitView,
}) => {
  const { isDarkMode } = useDarkMode();

  const buttonBaseClass = `
    p-1.5 rounded transition-colors
    ${isDarkMode
      ? 'hover:bg-gray-700 text-gray-400 hover:text-gray-200'
      : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800'}
  `;

  const buttonActiveClass = `
    ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-900'}
  `;

  return (
    <div className="flex items-center gap-2">
      {/* Layout direction toggle */}
      <div
        className={`
          flex items-center rounded-lg p-0.5
          ${isDarkMode ? 'bg-gray-700' : 'bg-gray-200'}
        `}
      >
        <button
          onClick={() => onLayoutChange('TB')}
          className={`${buttonBaseClass} ${layoutDirection === 'TB' ? buttonActiveClass : ''}`}
          title="Top to bottom layout"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
        <button
          onClick={() => onLayoutChange('LR')}
          className={`${buttonBaseClass} ${layoutDirection === 'LR' ? buttonActiveClass : ''}`}
          title="Left to right layout"
        >
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Separator */}
      <div
        className={`w-px h-5 ${isDarkMode ? 'bg-gray-600' : 'bg-gray-300'}`}
      />

      {/* Inferred relationships toggle */}
      <button
        onClick={() => onShowInferredChange(!showInferred)}
        className={`${buttonBaseClass} ${showInferred ? buttonActiveClass : ''}`}
        title={showInferred ? 'Hide inferred relationships' : 'Show inferred relationships'}
      >
        {showInferred ? (
          <Link2 className="w-4 h-4" />
        ) : (
          <Link2Off className="w-4 h-4" />
        )}
      </button>

      {/* Separator */}
      <div
        className={`w-px h-5 ${isDarkMode ? 'bg-gray-600' : 'bg-gray-300'}`}
      />

      {/* Expand/Collapse all */}
      <button
        onClick={onExpandAll}
        className={buttonBaseClass}
        title="Expand all tables"
      >
        <Maximize2 className="w-4 h-4" />
      </button>
      <button
        onClick={onCollapseAll}
        className={buttonBaseClass}
        title="Collapse all tables"
      >
        <Minimize2 className="w-4 h-4" />
      </button>

      {/* Separator */}
      <div
        className={`w-px h-5 ${isDarkMode ? 'bg-gray-600' : 'bg-gray-300'}`}
      />

      {/* Fit to view */}
      <button
        onClick={onFitView}
        className={buttonBaseClass}
        title="Fit diagram to view"
      >
        <Focus className="w-4 h-4" />
      </button>
    </div>
  );
};

export default ERDiagramControls;
