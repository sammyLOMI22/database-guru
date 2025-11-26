import React, { useState, useEffect } from 'react';
import { Clock, Database, Eye, Code, RefreshCw } from 'lucide-react';
import { cacheAPI, type RecentQueriesResponse } from '../services/cacheApi';
import axios from 'axios';

/** Extract error message from unknown error type */
const getErrorMessage = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message || fallback;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return fallback;
};

/**
 * Recent cached queries browser.
 *
 * Shows:
 * - List of cached queries
 * - Question, SQL, connection, hits
 * - Expandable SQL view
 *
 * Part of Phase 3.3: Semantic Caching UI Components
 */
export const RecentCachedQueries: React.FC = () => {
  const [data, setData] = useState<RecentQueriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedQuery, setExpandedQuery] = useState<string | null>(null);
  const [limit, setLimit] = useState(10);

  useEffect(() => {
    loadData(true);

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadData(false);
    }, 30000);

    return () => clearInterval(interval);
  }, [limit]);

  const loadData = async (isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await cacheAPI.getRecentQueries({ limit });
      setData(response);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const formatTimeAgo = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffDays > 0) return `${diffDays}d ago`;
      if (diffHours > 0) return `${diffHours}h ago`;
      if (diffMins > 0) return `${diffMins}m ago`;
      return 'Just now';
    } catch {
      return '';
    }
  };

  const dbTypeColors: Record<string, string> = {
    postgresql: 'bg-blue-100 text-blue-700',
    mysql: 'bg-orange-100 text-orange-700',
    sqlite: 'bg-green-100 text-green-700',
    duckdb: 'bg-yellow-100 text-yellow-700',
    mongodb: 'bg-purple-100 text-purple-700',
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-200 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button
          onClick={() => loadData(true)}
          className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600"
        >
          Retry
        </button>
      </div>
    );
  }

  const queries = data?.queries || [];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-600">
          Showing {queries.length} of {data?.total || 0} cached queries
        </p>
        <div className="flex items-center gap-3">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value={10}>10 per page</option>
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
          </select>
          <button
            onClick={() => loadData(false)}
            className="flex items-center gap-2 px-3 py-1 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Empty State */}
      {queries.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Database className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No cached queries yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Queries will appear here after you run some queries
          </p>
        </div>
      ) : (
        /* Query List */
        <div className="space-y-3">
          {queries.map((query, index) => (
            <div
              key={`${query.question}-${index}`}
              className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:border-amber-300 transition-colors"
            >
              {/* Main Row */}
              <div className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Question */}
                    <p className="font-medium text-gray-900 truncate" title={query.question}>
                      {query.question}
                    </p>

                    {/* Meta Info */}
                    <div className="flex items-center gap-3 mt-2 text-sm">
                      {/* Database Type Badge */}
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          dbTypeColors[query.database_type] || 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {query.database_type}
                      </span>

                      {/* Connection ID */}
                      <span className="text-gray-500 flex items-center gap-1">
                        <Database className="w-3 h-3" />
                        Connection #{query.connection_id}
                      </span>

                      {/* Created */}
                      <span className="text-gray-500 flex items-center gap-1" title={formatDate(query.created_at)}>
                        <Clock className="w-3 h-3" />
                        {formatTimeAgo(query.created_at)}
                      </span>

                      {/* Hits */}
                      <span className="text-gray-500 flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        {query.hits} hit{query.hits !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>

                  {/* Expand Button */}
                  <button
                    onClick={() =>
                      setExpandedQuery(
                        expandedQuery === query.question ? null : query.question
                      )
                    }
                    className="flex items-center gap-1 px-3 py-1 text-sm text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition-colors"
                  >
                    <Code className="w-4 h-4" />
                    {expandedQuery === query.question ? 'Hide SQL' : 'View SQL'}
                  </button>
                </div>
              </div>

              {/* Expanded SQL */}
              {expandedQuery === query.question && (
                <div className="border-t border-gray-200 bg-gray-50 p-4">
                  <p className="text-xs text-gray-500 mb-2 font-medium">CACHED SQL:</p>
                  <pre className="bg-gray-900 text-green-400 p-3 rounded-lg text-sm overflow-x-auto">
                    {query.sql}
                  </pre>
                  {query.last_hit_at && (
                    <p className="text-xs text-gray-400 mt-2">
                      Last hit: {formatDate(query.last_hit_at)}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Load More Hint */}
      {queries.length > 0 && queries.length < (data?.total || 0) && (
        <p className="text-center text-sm text-gray-500">
          Showing {queries.length} of {data?.total} queries. Increase page size to see more.
        </p>
      )}
    </div>
  );
};

export default RecentCachedQueries;
