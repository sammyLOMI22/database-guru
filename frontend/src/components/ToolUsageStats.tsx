import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { toolsAPI } from '../services/toolsApi';
import type { AllToolStatsResponse, ToolStatsResponse } from '../types/api';
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
 * Detailed usage statistics for each tool.
 *
 * Shows:
 * - Per-tool execution counts
 * - Success/failure rates
 * - Average execution times
 * - Cache hit rates
 * - Visual bars for comparison
 */
export const ToolUsageStats: React.FC = () => {
  const [stats, setStats] = useState<AllToolStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'executions' | 'success_rate' | 'avg_time'>('executions');

  useEffect(() => {
    loadStats(true);

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadStats(false);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const loadStats = async (isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    }
    setError(null);
    try {
      const data = await toolsAPI.getAllStats();
      setStats(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load stats'));
    } finally {
      setLoading(false);
    }
  };

  // Sort tools based on selected criteria
  const getSortedTools = (): [string, ToolStatsResponse][] => {
    if (!stats) return [];
    const entries = Object.entries(stats.by_tool);

    return entries.sort(([, a], [, b]) => {
      switch (sortBy) {
        case 'executions':
          return b.times_executed - a.times_executed;
        case 'success_rate':
          return b.success_rate - a.success_rate;
        case 'avg_time':
          return b.avg_time_ms - a.avg_time_ms;
        default:
          return 0;
      }
    });
  };

  // Get max value for bar scaling
  const getMaxValue = (key: keyof ToolStatsResponse): number => {
    if (!stats) return 1;
    return Math.max(
      1,
      ...Object.values(stats.by_tool).map((s) => Number(s[key]) || 0)
    );
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-48" />
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button
          onClick={() => loadStats(true)}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!stats || Object.keys(stats.by_tool).length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>No tool usage statistics available yet</p>
        <p className="text-sm dark:text-gray-500 mt-2">Tools will show stats after being executed</p>
      </div>
    );
  }

  const sortedTools = getSortedTools();
  const maxExecutions = getMaxValue('times_executed');
  const maxTime = getMaxValue('avg_time_ms');

  return (
    <div className="space-y-6">
      {/* Sort Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">Sort by:</span>
          <div className="flex gap-1">
            {[
              { key: 'executions', label: 'Executions', icon: TrendingUp },
              { key: 'success_rate', label: 'Success Rate', icon: CheckCircle },
              { key: 'avg_time', label: 'Avg Time', icon: Clock },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSortBy(key as typeof sortBy)}
                className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg transition-colors ${sortBy === key
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={() => loadStats(true)}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="space-y-3">
        {sortedTools.map(([toolName, toolStats]) => {
          const successPercent = toolStats.success_rate * 100;
          const executionBarWidth = (toolStats.times_executed / maxExecutions) * 100;
          const timeBarWidth = (toolStats.avg_time_ms / maxTime) * 100;

          return (
            <div
              key={toolName}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-orange-200 dark:hover:border-orange-900/50 transition-colors"
            >
              {/* Tool Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-orange-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-white">{toolName}</h3>
                </div>
                {toolStats.last_executed && (
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    Last: {new Date(toolStats.last_executed).toLocaleString()}
                  </span>
                )}
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Executions */}
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Executions</div>
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {toolStats.times_executed}
                  </div>
                  <div className="mt-1 h-1.5 bg-gray-100 dark:bg-gray-900 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${executionBarWidth}%` }}
                    />
                  </div>
                </div>

                {/* Success Rate */}
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Success Rate</div>
                  <div className="flex items-center gap-1">
                    {successPercent >= 80 ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : successPercent >= 50 ? (
                      <CheckCircle className="w-4 h-4 text-yellow-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span
                      className={`text-lg font-bold ${successPercent >= 80
                          ? 'text-green-600 dark:text-green-400'
                          : successPercent >= 50
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                    >
                      {successPercent.toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 bg-gray-100 dark:bg-gray-900 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${successPercent >= 80
                          ? 'bg-green-500'
                          : successPercent >= 50
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                      style={{ width: `${successPercent}%` }}
                    />
                  </div>
                </div>

                {/* Avg Time */}
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Time</div>
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {toolStats.avg_time_ms.toFixed(0)}ms
                  </div>
                  <div className="mt-1 h-1.5 bg-gray-100 dark:bg-gray-900 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-500 rounded-full transition-all"
                      style={{ width: `${timeBarWidth}%` }}
                    />
                  </div>
                </div>

                {/* Cache Hit Rate */}
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Cache Hits</div>
                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                    {(toolStats.cache_hit_rate * 100).toFixed(0)}%
                  </div>
                  <div className="mt-1 h-1.5 bg-gray-100 dark:bg-gray-900 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-orange-500 rounded-full transition-all"
                      style={{ width: `${toolStats.cache_hit_rate * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Success/Failure Counts */}
              <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1">
                  <CheckCircle className="w-3 h-3 text-green-500" />
                  {toolStats.successes} successes
                </span>
                <span className="flex items-center gap-1">
                  <XCircle className="w-3 h-3 text-red-500" />
                  {toolStats.failures} failures
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ToolUsageStats;
