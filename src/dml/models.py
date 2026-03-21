"""Pydantic schemas and data models for DML operations (Phase 18)."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class CellChangeSchema(BaseModel):
    """A single cell value change."""
    column: str
    old_value: Any = None
    new_value: Any = None


class RowChangeSchema(BaseModel):
    """Changes to a single row."""
    change_type: ChangeType
    table_name: str
    primary_key: Dict[str, Any] = Field(default_factory=dict)
    changes: List[CellChangeSchema] = Field(default_factory=list)
    new_row_data: Optional[Dict[str, Any]] = None


class DMLStatement(BaseModel):
    """A generated DML statement with both display and parameterized forms."""
    display_sql: str
    parameterized_sql: str
    params: Dict[str, Any] = Field(default_factory=dict)
    change_type: ChangeType
    table_name: str


class DMLPreviewRequest(BaseModel):
    """Request to preview DML changes."""
    connection_id: int
    changes: List[RowChangeSchema]
    wrap_in_transaction: bool = True


class DMLExecuteRequest(BaseModel):
    """Request to execute DML changes."""
    connection_id: int
    changes: List[RowChangeSchema]


class WritePermissionRequest(BaseModel):
    """Request to update write permissions."""
    allow_insert: bool = False
    allow_update: bool = False
    allow_delete: bool = False
    require_where_clause: bool = True
    max_rows_per_operation: int = Field(default=100, ge=1, le=10000)
    allowed_tables: Optional[List[str]] = None


class DMLPreviewResponse(BaseModel):
    """Response for DML preview."""
    sql: str
    change_count: int
    summary: Dict[str, int]
    statements: List[DMLStatement]


class ExecutionResult(BaseModel):
    """Result of DML execution."""
    success: bool
    rows_affected: int = 0
    error_message: Optional[str] = None
    executed_sql: Optional[str] = None


class WritePermissionResponse(BaseModel):
    """Response for write permissions."""
    connection_id: int
    write_enabled: bool
    allow_insert: bool = False
    allow_update: bool = False
    allow_delete: bool = False
    require_where_clause: bool = True
    max_rows_per_operation: int = 100
    allowed_tables: Optional[List[str]] = None


class TableInfoColumn(BaseModel):
    """Column info for table-info endpoint."""
    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    is_autoincrement: bool = False


class TableInfoResponse(BaseModel):
    """Response for table-info endpoint."""
    table_name: str
    primary_key_columns: List[str]
    columns: List[TableInfoColumn]
