/**
 * Data Lineage Types - Phase 11
 *
 * TypeScript interfaces matching backend lineage schemas.
 */

export type LineageNodeType = 'source_table' | 'source_column' | 'transformation' | 'output_column';
export type TransformationType = 'direct' | 'aggregation' | 'expression' | 'function';

export interface LineageNode {
  id: string;
  node_type: LineageNodeType;
  label: string;
  table_name?: string | null;
  column_name?: string | null;
  expression?: string | null;
  transformation_type?: TransformationType | null;
}

export interface LineageEdge {
  source_id: string;
  target_id: string;
  edge_type: string;
  label?: string | null;
}

export interface LineageGraphResponse {
  nodes: LineageNode[];
  edges: LineageEdge[];
  sql: string;
  tables_used: string[];
  columns_used: string[];
  output_columns: string[];
}

export interface ImpactedQuery {
  query_id: number;
  natural_language_query: string;
  generated_sql: string;
  impact_type: string;
  risk_level: string;
}

export interface ImpactAnalysisResponse {
  changed_object: string;
  object_type: string;
  impacted_queries: ImpactedQuery[];
  total_affected: number;
  risk_level: string;
  risk_counts: {
    low: number;
    medium: number;
    high: number;
  };
  summary: string;
}

export interface LineageStatsResponse {
  total_queries: number;
  unique_tables_referenced: number;
  tables: string[];
}

export interface TableQueriesResponse {
  table_name: string;
  queries: ImpactedQuery[];
  total: number;
}

// ============================================================================
// Query Pattern Analytics Types (Phase 11.5)
// ============================================================================

export interface TableUsageEntry {
  table_name: string;
  query_count: number;
  join_count: number;
  avg_execution_time_ms?: number | null;
  last_used_at?: string | null;
}

export interface JoinPattern {
  table_a: string;
  table_b: string;
  join_count: number;
  sample_sql: string;
  avg_execution_time_ms?: number | null;
}

export interface PerformanceBottleneck {
  table_name: string;
  query_count: number;
  avg_execution_time_ms: number;
  max_execution_time_ms: number;
  bottleneck_score: number;
}

export interface HeatmapDataResponse {
  table_usage: TableUsageEntry[];
  join_patterns: JoinPattern[];
  bottlenecks: PerformanceBottleneck[];
  time_range_days?: number | null;
  total_queries_analyzed: number;
  connection_id?: number | null;
}
