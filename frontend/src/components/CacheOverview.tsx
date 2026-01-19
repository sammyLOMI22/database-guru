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
 */
export const CacheOverview: React.FC = () => {
  const [stats, setStats] = useState<CacheStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData(true);
    const interval = setInterval(() => loadData(false), 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    else setRefreshing(true);
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
    if (!window.confirm(messages[cacheType])) return;

    setClearing(cacheType);
    try {
      if (cacheType === 'semantic') await cacheAPI.clearSemanticCache();
      else if (cacheType === 'llm') await cacheAPI.clearLLMCache();
      else await cacheAPI.clearAllCaches();
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
        <div className="h-20 glass-panel rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 glass-panel rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="glass-panel rounded-2xl p-8 max-w-md mx-auto">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <div className="text-red-500 mb-4 text-sm font-bold uppercase tracking-widest">Service Error</div>
          <p className="text-xs text-gray-500 mb-6">{error}</p>
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
  const redisConnected = stats?.redis_connected ?? false;

  return (
    <div className="space-y-6">
      {/* Service Status Banner */}
      <div className="glass-panel rounded-2xl p-5 border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 flex items-center gap-2">
            <Server className="w-4 h-4" />
            Service Status
          </h3>
          {refreshing && (
            <div className="flex items-center gap-2 text-[11px] font-bold text-gray-400 uppercase tracking-widest">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Refreshing
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Redis Status */}
          <div className={`glass-card rounded-xl p-4 flex items-center justify-between ${
            redisConnected ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5' : 'border-red-500/30 bg-gradient-to-br from-red-500/10 to-red-500/5'
          }`}>
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-xl glass-panel flex items-center justify-center ${redisConnected ? 'text-emerald-500' : 'text-red-500'}`}>
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-widest text-gray-900 dark:text-white">Redis Cache</h3>
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                  {redisConnected ? 'Semantic caching active' : 'Disconnected'}
                </p>
              </div>
            </div>
            <span className={`text-[11px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg ${
              redisConnected ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/20 text-red-600 dark:text-red-400'
            }`}>
              {redisConnected ? 'Online' : 'Offline'}
            </span>
          </div>

          {/* Ollama Status */}
          <div className={`glass-card rounded-xl p-4 flex items-center justify-between ${
            embedding?.ollama_available ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5' : 'border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-amber-500/5'
          }`}>
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-xl glass-panel flex items-center justify-center ${embedding?.ollama_available ? 'text-emerald-500' : 'text-amber-500'}`}>
                {embedding?.ollama_available ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-widest text-gray-900 dark:text-white">Embeddings</h3>
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                  {embedding?.ollama_available ? 'nomic-embed-text' : 'TF-IDF fallback'}
                </p>
              </div>
            </div>
            <span className={`text-[11px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg ${
              embedding?.ollama_available ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-amber-500/20 text-amber-600 dark:text-amber-400'
            }`}>
              {embedding?.ollama_available ? 'Ollama' : 'Fallback'}
            </span>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-blue-500/10 via-transparent to-blue-500/5 border-blue-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">Lookups</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">{semantic?.total_lookups || 0}</p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform">
              <Activity className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-amber-500/10 via-transparent to-amber-500/5 border-amber-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-amber-600 dark:text-amber-400">Hit Rate</p>
              <p className={`text-4xl font-black mt-2 ${(semantic?.hit_rate_percent || 0) > 50 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                {semantic ? `${semantic.hit_rate_percent.toFixed(0)}%` : '0%'}
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-amber-500 group-hover:scale-110 transition-transform">
              <Zap className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-purple-500/10 via-transparent to-purple-500/5 border-purple-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-purple-600 dark:text-purple-400">Semantic</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">{semantic?.semantic_hits || 0}</p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-purple-500 group-hover:scale-110 transition-transform">
              <Zap className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 bg-gradient-to-br from-emerald-500/10 via-transparent to-emerald-500/5 border-emerald-500/20 group">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-emerald-600 dark:text-emerald-400">Cached</p>
              <p className="text-4xl font-black text-gray-900 dark:text-white mt-2">{semantic?.memory_entries || 0}</p>
            </div>
            <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-emerald-500 group-hover:scale-110 transition-transform">
              <Clock className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Cache Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel rounded-2xl p-6 border-white/10">
          <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            Semantic Cache
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Total Hits', value: semantic?.total_hits || 0, color: 'text-gray-900 dark:text-white' },
              { label: 'Exact Hits', value: semantic?.exact_hits || 0, color: 'text-emerald-600 dark:text-emerald-400' },
              { label: 'Semantic Hits', value: semantic?.semantic_hits || 0, color: 'text-blue-600 dark:text-blue-400' },
              { label: 'Misses', value: semantic?.misses || 0, color: 'text-gray-400' },
            ].map((item) => (
              <div key={item.label} className="flex justify-between items-center glass-panel rounded-xl px-4 py-3 border-white/10">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">{item.label}</span>
                <span className={`text-sm font-black ${item.color}`}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-6 border-white/10">
          <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            LLM Cache
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Lookups', value: llm?.total_lookups || 0, color: 'text-gray-900 dark:text-white' },
              { label: 'Hits', value: llm?.hits || 0, color: 'text-emerald-600 dark:text-emerald-400' },
              { label: 'Hit Rate', value: `${llm?.hit_rate_percent?.toFixed(0) || 0}%`, color: 'text-blue-600 dark:text-blue-400' },
              { label: 'Misses', value: llm?.misses || 0, color: 'text-gray-400' },
            ].map((item) => (
              <div key={item.label} className="flex justify-between items-center glass-panel rounded-xl px-4 py-3 border-white/10">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">{item.label}</span>
                <span className={`text-sm font-black ${item.color}`}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="glass-panel rounded-2xl p-6 border-white/10 bg-gradient-to-br from-amber-500/5 via-transparent to-yellow-500/5">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          How It Works
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { step: 1, title: 'Vector Embed', desc: 'Queries converted to vectors using Ollama embeddings' },
            { step: 2, title: 'Similarity Search', desc: 'Cosine similarity finds queries with same intent' },
            { step: 3, title: 'Instant Response', desc: 'Matches return cached SQL in milliseconds' },
          ].map((item) => (
            <div key={item.step} className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-amber-500 to-yellow-500 text-white rounded-xl flex items-center justify-center font-black text-sm shadow-lg shadow-amber-500/20">
                {item.step}
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-widest text-gray-900 dark:text-white">{item.title}</p>
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleClearCache('semantic')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-amber-600 dark:text-amber-400 hover:scale-105 active:scale-95 disabled:opacity-50 transition-all text-xs font-black uppercase tracking-widest border-amber-500/20 bg-gradient-to-r from-amber-500/10 to-yellow-500/10"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'semantic' ? 'animate-pulse' : ''}`} />
            {clearing === 'semantic' ? 'Clearing...' : 'Clear Semantic'}
          </button>
          <button
            onClick={() => handleClearCache('llm')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-blue-600 dark:text-blue-400 hover:scale-105 active:scale-95 disabled:opacity-50 transition-all text-xs font-black uppercase tracking-widest border-blue-500/20 bg-gradient-to-r from-blue-500/10 to-cyan-500/10"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'llm' ? 'animate-pulse' : ''}`} />
            {clearing === 'llm' ? 'Clearing...' : 'Clear LLM'}
          </button>
          <button
            onClick={() => handleClearCache('all')}
            disabled={!!clearing}
            className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-red-600 dark:text-red-400 hover:scale-105 active:scale-95 disabled:opacity-50 transition-all text-xs font-black uppercase tracking-widest border-red-500/20 bg-gradient-to-r from-red-500/10 to-rose-500/10"
          >
            <Trash2 className={`w-4 h-4 ${clearing === 'all' ? 'animate-pulse' : ''}`} />
            {clearing === 'all' ? 'Clearing...' : 'Clear All'}
          </button>
          <button
            onClick={() => loadData(false)}
            disabled={refreshing}
            className="flex items-center gap-2 px-5 py-2.5 glass-card rounded-xl text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 disabled:opacity-50 transition-all text-xs font-black uppercase tracking-widest"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
};

export default CacheOverview;
