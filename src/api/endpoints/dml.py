"""DML (Edit Mode) API endpoints (Phase 18).

Provides preview, execute, permissions, and table-info endpoints
for inline data editing in query results.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.auth.dependencies import get_current_user, get_optional_user
from src.auth.models import User
from src.config.settings import Settings
from src.core.schema_inspector import SchemaInspector
from src.core.user_db_connector import UserDatabaseConnector
from src.database.models import ConnectionWritePermission, DatabaseConnection
from src.dml.constants import NOSQL_SAFE_IDENT_RE, NOSQL_TYPES, SAFE_IDENT_RE
from src.dml.dml_executor import DMLExecutor
from src.dml.dml_generator import DMLGenerator
from src.dml.dml_validator import DMLValidator
from src.dml.nosql_dml_executor import NoSQLDMLExecutor
from src.dml.nosql_dml_generator import NoSQLDMLGenerator
from src.dml.models import (
    DMLExecuteRequest,
    DMLPreviewRequest,
    DMLPreviewResponse,
    ExecutionResult,
    TableInfoColumn,
    TableInfoResponse,
    WritePermissionRequest,
    WritePermissionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dml", tags=["DML Operations"])


# ── helpers ──────────────────────────────────────────────────────────


async def _get_connection(
    db: AsyncSession, connection_id: int
) -> DatabaseConnection:
    """Fetch a connection or raise 404."""
    result = await db.execute(
        select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.is_deleted.isnot(True),
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found.",
        )
    return connection


def _check_connection_access(
    connection: DatabaseConnection, user: Optional[User]
) -> None:
    """Verify user can access this connection."""
    if connection.owner_id is not None:
        if user is None or connection.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this connection.",
            )


# ── endpoints ────────────────────────────────────────────────────────


@router.post("/preview", response_model=DMLPreviewResponse)
async def preview_changes(
    request: DMLPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Generate DML script from pending changes without executing.

    Returns human-readable SQL for review.
    """
    connection = await _get_connection(db, request.connection_id)
    _check_connection_access(connection, current_user)

    if connection.database_type in NOSQL_TYPES:
        generator = NoSQLDMLGenerator(database_type=connection.database_type)
        statements = generator.generate_statements(request.changes)
        preview_script = generator.generate_preview_script(request.changes)
    else:
        sql_generator = DMLGenerator(dialect=connection.database_type)
        statements = sql_generator.generate_statements(request.changes)
        preview_script = sql_generator.generate_preview_script(
            request.changes, wrap_in_transaction=request.wrap_in_transaction
        )

    summary = {"INSERT": 0, "UPDATE": 0, "DELETE": 0}
    for change in request.changes:
        summary[change.change_type.value] += 1

    return DMLPreviewResponse(
        sql=preview_script,
        change_count=len(request.changes),
        summary=summary,
        statements=statements,
    )


@router.post("/execute", response_model=ExecutionResult)
async def execute_changes(
    request: DMLExecuteRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Execute DML changes with transaction support.

    Always requires authentication — write operations must be attributable.
    """
    connection = await _get_connection(db, request.connection_id)
    _check_connection_access(connection, current_user)

    # Validate
    validator = DMLValidator()
    is_valid, error = await validator.validate(
        db, request.connection_id, request.changes, settings,
        user_id=current_user.id,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error,
        )

    # Generate and execute — branch on SQL vs NoSQL
    is_nosql = connection.database_type in NOSQL_TYPES
    if is_nosql:
        gen = NoSQLDMLGenerator(database_type=connection.database_type)
    else:
        gen = DMLGenerator(dialect=connection.database_type)
    statements = gen.generate_statements(request.changes)

    if not statements:
        return ExecutionResult(success=True, rows_affected=0)

    ip_address = http_request.client.host if http_request.client else None
    executor = NoSQLDMLExecutor() if is_nosql else DMLExecutor()
    result = await executor.execute(
        connection=connection,
        statements=statements,
        metadata_db=db,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=ip_address,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message,
        )

    return result


@router.get("/permissions/{connection_id}", response_model=WritePermissionResponse)
async def get_write_permissions(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get write permissions for a connection."""
    connection = await _get_connection(db, connection_id)
    _check_connection_access(connection, current_user)

    result = await db.execute(
        select(ConnectionWritePermission).where(
            ConnectionWritePermission.connection_id == connection_id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        return WritePermissionResponse(
            connection_id=connection_id,
            write_enabled=False,
        )

    return WritePermissionResponse(
        connection_id=connection_id,
        write_enabled=True,
        allow_insert=permission.allow_insert,
        allow_update=permission.allow_update,
        allow_delete=permission.allow_delete,
        require_where_clause=permission.require_where_clause,
        max_rows_per_operation=permission.max_rows_per_operation,
        allowed_tables=permission.allowed_tables,
    )


@router.put("/permissions/{connection_id}", response_model=WritePermissionResponse)
async def update_write_permissions(
    connection_id: int,
    request: WritePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Update write permissions for a connection.

    When auth is enabled, only the connection owner or an admin can modify
    permissions. Unowned connections require admin access.
    When auth is disabled (REQUIRE_AUTH=False), any user can modify permissions.
    """
    connection = await _get_connection(db, connection_id)
    _check_connection_access(connection, current_user)

    # When auth is active, enforce ownership / admin on shared connections
    if current_user is not None and connection.owner_id is None and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to modify permissions on shared connections.",
        )
    if current_user is not None and connection.owner_id is not None and connection.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the connection owner or an admin can modify permissions.",
        )

    result = await db.execute(
        select(ConnectionWritePermission).where(
            ConnectionWritePermission.connection_id == connection_id
        )
    )
    permission = result.scalar_one_or_none()

    if permission:
        permission.allow_insert = request.allow_insert
        permission.allow_update = request.allow_update
        permission.allow_delete = request.allow_delete
        permission.require_where_clause = request.require_where_clause
        permission.max_rows_per_operation = request.max_rows_per_operation
        permission.allowed_tables = request.allowed_tables
    else:
        permission = ConnectionWritePermission(
            connection_id=connection_id,
            allow_insert=request.allow_insert,
            allow_update=request.allow_update,
            allow_delete=request.allow_delete,
            require_where_clause=request.require_where_clause,
            max_rows_per_operation=request.max_rows_per_operation,
            allowed_tables=request.allowed_tables,
        )
        db.add(permission)

    await db.commit()

    return WritePermissionResponse(
        connection_id=connection_id,
        write_enabled=True,
        allow_insert=request.allow_insert,
        allow_update=request.allow_update,
        allow_delete=request.allow_delete,
        require_where_clause=request.require_where_clause,
        max_rows_per_operation=request.max_rows_per_operation,
        allowed_tables=request.allowed_tables,
    )


@router.get(
    "/table-info/{connection_id}/{table_name}",
    response_model=TableInfoResponse,
)
async def get_table_info(
    connection_id: int,
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get primary key columns and column types for a table.

    Used by the frontend to configure edit mode (which columns are
    editable, which are PKs, column types for input validation).
    """
    connection = await _get_connection(db, connection_id)
    _check_connection_access(connection, current_user)

    is_nosql = connection.database_type in NOSQL_TYPES
    ident_re = NOSQL_SAFE_IDENT_RE if is_nosql else SAFE_IDENT_RE
    if not ident_re.match(table_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table name: {table_name!r}",
        )

    if is_nosql:
        return await _get_nosql_table_info(connection, table_name)

    inspector = SchemaInspector()

    async with UserDatabaseConnector.get_user_db_session(connection) as session:
        columns_raw = await inspector.get_columns(session, table_name)
        pk_columns = await inspector.get_primary_keys(session, table_name)

    columns = []
    for col in columns_raw:
        is_pk = col["name"] in pk_columns
        default_val = col.get("default")
        is_auto = (
            is_pk
            and default_val is not None
            and any(
                kw in str(default_val).lower()
                for kw in ("nextval", "autoincrement", "auto_increment", "identity", "serial")
            )
        )
        columns.append(
            TableInfoColumn(
                name=col["name"],
                type=col.get("type", "text"),
                nullable=col.get("nullable", True),
                default=str(default_val) if default_val is not None else None,
                is_primary_key=is_pk,
                is_autoincrement=is_auto,
            )
        )

    return TableInfoResponse(
        table_name=table_name,
        primary_key_columns=pk_columns,
        columns=columns,
    )


async def _get_nosql_table_info(
    connection: DatabaseConnection, table_name: str
) -> TableInfoResponse:
    """Get table info for a NoSQL collection/index by inspecting schema."""
    from src.nosql.router import get_nosql_inspector

    inspector, _ = await get_nosql_inspector(connection)
    schema = await inspector.get_schema(connection)

    # Each NoSQL inspector returns schema with collections/tables/indices
    # containing field info. Try to find the requested table.
    pk_map = {
        "mongodb": ["_id"],
        "elasticsearch": ["_id"],
        "redis": ["key"],
        "dynamodb": None,  # extracted from schema
        "cassandra": None,  # extracted from schema
    }

    db_type = connection.database_type
    default_pks = pk_map.get(db_type, ["_id"])

    # Try to extract columns from schema
    columns = []
    pk_columns = default_pks or []

    # All NoSQL inspectors return {"tables": {name: {"columns": [...], "row_count": N}}}
    collections = schema.get("tables", {})
    if isinstance(collections, dict) and table_name in collections:
        table_schema = collections[table_name]
        col_list = table_schema.get("columns", []) if isinstance(table_schema, dict) else []

        # DynamoDB: columns with kind == "hash" or "range" are keys
        if db_type == "dynamodb":
            pk_columns = [
                c["name"] for c in col_list
                if isinstance(c, dict) and c.get("kind") in ("hash", "range")
            ] or ["pk"]
        # Cassandra: columns with kind == "partition_key" or "clustering" are keys
        elif db_type == "cassandra":
            pk_columns = [
                c["name"] for c in col_list
                if isinstance(c, dict) and c.get("kind") in ("partition_key", "clustering")
            ] or ["id"]

        for col in col_list:
            if not isinstance(col, dict):
                continue
            col_name = col.get("name", "")
            col_type = col.get("type", "text")
            columns.append(
                TableInfoColumn(
                    name=col_name,
                    type=col_type,
                    nullable=col.get("nullable", True),
                    is_primary_key=col_name in pk_columns,
                )
            )

    # If no columns found from schema, return minimal info
    if not columns:
        columns = [
            TableInfoColumn(
                name=pk_columns[0] if pk_columns else "_id",
                type="text",
                nullable=False,
                is_primary_key=True,
            )
        ]

    return TableInfoResponse(
        table_name=table_name,
        primary_key_columns=pk_columns,
        columns=columns,
    )
