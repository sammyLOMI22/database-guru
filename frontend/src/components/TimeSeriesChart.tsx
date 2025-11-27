/**
 * TimeSeriesChart Component
 *
 * Renders time-series data using Recharts LineChart.
 * Supports multiple value columns with automatic color assignment.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TimeSeriesChartProps {
  data: any[];
  timeColumn: string;
  valueColumns: string[];
  height?: number;
}

const CHART_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
];

export default function TimeSeriesChart({
  data,
  timeColumn,
  valueColumns,
  height = 400,
}: TimeSeriesChartProps) {
  // Format data for Recharts (ensure time column is properly formatted)
  const formattedData = data.map((row) => {
    const timeValue = row[timeColumn];
    let displayTime = timeValue;

    // Format date/timestamp for display
    if (timeValue) {
      try {
        const date = new Date(timeValue);
        if (!isNaN(date.getTime())) {
          // Format as readable date string
          displayTime = date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
          });
        }
      } catch (e) {
        // Keep original value if parsing fails
      }
    }

    return {
      ...row,
      [timeColumn]: displayTime,
    };
  });

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <div className="bg-white px-3 py-2 border border-gray-200 rounded shadow-lg">
        <p className="text-sm font-medium text-gray-900 mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-xs text-gray-700">
            <span style={{ color: entry.color }} className="font-medium">
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
      <LineChart
        data={formattedData}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey={timeColumn}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          angle={-45}
          textAnchor="end"
          height={60}
        />
        <YAxis
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          tickFormatter={(value) =>
            typeof value === 'number' ? value.toLocaleString() : value
          }
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '12px' }}
          iconType="line"
        />
        {valueColumns.map((column, index) => (
          <Line
            key={column}
            type="monotone"
            dataKey={column}
            stroke={CHART_COLORS[index % CHART_COLORS.length]}
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            name={column}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
