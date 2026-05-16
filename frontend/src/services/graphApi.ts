/**
 * Graph Mode API service — Phase 25.2 (Neo4j).
 *
 * Endpoints in scope:
 *   GET  /api/graph/connections/:id/schema           — cached or fresh schema
 *   POST /api/graph/connections/:id/introspect       — force-refresh
 *   POST /api/graph/connections/:id/ai/schema-summary — 2-3 sentence blurb
 *
 * 25.3+ adds query / explore / generate-cypher routes — they should land
 * in this file too so the frontend never sees more than one HTTP boundary
 * for graph features.
 */
import axios from 'axios';
import { getStoredToken } from '../hooks/useAuth';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 60_000,
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.data) {
      console.error('[Graph API] Error:', error.response.data);
    }
    return Promise.reject(error);
  },
);

// ── Types ────────────────────────────────────────────────────────────────

export interface GraphProperty {
  name: string;
  types: string[];
  indexed: boolean;
  nullable: boolean | null;
  sample_values: unknown[] | null;
}

export interface GraphNodeLabel {
  name: string;
  estimated_count: number | null;
  properties: GraphProperty[];
}

export interface GraphRelationshipType {
  name: string;
  estimated_count: number | null;
  properties: GraphProperty[];
}

export interface GraphRelationshipPattern {
  source_labels: string[];
  relationship_type: string;
  target_labels: string[];
  estimated_count: number | null;
}

export interface GraphIndex {
  name: string;
  entity_type: 'NODE' | 'RELATIONSHIP';
  labels_or_types: string[];
  properties: string[];
  type: string | null;
  state: string | null;
}

export interface GraphConstraint {
  name: string;
  entity_type: 'NODE' | 'RELATIONSHIP';
  labels_or_types: string[];
  properties: string[];
  type: string;
}

export interface GraphSchemaResponse {
  connection_id: number;
  provider: string;
  database_name: string;
  labels: GraphNodeLabel[];
  relationships: GraphRelationshipType[];
  patterns: GraphRelationshipPattern[];
  indexes: GraphIndex[];
  constraints: GraphConstraint[];
  warnings: string[];
  collected_at: string | null;
  schema_updated_at: string | null;
  server_version: string | null;
  edition: string | null;
  label_count: number;
  relationship_type_count: number;
  pattern_count: number;
  index_count: number;
  constraint_count: number;
  cached: boolean;
}

export interface GraphSchemaSummaryResponse {
  connection_id: number;
  summary: string;
  model: string | null;
  provider: string | null;
  used_fallback: boolean;
}

export interface GraphIntrospectOptions {
  overallTimeoutMs?: number;
  queryTimeoutMs?: number;
}

// ── API ──────────────────────────────────────────────────────────────────

export const graphAPI = {
  async getSchema(
    connectionId: number,
    options?: { refresh?: boolean },
  ): Promise<GraphSchemaResponse> {
    const params: Record<string, string> = {};
    if (options?.refresh) params.refresh = 'true';
    const { data } = await api.get<GraphSchemaResponse>(
      `/api/graph/connections/${connectionId}/schema`,
      { params },
    );
    return data;
  },

  async introspect(
    connectionId: number,
    options?: GraphIntrospectOptions,
  ): Promise<GraphSchemaResponse> {
    const payload: Record<string, number> = {};
    if (options?.overallTimeoutMs)
      payload.overall_timeout_ms = options.overallTimeoutMs;
    if (options?.queryTimeoutMs)
      payload.query_timeout_ms = options.queryTimeoutMs;
    const { data } = await api.post<GraphSchemaResponse>(
      `/api/graph/connections/${connectionId}/introspect`,
      payload,
    );
    return data;
  },

  async generateSchemaSummary(
    connectionId: number,
  ): Promise<GraphSchemaSummaryResponse> {
    const { data } = await api.post<GraphSchemaSummaryResponse>(
      `/api/graph/connections/${connectionId}/ai/schema-summary`,
    );
    return data;
  },
};
