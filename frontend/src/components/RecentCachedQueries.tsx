import React, { useState, useEffect } from 'react';
import { Clock, Database, Eye, Code, RefreshCw, ChevronDown } from 'lucide-react';
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

  const dbTypeStyles: Record<string, { bg: string; text: string; border: string }> = {
    postgresql: { bg: 'from-blue-500/20 to-blue-500/10', text: 'text-blue-600 dark:text-blue-400', border: 'border-blue-500/30' },
    mysql: { bg: 'from-orange-500/20 to-orange-500/10', text: 'text-orange-600 dark:text-orange-400', border: 'border-orange-500/30' },
    sqlite: { bg: 'from-emerald-500/20 to-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-500/30' },
    duckdb: { bg: 'from-yellow-500/20 to-yellow-500/10', text: 'text-yellow-600 dark:text-yellow-400', border: 'border-yellow-500/30' },
    mongodb: { bg: 'from-purple-500/20 to-purple-500/10', text: 'text-purple-600 dark:text-purple-400', border: 'border-purple-500/30' },
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 glass-panel rounded-2xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="glass-panel rounded-2xl p-8 max-w-md mx-auto">
          <div className="text-red-500 mb-4 text-sm font-bold uppercase tracking-widest">Error: {error}</div>
          <button
            onClick={() => loadData(true)}
            className="px-6 py-3 bg-gradient-to-r from-amber-500 to-yellow-500 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-amber-500/20"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const queries = data?.queries || [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex justify-between items-center">
        <p className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
          Showing {queries.length} of {data?.total || 0} cached queries
        </p>
        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="appearance-none pl-4 pr-10 py-2 glass-panel rounded-xl text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-widest focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all cursor-pointer border-white/10"
            >
              <option value={10}>10 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
          <button
            onClick={() => loadData(false)}
            className="flex items-center gap-2 px-4 py-2 glass-card rounded-xl text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 transition-all text-xs font-black uppercase tracking-widest"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Empty State */}
      {queries.length === 0 ? (
        <div className="text-center py-16 glass-panel rounded-2xl border-white/10">
          <div className="w-16 h-16 rounded-2xl glass-card flex items-center justify-center mx-auto mb-4">
            <Database className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">No cached queries yet</p>
          <p className="text-xs font-medium text-gray-400 dark:text-gray-500 mt-2">
            Queries will appear here after you run some queries
          </p>
        </div>
      ) : (
        /* Query List */
        <div className="space-y-3">
          {queries.map((query, index) => {
            const isExpanded = expandedQuery === query.question;
            const dbStyle = dbTypeStyles[query.database_type] || { bg: 'from-gray-500/20 to-gray-500/10', text: 'text-gray-600 dark:text-gray-400', border: 'border-gray-500/30' };

            return (
              <div
                key={`${query.question}-${index}`}
                className={`glass-card rounded-2xl overflow-hidden border-white/10 transition-all duration-300 ${isExpanded ? 'shadow-xl shadow-amber-500/5' : 'hover:border-amber-500/30'}`}
              >
                {/* Main Row */}
                <div className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Question */}
                      <p className="font-bold text-gray-900 dark:text-white truncate" title={query.question}>
                        {query.question}
                      </p>

                      {/* Meta Info */}
                      <div className="flex flex-wrap items-center gap-3 mt-3">
                        {/* Database Type Badge */}
                        <span
                          className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest bg-gradient-to-r ${dbStyle.bg} ${dbStyle.text} border ${dbStyle.border}`}
                        >
                          {query.database_type}
                        </span>

                        {/* Connection ID */}
                        <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400 flex items-center gap-1.5 glass-panel px-2.5 py-1 rounded-lg uppercase tracking-widest">
                          <Database className="w-3 h-3" />
                          #{query.connection_id}
                        </span>

                        {/* Created */}
                        <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400 flex items-center gap-1.5 glass-panel px-2.5 py-1 rounded-lg uppercase tracking-widest" title={formatDate(query.created_at)}>
                          <Clock className="w-3 h-3" />
                          {formatTimeAgo(query.created_at)}
                        </span>

                        {/* Hits */}
                        <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1.5 glass-panel px-2.5 py-1 rounded-lg uppercase tracking-widest bg-gradient-to-r from-amber-500/10 to-yellow-500/10 border border-amber-500/20">
                          <Eye className="w-3 h-3" />
                          {query.hits} hit{query.hits !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>

                    {/* Expand Button */}
                    <button
                      onClick={() =>
                        setExpandedQuery(isExpanded ? null : query.question)
                      }
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                        isExpanded
                          ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white shadow-lg shadow-amber-500/20'
                          : 'glass-panel text-amber-600 dark:text-amber-400 hover:scale-105 active:scale-95'
                      }`}
                    >
                      <Code className="w-4 h-4" />
                      {isExpanded ? 'Hide' : 'SQL'}
                    </button>
                  </div>
                </div>

                {/* Expanded SQL */}
                {isExpanded && (
                  <div className="border-t border-white/10 bg-black/5 dark:bg-white/5 p-5 animate-fadeIn">
                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-amber-500" />
                      Cached SQL
                    </p>
                    <pre className="glass-panel bg-gray-900 dark:bg-black text-emerald-400 dark:text-emerald-500 p-4 rounded-xl text-sm overflow-x-auto border border-emerald-500/20 font-mono">
                      {query.sql}
                    </pre>
                    {query.last_hit_at && (
                      <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 mt-3 uppercase tracking-widest">
                        Last hit: {formatDate(query.last_hit_at)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Load More Hint */}
      {queries.length > 0 && queries.length < (data?.total || 0) && (
        <p className="text-center text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest glass-panel rounded-xl py-3">
          Showing {queries.length} of {data?.total} queries. Increase page size to see more.
        </p>
      )}
    </div>
  );
};

export default RecentCachedQueries;
