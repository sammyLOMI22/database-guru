/**
 * IndexOverview - Stats Dashboard
 *
 * Summary view of index recommendations with:
 * - Key metrics cards (total, pending, applied, avg improvement)
 * - Priority breakdown chart
 * - Recent recommendations
 * - Quick actions
 */

import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle, Clock, TrendingUp, Zap } from 'lucide-react';
import { indexRecommendationsApi, IndexRecommendationStats } from '../services/indexRecommendationsApi';

interface IndexOverviewProps {
  onNavigate: (tab: 'recommendations' | 'statistics') => void;
}

export default function IndexOverview({ onNavigate }: IndexOverviewProps) {
  const { data: stats, isLoading, error } = useQuery<IndexRecommendationStats>({
    queryKey: ['index-recommendations-stats'],
    queryFn: () => indexRecommendationsApi.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-800">Failed to load statistics</h3>
            <p className="text-sm text-red-700 mt-1">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Recommendations */}
        <StatsCard
          icon={<Zap className="w-5 h-5" />}
          iconColor="text-purple-600"
          iconBg="bg-purple-100"
          label="Total Recommendations"
          value={stats?.total_recommendations || 0}
          subtitle="All time"
        />

        {/* Pending */}
        <StatsCard
          icon={<Clock className="w-5 h-5" />}
          iconColor="text-amber-600"
          iconBg="bg-amber-100"
          label="Pending Review"
          value={stats?.total_pending || 0}
          subtitle="Awaiting action"
        />

        {/* Applied */}
        <StatsCard
          icon={<CheckCircle className="w-5 h-5" />}
          iconColor="text-green-600"
          iconBg="bg-green-100"
          label="Applied"
          value={stats?.total_applied || 0}
          subtitle="Successfully implemented"
        />

        {/* Avg Improvement */}
        <StatsCard
          icon={<TrendingUp className="w-5 h-5" />}
          iconColor="text-blue-600"
          iconBg="bg-blue-100"
          label="Avg Improvement"
          value={
            stats?.avg_improvement_pct
              ? `${stats.avg_improvement_pct.toFixed(0)}%`
              : 'N/A'
          }
          subtitle="Estimated performance gain"
        />
      </div>

      {/* Priority Breakdown */}
      {stats && (
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Priority Breakdown</h3>
          <div className="space-y-3">
            <PriorityBar
              label="High Priority"
              count={stats.by_priority.high || 0}
              total={stats.total_recommendations}
              color="bg-red-500"
            />
            <PriorityBar
              label="Medium Priority"
              count={stats.by_priority.medium || 0}
              total={stats.total_recommendations}
              color="bg-amber-500"
            />
            <PriorityBar
              label="Low Priority"
              count={stats.by_priority.low || 0}
              total={stats.total_recommendations}
              color="bg-green-500"
            />
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          onClick={() => onNavigate('recommendations')}
          className="p-4 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors text-left"
        >
          <h3 className="text-sm font-medium text-purple-900 mb-1">
            View All Recommendations
          </h3>
          <p className="text-xs text-purple-700">
            Browse and manage index recommendations with filters
          </p>
        </button>

        <button
          onClick={() => onNavigate('statistics')}
          className="p-4 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors text-left"
        >
          <h3 className="text-sm font-medium text-blue-900 mb-1">
            View Statistics
          </h3>
          <p className="text-xs text-blue-700">
            Analyze performance metrics and trends
          </p>
        </button>
      </div>

      {/* Status Distribution */}
      {stats && stats.total_recommendations > 0 && (
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Status Distribution</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatusBadge
              label="Pending"
              count={stats.by_status.pending || 0}
              color="bg-amber-100 text-amber-800"
            />
            <StatusBadge
              label="Accepted"
              count={stats.by_status.accepted || 0}
              color="bg-blue-100 text-blue-800"
            />
            <StatusBadge
              label="Applied"
              count={stats.by_status.applied || 0}
              color="bg-green-100 text-green-800"
            />
            <StatusBadge
              label="Rejected"
              count={stats.by_status.rejected || 0}
              color="bg-gray-100 text-gray-800"
            />
            <StatusBadge
              label="Failed"
              count={stats.by_status.failed || 0}
              color="bg-red-100 text-red-800"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Helper Components

function StatsCard({
  icon,
  iconColor,
  iconBg,
  label,
  value,
  subtitle,
}: {
  icon: React.ReactNode;
  iconColor: string;
  iconBg: string;
  label: string;
  value: string | number;
  subtitle: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`${iconBg} ${iconColor} p-2 rounded-lg`}>{icon}</div>
        <div className="flex-1">
          <p className="text-xs text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
  );
}

function PriorityBar({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>{label}</span>
        <span>
          {count} ({percentage.toFixed(0)}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
}

function StatusBadge({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className={`${color} rounded-lg px-3 py-2 text-center`}>
      <p className="text-lg font-bold">{count}</p>
      <p className="text-xs">{label}</p>
    </div>
  );
}
