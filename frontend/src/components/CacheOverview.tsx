import React, { useState, useEffect } from 'react';
import {
  Database,
  Activity,
  CheckCircle,
  Zap,
  RefreshCw,
  Trash2,
  AlertCircle,
  Server,
  Clock,
} from 'lucide-react';
import { cacheAPI, type CacheStatsResponse } from '../services/cacheApi';
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
 * Overview dashboard for Semantic Cache.
 *
 * Shows:
 * - Total lookups and hit rate
 * - Semantic vs exact hits
 * - LLM cache stats
 * - Embedding service status
 * - Quick actions (clear cache)
 *
 * Part of Phase 3.3: Semantic Caching UI Components
 */
export const CacheOverview: React.FC = () => {
  const [stats, setStats] = useState<CacheStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

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
    } else {
      setRefreshing(true);
    }
    setError(null);
    try {
      const data = await cacheAPI.getStats();
      setStats(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleClearCache = async (cacheType: 'semantic' | 'llm' | 'all') => {
    const messages: Record<string, string> = {
      semantic: 'Clear semantic cache? Cached query results will be removed.',
      llm: 'Clear LLM cache? Cached SQL generation responses will be removed.',
      all: 'Clear all caches? This will remove all cached data.',
    };

    if (!window.confirm(messages[cacheType])) {
      return;
    }

    setClearing(cacheType);
    try {
      if (cacheType === 'semantic') {
        await cacheAPI.clearSemanticCache();
      } else if (cacheType === 'llm') {
        await cacheAPI.clearLLMCache();
      } else {
        await cacheAPI.clearAllCaches();
      }
      await loadData();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to clear cache'));
    } finally {
      setClearing(null);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-16 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-lg" />
          ))}
        </div>
        <div className="h-64 bg-gray-200 dark:bg-gray-800 rounded-lg" />
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

  const semantic = stats?.semantic_cache;
  const llm = stats?.llm_cache;
  const embedding = stats?.embedding_service;
  const redisConnected = stats?.redis_connected ?? false;

  return (
    <div className="space-y-6">
      {/* Service Status Banner */}
      <div className="bg-gradient-to-r from-gray-50 via-white to-gray-50 rounded-lg border-2 border-gray-200 p-4 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 dark:text-gray-300">
            <Server className="w-4 h-4" />
            Service Status
          </h3>
          {refreshing && (
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Refreshing...
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
          {/* Status Banner */}
          <div className={`p-4 rounded-lg flex items-center justify-between shadow-sm border ${redisConnected
            ? 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800/50 text-green-700 dark:text-green-400'
            : 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800/50 text-red-700 dark:text-red-400'
            }`}>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${redisConnected ? 'bg-green-100 dark:bg-green-900/40' : 'bg-red-100 dark:bg-red-900/40'}`}>
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                  Redis Semantic Cache
                </h3>
                <p className="text-sm opacity-90">
                  {redisConnected
                    ? 'Semantic caching is active and and optimizing queries'
                    : `Disconnected from Redis: ${error || 'Unknown error'}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${redisConnected
                ? 'bg-green-200 dark:bg-green-800/50 text-green-800 dark:text-green-300'
                : 'bg-red-200 dark:bg-red-800/50 text-red-800 dark:text-red-300'
                }`}>
                {redisConnected ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>
          </div>

          {/* Ollama Embeddings Status */}
          <div className={`flex items-center gap-3 p-3 rounded-lg border-2 ${embedding?.ollama_available
            ? 'bg-green-50 border-green-300 dark:bg-green-950/20 dark:border-green-800/50'
            : 'bg-yellow-50 border-yellow-300 dark:bg-yellow-950/20 dark:border-yellow-800/50'
            }`}>
            <div className={`p-2 rounded-full ${embedding?.ollama_available ? 'bg-green-200 dark:bg-green-900/40' : 'bg-yellow-200 dark:bg-yellow-900/40'
              }`}>
              {embedding?.ollama_available ? (
                <CheckCircle className="w-5 h-5 text-green-700 dark:text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-yellow-700 dark:text-yellow-400" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900 dark:text-gray-100">Ollama Embeddings</span>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${embedding?.ollama_available
                  ? 'bg-green-200 text-green-800 dark:bg-green-800/50 dark:text-green-300'
                  : 'bg-yellow-200 text-yellow-800 dark:bg-yellow-800/50 dark:text-yellow-300'
                  }`}>
                  {embedding?.ollama_available ? 'Online' : 'Offline'}
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-0.5 dark:text-gray-400">
                {embedding?.ollama_available
                  ? `Model: nomic-embed-text`
                  : 'Using TF-IDF fallback (lower accuracy)'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Lookup Rate Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Lookups</p>
          <div className="flex items-center justify-between mt-1">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {semantic?.total_lookups || 0}
            </p>
            <Activity className="w-8 h-8 text-blue-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Across all chat sessions
          </div>
        </div>

        {/* Hit Rate Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Global Hit Rate</p>
          <div className="flex items-center justify-between mt-1">
            <p className={`text-3xl font-bold ${(semantic?.hit_rate_percent || 0) > 50 ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
              }`}>
              {semantic ? `${semantic.hit_rate_percent.toFixed(1)}%` : '0%'}
            </p>
            <Zap className="w-8 h-8 text-amber-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Semantic matches found
          </div>
        </div>

        {/* Semantic Hits */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-5 border border-blue-200 dark:from-blue-950/20 dark:to-blue-900/20 dark:border-blue-800/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-700 dark:text-blue-400">Semantic Hits</p>
              <p className="text-3xl font-bold text-blue-900 mt-1 dark:text-blue-100">
                {semantic?.semantic_hits || 0}
              </p>
              <p className="text-xs text-blue-600 mt-1 dark:text-blue-300">
                {semantic?.semantic_hit_rate_percent?.toFixed(1) || 0}% of lookups
              </p>
            </div>
            <div className="p-3 bg-blue-200 rounded-full dark:bg-blue-900/40">
              <Zap className="w-6 h-6 text-blue-700 dark:text-blue-400" />
            </div>
          </div>
        </div>

        {/* Keys Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Cache Size</p>
          <div className="flex items-center justify-between mt-1">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {semantic?.memory_entries || 0}
            </p>
            <Clock className="w-8 h-8 text-purple-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Cached plan/results
          </div>
        </div>
      </div>

      {/* Cache Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Semantic Cache Details */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            Semantic Cache
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Total Hits</span>
              <span className="font-semibold text-gray-900 dark:text-white">{semantic?.total_hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Exact Hits</span>
              <span className="font-semibold text-green-600 dark:text-green-400">{semantic?.exact_hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Semantic Hits</span>
              <span className="font-semibold text-blue-600 dark:text-blue-400">{semantic?.semantic_hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Misses</span>
              <span className="font-semibold text-gray-500 dark:text-gray-400">{semantic?.misses || 0}</span>
            </div>
            <hr className="my-2 border-gray-200 dark:border-gray-700" />
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500 dark:text-gray-400">Similarity Threshold</span>
              <span className="text-gray-900 dark:text-white">{semantic?.similarity_threshold || 0.85}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500 dark:text-gray-400">TTL</span>
              <span className="text-gray-900 dark:text-white">{Math.round((semantic?.ttl_seconds || 86400) / 3600)}h</span>
            </div>
          </div>
        </div>

        {/* LLM Cache Details */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            LLM Response Cache
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Total Lookups</span>
              <span className="font-semibold text-gray-900 dark:text-white">{llm?.total_lookups || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Hits</span>
              <span className="font-semibold text-green-600 dark:text-green-400">{llm?.hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Hit Rate</span>
              <span className="font-semibold text-gray-900 dark:text-white">{llm?.hit_rate_percent?.toFixed(1) || 0}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-300">Misses</span>
              <span className="font-semibold text-gray-500 dark:text-gray-400">{llm?.misses || 0}</span>
            </div>
            <hr className="my-2 border-gray-200 dark:border-gray-700" />
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500 dark:text-gray-400">Similarity Threshold</span>
              <span className="text-gray-900 dark:text-white">{llm?.similarity_threshold || 0.88}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500 dark:text-gray-400">TTL</span>
              <span className="text-gray-900 dark:text-white">{Math.round((llm?.ttl_seconds || 43200) / 3600)}h</span>
            </div>
          </div>
        </div>
      </div>

      {/* Embedding Service Status */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          Embedding Service
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{embedding?.total_requests || 0}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Requests</p>
          </div>
          <div className="text-center p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">{embedding?.cache_hits || 0}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Cache Hits</p>
          </div>
          <div className="text-center p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {embedding?.cache_hit_rate_percent?.toFixed(0) || 0}%
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Hit Rate</p>
          </div>
          <div className="text-center p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{embedding?.ollama_calls || 0}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Ollama Calls</p>
          </div>
          <div className="text-center p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-center gap-2">
              {embedding?.ollama_available ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-500 dark:text-green-400" />
                  <span className="text-green-600 font-medium dark:text-green-400">Online</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-5 h-5 text-yellow-500 dark:text-yellow-400" />
                  <span className="text-yellow-600 font-medium dark:text-yellow-400">TF-IDF</span>
                </>
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200 p-5 dark:from-amber-950/20 dark:to-orange-950/20 dark:border-amber-800/50">
        <h3 className="text-lg font-semibold text-gray-900 mb-3 dark:text-white">How Semantic Caching Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Exact Hash Check</p>
              <p className="text-gray-600 dark:text-gray-300">
                First checks for exact query match (fastest path, ~0.5s)
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Semantic Similarity</p>
              <p className="text-gray-600 dark:text-gray-300">
                Compares query embeddings to find similar questions (threshold: 0.85)
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white">LLM Cache</p>
              <p className="text-gray-600 dark:text-gray-300">
                Caches LLM responses with schema fingerprinting (threshold: 0.88)
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
            onClick={() => handleClearCache('semantic')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 disabled:opacity-50 transition-colors dark:bg-amber-950/40 dark:text-amber-400 dark:hover:bg-amber-900/60 dark:border dark:border-amber-800/50"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'semantic' ? 'animate-pulse' : ''}`} />
            {clearing === 'semantic' ? 'Clearing...' : 'Clear Semantic Cache'}
          </button>
          <button
            onClick={() => handleClearCache('llm')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 disabled:opacity-50 transition-colors dark:bg-blue-950/40 dark:text-blue-400 dark:hover:bg-blue-900/60 dark:border dark:border-blue-800/50"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'llm' ? 'animate-pulse' : ''}`} />
            {clearing === 'llm' ? 'Clearing...' : 'Clear LLM Cache'}
          </button>
          <button
            onClick={() => handleClearCache('all')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/60 dark:border dark:border-red-800/50"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'all' ? 'animate-pulse' : ''}`} />
            {clearing === 'all' ? 'Clearing...' : 'Clear All Caches'}
          </button>
          <button
            onClick={() => loadData(false)}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Stats'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CacheOverview;
