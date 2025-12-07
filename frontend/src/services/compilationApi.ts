// Compilation API Service Layer
// Handles all API calls for query compilation monitoring and cache management
import axios from 'axios';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 10000,
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[Compilation API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(`[Compilation API Error] ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      console.error('[Compilation API Error] No response received:', error.request);
    } else {
      console.error('[Compilation API Error]', error.message);
    }
    return Promise.reject(error);
  }
);

export interface CompilationStats {
  success: boolean;
  plan_cache: {
    total_plans: number;
    cached_plans: number;
    total_lookups: number;
    hits: number;
    misses: number;
    hit_rate_percent: number;
    avg_lookup_ms: number;
  };
  statement_manager: {
    total_statements: number;
    prepared_statements: number;
    total_executions: number;
    avg_executions_per_statement: number;
    total_execution_ms: number;
    avg_execution_ms: number;
  };
  databases: {
    [key: string]: {
      connection_id: number;
      total_queries: number;
      prepared_statements: number;
      cached_plans: number;
      total_executions: number;
      total_execution_ms: number;
      avg_execution_ms: number;
    };
  };
  timestamp: string;
  error?: string;
}

export interface CompiledMetric {
  id: number;
  normalized_hash: string;
  template_sql: string;
  is_prepared: boolean;
  is_plan_cached: boolean;
  total_executions: number;
  total_execution_ms: number;
  avg_execution_ms: number;
  plan_cache_hits: number;
  plan_cache_misses: number;
  prepared_statement_hits: number;
  last_executed_at: string;
}

export interface ConnectionMetricsResponse {
  success: boolean;
  connection: {
    id: number;
    name: string;
    database_type: string;
  };
  metrics: CompiledMetric[];
  summary: {
    total_compiled_queries: number;
    prepared_statements: number;
    cached_plans: number;
    total_executions: number;
    total_execution_ms: number;
    avg_execution_ms: number;
  };
  pagination: {
    limit: number;
    offset: number;
    has_more: boolean;
  };
  error?: string;
}

export interface InvalidationLogEntry {
  id: number;
  connection_id: number;
  table_name: string | null;
  invalidation_reason: string;
  plans_invalidated: number;
  statements_invalidated: number;
  invalidated_at: string;
}

export interface InvalidationLogResponse {
  success: boolean;
  entries: InvalidationLogEntry[];
  pagination: {
    limit: number;
    offset: number;
    has_more: boolean;
  };
  error?: string;
}

export interface InvalidateResponse {
  success: boolean;
  connection_id: number;
  table_name?: string;
  plans_invalidated: number;
  statements_invalidated: number;
  log_id: number;
  error?: string;
}

export const compilationAPI = {
  // Get global compilation statistics
  async getStats(): Promise<CompilationStats> {
    const { data } = await api.get<CompilationStats>('/api/compilation/stats');
    return data;
  },

  // Get per-connection compilation metrics
  async getConnectionMetrics(
    connectionId: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<ConnectionMetricsResponse> {
    const { data } = await api.get<ConnectionMetricsResponse>(
      `/api/compilation/metrics/${connectionId}`,
      { params: { limit, offset } }
    );
    return data;
  },

  // Invalidate all caches for a connection
  async invalidateConnectionCache(connectionId: number): Promise<InvalidateResponse> {
    const { data } = await api.delete<InvalidateResponse>(
      `/api/compilation/cache/connection/${connectionId}`
    );
    return data;
  },

  // Invalidate cache for a specific table
  async invalidateTableCache(
    connectionId: number,
    tableName: string
  ): Promise<InvalidateResponse> {
    const { data } = await api.delete<InvalidateResponse>(
      `/api/compilation/cache/table/${connectionId}/${tableName}`
    );
    return data;
  },

  // Get invalidation log entries
  async getInvalidationLog(
    connectionId?: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<InvalidationLogResponse> {
    const params: any = { limit, offset };
    if (connectionId !== undefined) {
      params.connection_id = connectionId;
    }

    const { data } = await api.get<InvalidationLogResponse>(
      '/api/compilation/invalidation-log',
      { params }
    );
    return data;
  },
};

export default compilationAPI;
