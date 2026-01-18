import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Clock, RefreshCw } from 'lucide-react';
import { cacheAPI, type CacheStatsResponse } from '../services/cacheApi';
import axios from 'axios';

const getErrorMessage = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) return err.response?.data?.detail || err.message || fallback;
  if (err instanceof Error) return err.message;
  return fallback;
};

export const CacheStatistics: React.FC = () => {
  const [stats, setStats] = useState<CacheStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData(true);
    const interval = setInterval(() => loadData(false), 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async (isInitial = false) => {
    if (isInitial) setLoading(true);
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
        <div className="h-48 glass-panel rounded-2xl" />
        <div className="h-48 glass-panel rounded-2xl" />
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

  const semantic = stats?.semantic_cache;
  const llm = stats?.llm_cache;
  const embedding = stats?.embedding_service;

  const totalLookups = semantic?.total_lookups || 0;
  const exactHits = semantic?.exact_hits || 0;
  const semanticHits = semantic?.semantic_hits || 0;
  const misses = semantic?.misses || 0;

  const exactPercent = totalLookups > 0 ? (exactHits / totalLookups) * 100 : 0;
  const semanticPercent = totalLookups > 0 ? (semanticHits / totalLookups) * 100 : 0;
  const missPercent = totalLookups > 0 ? (misses / totalLookups) * 100 : 0;

  const avgTimeSavedPerHit = 2.5;
  const totalHits = exactHits + semanticHits;
  const estimatedTimeSaved = totalHits * avgTimeSavedPerHit;

  return (
    <div className="space-y-6">
      {/* Hit Type Distribution */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          <BarChart3 className="w-4 h-4 text-amber-500" />
          Hit Distribution
        </h3>

        <div className="space-y-5">
          {[
            { label: 'Exact Hits', value: exactHits, percent: exactPercent, color: 'emerald', desc: 'Identical queries - fastest response' },
            { label: 'Semantic Hits', value: semanticHits, percent: semanticPercent, color: 'blue', desc: 'Similar queries matched by embedding' },
            { label: 'Misses', value: misses, percent: missPercent, color: 'gray', desc: 'New queries requiring full processing' },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">{item.label}</span>
                <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">
                  {item.value} ({item.percent.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full bg-black/5 dark:bg-white/5 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${
                    item.color === 'emerald' ? 'from-emerald-500 to-green-500' :
                    item.color === 'blue' ? 'from-blue-500 to-cyan-500' :
                    'from-gray-400 to-gray-500'
                  }`}
                  style={{ width: `${Math.min(item.percent, 100)}%` }}
                />
              </div>
              <p className="text-[10px] font-medium text-gray-400 mt-1">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* LLM Cache Statistics */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          <TrendingUp className="w-4 h-4 text-blue-500" />
          LLM Response Cache
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass-card rounded-xl p-5 bg-gradient-to-br from-blue-500/10 via-transparent to-blue-500/5 border-blue-500/20">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Hit Rate</p>
            <p className="text-3xl font-black text-gray-900 dark:text-white mt-2">{llm?.hit_rate_percent?.toFixed(1) || 0}%</p>
            <p className="text-[10px] font-bold text-gray-400 mt-1 uppercase tracking-widest">{llm?.hits || 0} / {llm?.total_lookups || 0}</p>
          </div>
          <div className="glass-card rounded-xl p-5 bg-gradient-to-br from-emerald-500/10 via-transparent to-emerald-500/5 border-emerald-500/20">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">LLM Calls Saved</p>
            <p className="text-3xl font-black text-gray-900 dark:text-white mt-2">{llm?.hits || 0}</p>
            <p className="text-[10px] font-bold text-gray-400 mt-1 uppercase tracking-widest">Saves 2-5s each</p>
          </div>
          <div className="glass-card rounded-xl p-5 bg-gradient-to-br from-purple-500/10 via-transparent to-purple-500/5 border-purple-500/20">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Stored Entries</p>
            <p className="text-3xl font-black text-gray-900 dark:text-white mt-2">{llm?.total_stores || 0}</p>
            <p className="text-[10px] font-bold text-gray-400 mt-1 uppercase tracking-widest">Threshold: {llm?.similarity_threshold || 0.88}</p>
          </div>
        </div>
      </div>

      {/* Embedding Service Stats */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-purple-500" />
          <TrendingUp className="w-4 h-4 text-purple-500" />
          Embedding Efficiency
        </h3>

        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">Cache Hit Rate</span>
            <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">
              {embedding?.cache_hit_rate_percent?.toFixed(1) || 0}%
            </span>
          </div>
          <div className="w-full bg-black/5 dark:bg-white/5 rounded-full h-3 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-purple-500 to-indigo-500"
              style={{ width: `${Math.min(embedding?.cache_hit_rate_percent || 0, 100)}%` }}
            />
          </div>
          <p className="text-[10px] font-medium text-gray-400 mt-1">Cached embeddings save 50-200ms each</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Requests', value: embedding?.total_requests || 0, color: 'text-gray-900 dark:text-white' },
            { label: 'Cache Hits', value: embedding?.cache_hits || 0, color: 'text-emerald-600 dark:text-emerald-400' },
            { label: 'Ollama', value: embedding?.ollama_calls || 0, color: 'text-blue-600 dark:text-blue-400' },
            { label: 'Fallbacks', value: embedding?.tfidf_fallbacks || 0, color: 'text-amber-600 dark:text-amber-400' },
          ].map((item) => (
            <div key={item.label} className="glass-panel rounded-xl p-3 border-white/10 text-center">
              <p className={`text-xl font-black ${item.color}`}>{item.value}</p>
              <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest mt-1">{item.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Estimated Time Savings */}
      <div className="glass-panel rounded-2xl p-6 border-white/10 bg-gradient-to-br from-amber-500/5 via-transparent to-yellow-500/5">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          <Clock className="w-4 h-4 text-amber-500" />
          Performance Impact
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass-card rounded-xl p-5 text-center">
            <p className="text-4xl font-black text-amber-600 dark:text-amber-400">
              {estimatedTimeSaved >= 60 ? `${(estimatedTimeSaved / 60).toFixed(1)}m` : `${estimatedTimeSaved.toFixed(0)}s`}
            </p>
            <p className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300 mt-2">Time Saved</p>
            <p className="text-[10px] font-medium text-gray-400 mt-1">~2.5s per hit</p>
          </div>
          <div className="glass-card rounded-xl p-5 text-center">
            <p className="text-4xl font-black text-emerald-600 dark:text-emerald-400">{totalHits + (llm?.hits || 0)}</p>
            <p className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300 mt-2">Total Hits</p>
            <p className="text-[10px] font-medium text-gray-400 mt-1">Semantic + LLM</p>
          </div>
          <div className="glass-card rounded-xl p-5 text-center">
            <p className="text-4xl font-black text-blue-600 dark:text-blue-400">
              {totalLookups > 0 ? `${(((exactHits + semanticHits) / totalLookups) * 100).toFixed(0)}%` : '0%'}
            </p>
            <p className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300 mt-2">Efficiency</p>
            <p className="text-[10px] font-medium text-gray-400 mt-1">From cache</p>
          </div>
        </div>
      </div>

      {/* Refresh Button */}
      <div className="flex justify-end">
        <button
          onClick={() => loadData(false)}
          className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 transition-all text-xs font-black uppercase tracking-widest"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>
    </div>
  );
};

export default CacheStatistics;
