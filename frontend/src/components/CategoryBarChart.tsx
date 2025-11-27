/**
 * CategoryBarChart Component
 *
 * Renders categorical data using Recharts BarChart.
 * Supports multiple value columns with grouped bars.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface CategoryBarChartProps {
  data: any[];
  categoryColumn: string;
  valueColumns: string[];
  height?: number;
  orientation?: 'vertical' | 'horizontal';
}

const CHART_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
];

export default function CategoryBarChart({
  data,
  categoryColumn,
  valueColumns,
  height = 400,
  orientation = 'vertical',
}: CategoryBarChartProps) {
  // Truncate long category names for display
  const formattedData = data.map((row) => ({
    ...row,
    [categoryColumn]:
      typeof row[categoryColumn] === 'string' && row[categoryColumn].length > 20
        ? row[categoryColumn].substring(0, 17) + '...'
        : row[categoryColumn],
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <div className="bg-white px-3 py-2 border border-gray-200 rounded shadow-lg">
        <p className="text-sm font-medium text-gray-900 mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-xs text-gray-700">
            <span style={{ color: entry.fill }} className="font-medium">
              {entry.name}:
            </span>{' '}
            {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={formattedData}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        layout={orientation === 'horizontal' ? 'horizontal' : 'vertical'}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        {orientation === 'vertical' ? (
          <>
            <XAxis
              dataKey={categoryColumn}
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) =>
                typeof value === 'number' ? value.toLocaleString() : value
              }
            />
          </>
        ) : (
          <>
            <XAxis
              type="number"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) =>
                typeof value === 'number' ? value.toLocaleString() : value
              }
            />
            <YAxis
              dataKey={categoryColumn}
              type="category"
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              width={100}
            />
          </>
        )}
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
        {valueColumns.map((column, index) => (
          <Bar
            key={column}
            dataKey={column}
            fill={CHART_COLORS[index % CHART_COLORS.length]}
            name={column}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
