"""Dialect-aware DML generator with parameterized query support (Phase 18).

Produces two forms of each statement:
- display_sql: human-readable with literal values (for preview)
- parameterized_sql + params: safe for execution via text().bindparams()
"""
import logging
from typing import Any, Dict, List

from src.dml.constants import SAFE_IDENT_RE, SUPPORTED_DIALECTS
from src.dml.models import (
    ChangeType,
    CellChangeSchema,
    DMLStatement,
    RowChangeSchema,
)

logger = logging.getLogger(__name__)


class DMLGenerator:
    """Generates dialect-aware, parameterized DML statements."""

    def __init__(self, dialect: str = "postgresql"):
        self.dialect = dialect.lower()
        if self.dialect not in SUPPORTED_DIALECTS:
            raise ValueError(
                f"Unsupported dialect: {dialect!r}. "
                f"Supported: {', '.join(sorted(SUPPORTED_DIALECTS))}"
            )
        self._param_counter = 0

    def generate_statements(
        self, changes: List[RowChangeSchema]
    ) -> List[DMLStatement]:
        """Generate parameterized DML statements from a list of changes.

        Returns statements ordered: DELETEs first, UPDATEs second, INSERTs last.
        """
        self._param_counter = 0
        ordered = sorted(
            changes,
            key=lambda c: (
                0 if c.change_type == ChangeType.DELETE else
                1 if c.change_type == ChangeType.UPDATE else 2
            ),
        )
        statements = []
        for change in ordered:
            stmt = self._generate_one(change)
            if stmt:
                statements.append(stmt)
        return statements

    def generate_preview_script(
        self,
        changes: List[RowChangeSchema],
        wrap_in_transaction: bool = True,
    ) -> str:
        """Generate a human-readable SQL script for display."""
        statements = self.generate_statements(changes)
        lines = [
            f"-- Generated DML Script",
            f"-- Dialect: {self.dialect}",
            f"-- Changes: {len(statements)}",
            "",
        ]
        if wrap_in_transaction:
            lines.append(self._begin_transaction())
            lines.append("")

        for stmt in statements:
            lines.append(f"-- {stmt.change_type.value} on {stmt.table_name}")
            lines.append(stmt.display_sql)
            lines.append("")

        if wrap_in_transaction:
            lines.append("COMMIT;")

        return "\n".join(lines)

    # ── internal generation ──────────────────────────────────────────

    def _generate_one(self, change: RowChangeSchema) -> DMLStatement | None:
        if change.change_type == ChangeType.INSERT:
            return self._generate_insert(change)
        elif change.change_type == ChangeType.UPDATE:
            return self._generate_update(change)
        elif change.change_type == ChangeType.DELETE:
            return self._generate_delete(change)
        return None

    def _generate_insert(self, change: RowChangeSchema) -> DMLStatement | None:
        if not change.new_row_data:
            return None

        columns = list(change.new_row_data.keys())
        for col in columns:
            self._validate_identifier(col)
        self._validate_identifier(change.table_name)

        params: Dict[str, Any] = {}
        param_placeholders = []
        display_values = []

        for col in columns:
            val = change.new_row_data[col]
            pname = self._next_param()
            params[pname] = val
            param_placeholders.append(f":{pname}")
            display_values.append(self._format_literal(val))

        quoted_cols = ", ".join(self._quote(c) for c in columns)
        table = self._quote(change.table_name)

        display_sql = (
            f"INSERT INTO {table} ({quoted_cols})\n"
            f"VALUES ({', '.join(display_values)});"
        )
        parameterized_sql = (
            f"INSERT INTO {table} ({quoted_cols})\n"
            f"VALUES ({', '.join(param_placeholders)})"
        )

        return DMLStatement(
            display_sql=display_sql,
            parameterized_sql=parameterized_sql,
            params=params,
            change_type=ChangeType.INSERT,
            table_name=change.table_name,
        )

    def _generate_update(self, change: RowChangeSchema) -> DMLStatement | None:
        if not change.changes:
            return None
        self._validate_identifier(change.table_name)

        params: Dict[str, Any] = {}
        set_display = []
        set_param = []

        for cell in change.changes:
            self._validate_identifier(cell.column)
            pname = self._next_param()
            params[pname] = cell.new_value
            col = self._quote(cell.column)
            set_display.append(f"{col} = {self._format_literal(cell.new_value)}")
            set_param.append(f"{col} = :{pname}")

        where_display, where_param, where_params = self._build_where(change.primary_key)
        params.update(where_params)

        table = self._quote(change.table_name)

        display_sql = (
            f"UPDATE {table}\n"
            f"SET {', '.join(set_display)}\n"
            f"WHERE {where_display};"
        )
        parameterized_sql = (
            f"UPDATE {table}\n"
            f"SET {', '.join(set_param)}\n"
            f"WHERE {where_param}"
        )

        return DMLStatement(
            display_sql=display_sql,
            parameterized_sql=parameterized_sql,
            params=params,
            change_type=ChangeType.UPDATE,
            table_name=change.table_name,
        )

    def _generate_delete(self, change: RowChangeSchema) -> DMLStatement | None:
        self._validate_identifier(change.table_name)

        params: Dict[str, Any] = {}
        where_display, where_param, where_params = self._build_where(change.primary_key)
        params.update(where_params)

        table = self._quote(change.table_name)

        display_sql = (
            f"DELETE FROM {table}\n"
            f"WHERE {where_display};"
        )
        parameterized_sql = (
            f"DELETE FROM {table}\n"
            f"WHERE {where_param}"
        )

        return DMLStatement(
            display_sql=display_sql,
            parameterized_sql=parameterized_sql,
            params=params,
            change_type=ChangeType.DELETE,
            table_name=change.table_name,
        )

    # ── helpers ──────────────────────────────────────────────────────

    def _build_where(
        self, primary_key: Dict[str, Any]
    ) -> tuple[str, str, Dict[str, Any]]:
        """Build WHERE clause in both display and parameterized forms."""
        display_parts = []
        param_parts = []
        params: Dict[str, Any] = {}

        for col, val in primary_key.items():
            self._validate_identifier(col)
            pname = self._next_param()
            params[pname] = val
            qcol = self._quote(col)
            display_parts.append(f"{qcol} = {self._format_literal(val)}")
            param_parts.append(f"{qcol} = :{pname}")

        return (
            " AND ".join(display_parts),
            " AND ".join(param_parts),
            params,
        )

    def _next_param(self) -> str:
        self._param_counter += 1
        return f"p{self._param_counter}"

    def _quote(self, identifier: str) -> str:
        """Quote an identifier based on dialect."""
        if self.dialect in ("postgresql", "sqlite", "duckdb", "oracle"):
            return f'"{identifier}"'
        elif self.dialect == "mysql":
            return f"`{identifier}`"
        elif self.dialect == "mssql":
            return f"[{identifier}]"
        raise ValueError(f"Unsupported dialect for quoting: {self.dialect!r}")

    def _format_literal(self, value: Any) -> str:
        """Format a value as a SQL literal for display purposes only."""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        else:
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"

    def _begin_transaction(self) -> str:
        if self.dialect == "mssql":
            return "BEGIN TRANSACTION;"
        return "BEGIN;"

    @staticmethod
    def _validate_identifier(name: str) -> None:
        """Reject identifiers that don't match safe pattern."""
        if not SAFE_IDENT_RE.match(name):
            raise ValueError(
                f"Unsafe identifier rejected: {name!r}. "
                "Only letters, digits, and underscores are allowed."
            )
