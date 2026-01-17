/**
 * Chart Toggle Component
 *
 * Toggle buttons to switch between table and chart view,
 * with optional chart type selector dropdown.
 */

import React, { useState, useRef, useEffect } from 'react';
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
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const effectiveChartType = selectedChartType || chartType;

  const handleChartTypeSelect = (type: ChartType) => {
    onChartTypeChange?.(type);
    setDropdownOpen(false);
    // Also switch to chart view if not already
    if (mode !== 'chart') {
      onModeChange('chart');
    }
  };

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

      {/* Chart Type Selector Dropdown */}
      {showChartTypeSelector && chartAvailable && onChartTypeChange && (
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="inline-flex items-center gap-1 px-2 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            title="Select chart type"
          >
            <ChevronDown className={`w-4 h-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-52 glass-card bg-white/95 dark:bg-gray-900/95 border-gray-500/20 rounded-xl shadow-2xl z-50 overflow-hidden animate-scaleUp">
              <div className="py-1.5">
                <div className="px-4 py-2 text-[10px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-[0.2em]">
                  Visualization Selection
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
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-500/10'}
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
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChartToggle;
