import React, { useState, useEffect } from 'react';
import {
  Wrench,
  Activity,
  CheckCircle,
  Clock,
  Database,
  Search,
  FileText,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { toolsAPI } from '../services/toolsApi';
import type { AllToolStatsResponse, ToolResponse } from '../types/api';
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
 * Overview dashboard for Tool-Using Agent.
 *
 * Shows:
 * - Total tools available
 * - Total executions
 * - Overall success rate
 * - Tools by category breakdown
 * - Quick actions (invalidate cache)
 */
export const ToolsOverview: React.FC = () => {
  const [stats, setStats] = useState<AllToolStatsResponse | null>(null);
  const [tools, setTools] = useState<ToolResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [invalidating, setInvalidating] = useState(false);

  useEffect(() => {
    loadData(true);

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadData(false);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const loadData = async (isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    }
    setError(null);
    try {
      const [statsData, toolsData] = await Promise.all([
        toolsAPI.getAllStats(),
        toolsAPI.listTools(),
      ]);
      setStats(statsData);
      setTools(toolsData);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  const handleInvalidateAllCache = async () => {
    if (!window.confirm('Invalidate cache for all tools? This will clear cached results.')) {
      return;
    }
    setInvalidating(true);
    try {
      await toolsAPI.invalidateAllCache();
      await loadData(true);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to invalidate cache'));
    } finally {
      setInvalidating(false);
    }
  };

  // Count tools by category
  const toolsByCategory = tools.reduce(
    (acc, tool) => {
      acc[tool.category] = (acc[tool.category] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const categoryIcons: Record<string, React.ReactNode> = {
    schema: <Database className="w-5 h-5" />,
    data: <FileText className="w-5 h-5" />,
    query: <Search className="w-5 h-5" />,
    validation: <CheckCircle className="w-5 h-5" />,
  };

  const categoryStyles: Record<string, { icon: string; bg: string }> = {
    schema: { icon: 'text-blue-500', bg: 'from-blue-500/10 to-blue-500/5 border-blue-500/20' },
    data: { icon: 'text-emerald-500', bg: 'from-emerald-500/10 to-emerald-500/5 border-emerald-500/20' },
    query: { icon: 'text-purple-500', bg: 'from-purple-500/10 to-purple-500/5 border-purple-500/20' },
    validation: { icon: 'text-orange-500', bg: 'from-orange-500/10 to-orange-500/5 border-orange-500/20' },
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 glass-panel rounded-2xl" />
          ))}
        </div>
        <div className="h-40 glass-panel rounded-2xl" />
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
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-orange-500/20"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Tools */}
        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-orange-500/10 via-transparent to-orange-500/5 border-orange-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-orange-600 dark:text-orange-400">Total Tools</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">
                {stats?.total_tools || 0}
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-orange-500 group-hover:scale-110 transition-transform">
              <Wrench className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Total Executions */}
        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-blue-500/10 via-transparent to-blue-500/5 border-blue-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">Executions</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">
                {stats?.total_executions || 0}
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform">
              <Activity className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-emerald-500/10 via-transparent to-emerald-500/5 border-emerald-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-600 dark:text-emerald-400">Success Rate</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">
                {stats ? `${(stats.overall_success_rate * 100).toFixed(0)}%` : '-'}
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-emerald-500 group-hover:scale-110 transition-transform">
              <CheckCircle className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Categories */}
        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-purple-500/10 via-transparent to-purple-500/5 border-purple-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-purple-600 dark:text-purple-400">Categories</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">
                {Object.keys(toolsByCategory).length}
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-purple-500 group-hover:scale-110 transition-transform">
              <Zap className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Tools by Category */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
          Tools by Category
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(toolsByCategory).map(([category, count]) => {
            const style = categoryStyles[category] || { icon: 'text-gray-500', bg: 'from-gray-500/10 to-gray-500/5 border-gray-500/20' };
            return (
              <div
                key={category}
                className={`glass-card rounded-xl p-4 bg-gradient-to-br ${style.bg} flex items-center gap-4 group hover:scale-105 transition-all`}
              >
                <div className={`w-10 h-10 rounded-xl glass-panel flex items-center justify-center ${style.icon}`}>
                  {categoryIcons[category] || <Wrench className="w-5 h-5" />}
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-widest text-gray-900 dark:text-white capitalize">{category}</p>
                  <p className="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mt-0.5">{count} tools</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* How It Works */}
      <div className="glass-panel rounded-2xl p-6 border-white/10 bg-gradient-to-br from-orange-500/5 via-transparent to-amber-500/5">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
          How Tool Agent Works
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { step: 1, title: 'Analyze Question', desc: 'Identifies what information is needed (tables, columns, values)' },
            { step: 2, title: 'Execute Tools', desc: 'Explores schema and samples data (e.g., discovers "CA" not "California")' },
            { step: 3, title: 'Generate SQL', desc: 'Builds enriched context for accurate first-attempt SQL generation' },
          ].map((item) => (
            <div key={item.step} className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-orange-500 to-amber-500 text-white rounded-xl flex items-center justify-center font-black text-sm shadow-lg shadow-orange-500/20">
                {item.step}
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-widest text-gray-900 dark:text-white">{item.title}</p>
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                  {item.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleInvalidateAllCache}
            disabled={invalidating}
            className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-orange-600 dark:text-orange-400 hover:scale-105 active:scale-95 disabled:opacity-50 transition-all text-xs font-black uppercase tracking-widest border-orange-500/20 bg-gradient-to-r from-orange-500/10 to-amber-500/10"
          >
            <RefreshCw className={`w-4 h-4 ${invalidating ? 'animate-spin' : ''}`} />
            {invalidating ? 'Clearing...' : 'Clear Tool Cache'}
          </button>
          <button
            onClick={() => loadData(true)}
            className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 transition-all text-xs font-black uppercase tracking-widest"
          >
            <Clock className="w-4 h-4" />
            Refresh Stats
          </button>
        </div>
      </div>
    </div>
  );
};

export default ToolsOverview;
