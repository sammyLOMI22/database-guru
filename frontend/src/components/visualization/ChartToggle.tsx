/**
 * Chart Toggle Component
 *
 * Toggle buttons to switch between table and chart view.
 */

import React from 'react';
import { Table, BarChart2 } from 'lucide-react';
import { ChartType } from '../../utils/chartUtils';

export type ViewMode = 'table' | 'chart';

interface ChartToggleProps {
  mode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
  chartAvailable: boolean;
  chartType: ChartType | null;
}

const chartTypeIcons: Record<ChartType, string> = {
  bar: 'Bar Chart',
  line: 'Line Chart',
  pie: 'Pie Chart',
  scatter: 'Scatter Plot',
  table: 'Table',
};

export const ChartToggle: React.FC<ChartToggleProps> = ({
  mode,
  onModeChange,
  chartAvailable,
  chartType,
}) => {
  return (
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
            ? `View as ${chartType ? chartTypeIcons[chartType] : 'chart'}`
            : 'No chart available for this data'
        }
      >
        <BarChart2 className="w-4 h-4" />
        <span className="hidden sm:inline">Chart</span>
      </button>
    </div>
  );
};

export default ChartToggle;
