/**
 * Cache API Service
 *
 * Provides API methods for interacting with the Semantic Caching system.
 * Part of Phase 3.3: Semantic Caching UI Components
 */
import axios from 'axios';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 10000,
});

// Request logging
api.interceptors.request.use((config) => {
  console.log(`[Cache API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[Cache API] Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============================================================================
// Types
// ============================================================================

export interface SemanticCacheStats {
  total_lookups: number;
  total_hits: number;
  exact_hits: number;
  semantic_hits: number;
  misses: number;
  hit_rate_percent: number;
  semantic_hit_rate_percent: number;
  total_stores: number;
  similarity_threshold: number;
  ttl_seconds: number;
  memory_entries: number;
}

export interface LLMCacheStats {
  total_lookups: number;
  hits: number;
  misses: number;
  hit_rate_percent: number;
  total_stores: number;
  similarity_threshold: number;
  ttl_seconds: number;
}

export interface EmbeddingServiceStats {
  total_requests: number;
  cache_hits: number;
  cache_hit_rate_percent: number;
  ollama_calls: number;
  tfidf_fallbacks: number;
  ollama_available: boolean;
}

export interface CacheStatsResponse {
  semantic_cache: SemanticCacheStats;
  llm_cache: LLMCacheStats;
  embedding_service: EmbeddingServiceStats;
  redis_connected: boolean;
}

export interface CachedQueryResponse {
  question: string;
  sql: string;
  connection_id: number;
  database_type: string;
  created_at: string;
  hits: number;
  last_hit_at: string | null;
}

export interface RecentQueriesResponse {
  queries: CachedQueryResponse[];
  total: number;
}

export interface ClearCacheResponse {
  message: string;
  entries_cleared: number;
}

export interface RecentQueriesFilters {
  limit?: number;
  connection_id?: number;
  database_type?: string;
}

// ============================================================================
// API Methods
// ============================================================================

export const cacheAPI = {
  /**
   * Get statistics for all cache layers
   */
  async getStats(): Promise<CacheStatsResponse> {
    const { data } = await api.get<CacheStatsResponse>('/api/cache/stats');
    return data;
  },

  /**
   * Get recent cached queries from semantic cache
   */
  async getRecentQueries(filters?: RecentQueriesFilters): Promise<RecentQueriesResponse> {
    const { data } = await api.get<RecentQueriesResponse>('/api/cache/semantic/recent', {
      params: filters,
    });
    return data;
  },

  /**
   * Clear semantic cache
   */
  async clearSemanticCache(): Promise<ClearCacheResponse> {
    const { data } = await api.delete<ClearCacheResponse>('/api/cache/semantic');
    return data;
  },

  /**
   * Clear LLM cache
   */
  async clearLLMCache(): Promise<ClearCacheResponse> {
    const { data } = await api.delete<ClearCacheResponse>('/api/cache/llm');
    return data;
  },

  /**
   * Clear all caches (semantic + LLM)
   */
  async clearAllCaches(): Promise<ClearCacheResponse> {
    const { data } = await api.delete<ClearCacheResponse>('/api/cache/all');
    return data;
  },

  /**
   * Clear cache for a specific connection
   */
  async clearConnectionCache(connectionId: number): Promise<ClearCacheResponse> {
    const { data } = await api.delete<ClearCacheResponse>(
      `/api/cache/semantic/connection/${connectionId}`
    );
    return data;
  },
};

export default cacheAPI;
