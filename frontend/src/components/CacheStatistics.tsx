import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Clock, RefreshCw } from 'lucide-react';
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
 * Statistics dashboard for Semantic Cache.
 *
 * Shows:
 * - Hit rate breakdown (exact vs semantic)
 * - Cache efficiency metrics
 * - Time savings estimates
 *
 * Part of Phase 3.3: Semantic Caching UI Components
 */
export const CacheStatistics: React.FC = () => {
  const [stats, setStats] = useState<CacheStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      const data = await cacheAPI.getStats();
      setStats(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load data'));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-48 bg-gray-200 rounded-lg" />
        <div className="h-48 bg-gray-200 rounded-lg" />
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

  // Calculate percentages
  const totalLookups = semantic?.total_lookups || 0;
  const exactHits = semantic?.exact_hits || 0;
  const semanticHits = semantic?.semantic_hits || 0;
  const misses = semantic?.misses || 0;

  const exactPercent = totalLookups > 0 ? (exactHits / totalLookups) * 100 : 0;
  const semanticPercent = totalLookups > 0 ? (semanticHits / totalLookups) * 100 : 0;
  const missPercent = totalLookups > 0 ? (misses / totalLookups) * 100 : 0;

  // Estimated time savings (rough estimates)
  const avgTimeSavedPerHit = 2.5; // seconds
  const totalHits = exactHits + semanticHits;
  const estimatedTimeSaved = totalHits * avgTimeSavedPerHit;

  return (
    <div className="space-y-6">
      {/* Hit Type Distribution */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-amber-600" />
          Hit Type Distribution
        </h3>

        <div className="space-y-4">
          {/* Exact Hits */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-gray-700">Exact Hits</span>
              <span className="text-sm text-gray-600">
                {exactHits} ({exactPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(exactPercent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Identical queries - fastest response
            </p>
          </div>

          {/* Semantic Hits */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-gray-700">Semantic Hits</span>
              <span className="text-sm text-gray-600">
                {semanticHits} ({semanticPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-blue-500 h-4 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(semanticPercent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Similar queries matched by embedding similarity
            </p>
          </div>

          {/* Misses */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-gray-700">Cache Misses</span>
              <span className="text-sm text-gray-600">
                {misses} ({missPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-gray-400 h-4 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(missPercent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              New queries requiring full processing
            </p>
          </div>
        </div>
      </div>

      {/* LLM Cache Statistics */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          LLM Response Cache
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-700">Hit Rate</p>
            <p className="text-2xl font-bold text-blue-900">
              {llm?.hit_rate_percent?.toFixed(1) || 0}%
            </p>
            <p className="text-xs text-blue-600 mt-1">
              {llm?.hits || 0} hits / {llm?.total_lookups || 0} lookups
            </p>
          </div>

          <div className="p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-lg border border-green-200">
            <p className="text-sm text-green-700">LLM Calls Saved</p>
            <p className="text-2xl font-bold text-green-900">{llm?.hits || 0}</p>
            <p className="text-xs text-green-600 mt-1">
              Each hit saves 2-5 seconds
            </p>
          </div>

          <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
            <p className="text-sm text-purple-700">Stored Entries</p>
            <p className="text-2xl font-bold text-purple-900">{llm?.total_stores || 0}</p>
            <p className="text-xs text-purple-600 mt-1">
              Threshold: {llm?.similarity_threshold || 0.88}
            </p>
          </div>
        </div>
      </div>

      {/* Embedding Service Stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-purple-600" />
          Embedding Service Efficiency
        </h3>

        <div className="space-y-4">
          {/* Embedding Cache Hit Rate */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-gray-700">Embedding Cache Hit Rate</span>
              <span className="text-sm text-gray-600">
                {embedding?.cache_hit_rate_percent?.toFixed(1) || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-purple-500 h-4 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(embedding?.cache_hit_rate_percent || 0, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Cached embeddings avoid recomputation (saves 50-200ms each)
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-gray-900">{embedding?.total_requests || 0}</p>
              <p className="text-xs text-gray-500">Total Requests</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-green-600">{embedding?.cache_hits || 0}</p>
              <p className="text-xs text-gray-500">Cache Hits</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-blue-600">{embedding?.ollama_calls || 0}</p>
              <p className="text-xs text-gray-500">Ollama Calls</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-orange-600">{embedding?.tfidf_fallbacks || 0}</p>
              <p className="text-xs text-gray-500">TF-IDF Fallbacks</p>
            </div>
          </div>
        </div>
      </div>

      {/* Estimated Time Savings */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200 p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-amber-600" />
          Estimated Performance Impact
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-white rounded-lg border border-amber-200">
            <p className="text-3xl font-bold text-amber-600">
              {estimatedTimeSaved >= 60
                ? `${(estimatedTimeSaved / 60).toFixed(1)}m`
                : `${estimatedTimeSaved.toFixed(0)}s`}
            </p>
            <p className="text-sm text-gray-600 mt-1">Estimated Time Saved</p>
            <p className="text-xs text-gray-400">Based on ~2.5s per cache hit</p>
          </div>

          <div className="text-center p-4 bg-white rounded-lg border border-amber-200">
            <p className="text-3xl font-bold text-green-600">
              {totalHits + (llm?.hits || 0)}
            </p>
            <p className="text-sm text-gray-600 mt-1">Total Cache Hits</p>
            <p className="text-xs text-gray-400">Semantic + LLM combined</p>
          </div>

          <div className="text-center p-4 bg-white rounded-lg border border-amber-200">
            <p className="text-3xl font-bold text-blue-600">
              {totalLookups > 0
                ? `${(((exactHits + semanticHits) / totalLookups) * 100).toFixed(0)}%`
                : '0%'}
            </p>
            <p className="text-sm text-gray-600 mt-1">Overall Efficiency</p>
            <p className="text-xs text-gray-400">Queries served from cache</p>
          </div>
        </div>
      </div>

      {/* Refresh Button */}
      <div className="flex justify-end">
        <button
          onClick={() => loadData(false)}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh Statistics
        </button>
      </div>
    </div>
  );
};

export default CacheStatistics;
