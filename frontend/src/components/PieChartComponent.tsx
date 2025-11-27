/**
 * PieChartComponent
 *
 * Renders categorical data using Recharts PieChart.
 * Optimized for small datasets (2-12 categories).
 */

import { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface PieChartComponentProps {
  data: any[];
  categoryColumn: string;
  valueColumn: string;
  height?: number;
  variant?: 'pie' | 'donut';
}

const CHART_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#84cc16', // lime-500
  '#f97316', // orange-500
  '#a855f7', // purple-500
  '#14b8a6', // teal-500
  '#f43f5e', // rose-500
];

export default function PieChartComponent({
  data,
  categoryColumn,
  valueColumn,
  height = 400,
  variant = 'pie',
}: PieChartComponentProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  // Transform data for Recharts PieChart
  const chartData = data.map((row) => ({
    name: row[categoryColumn]?.toString() || 'Unknown',
    value: typeof row[valueColumn] === 'number' ? row[valueColumn] : 0,
  }));

  // Calculate total for percentage display
  const total = chartData.reduce((sum, entry) => sum + entry.value, 0);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0];
    const percentage = total > 0 ? ((data.value / total) * 100).toFixed(1) : '0.0';

    return (
      <div className="bg-white px-3 py-2 border border-gray-200 rounded shadow-lg">
        <p className="text-sm font-medium text-gray-900">{data.name}</p>
        <p className="text-xs text-gray-700">
          Value: <span className="font-medium">{data.value.toLocaleString()}</span>
        </p>
        <p className="text-xs text-gray-700">
          Share: <span className="font-medium">{percentage}%</span>
        </p>
      </div>
    );
  };

  // Custom label renderer
  const renderLabel = (entry: any) => {
    const percentage = total > 0 ? ((entry.value / total) * 100).toFixed(0) : '0';
    return `${percentage}%`;
  };

  // Handle pie slice click
  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(null);
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={chartData.length <= 8}
          label={chartData.length <= 8 ? renderLabel : false}
          outerRadius={variant === 'donut' ? 120 : 140}
          innerRadius={variant === 'donut' ? 60 : 0}
          fill="#8884d8"
          dataKey="value"
          onMouseEnter={onPieEnter}
          onMouseLeave={onPieLeave}
        >
          {chartData.map((_, index) => (
            <Cell
              key={`cell-${index}`}
              fill={CHART_COLORS[index % CHART_COLORS.length]}
              opacity={activeIndex === null || activeIndex === index ? 1 : 0.6}
              style={{
                cursor: 'pointer',
                transition: 'opacity 0.2s',
              }}
            />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          verticalAlign="bottom"
          height={36}
          wrapperStyle={{ fontSize: '12px' }}
          formatter={(value, entry: any) => {
            const percentage = total > 0 ? ((entry.payload.value / total) * 100).toFixed(1) : '0.0';
            return `${value} (${percentage}%)`;
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
