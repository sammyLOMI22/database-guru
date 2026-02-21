// Phase 20: Migration Toolkit Types

export interface ColumnDiff {
  table_name: string;
  column_name: string;
  diff_type: 'added' | 'removed' | 'type_changed' | 'nullability_changed' | 'default_changed';
  source_state: Record<string, any> | null;
  target_state: Record<string, any> | null;
  is_breaking: boolean;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

export interface ConstraintDiff {
  table_name: string;
  constraint_type: 'primary_key' | 'foreign_key' | 'index';
  diff_type: 'added' | 'removed' | 'modified';
  source_state: any;
  target_state: any;
  risk_level: string;
}

export interface TableDiff {
  table_name: string;
  diff_type: 'added' | 'removed' | 'modified';
  column_diffs: ColumnDiff[];
  constraint_diffs: ConstraintDiff[];
  risk_level: string;
}

export interface SchemaDiffResponse {
  source_connection_id: number | null;
  target_connection_id: number | null;
  source_fingerprint: string;
  target_fingerprint: string;
  table_diffs: TableDiff[];
  total_breaking_changes: number;
  total_safe_changes: number;
  overall_risk: string;
  diff_summary: string;
  compared_at: string;
  project_id: number | null;
}

export interface MigrationProjectSummary {
  id: number;
  name: string;
  source_connection_id: number | null;
  target_connection_id: number | null;
  source_connection_name: string | null;
  target_connection_name: string | null;
  overall_risk: string | null;
  status: string;
  target_dialect: string | null;
  created_at: string;
  updated_at: string;
}

export interface MigrationProjectDetail extends MigrationProjectSummary {
  diff_snapshot: Record<string, any> | null;
  migration_plan: Record<string, any> | null;
  data_migration_plan: Record<string, any> | null;
  up_sql: string | null;
  down_sql: string | null;
  verify_sql: string | null;
  notes: string | null;
}

export interface MigrationStep {
  step_number: number;
  action: string;
  description: string;
  sql_hint: string | null;
  table_name: string | null;
  lock_type: string;
  estimated_duration: string;
  risk_level: string;
  is_reversible: boolean;
  depends_on: number[];
  warnings: string[];
}

export interface MigrationPlanResponse {
  project_id: number;
  steps: MigrationStep[];
  execution_order: string[];
  total_estimated_downtime: string;
  recommended_maintenance_window: boolean;
  pre_migration_checklist: string[];
  post_migration_checklist: string[];
  rollback_strategy: string;
  overall_complexity: string;
  llm_used: boolean;
  generated_at: string;
}

export interface GeneratedScriptsResponse {
  project_id: number;
  target_dialect: string;
  up_sql: string;
  down_sql: string;
  verify_sql: string;
  warnings: string[];
  generated_at: string;
  llm_used: boolean;
}

export interface ColumnMapping {
  source_col: string | null;
  target_col: string;
  transform_expression: string;
  requires_llm: boolean;
}

export interface TableDataMigration {
  source_table: string;
  target_table: string;
  column_mappings: ColumnMapping[];
  insert_sql: string;
  batched_insert_sql: string;
  count_verify_sql: string;
  warnings: string[];
}

export interface DataMigrationPlanResponse {
  project_id: number;
  table_migrations: TableDataMigration[];
  batch_size: number;
  recommended_order: string[];
  total_tables_with_data: number;
  llm_used: boolean;
  generated_at: string;
}

export interface ConnectionOption {
  id: number;
  name: string;
  database_type: string;
}
