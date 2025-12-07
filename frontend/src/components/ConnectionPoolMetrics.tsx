import React, { useState, useEffect, useRef } from 'react';
import {
  Database,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Trash2,
  Clock,
  TrendingUp,
  Server,
  Gauge,
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
 *
 * Part of Phase 4.1: Connection Pooling Optimization (Day 3)
 */
export const ConnectionPoolMetrics: React.FC = () => {
  const [stats, setStats] = useState<PoolStatsResponse | null>(null);
  const [health, setHealth] = useState<PoolHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evicting, setEvicting] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Use ref to store interval ID for manual control
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const startAutoRefresh = () => {
    // Clear any existing interval first
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    // Start new interval
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

    // Pause auto-refresh during eviction to prevent race conditions
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setEvicting(connectionId);
    setError(null);
    try {
      const result = await poolsAPI.evictConnectionPools(connectionId, databaseType);
      console.log('✅ Eviction successful:', result);

      // Small delay to ensure backend has fully processed eviction
      await new Promise(resolve => setTimeout(resolve, 300));

      // Force full reload of data with loading state
      console.log('🔄 Reloading pool data...');
      await loadData(true);
      console.log('✅ Data reloaded. Total pools:', stats?.total_pools);
    } catch (err: unknown) {
      console.error('❌ Eviction error:', err);
      setError(getErrorMessage(err, 'Failed to evict pool'));
    } finally {
      setEvicting(null);
      // Restart auto-refresh
      startAutoRefresh();
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'degraded':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'unhealthy':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Activity className="w-4 h-4 text-gray-400" />;
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'unhealthy':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 80) return 'bg-red-500';
    if (utilization >= 60) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-200 rounded-lg" />
          ))}
        </div>
        <div className="h-64 bg-gray-200 rounded-lg" />
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

  // Check if pooling is disabled
  if (!stats?.pooling_enabled) {
    return (
      <div className="text-center py-12">
        <Server className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-700 mb-2">
          Connection Pooling Disabled
        </h3>
        <p className="text-gray-600 mb-4">
          Set ENABLE_CONNECTION_POOLING=True to enable connection pooling
        </p>
      </div>
    );
  }

  const globalMetrics = stats.global_metrics;

  return (
    <div className="space-y-6">
      {/* Overall Status Banner */}
      <div className={`rounded-lg border-2 p-4 ${getHealthColor(health?.status || 'disabled')}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getHealthIcon(health?.status || 'disabled')}
            <div>
              <h3 className="font-semibold">
                Pool Health: {health?.status?.toUpperCase()}
              </h3>
              {health?.warnings && health.warnings.length > 0 && (
                <p className="text-sm mt-1">
                  {health.warnings.join(', ')}
                </p>
              )}
            </div>
          </div>
          {refreshing && (
            <div className="flex items-center gap-2 text-sm">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Refreshing...
            </div>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Pools */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border-2 border-blue-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Database className="w-8 h-8 text-blue-600" />
            <span className="text-3xl font-bold text-blue-900">
              {stats.total_pools}
            </span>
          </div>
          <div className="text-sm font-medium text-blue-700">Total Pools</div>
          <div className="text-xs text-blue-600 mt-1">
            Active connection pools
          </div>
        </div>

        {/* Active Connections */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg border-2 border-green-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Activity className="w-8 h-8 text-green-600" />
            <span className="text-3xl font-bold text-green-900">
              {globalMetrics.total_active_connections}
            </span>
          </div>
          <div className="text-sm font-medium text-green-700">Active</div>
          <div className="text-xs text-green-600 mt-1">
            Currently in use
          </div>
        </div>

        {/* Idle Connections */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border-2 border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Clock className="w-8 h-8 text-gray-600" />
            <span className="text-3xl font-bold text-gray-900">
              {globalMetrics.total_idle_connections}
            </span>
          </div>
          <div className="text-sm font-medium text-gray-700">Idle</div>
          <div className="text-xs text-gray-600 mt-1">
            Ready for reuse
          </div>
        </div>

        {/* Average Utilization */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border-2 border-purple-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <Gauge className="w-8 h-8 text-purple-600" />
            <span className="text-3xl font-bold text-purple-900">
              {globalMetrics.avg_utilization_percent.toFixed(0)}%
            </span>
          </div>
          <div className="text-sm font-medium text-purple-700">Utilization</div>
          <div className="text-xs text-purple-600 mt-1">
            Average across pools
          </div>
        </div>
      </div>

      {/* Per-Pool Status Table */}
      <div className="bg-white rounded-lg border-2 border-gray-200 overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Pool Details
          </h3>
        </div>

        {stats.pools.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No active pools. Pools will be created on first query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Connection
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Database Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Health
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Connections
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Utilization
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Wait Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Age
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {stats.pools.map((pool: PoolInfo) => (
                  <tr key={`${pool.connection_id}-${pool.database_type}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      #{pool.connection_id}
                      <div className="text-xs text-gray-500">{pool.connection_name}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      <span className="px-2 py-1 rounded bg-gray-100 text-xs font-mono">
                        {pool.database_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getHealthIcon(pool.metrics.health_status)}
                        <span className="text-xs capitalize">
                          {pool.metrics.health_status}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-green-600 font-semibold">
                          {pool.metrics.active_connections}
                        </span>
                        <span className="text-gray-400">/</span>
                        <span className="text-gray-600">
                          {pool.metrics.idle_connections}
                        </span>
                        <span className="text-gray-400">/</span>
                        <span className="text-gray-500 text-xs">
                          {pool.metrics.capacity}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        active / idle / capacity
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                        <div
                          className={`h-2 rounded-full transition-all ${getUtilizationColor(
                            pool.metrics.utilization_percent
                          )}`}
                          style={{ width: `${Math.min(pool.metrics.utilization_percent, 100)}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-600">
                        {pool.metrics.utilization_percent.toFixed(0)}%
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="text-gray-700">
                        {pool.metrics.avg_wait_time_ms.toFixed(1)}ms
                      </div>
                      <div className="text-xs text-gray-500">
                        max: {pool.metrics.max_wait_time_ms.toFixed(0)}ms
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {formatDuration(pool.age_seconds)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleEvictPool(pool.connection_id, pool.database_type)}
                        disabled={evicting === pool.connection_id}
                        className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
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
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-red-900 mb-2">Unhealthy Pools</h4>
              <ul className="space-y-1 text-sm text-red-700">
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
        <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-yellow-900 mb-2">High Utilization Pools</h4>
              <ul className="space-y-1 text-sm text-yellow-700">
                {health.high_utilization_pools.map((pool) => (
                  <li key={`${pool.connection_id}-${pool.database_type}`}>
                    Connection #{pool.connection_id} ({pool.database_type}): {pool.utilization.toFixed(0)}% utilization
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
