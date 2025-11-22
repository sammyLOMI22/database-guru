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
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, toolsData] = await Promise.all([
        toolsAPI.getAllStats(),
        toolsAPI.listTools(),
      ]);
      setStats(statsData);
      setTools(toolsData);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load data');
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
      await loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to invalidate cache');
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
            <div key={i} className="h-28 bg-gray-200 rounded-lg" />
          ))}
        </div>
        <div className="h-40 bg-gray-200 rounded-lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button
          onClick={loadData}
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
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-5 border border-orange-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-700">Total Tools</p>
              <p className="text-3xl font-bold text-orange-900 mt-1">
                {stats?.total_tools || 0}
              </p>
            </div>
            <div className="p-3 bg-orange-200 rounded-full">
              <Wrench className="w-6 h-6 text-orange-700" />
            </div>
          </div>
        </div>

        {/* Total Executions */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-5 border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-700">Total Executions</p>
              <p className="text-3xl font-bold text-blue-900 mt-1">
                {stats?.total_executions || 0}
              </p>
            </div>
            <div className="p-3 bg-blue-200 rounded-full">
              <Activity className="w-6 h-6 text-blue-700" />
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-5 border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-700">Success Rate</p>
              <p className="text-3xl font-bold text-green-900 mt-1">
                {stats ? `${(stats.overall_success_rate * 100).toFixed(1)}%` : '-'}
              </p>
            </div>
            <div className="p-3 bg-green-200 rounded-full">
              <CheckCircle className="w-6 h-6 text-green-700" />
            </div>
          </div>
        </div>

        {/* Active Tools */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-5 border border-purple-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-purple-700">Categories</p>
              <p className="text-3xl font-bold text-purple-900 mt-1">
                {Object.keys(toolsByCategory).length}
              </p>
            </div>
            <div className="p-3 bg-purple-200 rounded-full">
              <Zap className="w-6 h-6 text-purple-700" />
            </div>
          </div>
        </div>
      </div>

      {/* Tools by Category */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Tools by Category</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(toolsByCategory).map(([category, count]) => (
            <div
              key={category}
              className={`flex items-center gap-3 p-4 rounded-lg ${categoryColors[category] || 'bg-gray-100'}`}
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
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">How Tool-Using Agent Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <div>
              <p className="font-medium text-gray-900">Analyze Question</p>
              <p className="text-gray-600">
                Identifies what information is needed (tables, columns, values)
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <div>
              <p className="font-medium text-gray-900">Use Tools</p>
              <p className="text-gray-600">
                Explores schema and samples data (e.g., discovers "CA" not "California")
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <div>
              <p className="font-medium text-gray-900">Generate SQL</p>
              <p className="text-gray-600">
                Builds enriched context for accurate first-attempt SQL generation
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleInvalidateAllCache}
            disabled={invalidating}
            className="flex items-center gap-2 px-4 py-2 bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${invalidating ? 'animate-spin' : ''}`} />
            {invalidating ? 'Invalidating...' : 'Clear All Tool Cache'}
          </button>
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
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
