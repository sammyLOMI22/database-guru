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
        <div className="h-16 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-200 dark:bg-gray-800 rounded-lg" />
          ))}
        </div>
        <div className="h-48 bg-gray-200 dark:bg-gray-800 rounded-lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button
          onClick={() => loadData(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!stats?.pooling_enabled) {
    return (
      <div className="text-center py-12">
        <Server className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Connection Pooling Disabled
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Set ENABLE_CONNECTION_POOLING=True to enable connection pooling
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <div className={`p-4 rounded-lg flex items-center justify-between shadow-sm border ${isHealthy
          ? 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800/50 text-green-700 dark:text-green-400'
          : 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800/50 text-red-700 dark:text-red-400'
        }`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full ${isHealthy ? 'bg-green-100 dark:bg-green-900/40' : 'bg-red-100 dark:bg-red-900/40'}`}>
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              Connection Pool Health
            </h3>
            <p className="text-sm opacity-90">
              {isHealthy
                ? 'All connection pools are within normal operating parameters'
                : 'Some pools are experiencing high utilization or degradation'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {refreshing && (
            <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
          )}
          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${isHealthy
              ? 'bg-green-200 dark:bg-green-800/50 text-green-800 dark:text-green-300'
              : 'bg-red-200 dark:bg-red-800/50 text-red-800 dark:text-red-300'
            }`}>
            {isHealthy ? 'HEALTHY' : 'DEGRADED'}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Pools Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Pools</p>
          <div className="flex items-center justify-between mt-1">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.total_pools || 0}
            </p>
            <Database className="w-8 h-8 text-blue-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Active connection pools
          </div>
        </div>

        {/* Active Connections Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Active Connections</p>
          <div className="flex items-center justify-between mt-1">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.global_metrics.total_active_connections || 0}
            </p>
            <Activity className="w-8 h-8 text-green-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Currently processing queries
          </div>
        </div>

        {/* Idle Connections Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Idle Connections</p>
          <div className="flex items-center justify-between mt-1">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.global_metrics.total_idle_connections || 0}
            </p>
            <BarChart3 className="w-8 h-8 text-slate-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Available in pool
          </div>
        </div>

        {/* Average Utilization Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Average Utilization</p>
          <div className="flex items-center justify-between mt-1">
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats?.global_metrics.avg_utilization_percent.toFixed(0) || 0}%
            </p>
            <Gauge className="w-8 h-8 text-purple-500 opacity-50 dark:opacity-30" />
          </div>
          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
            Average across pools
          </div>
        </div>
      </div>

      {/* Per-Pool Status Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-gray-900/50">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-green-500" />
            Active Pools
          </h3>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {stats?.pools.length || 0} pools monitored
          </span>
        </div>

        {stats.pools.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No active pools. Pools will be created on first query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-gray-50 dark:bg-gray-900/50 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Connection</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Active</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Idle</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Utilization</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Status</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Wait Time</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Age</th>
                  <th className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {stats.pools.map((pool: PoolInfo) => (
                  <tr key={`${pool.connection_id}-${pool.database_type}`} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-gray-100">#{pool.connection_id}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{pool.connection_name} ({pool.database_type})</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">{pool.metrics.active_connections}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">{pool.metrics.idle_connections}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${pool.metrics.utilization_percent > 80 ? 'bg-amber-500' : 'bg-green-500'
                              }`}
                            style={{ width: `${pool.metrics.utilization_percent}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {pool.metrics.utilization_percent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${pool.metrics.health_status === 'healthy'
                          ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400'
                          : 'bg-red-100 dark:bg-red-800/50 text-red-700 dark:text-red-400'
                        }`}>
                        {pool.metrics.health_status === 'healthy' ? (
                          <>
                            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                            Healthy
                          </>
                        ) : 'Degraded'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">
                      {pool.metrics.avg_wait_time_ms.toFixed(1)}ms
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        max: {pool.metrics.max_wait_time_ms.toFixed(0)}ms
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">
                      {formatDuration(pool.age_seconds)}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          handleEvictPool(pool.connection_id, pool.database_type);
                        }}
                        disabled={evicting === pool.connection_id}
                        className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors disabled:opacity-50"
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
        <div className="bg-red-50 dark:bg-red-950/20 border-2 border-red-200 dark:border-red-800/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-red-900 dark:text-red-100 mb-2">Unhealthy Pools</h4>
              <ul className="space-y-1 text-sm text-red-700 dark:text-red-300">
                {health.unhealthy_pools.map((pool) => (
                  <li key={`${pool.connection_id}-${pool.database_type}`}>
                    Connection #{pool.connection_id} ({pool.database_type}): {pool.failed_checkouts} failed checkouts
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {health?.high_utilization_pools && health.high_utilization_pools.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-950/20 border-2 border-yellow-200 dark:border-yellow-800/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-2">High Utilization Pools</h4>
              <ul className="space-y-1 text-sm text-yellow-700 dark:text-yellow-300">
                {health.high_utilization_pools.map((pool) => (
                  <li key={`${pool.connection_id}-${pool.database_type}`}>
                    Connection #{pool.connection_id} ({pool.database_type}): {(pool.utilization * 100).toFixed(0)}% utilization
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
