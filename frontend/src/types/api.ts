// API Types for Database Guru

export interface QueryRequest {
  question: string;
  database_type?: string;
  schema?: string;
  model?: string;
  allow_write?: boolean;
  use_cache?: boolean;
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
  start_time: string;
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
}
