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

  const categoryColors: Record<string, string> = {
    schema: 'text-blue-600 bg-blue-100',
    data: 'text-green-600 bg-green-100',
    query: 'text-purple-600 bg-purple-100',
    validation: 'text-orange-600 bg-orange-100',
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-lg" />
          ))}
        </div>
        <div className="h-40 bg-gray-200 dark:bg-gray-800 rounded-lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button
          onClick={() => loadData(true)}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Tools */}
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950/20 dark:to-orange-900/10 rounded-lg p-5 border border-orange-200 dark:border-orange-800/50 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-700 dark:text-orange-400">Total Tools</p>
              <p className="text-3xl font-bold text-orange-900 dark:text-orange-100 mt-1">
                {stats?.total_tools || 0}
              </p>
            </div>
            <div className="p-3 bg-orange-200 dark:bg-orange-800/50 rounded-full">
              <Wrench className="w-6 h-6 text-orange-700 dark:text-orange-300" />
            </div>
          </div>
        </div>

        {/* Total Executions */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/20 dark:to-blue-900/10 rounded-lg p-5 border border-blue-200 dark:border-blue-800/50 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-700 dark:text-blue-400">Total Executions</p>
              <p className="text-3xl font-bold text-blue-900 dark:text-blue-100 mt-1">
                {stats?.total_executions || 0}
              </p>
            </div>
            <div className="p-3 bg-blue-200 dark:bg-blue-800/50 rounded-full">
              <Activity className="w-6 h-6 text-blue-700 dark:text-blue-300" />
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/20 dark:to-green-900/10 rounded-lg p-5 border border-green-200 dark:border-green-800/50 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-700 dark:text-green-400">Success Rate</p>
              <p className="text-3xl font-bold text-green-900 dark:text-green-100 mt-1">
                {stats ? `${(stats.overall_success_rate * 100).toFixed(1)}%` : '-'}
              </p>
            </div>
            <div className="p-3 bg-green-200 dark:bg-green-800/50 rounded-full">
              <CheckCircle className="w-6 h-6 text-green-700 dark:text-green-300" />
            </div>
          </div>
        </div>

        {/* Active Tools */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950/20 dark:to-purple-900/10 rounded-lg p-5 border border-purple-200 dark:border-purple-800/50 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-purple-700 dark:text-purple-400">Categories</p>
              <p className="text-3xl font-bold text-purple-900 dark:text-purple-100 mt-1">
                {Object.keys(toolsByCategory).length}
              </p>
            </div>
            <div className="p-3 bg-purple-200 dark:bg-purple-800/50 rounded-full">
              <Zap className="w-6 h-6 text-purple-700 dark:text-purple-300" />
            </div>
          </div>
        </div>
      </div>

      {/* Tools by Category */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Tools by Category</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(toolsByCategory).map(([category, count]) => (
            <div
              key={category}
              className={`flex items-center gap-3 p-4 rounded-lg border transition-colors ${categoryColors[category] || 'bg-gray-100 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                } ${category === 'schema' ? 'dark:bg-blue-900/20 dark:border-blue-800/50 dark:text-blue-300' :
                  category === 'data' ? 'dark:bg-green-900/20 dark:border-green-800/50 dark:text-green-300' :
                    category === 'query' ? 'dark:bg-purple-900/20 dark:border-purple-800/50 dark:text-purple-300' :
                      category === 'validation' ? 'dark:bg-orange-900/20 dark:border-orange-800/50 dark:text-orange-300' : ''
                }`}
            >
              <div className="flex-shrink-0">
                {categoryIcons[category] || <Wrench className="w-5 h-5" />}
              </div>
              <div>
                <p className="font-semibold capitalize">{category}</p>
                <p className="text-sm opacity-75">{count} tools</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">How Tool-Using Agent Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">Analyze Question</p>
              <p className="text-gray-600 dark:text-gray-400">
                Identifies what information is needed (tables, columns, values)
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">Use Tools</p>
              <p className="text-gray-600 dark:text-gray-400">
                Explores schema and samples data (e.g., discovers "CA" not "California")
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">Generate SQL</p>
              <p className="text-gray-600 dark:text-gray-400">
                Builds enriched context for accurate first-attempt SQL generation
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleInvalidateAllCache}
            disabled={invalidating}
            className="flex items-center gap-2 px-4 py-2 bg-orange-100 dark:bg-orange-950/40 text-orange-700 dark:text-orange-400 rounded-lg hover:bg-orange-200 dark:hover:bg-orange-900/60 disabled:opacity-50 transition-colors border border-orange-200 dark:border-orange-800/50"
          >
            <RefreshCw className={`w-4 h-4 ${invalidating ? 'animate-spin' : ''}`} />
            {invalidating ? 'Invalidating...' : 'Clear All Tool Cache'}
          </button>
          <button
            onClick={() => loadData(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors border border-gray-300 dark:border-gray-600"
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
