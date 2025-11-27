/**
 * RecommendationsList - Browsable List
 *
 * Filterable list of index recommendations with:
 * - Search and filter controls
 * - Priority/status badges
 * - Expandable details
 * - Bulk actions
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search, Filter, ChevronDown, ChevronRight, Check, X,
  AlertCircle, Database, Copy
} from 'lucide-react';
import { indexRecommendationsApi, IndexRecommendation } from '../services/indexRecommendationsApi';

export default function RecommendationsList() {
  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    database_type: '',
    search: '',
  });
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: recommendations = [], isLoading, error } = useQuery<IndexRecommendation[]>({
    queryKey: ['index-recommendations', filters],
    queryFn: () => indexRecommendationsApi.listRecommendations({
      status: filters.status || undefined,
      priority: filters.priority || undefined,
      database_type: filters.database_type || undefined,
    }),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      indexRecommendationsApi.updateRecommendation(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index-recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['index-recommendations-stats'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => indexRecommendationsApi.deleteRecommendation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index-recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['index-recommendations-stats'] });
    },
  });

  const handleStatusChange = (id: number, status: string) => {
    updateMutation.mutate({ id, status });
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this recommendation?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleCopySQL = (sql: string) => {
    navigator.clipboard.writeText(sql);
  };

  // Filter recommendations by search
  const filteredRecommendations = recommendations.filter((rec) => {
    if (!filters.search) return true;
    const searchLower = filters.search.toLowerCase();
    return (
      rec.table_name.toLowerCase().includes(searchLower) ||
      rec.index_name.toLowerCase().includes(searchLower) ||
      rec.slow_query_sql.toLowerCase().includes(searchLower)
    );
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
            <h3 className="text-sm font-medium text-red-800">Failed to load recommendations</h3>
            <p className="text-sm text-red-700 mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Filters */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <Filter className="w-4 h-4" />
          Filters
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tables, indexes..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="applied">Applied</option>
            <option value="rejected">Rejected</option>
            <option value="failed">Failed</option>
          </select>

          {/* Priority Filter */}
          <select
            value={filters.priority}
            onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>

          {/* Database Type Filter */}
          <select
            value={filters.database_type}
            onChange={(e) => setFilters({ ...filters, database_type: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Databases</option>
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="sqlite">SQLite</option>
          </select>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-600">
          {filteredRecommendations.length} recommendation{filteredRecommendations.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Recommendations List */}
      {filteredRecommendations.length === 0 ? (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500">No recommendations found</p>
          <p className="text-sm text-gray-400 mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredRecommendations.map((rec) => (
            <RecommendationCard
              key={rec.id}
              recommendation={rec}
              isExpanded={expandedId === rec.id}
              onToggleExpand={() => setExpandedId(expandedId === rec.id ? null : rec.id)}
              onStatusChange={handleStatusChange}
              onDelete={handleDelete}
              onCopySQL={handleCopySQL}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Individual Recommendation Card
function RecommendationCard({
  recommendation,
  isExpanded,
  onToggleExpand,
  onStatusChange,
  onDelete,
  onCopySQL,
}: {
  recommendation: IndexRecommendation;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onStatusChange: (id: number, status: string) => void;
  onDelete: (id: number) => void;
  onCopySQL: (sql: string) => void;
}) {
  const priorityColors = {
    high: 'bg-red-100 text-red-800 border-red-200',
    medium: 'bg-amber-100 text-amber-800 border-amber-200',
    low: 'bg-green-100 text-green-800 border-green-200',
  };

  const statusColors = {
    pending: 'bg-amber-100 text-amber-800',
    accepted: 'bg-blue-100 text-blue-800',
    applied: 'bg-green-100 text-green-800',
    rejected: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <div className={`border rounded-lg ${priorityColors[recommendation.priority as keyof typeof priorityColors]}`}>
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <button
            onClick={onToggleExpand}
            className="flex items-start gap-3 flex-1 text-left"
          >
            {isExpanded ? (
              <ChevronDown className="w-5 h-5 flex-shrink-0 mt-0.5" />
            ) : (
              <ChevronRight className="w-5 h-5 flex-shrink-0 mt-0.5" />
            )}

            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-medium">{recommendation.index_name}</h3>
                <span className={`px-2 py-0.5 text-xs rounded ${statusColors[recommendation.status as keyof typeof statusColors]}`}>
                  {recommendation.status}
                </span>
              </div>

              <p className="text-sm opacity-90 mb-2">
                Table: <span className="font-mono">{recommendation.table_name}</span> •
                Columns: <span className="font-mono">{recommendation.column_names.join(', ')}</span>
              </p>

              <p className="text-sm opacity-80">{recommendation.reason}</p>
            </div>
          </button>

          {/* Metrics */}
          <div className="flex items-center gap-4 text-sm">
            <div className="text-right">
              <p className="font-medium">{recommendation.execution_time_ms.toFixed(0)}ms</p>
              <p className="text-xs opacity-75">Query time</p>
            </div>
            {recommendation.estimated_improvement_pct && (
              <div className="text-right">
                <p className="font-medium">↓{recommendation.estimated_improvement_pct.toFixed(0)}%</p>
                <p className="text-xs opacity-75">Improvement</p>
              </div>
            )}
          </div>
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t space-y-3">
            {/* SQL */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <h4 className="text-sm font-medium">Create Index SQL</h4>
                <button
                  onClick={() => onCopySQL(recommendation.create_index_sql)}
                  className="text-xs text-purple-600 hover:text-purple-700 flex items-center gap-1"
                >
                  <Copy className="w-3 h-3" />
                  Copy
                </button>
              </div>
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto">
                {recommendation.create_index_sql}
              </pre>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              {recommendation.status === 'pending' && (
                <>
                  <button
                    onClick={() => onStatusChange(recommendation.id, 'accepted')}
                    className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 flex items-center gap-1"
                  >
                    <Check className="w-4 h-4" />
                    Accept
                  </button>
                  <button
                    onClick={() => onStatusChange(recommendation.id, 'rejected')}
                    className="px-3 py-1.5 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 flex items-center gap-1"
                  >
                    <X className="w-4 h-4" />
                    Reject
                  </button>
                </>
              )}

              <button
                onClick={() => onDelete(recommendation.id)}
                className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 ml-auto"
              >
                Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
