import React, { useState, useEffect, useRef } from 'react';
import {
  Database,
  Activity,
  AlertTriangle,
  RefreshCw,
  Gauge,
  BarChart3,
  ShieldCheck,
  Trash2,
  XCircle,
  Server,
} from 'lucide-react';
import { poolsAPI, type PoolStatsResponse, type PoolInfo, type PoolHealthResponse } from '../services/poolsApi';
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
 * Connection Pool Metrics Dashboard
 *
 * Displays real-time monitoring of database connection pools:
 * - Pool statistics overview
 * - Per-database pool status table
 * - Health indicators and warnings
 * - Manual pool eviction controls
 */
export const ConnectionPoolMetrics: React.FC = () => {
  const [stats, setStats] = useState<PoolStatsResponse | null>(null);
  const [health, setHealth] = useState<PoolHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evicting, setEvicting] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Use ref to store interval ID for manual control
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startAutoRefresh = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    intervalRef.current = setInterval(() => {
      loadData(false);
    }, 10000);
  };

  useEffect(() => {
    loadData(true);
    startAutoRefresh();

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const loadData = async (isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    setError(null);
    try {
      const [statsData, healthData] = await Promise.all([
        poolsAPI.getPoolStats(),
        poolsAPI.getPoolHealth(),
      ]);
      setStats(statsData);
      setHealth(healthData);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load pool metrics'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleEvictPool = async (connectionId: number, databaseType: string) => {
    if (!window.confirm(
      `Evict ${databaseType} pool for connection #${connectionId}? The pool will be recreated on next use.`
    )) {
      return;
    }

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setEvicting(connectionId);
    setError(null);
    try {
      await poolsAPI.evictConnectionPools(connectionId, databaseType);
      await new Promise(resolve => setTimeout(resolve, 300));
      await loadData(true);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to evict pool'));
    } finally {
      setEvicting(null);
      startAutoRefresh();
    }
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const isHealthy = health?.status === 'healthy';

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-20 glass-panel rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 glass-panel rounded-2xl" />
          ))}
        </div>
        <div className="h-64 glass-panel rounded-2xl" />
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
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-cyan-500/20"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats?.pooling_enabled) {
    return (
      <div className="text-center py-16 glass-panel rounded-2xl border-white/10">
        <div className="w-20 h-20 rounded-2xl glass-card flex items-center justify-center mx-auto mb-5">
          <Server className="w-10 h-10 text-gray-400" />
        </div>
        <h3 className="text-xl font-black uppercase tracking-widest text-gray-700 dark:text-gray-300 mb-3">
          Connection Pooling Disabled
        </h3>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400 max-w-md mx-auto">
          Set <code className="px-2 py-0.5 glass-panel rounded text-cyan-600 dark:text-cyan-400 text-xs font-mono">ENABLE_CONNECTION_POOLING=True</code> to enable connection pooling
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <div className={`glass-panel rounded-2xl p-5 flex items-center justify-between border ${isHealthy
          ? 'bg-gradient-to-r from-emerald-500/10 via-transparent to-green-500/10 border-emerald-500/20'
          : 'bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/10 border-red-500/20'
        }`}>
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-xl glass-panel flex items-center justify-center ${isHealthy ? 'text-emerald-500' : 'text-red-500'}`}>
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-red-500'} animate-pulse`} />
              Connection Pool Health
            </h3>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {isHealthy
                ? 'All connection pools are within normal operating parameters'
                : 'Some pools are experiencing high utilization or degradation'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {refreshing && (
            <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
          )}
          <span className={`px-3 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg ${isHealthy
              ? 'bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
              : 'bg-gradient-to-r from-red-500/20 to-rose-500/20 text-red-600 dark:text-red-400 border border-red-500/30'
            }`}>
            {isHealthy ? 'HEALTHY' : 'DEGRADED'}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Pools Card */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-blue-500/10 via-transparent to-blue-500/5 hover:border-blue-500/30 transition-all duration-300 group">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Total Pools</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">
              {stats?.total_pools || 0}
            </p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform">
              <Database className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[10px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            Active connection pools
          </p>
        </div>

        {/* Active Connections Card */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-emerald-500/10 via-transparent to-emerald-500/5 hover:border-emerald-500/30 transition-all duration-300 group">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Active Connections</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">
              {stats?.global_metrics.total_active_connections || 0}
            </p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-emerald-500 group-hover:scale-110 transition-transform">
              <Activity className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[10px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            Currently processing queries
          </p>
        </div>

        {/* Idle Connections Card */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-gray-500/10 via-transparent to-gray-500/5 hover:border-gray-500/30 transition-all duration-300 group">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Idle Connections</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">
              {stats?.global_metrics.total_idle_connections || 0}
            </p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-gray-500 group-hover:scale-110 transition-transform">
              <BarChart3 className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[10px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            Available in pool
          </p>
        </div>

        {/* Average Utilization Card */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-purple-500/10 via-transparent to-purple-500/5 hover:border-purple-500/30 transition-all duration-300 group">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Average Utilization</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">
              {stats?.global_metrics.avg_utilization_percent.toFixed(0) || 0}%
            </p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-purple-500 group-hover:scale-110 transition-transform">
              <Gauge className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[10px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            Average across pools
          </p>
        </div>
      </div>

      {/* Per-Pool Status Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border-white/10">
        <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between bg-black/5 dark:bg-white/5">
          <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            Active Pools
          </h3>
          <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest glass-panel px-3 py-1.5 rounded-lg">
            {stats?.pools.length || 0} pools monitored
          </span>
        </div>

        {stats.pools.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 rounded-2xl glass-card flex items-center justify-center mx-auto mb-4">
              <Database className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">No active pools</p>
            <p className="text-xs font-medium text-gray-400 mt-2">Pools will be created on first query</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-black/5 dark:bg-white/5">
                <tr>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Connection</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Active</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Idle</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Utilization</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Status</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Wait Time</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Age</th>
                  <th className="px-6 py-4 border-b border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {stats.pools.map((pool: PoolInfo) => (
                  <tr key={`${pool.connection_id}-${pool.database_type}`} className="hover:bg-white/5 dark:hover:bg-white/5 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-bold text-gray-900 dark:text-white">#{pool.connection_id}</div>
                        <div className="text-[10px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">{pool.connection_name} ({pool.database_type})</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-black text-gray-900 dark:text-white">{pool.metrics.active_connections}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-black text-gray-900 dark:text-white">{pool.metrics.idle_connections}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-20 bg-black/5 dark:bg-white/5 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${pool.metrics.utilization_percent > 80
                              ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                              : 'bg-gradient-to-r from-emerald-500 to-green-500'
                              }`}
                            style={{ width: `${pool.metrics.utilization_percent}%` }}
                          />
                        </div>
                        <span className="text-sm font-black text-gray-900 dark:text-white">
                          {pool.metrics.utilization_percent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest ${pool.metrics.health_status === 'healthy'
                          ? 'bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                          : 'bg-gradient-to-r from-red-500/20 to-rose-500/20 text-red-600 dark:text-red-400 border border-red-500/30'
                        }`}>
                        {pool.metrics.health_status === 'healthy' ? (
                          <>
                            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                            Healthy
                          </>
                        ) : 'Degraded'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-bold text-gray-900 dark:text-white">
                        {pool.metrics.avg_wait_time_ms.toFixed(1)}ms
                      </div>
                      <div className="text-[10px] font-medium text-gray-400 mt-0.5">
                        max: {pool.metrics.max_wait_time_ms.toFixed(0)}ms
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-bold text-gray-900 dark:text-white">
                        {formatDuration(pool.age_seconds)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          handleEvictPool(pool.connection_id, pool.database_type);
                        }}
                        disabled={evicting === pool.connection_id}
                        className="p-2.5 rounded-xl glass-panel text-red-500 hover:bg-red-500/10 hover:border-red-500/30 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                        title="Evict pool (will be recreated on next use)"
                      >
                        {evicting === pool.connection_id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Warnings Section */}
      {health?.unhealthy_pools && health.unhealthy_pools.length > 0 && (
        <div className="glass-panel rounded-2xl p-5 border-2 border-red-500/30 bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/10">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-red-500 flex-shrink-0">
              <XCircle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-black uppercase tracking-widest text-red-600 dark:text-red-400 mb-3">Unhealthy Pools</h4>
              <ul className="space-y-2">
                {health.unhealthy_pools.map((pool) => (
                  <li key={`${pool.connection_id}-${pool.database_type}`} className="text-xs font-medium text-red-700 dark:text-red-300 glass-panel px-3 py-2 rounded-lg">
                    Connection #{pool.connection_id} ({pool.database_type}): <span className="font-bold">{pool.failed_checkouts}</span> failed checkouts
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {health?.high_utilization_pools && health.high_utilization_pools.length > 0 && (
        <div className="glass-panel rounded-2xl p-5 border-2 border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-transparent to-yellow-500/10">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-amber-500 flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-black uppercase tracking-widest text-amber-600 dark:text-amber-400 mb-3">High Utilization Pools</h4>
              <ul className="space-y-2">
                {health.high_utilization_pools.map((pool) => (
                  <li key={`${pool.connection_id}-${pool.database_type}`} className="text-xs font-medium text-amber-700 dark:text-amber-300 glass-panel px-3 py-2 rounded-lg">
                    Connection #{pool.connection_id} ({pool.database_type}): <span className="font-bold">{(pool.utilization * 100).toFixed(0)}%</span> utilization
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConnectionPoolMetrics;
