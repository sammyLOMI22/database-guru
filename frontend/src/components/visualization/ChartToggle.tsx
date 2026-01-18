/**
 * Chart Toggle Component
 *
 * Toggle buttons to switch between table and chart view,
 * with optional chart type selector dropdown.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import {
  Table,
  BarChart2,
  ChevronDown,
  TrendingUp,
  PieChart,
  ScatterChart,
  LayoutGrid,
  BarChart3,
  Activity,
  Circle,
  Sparkles,
} from 'lucide-react';
import { ChartType } from '../../utils/chartUtils';

export type ViewMode = 'table' | 'chart';

interface ChartToggleProps {
  mode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
  chartAvailable: boolean;
  chartType: ChartType | null;
  /** Currently selected chart type (defaults to recommended) */
  selectedChartType?: ChartType | null;
  /** Callback when user selects a different chart type */
  onChartTypeChange?: (chartType: ChartType) => void;
  /** Show chart type selector dropdown */
  showChartTypeSelector?: boolean;
}

const chartTypeLabels: Record<ChartType, string> = {
  bar: 'Bar Chart',
  line: 'Line Chart',
  pie: 'Pie Chart',
  scatter: 'Scatter Plot',
  table: 'Table',
  // Phase 10: Advanced Charts
  treemap: 'Treemap',
  sunburst: 'Sunburst',
  boxplot: 'Box Plot',
  histogram: 'Histogram',
  bubble: 'Bubble Chart',
  area: 'Area Chart',
};

const chartTypeIcons: Record<ChartType, React.ReactNode> = {
  bar: <BarChart2 className="w-4 h-4" />,
  line: <TrendingUp className="w-4 h-4" />,
  pie: <PieChart className="w-4 h-4" />,
  scatter: <ScatterChart className="w-4 h-4" />,
  table: <Table className="w-4 h-4" />,
  // Phase 10: Advanced Charts
  treemap: <LayoutGrid className="w-4 h-4" />,
  sunburst: <Circle className="w-4 h-4" />,
  boxplot: <BarChart3 className="w-4 h-4" />,
  histogram: <BarChart3 className="w-4 h-4" />,
  bubble: <Circle className="w-4 h-4" />,
  area: <Activity className="w-4 h-4" />,
};

// Basic chart types always available
const basicChartTypes: ChartType[] = ['bar', 'line', 'pie', 'scatter'];
// Advanced chart types (Phase 10)
const advancedChartTypes: ChartType[] = ['area', 'histogram', 'boxplot', 'treemap', 'sunburst', 'bubble'];
const availableChartTypes: ChartType[] = [...basicChartTypes, ...advancedChartTypes];

export const ChartToggle: React.FC<ChartToggleProps> = ({
  mode,
  onModeChange,
  chartAvailable,
  chartType,
  selectedChartType,
  onChartTypeChange,
  showChartTypeSelector = true,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Calculate dropdown position when opening
  const updateDropdownPosition = useCallback(() => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      const dropdownWidth = 208;
      let left = rect.right - dropdownWidth;

      // Keep within viewport
      if (left < 8) left = 8;
      if (left + dropdownWidth > window.innerWidth - 8) {
        left = window.innerWidth - dropdownWidth - 8;
      }

      setDropdownPosition({
        top: rect.bottom + 8,
        left: left,
      });
    }
  }, []);

  // Update position when dropdown opens
  useEffect(() => {
    if (dropdownOpen) {
      updateDropdownPosition();
    }
  }, [dropdownOpen, updateDropdownPosition]);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!dropdownOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        buttonRef.current && !buttonRef.current.contains(target) &&
        dropdownRef.current && !dropdownRef.current.contains(target)
      ) {
        setDropdownOpen(false);
      }
    };

    // Use setTimeout to avoid the click that opened the dropdown from closing it
    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  // Close on escape key
  useEffect(() => {
    if (!dropdownOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [dropdownOpen]);

  const effectiveChartType = selectedChartType || chartType;

  const handleChartTypeSelect = (type: ChartType) => {
    onChartTypeChange?.(type);
    setDropdownOpen(false);
    // Also switch to chart view if not already
    if (mode !== 'chart') {
      onModeChange('chart');
    }
  };

  const handleToggleDropdown = () => {
    setDropdownOpen(prev => !prev);
  };

  // Dropdown portal content
  const dropdownContent = dropdownOpen ? createPortal(
    <div
      ref={dropdownRef}
      className="fixed w-52 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl overflow-hidden"
      style={{
        top: dropdownPosition.top,
        left: dropdownPosition.left,
        zIndex: 99999,
      }}
    >
      <div className="py-1.5 max-h-[400px] overflow-y-auto">
        <div className="px-4 py-2 text-xs font-black text-gray-500 dark:text-gray-400 uppercase tracking-[0.2em]">
          Visualization
        </div>
        {availableChartTypes.map((type) => (
          <button
            key={type}
            onClick={() => handleChartTypeSelect(type)}
            className={`
              w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left
              transition-colors duration-200
              ${effectiveChartType === type
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}
            `}
          >
            <div className={`${effectiveChartType === type ? 'text-blue-500' : 'text-gray-400'}`}>
              {chartTypeIcons[type]}
            </div>
            <span className="flex-1 capitalize">{chartTypeLabels[type].replace(' Chart', '').replace(' Plot', '')}</span>
            {chartType === type && (
              <div className="p-1 bg-blue-500/10 rounded">
                <Sparkles className="w-3 h-3 text-blue-500" />
              </div>
            )}
          </button>
        ))}
      </div>
    </div>,
    document.body
  ) : null;

  return (
    <div className="inline-flex items-center gap-1.5 animate-fadeIn">
      <div className="inline-flex rounded-xl glass-card bg-gray-500/5 border-gray-500/10 p-1 shadow-inner">
        {/* Table View Button */}
        <button
          onClick={() => onModeChange('table')}
          className={`
            inline-flex items-center gap-2 px-3.5 py-1.5 text-[13px] font-bold rounded-lg
            transition-all duration-300
            ${mode === 'table'
              ? 'glass-card bg-white/40 dark:bg-white/10 text-gray-900 dark:text-gray-100 shadow-sm border-white/30 scale-105 z-10'
              : 'text-gray-500 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-white/10'
            }
          `}
          title="View as table"
        >
          <Table className={`w-4 h-4 transition-transform duration-300 ${mode === 'table' ? 'scale-110' : ''}`} />
          <span className="hidden sm:inline">Table</span>
        </button>

        {/* Chart View Button */}
        <button
          onClick={() => chartAvailable && onModeChange('chart')}
          disabled={!chartAvailable}
          className={`
            inline-flex items-center gap-2 px-3.5 py-1.5 text-[13px] font-bold rounded-lg
            transition-all duration-300
            ${!chartAvailable
              ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
              : mode === 'chart'
                ? 'glass-card bg-blue-500/20 text-blue-600 dark:text-blue-400 shadow-sm border-blue-500/20 scale-105 z-10 glow-sm'
                : 'text-gray-500 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-white/10'
            }
          `}
          title={
            chartAvailable
              ? `View as ${effectiveChartType ? chartTypeLabels[effectiveChartType] : 'chart'}`
              : 'No chart available for this data'
          }
        >
          {effectiveChartType && effectiveChartType !== 'table'
            ? React.cloneElement(chartTypeIcons[effectiveChartType] as React.ReactElement, {
              className: `w-4 h-4 transition-transform duration-300 ${mode === 'chart' ? 'scale-110' : ''}`
            })
            : <BarChart2 className={`w-4 h-4 transition-transform duration-300 ${mode === 'chart' ? 'scale-110' : ''}`} />}
          <span className="hidden sm:inline">
            {effectiveChartType && effectiveChartType !== 'table'
              ? chartTypeLabels[effectiveChartType].replace(' Chart', '').replace(' Plot', '')
              : 'Chart'}
          </span>
        </button>
      </div>

      {/* Chart Type Selector Dropdown Trigger */}
      {showChartTypeSelector && chartAvailable && onChartTypeChange && (
        <button
          ref={buttonRef}
          onClick={handleToggleDropdown}
          className={`inline-flex items-center gap-1 px-2 py-1.5 text-sm rounded-lg transition-colors glass-card border-gray-500/10 ${
            dropdownOpen
              ? 'text-blue-600 dark:text-blue-400 bg-blue-500/10'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
          title="Select chart type"
        >
          <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
        </button>
      )}

      {/* Dropdown rendered via portal */}
      {dropdownContent}
    </div>
  );
};

export default ChartToggle;
