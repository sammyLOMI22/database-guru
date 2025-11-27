/**
 * IndexStatistics - Charts and Metrics
 *
 * Visual analytics for index recommendations using AutoChart:
 * - Priority distribution chart
 * - Status breakdown chart
 * - Execution time trends
 * - Improvement potential analysis
 *
 * Integrates with Phase 4.1 Chart Visualization system
 */

import { useQuery } from '@tanstack/react-query';
import { AlertCircle, TrendingUp, Clock, Database } from 'lucide-react';
import { indexRecommendationsApi, IndexRecommendation, IndexRecommendationStats } from '../services/indexRecommendationsApi';
import AutoChart from './AutoChart';

export default function IndexStatistics() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery<IndexRecommendationStats>({
    queryKey: ['index-recommendations-stats'],
    queryFn: () => indexRecommendationsApi.getStats(),
    refetchInterval: 30000,
  });

  const { data: recommendations = [], isLoading: recsLoading } = useQuery<IndexRecommendation[]>({
    queryKey: ['index-recommendations-all'],
    queryFn: () => indexRecommendationsApi.listRecommendations({ limit: 500 }),
    refetchInterval: 30000,
  });

  if (statsLoading || recsLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-800">Failed to load statistics</h3>
            <p className="text-sm text-red-700 mt-1">
              {statsError instanceof Error ? statsError.message : 'Unknown error'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const priorityData = [
    { priority: 'High', count: stats?.by_priority.high || 0 },
    { priority: 'Medium', count: stats?.by_priority.medium || 0 },
    { priority: 'Low', count: stats?.by_priority.low || 0 },
  ];

  const statusData = [
    { status: 'Pending', count: stats?.by_status.pending || 0 },
    { status: 'Accepted', count: stats?.by_status.accepted || 0 },
    { status: 'Applied', count: stats?.by_status.applied || 0 },
    { status: 'Rejected', count: stats?.by_status.rejected || 0 },
    { status: 'Failed', count: stats?.by_status.failed || 0 },
  ];

  const databaseTypeData = Object.entries(stats?.by_database_type || {}).map(([type, count]) => ({
    database: type.charAt(0).toUpperCase() + type.slice(1),
    recommendations: count,
  }));

  // Top slow queries
  const topSlowQueries = recommendations
    .sort((a, b) => b.execution_time_ms - a.execution_time_ms)
    .slice(0, 10)
    .map((rec) => ({
      table: rec.table_name,
      execution_time_ms: rec.execution_time_ms,
      improvement_pct: rec.estimated_improvement_pct || 0,
    }));

  // Improvement potential data
  const improvementData = recommendations
    .filter((rec) => rec.estimated_improvement_pct !== null)
    .map((rec) => ({
      table: rec.table_name,
      improvement_pct: rec.estimated_improvement_pct || 0,
    }))
    .sort((a, b) => b.improvement_pct - a.improvement_pct)
    .slice(0, 15);

  return (
    <div className="p-6 space-y-6">
      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          icon={<Database className="w-5 h-5" />}
          label="Total Recommendations"
          value={stats?.total_recommendations || 0}
          color="text-purple-600 bg-purple-100"
        />
        <MetricCard
          icon={<Clock className="w-5 h-5" />}
          label="Avg Query Time"
          value={`${(stats?.avg_execution_time_ms || 0).toFixed(0)}ms`}
          color="text-amber-600 bg-amber-100"
        />
        <MetricCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Avg Improvement"
          value={stats?.avg_improvement_pct ? `${stats.avg_improvement_pct.toFixed(0)}%` : 'N/A'}
          color="text-green-600 bg-green-100"
        />
      </div>

      {/* Priority Distribution - AutoChart */}
      {priorityData.some((d) => d.count > 0) && (
        <AutoChart
          data={priorityData}
          title="Priority Distribution"
          allowManualOverride={true}
          showExporter={true}
        />
      )}

      {/* Status Breakdown - AutoChart */}
      {statusData.some((d) => d.count > 0) && (
        <AutoChart
          data={statusData}
          title="Status Breakdown"
          allowManualOverride={true}
          showExporter={true}
        />
      )}

      {/* Database Type Distribution - AutoChart */}
      {databaseTypeData.length > 0 && (
        <AutoChart
          data={databaseTypeData}
          title="Recommendations by Database Type"
          allowManualOverride={true}
          showExporter={true}
        />
      )}

      {/* Top Slow Queries - AutoChart */}
      {topSlowQueries.length > 0 && (
        <AutoChart
          data={topSlowQueries}
          title="Top 10 Slowest Queries"
          allowManualOverride={true}
          showExporter={true}
        />
      )}

      {/* Improvement Potential - AutoChart */}
      {improvementData.length > 0 && (
        <AutoChart
          data={improvementData}
          title="Estimated Performance Improvement by Table"
          allowManualOverride={true}
          showExporter={true}
        />
      )}

      {/* No Data State */}
      {stats?.total_recommendations === 0 && (
        <div className="text-center py-12">
          <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Statistics Available</h3>
          <p className="text-gray-500">
            Index recommendations will appear here once slow queries are detected
          </p>
        </div>
      )}
    </div>
  );
}

// Helper Component
function MetricCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-3">
        <div className={`${color} p-3 rounded-lg`}>{icon}</div>
        <div>
          <p className="text-sm text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}
