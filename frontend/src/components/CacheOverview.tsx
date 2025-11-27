import { useState, useEffect } from 'react';
import {
  Database,
  Activity,
  CheckCircle,
  Zap,
  RefreshCw,
  Trash2,
  AlertCircle,
  Server,
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
      <div className="bg-gradient-to-r from-gray-50 via-white to-gray-50 rounded-lg border-2 border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Server className="w-4 h-4" />
            Service Status
          </h3>
          {refreshing && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Refreshing...
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
          {/* Redis Status */}
          <div className={`flex items-center gap-3 p-3 rounded-lg border-2 ${
            redisConnected
              ? 'bg-green-50 border-green-300'
              : 'bg-yellow-50 border-yellow-300'
          }`}>
            <div className={`p-2 rounded-full ${
              redisConnected ? 'bg-green-200' : 'bg-yellow-200'
            }`}>
              {redisConnected ? (
                <CheckCircle className="w-5 h-5 text-green-700" />
              ) : (
                <AlertCircle className="w-5 h-5 text-yellow-700" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900">Redis</span>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  redisConnected
                    ? 'bg-green-200 text-green-800'
                    : 'bg-yellow-200 text-yellow-800'
                }`}>
                  {redisConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-0.5">
                {redisConnected
                  ? 'Persistent caching enabled'
                  : 'Using in-memory fallback (data lost on restart)'}
              </p>
            </div>
          </div>

          {/* Ollama Embeddings Status */}
          <div className={`flex items-center gap-3 p-3 rounded-lg border-2 ${
            embedding?.ollama_available
              ? 'bg-green-50 border-green-300'
              : 'bg-yellow-50 border-yellow-300'
          }`}>
            <div className={`p-2 rounded-full ${
              embedding?.ollama_available ? 'bg-green-200' : 'bg-yellow-200'
            }`}>
              {embedding?.ollama_available ? (
                <CheckCircle className="w-5 h-5 text-green-700" />
              ) : (
                <AlertCircle className="w-5 h-5 text-yellow-700" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900">Ollama Embeddings</span>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  embedding?.ollama_available
                    ? 'bg-green-200 text-green-800'
                    : 'bg-yellow-200 text-yellow-800'
                }`}>
                  {embedding?.ollama_available ? 'Online' : 'Offline'}
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-0.5">
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
        {/* Total Lookups */}
        <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-5 border border-amber-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-amber-700">Total Lookups</p>
              <p className="text-3xl font-bold text-amber-900 mt-1">
                {semantic?.total_lookups || 0}
              </p>
            </div>
            <div className="p-3 bg-amber-200 rounded-full">
              <Activity className="w-6 h-6 text-amber-700" />
            </div>
          </div>
        </div>

        {/* Hit Rate */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-5 border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-700">Hit Rate</p>
              <p className="text-3xl font-bold text-green-900 mt-1">
                {semantic?.hit_rate_percent?.toFixed(1) || 0}%
              </p>
            </div>
            <div className="p-3 bg-green-200 rounded-full">
              <CheckCircle className="w-6 h-6 text-green-700" />
            </div>
          </div>
        </div>

        {/* Semantic Hits */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-5 border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-700">Semantic Hits</p>
              <p className="text-3xl font-bold text-blue-900 mt-1">
                {semantic?.semantic_hits || 0}
              </p>
              <p className="text-xs text-blue-600 mt-1">
                {semantic?.semantic_hit_rate_percent?.toFixed(1) || 0}% of lookups
              </p>
            </div>
            <div className="p-3 bg-blue-200 rounded-full">
              <Zap className="w-6 h-6 text-blue-700" />
            </div>
          </div>
        </div>

        {/* Cached Entries */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-5 border border-purple-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-purple-700">Cached Entries</p>
              <p className="text-3xl font-bold text-purple-900 mt-1">
                {semantic?.memory_entries || 0}
              </p>
            </div>
            <div className="p-3 bg-purple-200 rounded-full">
              <Database className="w-6 h-6 text-purple-700" />
            </div>
          </div>
        </div>
      </div>

      {/* Cache Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Semantic Cache Details */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-amber-600" />
            Semantic Cache
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Hits</span>
              <span className="font-semibold">{semantic?.total_hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Exact Hits</span>
              <span className="font-semibold text-green-600">{semantic?.exact_hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Semantic Hits</span>
              <span className="font-semibold text-blue-600">{semantic?.semantic_hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Misses</span>
              <span className="font-semibold text-gray-500">{semantic?.misses || 0}</span>
            </div>
            <hr className="my-2" />
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Similarity Threshold</span>
              <span>{semantic?.similarity_threshold || 0.85}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">TTL</span>
              <span>{Math.round((semantic?.ttl_seconds || 86400) / 3600)}h</span>
            </div>
          </div>
        </div>

        {/* LLM Cache Details */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-600" />
            LLM Response Cache
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Lookups</span>
              <span className="font-semibold">{llm?.total_lookups || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Hits</span>
              <span className="font-semibold text-green-600">{llm?.hits || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Hit Rate</span>
              <span className="font-semibold">{llm?.hit_rate_percent?.toFixed(1) || 0}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Misses</span>
              <span className="font-semibold text-gray-500">{llm?.misses || 0}</span>
            </div>
            <hr className="my-2" />
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Similarity Threshold</span>
              <span>{llm?.similarity_threshold || 0.88}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">TTL</span>
              <span>{Math.round((llm?.ttl_seconds || 43200) / 3600)}h</span>
            </div>
          </div>
        </div>
      </div>

      {/* Embedding Service Status */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-gray-600" />
          Embedding Service
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center p-3 bg-white rounded-lg border">
            <p className="text-2xl font-bold text-gray-900">{embedding?.total_requests || 0}</p>
            <p className="text-sm text-gray-500">Requests</p>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <p className="text-2xl font-bold text-green-600">{embedding?.cache_hits || 0}</p>
            <p className="text-sm text-gray-500">Cache Hits</p>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <p className="text-2xl font-bold text-blue-600">
              {embedding?.cache_hit_rate_percent?.toFixed(0) || 0}%
            </p>
            <p className="text-sm text-gray-500">Hit Rate</p>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <p className="text-2xl font-bold text-purple-600">{embedding?.ollama_calls || 0}</p>
            <p className="text-sm text-gray-500">Ollama Calls</p>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <div className="flex items-center justify-center gap-2">
              {embedding?.ollama_available ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="text-green-600 font-medium">Online</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-5 h-5 text-yellow-500" />
                  <span className="text-yellow-600 font-medium">TF-IDF</span>
                </>
              )}
            </div>
            <p className="text-sm text-gray-500">Status</p>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">How Semantic Caching Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <div>
              <p className="font-medium text-gray-900">Exact Hash Check</p>
              <p className="text-gray-600">
                First checks for exact query match (fastest path, ~0.5s)
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <div>
              <p className="font-medium text-gray-900">Semantic Similarity</p>
              <p className="text-gray-600">
                Compares query embeddings to find similar questions (threshold: 0.85)
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <div>
              <p className="font-medium text-gray-900">LLM Cache</p>
              <p className="text-gray-600">
                Caches LLM responses with schema fingerprinting (threshold: 0.88)
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
            onClick={() => handleClearCache('semantic')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 disabled:opacity-50 transition-colors"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'semantic' ? 'animate-pulse' : ''}`} />
            {clearing === 'semantic' ? 'Clearing...' : 'Clear Semantic Cache'}
          </button>
          <button
            onClick={() => handleClearCache('llm')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 disabled:opacity-50 transition-colors"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'llm' ? 'animate-pulse' : ''}`} />
            {clearing === 'llm' ? 'Clearing...' : 'Clear LLM Cache'}
          </button>
          <button
            onClick={() => handleClearCache('all')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors"
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
