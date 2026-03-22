"""DML validation — checks permissions, safety, and schema constraints (Phase 18)."""
import logging
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.database.models import ConnectionWritePermission, DatabaseConnection
from src.dml.constants import SAFE_IDENT_RE
from src.dml.models import ChangeType, RowChangeSchema

logger = logging.getLogger(__name__)


class DMLValidator:
    """Validates DML changes against permissions, safety rules, and schema."""

    async def validate(
        self,
        db: AsyncSession,
        connection_id: int,
        changes: List[RowChangeSchema],
        settings: Settings,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate changes. Returns (is_valid, error_message)."""
        if not changes:
            return True, None

        # 1. Global write operations setting
        if not settings.ALLOW_WRITE_OPERATIONS:
            return False, "Write operations are disabled globally. Set ALLOW_WRITE_OPERATIONS=true to enable."

        # 2. Connection exists and is accessible
        result = await db.execute(
            select(DatabaseConnection).where(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.is_deleted.isnot(True),
            )
        )
        connection = result.scalar_one_or_none()
        if not connection:
            return False, f"Connection {connection_id} not found or has been deleted."

        # 3. Ownership check
        if connection.owner_id is not None:
            if user_id is None:
                return False, "Authentication required to modify data on owned connections."
            if connection.owner_id != user_id:
                return False, "You do not have access to this connection."

        # 4. NoSQL check
        nosql_types = {'mongodb', 'redis', 'cassandra', 'dynamodb', 'elasticsearch'}
        if connection.database_type in nosql_types:
            return False, "Edit mode is not supported for NoSQL databases."

        # 5. Write permission record exists
        perm_result = await db.execute(
            select(ConnectionWritePermission).where(
                ConnectionWritePermission.connection_id == connection_id
            )
        )
        permission = perm_result.scalar_one_or_none()
        if not permission:
            return False, "Write permissions have not been configured for this connection."

        # 6. Per-operation-type permission check
        change_types_needed = {c.change_type for c in changes}
        if ChangeType.INSERT in change_types_needed and not permission.allow_insert:
            return False, "INSERT operations are not allowed on this connection."
        if ChangeType.UPDATE in change_types_needed and not permission.allow_update:
            return False, "UPDATE operations are not allowed on this connection."
        if ChangeType.DELETE in change_types_needed and not permission.allow_delete:
            return False, "DELETE operations are not allowed on this connection."

        # 7. Table whitelist
        if permission.allowed_tables is not None:
            allowed = set(permission.allowed_tables)
            for change in changes:
                if change.table_name not in allowed:
                    return False, f"Table '{change.table_name}' is not in the allowed tables list."

        # 8. Primary key requirement for UPDATE/DELETE
        # Always require a primary key to prevent full-table modifications,
        # regardless of the require_where_clause setting.
        for change in changes:
            if change.change_type in (ChangeType.UPDATE, ChangeType.DELETE):
                if not change.primary_key:
                    return False, (
                        f"{change.change_type.value} requires a primary key "
                        f"to identify target rows."
                    )

        # 9. Row count limits
        max_rows = permission.max_rows_per_operation
        counts = {"INSERT": 0, "UPDATE": 0, "DELETE": 0}
        for change in changes:
            counts[change.change_type.value] += 1
        for op_type, count in counts.items():
            if count > max_rows:
                return False, (
                    f"Too many {op_type} operations ({count}). "
                    f"Maximum allowed: {max_rows} per operation type."
                )

        # 10. Identifier safety
        for change in changes:
            if not SAFE_IDENT_RE.match(change.table_name):
                return False, f"Invalid table name: {change.table_name!r}"
            for col, _ in change.primary_key.items():
                if not SAFE_IDENT_RE.match(col):
                    return False, f"Invalid column name in primary key: {col!r}"
            for cell in change.changes:
                if not SAFE_IDENT_RE.match(cell.column):
                    return False, f"Invalid column name: {cell.column!r}"
            if change.new_row_data:
                for col in change.new_row_data:
                    if not SAFE_IDENT_RE.match(col):
                        return False, f"Invalid column name in row data: {col!r}"

        return True, None
