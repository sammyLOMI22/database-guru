/**
 * Pie Chart Component
 *
 * Displays categorical distribution as a pie chart using Recharts.
 */

import React, { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { PIE_PALETTE, prepareChartData } from '../../utils/chartUtils';

interface PieChartViewProps {
  data: Record<string, unknown>[];
  xColumn: string;
  yColumn: string;
  title?: string;
  height?: number;
  showLegend?: boolean;
  animate?: boolean;
}

interface PieDataItem {
  name: string;
  value: number;
  [key: string]: unknown;
}

const RADIAN = Math.PI / 180;

interface LabelProps {
  cx?: number;
  cy?: number;
  midAngle?: number;
  innerRadius?: number;
  outerRadius?: number;
  percent?: number;
}

const renderCustomizedLabel = ({
  cx = 0,
  cy = 0,
  midAngle = 0,
  innerRadius = 0,
  outerRadius = 0,
  percent = 0,
}: LabelProps) => {
  // Only show label if percentage is significant
  if (percent < 0.05) return null;

  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={500}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export const PieChartView: React.FC<PieChartViewProps> = ({
  data,
  xColumn,
  yColumn,
  title,
  height = 300,
  showLegend = true,
  animate = true,
}) => {
  const chartData = useMemo((): PieDataItem[] => {
    const prepared = prepareChartData(data, xColumn, yColumn, 'pie', 20);
    // Transform to pie chart format with name and value
    return prepared.map((item) => ({
      ...item,
      name: String(item[xColumn] ?? 'Unknown'),
      value: Number(item[yColumn]) || 0,
    }));
  }, [data, xColumn, yColumn]);

  const total = useMemo(() => {
    return chartData.reduce((sum, item) => sum + (item.value || 0), 0);
  }, [chartData]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No data available for pie chart
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {title && (
        <h4 className="text-sm font-medium text-gray-700 mb-3">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomizedLabel}
            outerRadius={Math.min(height / 2 - 40, 120)}
            fill="#8884d8"
            dataKey="value"
            isAnimationActive={animate}
          >
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={PIE_PALETTE[index % PIE_PALETTE.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number | undefined, name: string | undefined) => [
              value !== undefined
                ? `${value.toLocaleString()} (${((value / total) * 100).toFixed(1)}%)`
                : '0',
              name ?? '',
            ]}
          />
          {showLegend && (
            <Legend
              layout="vertical"
              verticalAlign="middle"
              align="right"
              wrapperStyle={{ fontSize: 12 }}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
