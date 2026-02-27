// Phase 22: Performance Guru Types

export interface PlanNode {
  node_type: string;
  relation?: string | null;
  cost_startup?: number | null;
  cost_total?: number | null;
  rows_estimated?: number | null;
  rows_actual?: number | null;
  loops?: number | null;
  actual_time_ms?: number | null;
  filter?: string | null;
  index_name?: string | null;
  join_type?: string | null;
  disk_spill: boolean;
  children: PlanNode[];
  raw_text: string;
  depth: number;
}

export interface ExecutionPlan {
  dialect: string;
  sql: string;
  analyzed: boolean;
  root_node?: PlanNode | null;
  all_nodes: PlanNode[];
  total_cost?: number | null;
  total_actual_time_ms?: number | null;
  has_seq_scans: boolean;
  has_disk_spill: boolean;
  has_hash_batches: boolean;
  node_count: number;
  seq_scan_tables: string[];
  missing_index_hints: string[];
  raw_plan: string[];
  parsed_at?: string | null;
  warnings: string[];
}

export interface Bottleneck {
  node_type: string;
  table_or_index: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  impact_estimate: string;
}

export interface IndexSuggestion {
  table: string;
  columns: string[];
  reason: string;
  create_sql: string;
  estimated_speedup: string;
}

export interface QueryRewrite {
  original_pattern: string;
  rewritten_sql: string;
  reason: string;
  expected_improvement: string;
}

export interface PerformanceInsights {
  summary: string;
  overall_severity: 'good' | 'warning' | 'critical';
  bottlenecks: Bottleneck[];
  index_suggestions: IndexSuggestion[];
  query_rewrites: QueryRewrite[];
  before_after_estimate?: string | null;
  general_recommendations: string[];
  confidence: number;
  llm_used: boolean;
  generated_at?: string | null;
}

export interface PerformanceAnalysisRequest {
  sql: string;
  connection_id: number;
  run_analyze?: boolean;
  include_schema_context?: boolean;
  model?: string | null;
}

export interface PerformanceAnalysisResponse {
  plan: ExecutionPlan;
  insights: PerformanceInsights;
  connection_id: number;
  sql: string;
  analyzed: boolean;
  dialect: string;
}

export interface ExplainOnlyResponse {
  plan: ExecutionPlan;
  dialect: string;
  analyzed: boolean;
  warnings: string[];
}
