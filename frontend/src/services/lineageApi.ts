/**
 * Lineage API Service - Phase 11
 *
 * API client for data lineage endpoints.
 * Follows cacheApi.ts patterns.
 */
import axios from 'axios';
import type {
  LineageGraphResponse,
  ImpactAnalysisResponse,
  LineageStatsResponse,
  TableQueriesResponse,
} from '../types/lineage';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 15000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[Lineage API] Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const lineageAPI = {
  /**
   * Parse SQL and return lineage graph.
   */
  async parseSql(sql: string, connectionId?: number): Promise<LineageGraphResponse> {
    const { data } = await api.post<LineageGraphResponse>('/api/lineage/parse', {
      sql,
      connection_id: connectionId,
    });
    return data;
  },

  /**
   * Get lineage for a query from history.
   */
  async getQueryLineage(queryId: number): Promise<LineageGraphResponse> {
    const { data } = await api.get<LineageGraphResponse>(`/api/lineage/query/${queryId}`);
    return data;
  },

  /**
   * Analyze impact of a schema change.
   */
  async analyzeImpact(tableName: string, columnName?: string): Promise<ImpactAnalysisResponse> {
    const { data } = await api.post<ImpactAnalysisResponse>('/api/lineage/impact', {
      table_name: tableName,
      column_name: columnName,
    });
    return data;
  },

  /**
   * Get queries referencing a table.
   */
  async getTableQueries(tableName: string): Promise<TableQueriesResponse> {
    const { data } = await api.get<TableQueriesResponse>(`/api/lineage/table/${tableName}/queries`);
    return data;
  },

  /**
   * Get lineage statistics.
   */
  async getStats(): Promise<LineageStatsResponse> {
    const { data } = await api.get<LineageStatsResponse>('/api/lineage/stats');
    return data;
  },
};

export default lineageAPI;
