/**
 * Connection Pools API Service
 *
 * Provides API methods for monitoring and managing database connection pools.
 * Part of Phase 4.1: Connection Pooling Optimization
 */
import axios from 'axios';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 10000,
});

// Request logging
api.interceptors.request.use((config) => {
  console.log(`[Pools API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[Pools API] Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Type definitions matching backend response models

export interface PoolMetrics {
  active_connections: number;
  idle_connections: number;
  total_connections: number;
  utilization_percent: number;
  total_checkouts: number;
  total_checkins: number;
  failed_checkouts: number;
  avg_wait_time_ms: number;
  max_wait_time_ms: number;
  health_status: 'healthy' | 'degraded' | 'unhealthy';
  pool_size: number;
  max_overflow: number;
  capacity: number;
}

export interface PoolInfo {
  connection_id: number;
  database_type: string;
  connection_name: string;
  created_at: string;
  last_used: string;
  age_seconds: number;
  metrics: PoolMetrics;
}

export interface GlobalMetrics {
  total_active_connections: number;
  total_idle_connections: number;
  avg_utilization_percent: number;
}

export interface PoolStatsResponse {
  total_pools: number;
  global_metrics: GlobalMetrics;
  pools: PoolInfo[];
  pooling_enabled: boolean;
}

export interface ConnectionPoolStatsResponse {
  connection_id: number;
  pools: PoolInfo[];
  total_pools: number;
}

export interface PoolEvictionResponse {
  success: boolean;
  message: string;
  pools_evicted: number;
}

export interface UnhealthyPool {
  connection_id: number;
  database_type: string;
  failed_checkouts: number;
}

export interface HighUtilizationPool {
  connection_id: number;
  database_type: string;
  utilization: number;
}

export interface PoolHealthResponse {
  pooling_enabled: boolean;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'disabled';
  total_pools?: number;
  warnings?: string[];
  unhealthy_pools?: UnhealthyPool[];
  high_utilization_pools?: HighUtilizationPool[];
  global_metrics?: GlobalMetrics;
  message?: string;
}

export const poolsAPI = {
  /**
   * Get overall connection pool statistics
   */
  async getPoolStats(): Promise<PoolStatsResponse> {
    const { data } = await api.get<PoolStatsResponse>('/api/pools/stats');
    return data;
  },

  /**
   * Get statistics for a specific database connection's pools
   */
  async getConnectionPoolStats(connectionId: number): Promise<ConnectionPoolStatsResponse> {
    const { data } = await api.get<ConnectionPoolStatsResponse>(
      `/api/pools/stats/${connectionId}`
    );
    return data;
  },

  /**
   * Manually evict pool(s) for a database connection
   *
   * @param connectionId - Database connection ID
   * @param databaseType - Optional database type filter (postgresql, mysql, sqlite, duckdb)
   */
  async evictConnectionPools(
    connectionId: number,
    databaseType?: string
  ): Promise<PoolEvictionResponse> {
    const { data } = await api.delete<PoolEvictionResponse>(
      `/api/pools/${connectionId}`,
      {
        params: databaseType ? { database_type: databaseType } : undefined,
      }
    );
    return data;
  },

  /**
   * Get connection pool health status
   */
  async getPoolHealth(): Promise<PoolHealthResponse> {
    const { data } = await api.get<PoolHealthResponse>('/api/pools/health');
    return data;
  },
};

export default poolsAPI;
