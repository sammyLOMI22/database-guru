// Mappings API Service - For managing learned column/table mappings and validation patterns
import axios from 'axios';
import type {
  ColumnMapping,
  TableMapping,
  ResultPattern,
  MappingStats,
  PatternStats,
} from '../types/api';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 10000,
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[Mappings API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(`[Mappings API Error] ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      console.error('[Mappings API Error] No response received:', error.request);
    } else {
      console.error('[Mappings API Error]', error.message);
    }
    return Promise.reject(error);
  }
);

export interface MappingFilters {
  connection_name?: string;
  table_name?: string;
  database_type?: string;
  mapping_type?: string;
  pattern_type?: string;
  action?: string;
  limit?: number;
  offset?: number;
}

export const mappingsAPI = {
  // ============================================================================
  // Column Mappings
  // ============================================================================

  /**
   * Get list of column mappings with optional filtering
   */
  async getColumnMappings(filters?: MappingFilters): Promise<ColumnMapping[]> {
    const { data } = await api.get<ColumnMapping[]>('/api/mappings/columns', {
      params: filters,
    });
    return data;
  },

  /**
   * Get column mapping statistics
   */
  async getColumnMappingStats(filters?: {
    database_type?: string;
    connection_name?: string;
  }): Promise<MappingStats> {
    const { data } = await api.get<MappingStats>('/api/mappings/columns/stats', {
      params: filters,
    });
    return data;
  },

  /**
   * Delete a column mapping
   */
  async deleteColumnMapping(mappingId: number): Promise<void> {
    await api.delete(`/api/mappings/columns/${mappingId}`);
  },

  // ============================================================================
  // Table Mappings
  // ============================================================================

  /**
   * Get list of table mappings with optional filtering
   */
  async getTableMappings(filters?: MappingFilters): Promise<TableMapping[]> {
    const { data } = await api.get<TableMapping[]>('/api/mappings/tables', {
      params: filters,
    });
    return data;
  },

  /**
   * Get table mapping statistics
   */
  async getTableMappingStats(filters?: {
    database_type?: string;
    connection_name?: string;
  }): Promise<MappingStats> {
    const { data } = await api.get<MappingStats>('/api/mappings/tables/stats', {
      params: filters,
    });
    return data;
  },

  /**
   * Delete a table mapping
   */
  async deleteTableMapping(mappingId: number): Promise<void> {
    await api.delete(`/api/mappings/tables/${mappingId}`);
  },

  // ============================================================================
  // Result Validation Patterns
  // ============================================================================

  /**
   * Get list of result validation patterns with optional filtering
   */
  async getResultPatterns(filters?: MappingFilters): Promise<ResultPattern[]> {
    const { data } = await api.get<ResultPattern[]>('/api/mappings/patterns', {
      params: filters,
    });
    return data;
  },

  /**
   * Get result pattern statistics
   */
  async getResultPatternStats(): Promise<PatternStats> {
    const { data } = await api.get<PatternStats>('/api/mappings/patterns/stats');
    return data;
  },

  /**
   * Mark a result validation pattern as helpful
   */
  async markPatternHelpful(patternId: number): Promise<void> {
    await api.post(`/api/mappings/patterns/${patternId}/helpful`);
  },

  /**
   * Delete a result validation pattern
   */
  async deleteResultPattern(patternId: number): Promise<void> {
    await api.delete(`/api/mappings/patterns/${patternId}`);
  },
};
