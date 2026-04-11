// DML (Edit Mode) types — Phase 18

export type ChangeType = 'INSERT' | 'UPDATE' | 'DELETE';

export interface CellChange {
  column: string;
  old_value: any;
  new_value: any;
}

export interface RowChange {
  change_type: ChangeType;
  table_name: string;
  primary_key: Record<string, any>;
  changes: CellChange[];
  new_row_data?: Record<string, any>;
}

export interface DMLStatement {
  display_sql: string;
  parameterized_sql: string;
  params: Record<string, any>;
  change_type: ChangeType;
  table_name: string;
}

export interface WritePermission {
  connection_id: number;
  write_enabled: boolean;
  allow_insert: boolean;
  allow_update: boolean;
  allow_delete: boolean;
  require_where_clause: boolean;
  max_rows_per_operation: number;
  allowed_tables: string[] | null;
}

export interface WritePermissionRequest {
  allow_insert: boolean;
  allow_update: boolean;
  allow_delete: boolean;
  require_where_clause?: boolean;
  max_rows_per_operation?: number;
  allowed_tables?: string[] | null;
}

export interface TableInfoColumn {
  name: string;
  type: string;
  nullable: boolean;
  default: string | null;
  is_primary_key: boolean;
  is_autoincrement: boolean;
}

export interface TableInfo {
  table_name: string;
  primary_key_columns: string[];
  columns: TableInfoColumn[];
}

export interface DMLPreviewRequest {
  connection_id: number;
  changes: RowChange[];
  wrap_in_transaction?: boolean;
}

export interface DMLPreviewResponse {
  sql: string;
  change_count: number;
  summary: { INSERT: number; UPDATE: number; DELETE: number };
  statements: DMLStatement[];
}

export interface DMLExecuteRequest {
  connection_id: number;
  changes: RowChange[];
}

export interface DMLExecuteResponse {
  success: boolean;
  rows_affected: number;
  error_message?: string;
  executed_sql?: string;
}

export interface ChangeSummary {
  INSERT: number;
  UPDATE: number;
  DELETE: number;
  total: number;
}
