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
  Route,
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
  /** Whether to show query path overlay */
  showQueryPath?: boolean;
  /** Callback when query path toggle changes */
  onShowQueryPathChange?: (show: boolean) => void;
  /** Whether there is a last query to highlight */
  hasLastQuery?: boolean;
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
  showQueryPath,
  onShowQueryPathChange,
  hasLastQuery,
  onExpandAll,
  onCollapseAll,
  onFitView,
}) => {
  const { isDarkMode } = useDarkMode();

  const buttonBaseClass = `
    p-2 rounded-lg transition-all duration-200
    ${isDarkMode
      ? 'hover:bg-blue-500/20 text-gray-400 hover:text-blue-300'
      : 'hover:bg-blue-50 text-gray-600 hover:text-blue-600'}
  `;

  const buttonActiveClass = `
    ${isDarkMode ? 'bg-blue-600/30 text-blue-400' : 'bg-blue-100 text-blue-700 font-bold'}
  `;

  return (
    <div
      className={`
        flex items-center gap-1.5 p-1 rounded-xl shadow-lg
        ${isDarkMode
          ? 'bg-gray-800/40 backdrop-blur-md border border-gray-700/50'
          : 'bg-white/60 backdrop-blur-md border border-gray-200'}
      `}
    >
      {/* Layout direction toggle */}
      <div
        className={`
          flex items-center rounded-lg p-0.5
          ${isDarkMode ? 'bg-gray-900/40' : 'bg-gray-100'}
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

      {/* Query path overlay toggle */}
      {onShowQueryPathChange && (
        <button
          onClick={() => onShowQueryPathChange(!showQueryPath)}
          className={`${buttonBaseClass} ${showQueryPath ? buttonActiveClass : ''} ${!hasLastQuery ? 'opacity-40 cursor-not-allowed' : ''}`}
          title={hasLastQuery ? (showQueryPath ? 'Hide query path' : 'Highlight tables from last query') : 'No query to highlight'}
          disabled={!hasLastQuery}
        >
          <Route className="w-4 h-4" />
        </button>
      )}

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
