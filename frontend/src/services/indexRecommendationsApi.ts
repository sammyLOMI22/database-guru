/**
 * Index Recommendations API Service
 *
 * Client-side service for interacting with index recommendation endpoints.
 * Provides methods for listing, analyzing, updating, and managing index recommendations.
 *
 * Part of Phase 4: Database Index Recommendations
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// ============================================================================
// Types
// ============================================================================

export interface IndexRecommendation {
  id: number;
  connection_id: number;
  database_name: string;
  database_type: string;
  query_id?: number;
  slow_query_sql: string;
  execution_time_ms: number;
  query_frequency: number;
  table_name: string;
  column_names: string[];
  index_type: string;
  index_name: string;
  estimated_improvement_pct?: number;
  estimated_rows_scanned?: number;
  current_cost?: number;
  projected_cost?: number;
  similar_indexes_exist: boolean;
  conflicting_indexes?: string[];
  confidence_score: number;
  priority: string;
  reason: string;
  status: string;
  applied_at?: string;
  applied_by?: string;
  create_index_sql: string;
  drop_index_sql?: string;
  analysis_method: string;
  validated: boolean;
  validation_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface IndexRecommendationStats {
  total_recommendations: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_database_type: Record<string, number>;
  avg_execution_time_ms: number;
  avg_improvement_pct?: number;
  total_applied: number;
  total_pending: number;
}

export interface ListRecommendationsParams {
  connection_id?: number;
  status?: string;
  priority?: string;
  database_type?: string;
  table_name?: string;
  limit?: number;
  offset?: number;
}

export interface AnalyzeQueryRequest {
  connection_id: number;
  query_sql: string;
  execution_time_ms?: number;
  auto_save?: boolean;
}

export interface UpdateRecommendationRequest {
  status?: string;
  applied_by?: string;
  validated?: boolean;
  validation_notes?: string;
  priority?: string;
}

// ============================================================================
// API Methods
// ============================================================================

export const indexRecommendationsApi = {
  /**
   * List index recommendations with optional filters
   */
  async listRecommendations(
    params?: ListRecommendationsParams
  ): Promise<IndexRecommendation[]> {
    const response = await axios.get<IndexRecommendation[]>(
      `${API_BASE_URL}/index-recommendations/`,
      { params }
    );
    return response.data;
  },

  /**
   * Get a single recommendation by ID
   */
  async getRecommendation(id: number): Promise<IndexRecommendation> {
    const response = await axios.get<IndexRecommendation>(
      `${API_BASE_URL}/index-recommendations/${id}`
    );
    return response.data;
  },

  /**
   * Get recommendation statistics
   */
  async getStats(connectionId?: number): Promise<IndexRecommendationStats> {
    const response = await axios.get<IndexRecommendationStats>(
      `${API_BASE_URL}/index-recommendations/stats`,
      {
        params: connectionId ? { connection_id: connectionId } : {}
      }
    );
    return response.data;
  },

  /**
   * Analyze a slow query and generate recommendation
   */
  async analyzeQuery(request: AnalyzeQueryRequest): Promise<IndexRecommendation> {
    const response = await axios.post<IndexRecommendation>(
      `${API_BASE_URL}/index-recommendations/analyze`,
      request
    );
    return response.data;
  },

  /**
   * Update recommendation status and metadata
   */
  async updateRecommendation(
    id: number,
    update: UpdateRecommendationRequest
  ): Promise<IndexRecommendation> {
    const response = await axios.put<IndexRecommendation>(
      `${API_BASE_URL}/index-recommendations/${id}`,
      update
    );
    return response.data;
  },

  /**
   * Delete a recommendation
   */
  async deleteRecommendation(id: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/index-recommendations/${id}`);
  },

  /**
   * Bulk update multiple recommendations
   */
  async bulkUpdate(
    recommendation_ids: number[],
    status: string
  ): Promise<{ updated: number; requested: number }> {
    const response = await axios.post(
      `${API_BASE_URL}/index-recommendations/bulk-update`,
      { recommendation_ids, status }
    );
    return response.data;
  },

  /**
   * Delete all recommendations for a connection
   */
  async deleteConnectionRecommendations(connectionId: number): Promise<void> {
    await axios.delete(
      `${API_BASE_URL}/index-recommendations/connection/${connectionId}`
    );
  },
};

export default indexRecommendationsApi;
