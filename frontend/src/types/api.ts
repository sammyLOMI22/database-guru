// API Types for Database Guru

import { ChartType } from '../utils/chartUtils';

export interface QueryRequest {
  question: string;
  database_type?: string;
  schema?: string;
  model?: string;
  allow_write?: boolean;
  use_cache?: boolean;
  session_id?: string;
  force_schema_refresh?: boolean;
  enable_narratives?: boolean;
  /** User-requested chart type from natural language parsing */
  preferred_chart_type?: ChartType | null;
}

// Option 2: Observability Types
export interface AgentTraceStep {
  timestamp: string;
  elapsed_ms: number;
  type: string;
  message: string;
  metadata: Record<string, any>;
  icon: string;
}

export interface AgentTrace {
  steps: AgentTraceStep[];
  total_elapsed_ms: number;
  total_duration_ms?: number;  // Alternative name used by some traces
  start_time?: string;
  from_cache?: boolean;  // For cache hit traces
}

export interface ConfidencePrediction {
  overall: number;
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW';
  factors: {
    error_type: number;
    schema_match: number;
    historical_success: number;
    correction_complexity: number;
    similarity: number;
  };
  reasoning: string;
  recommendation: string;
}

// Parallel Execution Metrics (Phase: Parallel Multi-Database Execution)
export interface ParallelExecutionMetrics {
  total_queries: number;
  max_concurrent: number;
  actual_concurrent: number;
  successful_queries: number;
  failed_queries: number;
  elapsed_ms: number;
  average_query_time_ms: number;
  estimated_sequential_ms?: number;
  speedup?: number;  // e.g., 3.0x faster
}

export interface ParallelCorrectionMetrics {
  strategies_attempted: number;
  strategies_succeeded: number;
  strategies_failed: number;
  strategies_timed_out: number;
  winning_strategy: string | null;  // "quick_fix" | "learned" | "llm" | "tool_using" | "llm_fallback_timeout"
  elapsed_ms: number;
  timed_out: boolean;
}

export interface CorrectionAttempt {
  attempt_number: number;
  sql: string;
  success: boolean;
  error?: string | null;
  error_type?: string | null;
  execution_time_ms?: number | null;
  row_count?: number | null;
  fix_method?: string | null;
  confidence_prediction?: ConfidencePrediction | null;
  metrics?: ParallelCorrectionMetrics | null;  // NEW: Parallel correction metrics
}

export interface QueryPlan {
  complexity: string;
  intent: string;
  confidence: number;
  reasoning?: string;
  tables?: Array<{
    name: string;
    alias?: string;
    purpose?: string;
  }>;
  joins?: Array<{
    from: string;
    to: string;
    type: string;
    on: string;
    purpose?: string;
  }>;
  filters?: Array<{
    column: string;
    operator: string;
    value: string;
    purpose?: string;
  }>;
  aggregations?: Array<{
    function: string;
    column: string;
    alias?: string;
    purpose?: string;
  }>;
  grouping?: {
    columns: string[];
    purpose?: string;
  } | null;
  ordering?: {
    column: string;
    direction: string;
    purpose?: string;
  } | null;
  limit?: number | null;
  joins_count: number;
  filters_count: number;
  aggregations_count: number;
}

// Conversational Memory Types
export interface ConversationMessage {
  question: string;
  sql: string;
  success: boolean;
  timestamp?: string;
}

export interface ConversationContext {
  has_context: boolean;
  window_size: number;
  messages: ConversationMessage[];
}

export interface ConversationContextResponse {
  session_id: string;
  context: ConversationContext;
  window_size: number;
}

// Intelligent Data Narratives Types
export interface ResultAnalysis {
  summary: string;
  key_insights: string[];
  direct_answer: string | null;
  confidence: number;
  statistics: Record<string, any>;
  generated_at: string;
}

export interface QueryResponse {
  query_id: number;
  question: string;
  sql: string;
  is_valid: boolean;
  is_read_only: boolean;
  warnings: string[];
  results: Record<string, any>[] | null;
  row_count: number | null;
  execution_time_ms: number | null;
  cached: boolean;
  timestamp: string;
  // Option 2: Observability fields
  agent_trace?: AgentTrace | null;
  query_plan?: QueryPlan | null;
  attempts?: CorrectionAttempt[] | null;
  self_corrected?: boolean;
  total_attempts?: number;
  verification_warnings?: string[];
  used_planning?: boolean;
  // Conversational Memory fields
  conversation_context?: ConversationContext | null;
  used_context?: boolean;
  // Parallel Execution Metrics
  parallelExecutionMetrics?: ParallelExecutionMetrics | null;
  parallelCorrectionMetrics?: ParallelCorrectionMetrics | null;
  // Cache Information
  cache_type?: 'exact' | 'semantic' | null;
  semantic_similarity?: number | null;
  matched_question?: string | null;
  // Intelligent Data Narratives fields
  result_analysis?: ResultAnalysis | null;
  // Chart Intent fields (Phase 8: Chart Intelligence)
  preferred_chart_type?: ChartType | null;
}

export interface Model {
  name: string;
  size?: string;
  modified?: string;
  available: boolean;
}

export interface ModelListResponse {
  models: string[];
  default_model: string;
  count: number;
}

export interface SchemaTable {
  columns: Array<{
    name: string;
    type: string;
    nullable: boolean;
    default: string | null;
    max_length: number | null;
  }>;
  primary_keys: string[];
  foreign_keys: Array<{
    column: string;
    referred_table: string;
    referred_column: string;
    constraint_name: string;
  }>;
  indexes: Array<{
    name: string;
    definition: string;
  }>;
}

export interface SchemaResponse {
  schema: {
    tables: Record<string, SchemaTable>;
    relationships: Array<{
      from_table: string;
      from_column: string;
      to_table: string;
      to_column: string;
    }>;
    summary: {
      table_count: number;
      total_columns: number;
    };
  };
  cached: boolean;
  table_count: number;
  column_count: number;
  relationship_count: number;
}

export interface QueryHistoryItem {
  id: number;
  natural_language_query: string;
  generated_sql: string;
  sql_validated: boolean;
  executed: boolean;
  execution_time_ms: number | null;
  result_count: number | null;
  error_message: string | null;
  database_type: string | null;
  model_used: string | null;
  created_at: string;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  services: {
    database: boolean;
    cache: boolean;
    llm: boolean;
  };
  timestamp: string;
}

// Database Connection Types
export interface DatabaseConnection {
  id: number;
  name: string;
  database_type: string;
  host?: string;
  port?: number;
  database_name: string;
  is_active: boolean;
  last_tested_at?: string;
  created_at: string;
}

export interface ConnectionListResponse {
  connections: DatabaseConnection[];
  count: number;
}

// Chat Session Types
export interface ConnectionInfo {
  id: number;
  name: string;
  database_type: string;
  database_name: string;
}

export interface ChatSession {
  id: string;
  name: string;
  user_id?: string;
  active_connection_ids: number[];
  connections: ConnectionInfo[];
  created_at: string;
  updated_at: string;
  last_active_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: number;
  chat_session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  query_history_id?: number;
  databases_used?: Array<{
    conn_id: number;
    name: string;
    rows: number;
  }>;
  created_at: string;
}

export interface CreateChatSessionRequest {
  name: string;
  connection_ids: number[];
  user_id?: string;
}

export interface UpdateChatSessionRequest {
  name?: string;
  connection_ids?: number[];
}

// Multi-Database Query Types
export interface MultiDatabaseQueryRequest {
  question: string;
  chat_session_id?: string;
  connection_ids?: number[];
  allow_write?: boolean;
  use_cache?: boolean;
  model?: string;
  force_schema_refresh?: boolean;
  enable_narratives?: boolean;
  /** User-requested chart type from natural language parsing */
  preferred_chart_type?: ChartType | null;
}

export interface DatabaseQueryResult {
  connection_id: number;
  connection_name: string;
  database_type: string;
  sql: string;
  success: boolean;
  results?: Record<string, any>[];
  row_count?: number;
  execution_time_ms?: number;
  error?: string;
  query_id?: number; // For user feedback integration
  // Option 2: Observability fields
  agent_trace?: AgentTrace | null;
  query_plan?: QueryPlan | null;
  attempts?: CorrectionAttempt[] | null;
  self_corrected?: boolean;
  total_attempts?: number;
  verification_warnings?: string[];
  used_planning?: boolean;
  // Parallel Execution Metrics
  _parallel_execution_metrics?: ParallelExecutionMetrics | null;
  // Intelligent Data Narratives fields
  result_analysis?: ResultAnalysis | null;
}

// Cache Info for Multi-Database Queries (Phase 3.2: Semantic Caching)
export interface CacheInfo {
  semantic_hits: number;
  semantic_misses: number;
  results_stored: number;
  results_skipped: number;
  hit_databases: string[];
  miss_databases: string[];
}

export interface MultiDatabaseQueryResponse {
  query_id: number;
  question: string;
  database_results: DatabaseQueryResult[];
  total_databases_queried: number;
  total_rows: number;
  total_execution_time_ms: number;
  warnings: string[];
  cached: boolean;
  timestamp: string;
  cache_info?: CacheInfo | null;  // Cache operation summary
  // Intelligent Data Narratives fields
  combined_analysis?: ResultAnalysis | null;
  // Chart Intent fields (Phase 8: Chart Intelligence)
  preferred_chart_type?: ChartType | null;
}

// Mapping Management Types (Phase 2: Non-SQL Feedback)
export interface ColumnMapping {
  id: number;
  source_column: string;
  target_column: string;
  table_name: string | null;
  connection_name: string | null;
  database_type: string;
  description: string | null;
  confidence_score: number;
  times_applied: number;
  success_rate: number;
  created_by: string;
  created_at: string;
  last_applied_at: string | null;
}

export interface TableMapping {
  id: number;
  source_table: string;
  target_table: string;
  connection_name: string | null;
  database_type: string;
  mapping_type: string;
  description: string | null;
  confidence_score: number;
  times_applied: number;
  success_rate: number;
  created_by: string;
  created_at: string;
  last_applied_at: string | null;
}

export interface ResultPattern {
  id: number;
  pattern_type: string;
  pattern_description: string;
  matching_criteria: Record<string, any>;
  action: string;
  suggestion: string | null;
  times_triggered: number;
  times_helpful: number;
  confidence_score: number;
  created_at: string;
  last_triggered_at: string | null;
}

export interface MappingStats {
  total_mappings: number;
  total_applications: number;
  average_success_rate: number;
  most_used: Array<{
    source: string;
    target: string;
    table?: string;
    connection?: string;
    type?: string;
    times_applied: number;
  }>;
  by_database_type: Record<string, number>;
  by_connection: Record<string, number>;
}

export interface PatternStats {
  total_patterns: number;
  total_triggers: number;
  total_helpful: number;
  helpfulness_rate: number;
  by_type: Record<string, number>;
  by_action: Record<string, number>;
}

// Tool-Using Agent Types (Phase 3.1)
export type ToolCategory = 'schema' | 'data' | 'query' | 'validation';

export interface ToolParameter {
  type: string;
  description: string;
  default?: any;
}

export interface ToolResponse {
  name: string;
  description: string;
  category: ToolCategory;
  parameters: Record<string, ToolParameter>;
  required_params: string[];
  cacheable: boolean;
  cache_ttl: number;
}

export interface ToolStatsResponse {
  tool_name: string;
  times_executed: number;
  successes: number;
  failures: number;
  success_rate: number;
  avg_time_ms: number;
  cache_hit_rate: number;
  last_executed: string | null;
}

export interface AllToolStatsResponse {
  total_tools: number;
  total_executions: number;
  overall_success_rate: number;
  by_tool: Record<string, ToolStatsResponse>;
}

export interface ToolsPromptResponse {
  prompt: string;
  tool_count: number;
}
