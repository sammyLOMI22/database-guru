// API Types for Database Guru

export interface QueryRequest {
  question: string;
  database_type?: string;
  schema?: string;
  model?: string;
  allow_write?: boolean;
  use_cache?: boolean;
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
