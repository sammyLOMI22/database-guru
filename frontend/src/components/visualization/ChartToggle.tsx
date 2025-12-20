/**
 * Chart Toggle Component
 *
 * Toggle buttons to switch between table and chart view,
 * with optional chart type selector dropdown.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Table, BarChart2, ChevronDown, TrendingUp, PieChart, ScatterChart } from 'lucide-react';
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
};

const chartTypeIcons: Record<ChartType, React.ReactNode> = {
  bar: <BarChart2 className="w-4 h-4" />,
  line: <TrendingUp className="w-4 h-4" />,
  pie: <PieChart className="w-4 h-4" />,
  scatter: <ScatterChart className="w-4 h-4" />,
  table: <Table className="w-4 h-4" />,
};

const availableChartTypes: ChartType[] = ['bar', 'line', 'pie', 'scatter'];

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
    <div className="inline-flex items-center gap-1">
      <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
        {/* Table View Button */}
        <button
          onClick={() => onModeChange('table')}
          className={`
            inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md
            transition-all duration-150
            ${
              mode === 'table'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }
          `}
          title="View as table"
        >
          <Table className="w-4 h-4" />
          <span className="hidden sm:inline">Table</span>
        </button>

        {/* Chart View Button */}
        <button
          onClick={() => chartAvailable && onModeChange('chart')}
          disabled={!chartAvailable}
          className={`
            inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md
            transition-all duration-150
            ${
              !chartAvailable
                ? 'text-gray-400 cursor-not-allowed'
                : mode === 'chart'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }
          `}
          title={
            chartAvailable
              ? `View as ${effectiveChartType ? chartTypeLabels[effectiveChartType] : 'chart'}`
              : 'No chart available for this data'
          }
        >
          {effectiveChartType && effectiveChartType !== 'table'
            ? chartTypeIcons[effectiveChartType]
            : <BarChart2 className="w-4 h-4" />}
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
            <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              <div className="py-1">
                <div className="px-3 py-1.5 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Chart Type
                </div>
                {availableChartTypes.map((type) => (
                  <button
                    key={type}
                    onClick={() => handleChartTypeSelect(type)}
                    className={`
                      w-full flex items-center gap-2 px-3 py-2 text-sm text-left
                      ${effectiveChartType === type
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-50'}
                    `}
                  >
                    {chartTypeIcons[type]}
                    <span className="flex-1">{chartTypeLabels[type]}</span>
                    {chartType === type && (
                      <span className="text-xs text-blue-500 font-medium">(recommended)</span>
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
