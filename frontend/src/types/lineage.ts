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

// ============================================================================
// Lineage Narrative Types (Phase 12.1)
// ============================================================================

export interface TransformationExplanation {
  node_id: string;
  transformation_type: string;
  input_columns: string[];
  output_column: string;
  explanation: string;
  business_meaning?: string | null;
}

export interface LineageNarrative {
  summary: string;
  data_flow_description: string;
  column_explanations: Record<string, string>;
  transformations_explained: TransformationExplanation[];
  business_context: Record<string, string>;
  potential_issues: string[];
  confidence: number;
  generated_at?: string | null;
}

export interface LineageGraphResponse {
  nodes: LineageNode[];
  edges: LineageEdge[];
  sql: string;
  tables_used: string[];
  columns_used: string[];
  output_columns: string[];
  narrative?: LineageNarrative | null;  // Phase 12.1: LLM narrative
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

// ============================================================================
// Impact Advisor Types (Phase 12.2)
// ============================================================================

export type ChangeType =
  | 'rename_column'
  | 'rename_table'
  | 'drop_column'
  | 'drop_table'
  | 'change_type'
  | 'add_constraint'
  | 'remove_constraint';

export interface SQLPatch {
  query_id: number;
  original_sql: string;
  patched_sql: string;
  change_description: string;
  confidence: number;
  requires_review: boolean;
}

export interface MigrationStep {
  step_number: number;
  action: string;
  description: string;
  sql?: string | null;
  reversible: boolean;
  risk_level: string;
}

export interface MigrationPlan {
  change_type: string;
  target_object: string;
  new_value?: string | null;
  steps: MigrationStep[];
  estimated_downtime: string;
  rollback_possible: boolean;
  warnings: string[];
  generated_at?: string | null;
}

export interface RiskExplanation {
  risk_level: string;
  summary: string;
  detailed_explanation: string;
  affected_areas: string[];
  recommendations: string[];
  confidence: number;
}

export interface ImpactAdviceRequest {
  change_type: ChangeType;
  table_name: string;
  column_name?: string | null;
  new_value?: string | null;
  include_patches?: boolean;
}

export interface ImpactAdviceResponse {
  impact: ImpactAnalysisResponse;
  change_type: string;
  new_value?: string | null;
  risk_explanation?: RiskExplanation | null;
  migration_plan?: MigrationPlan | null;
  sql_patches: SQLPatch[];
  generated_at?: string | null;
  llm_used: boolean;
}

// ============================================================================
// Schema Health Analyzer Types (Phase 12.3)
// ============================================================================

export type HealthGrade = 'A' | 'B' | 'C' | 'D' | 'F';

export type IssueSeverity = 'info' | 'warning' | 'error' | 'critical';

export type IssueCategory =
  | 'indexing'
  | 'normalization'
  | 'naming'
  | 'structure'
  | 'performance'
  | 'integrity';

export interface IndexSuggestion {
  table_name: string;
  columns: string[];
  index_type: string;
  reason: string;
  estimated_impact: string;
  create_sql: string;
  query_count_benefiting: number;
}

export interface SchemaIssue {
  category: string;
  severity: string;
  title: string;
  description: string;
  affected_objects: string[];
  recommendation: string;
  fix_sql?: string | null;
}

export interface NormalizationIssue {
  table_name: string;
  issue_type: string;
  description: string;
  affected_columns: string[];
  recommendation: string;
}

export interface TableHealthSummary {
  table_name: string;
  column_count: number;
  has_primary_key: boolean;
  foreign_key_count: number;
  index_count: number;
  issues: SchemaIssue[];
  suggestions: IndexSuggestion[];
}

export interface SchemaHealthReport {
  connection_id: number;
  database_name: string;
  grade: HealthGrade;
  score: number;
  table_count: number;
  total_issues: number;
  critical_issues: number;
  index_suggestions: IndexSuggestion[];
  normalization_issues: NormalizationIssue[];
  anti_patterns: SchemaIssue[];
  table_summaries: TableHealthSummary[];
  summary: string;
  recommendations: string[];
  analyzed_at?: string | null;
  llm_used: boolean;
}

// ============================================================================
// Pattern Intelligence Types (Phase 12.4)
// ============================================================================

export interface BottleneckAnalysis {
  table_name: string;
  bottleneck_score: number;
  root_causes: string[];
  contributing_factors: string[];
  optimization_suggestions: string[];
  estimated_improvement: string;
  sample_slow_queries: string[];
  confidence: number;
}

export interface OptimizationSuggestion {
  category: string;
  title: string;
  description: string;
  affected_tables: string[];
  estimated_impact: string;
  implementation_sql?: string | null;
  priority: number;
}

export interface QueryAntiPattern {
  pattern_type: string;
  severity: string;
  title: string;
  description: string;
  affected_queries: number[];
  sample_sql: string;
  recommendation: string;
  occurrence_count: number;
}

export interface UsageTrend {
  table_name: string;
  period: string;
  data_points: Array<{ date: string; count: number }>;
  trend_direction: string;
  change_percentage: number;
}

export interface TrendAnalysis {
  connection_id: number;
  time_range_days: number;
  table_trends: UsageTrend[];
  busiest_tables: string[];
  emerging_tables: string[];
  declining_tables: string[];
  summary: string;
}

export interface PatternIntelligenceReport {
  connection_id: number;
  bottleneck_analyses: BottleneckAnalysis[];
  optimization_suggestions: OptimizationSuggestion[];
  anti_patterns: QueryAntiPattern[];
  trend_analysis?: TrendAnalysis | null;
  summary: string;
  recommendations: string[];
  analyzed_at?: string | null;
  llm_used: boolean;
}

// ============================================================================
// Conversational Lineage Types (Phase 12.5)
// ============================================================================

export type QuestionType =
  | 'lineage'
  | 'impact'
  | 'pattern'
  | 'schema'
  | 'recommendation'
  | 'general';

export interface LineageQuestionRequest {
  question: string;
  connection_id: number;
  session_id?: string | null;
}

export interface LineageAnswer {
  question: string;
  question_type: QuestionType;
  answer: string;
  supporting_data: Record<string, any>;
  related_tables: string[];
  related_queries: number[];
  confidence: number;
  follow_up_suggestions: string[];
  generated_at?: string | null;
  llm_used: boolean;
}
