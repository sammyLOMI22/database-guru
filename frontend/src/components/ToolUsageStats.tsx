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
        <div className="h-10 glass-panel rounded-xl w-48" />
        {[...Array(6)].map((_, i) => (
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
            onClick={() => loadStats(true)}
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-orange-500/20"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats || Object.keys(stats.by_tool).length === 0) {
    return (
      <div className="text-center py-12">
        <div className="glass-panel rounded-2xl p-8 max-w-md mx-auto">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-400 opacity-50" />
          <p className="text-sm font-bold text-gray-500 uppercase tracking-widest">No stats yet</p>
          <p className="text-xs font-medium text-gray-400 mt-2">Tools will show stats after being executed</p>
        </div>
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
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Sort</span>
          <div className="flex p-1 glass-panel rounded-xl border-white/10 bg-black/5 dark:bg-white/5">
            {[
              { key: 'executions', label: 'Runs', icon: TrendingUp },
              { key: 'success_rate', label: 'Success', icon: CheckCircle },
              { key: 'avg_time', label: 'Time', icon: Clock },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSortBy(key as typeof sortBy)}
                className={`flex items-center gap-1.5 px-4 py-2 text-xs font-black uppercase tracking-widest rounded-lg transition-all duration-300 ${
                  sortBy === key
                    ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-lg shadow-orange-500/20'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/10'
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
          className="flex items-center gap-2 px-4 py-2 glass-card rounded-xl text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 transition-all text-xs font-black uppercase tracking-widest"
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
              className="glass-card rounded-2xl p-5 border-white/10 hover:border-orange-500/30 hover:shadow-lg hover:shadow-orange-500/5 transition-all duration-300 group"
            >
              {/* Tool Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-orange-500 group-hover:scale-110 transition-transform">
                    <Zap className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white">{toolName}</h3>
                </div>
                {toolStats.last_executed && (
                  <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest glass-panel px-2 py-1 rounded-lg">
                    {new Date(toolStats.last_executed).toLocaleString()}
                  </span>
                )}
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Executions */}
                <div className="glass-panel rounded-xl p-3 border-white/10">
                  <div className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-1">Runs</div>
                  <div className="text-2xl font-black text-gray-900 dark:text-white">
                    {toolStats.times_executed}
                  </div>
                  <div className="mt-2 h-1.5 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all"
                      style={{ width: `${executionBarWidth}%` }}
                    />
                  </div>
                </div>

                {/* Success Rate */}
                <div className="glass-panel rounded-xl p-3 border-white/10">
                  <div className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-1">Success</div>
                  <div className="flex items-center gap-1.5">
                    {successPercent >= 80 ? (
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : successPercent >= 50 ? (
                      <CheckCircle className="w-4 h-4 text-amber-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span
                      className={`text-2xl font-black ${
                        successPercent >= 80
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : successPercent >= 50
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {successPercent.toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        successPercent >= 80
                          ? 'bg-gradient-to-r from-emerald-500 to-green-500'
                          : successPercent >= 50
                          ? 'bg-gradient-to-r from-amber-500 to-yellow-500'
                          : 'bg-gradient-to-r from-red-500 to-rose-500'
                      }`}
                      style={{ width: `${successPercent}%` }}
                    />
                  </div>
                </div>

                {/* Avg Time */}
                <div className="glass-panel rounded-xl p-3 border-white/10">
                  <div className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-1">Avg Time</div>
                  <div className="text-2xl font-black text-gray-900 dark:text-white">
                    {toolStats.avg_time_ms.toFixed(0)}<span className="text-sm font-bold text-gray-400">ms</span>
                  </div>
                  <div className="mt-2 h-1.5 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all"
                      style={{ width: `${timeBarWidth}%` }}
                    />
                  </div>
                </div>

                {/* Cache Hit Rate */}
                <div className="glass-panel rounded-xl p-3 border-white/10">
                  <div className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-1">Cache</div>
                  <div className="text-2xl font-black text-gray-900 dark:text-white">
                    {(toolStats.cache_hit_rate * 100).toFixed(0)}%
                  </div>
                  <div className="mt-2 h-1.5 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all"
                      style={{ width: `${toolStats.cache_hit_rate * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Success/Failure Counts */}
              <div className="mt-4 flex items-center gap-4 text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1.5 glass-panel px-2 py-1 rounded-lg">
                  <CheckCircle className="w-3 h-3 text-emerald-500" />
                  {toolStats.successes} ok
                </span>
                <span className="flex items-center gap-1.5 glass-panel px-2 py-1 rounded-lg">
                  <XCircle className="w-3 h-3 text-red-500" />
                  {toolStats.failures} fail
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
