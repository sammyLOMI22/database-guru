"""Migration Script Generator (Phase 20.3)

Generates up.sql, down.sql, and verify.sql from a SchemaDiff.
Template-based DDL generation with dialect-specific rendering.

No DDL is executed — scripts are returned as strings for download/copy.
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.migration.schema_comparator import (
    SchemaDiff, TableDiff, ColumnDiff, ConstraintDiff,
    _normalize_type, _extract_base_type,
)
from src.llm.dialect_registry import DatabaseDialect, get_dialect_for_database_type

logger = logging.getLogger(__name__)


@dataclass
class GeneratedScripts:
    """Container for generated migration scripts."""
    project_id: int = 0
    target_dialect: str = ""
    up_sql: str = ""
    down_sql: str = ""
    verify_sql: str = ""
    warnings: List[str] = field(default_factory=list)
    generated_at: str = ""
    llm_used: bool = False

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "target_dialect": self.target_dialect,
            "up_sql": self.up_sql,
            "down_sql": self.down_sql,
            "verify_sql": self.verify_sql,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
            "llm_used": self.llm_used,
        }


class ScriptGenerator:
    """Generate DDL migration scripts from a SchemaDiff."""

    def __init__(self, dialect: DatabaseDialect):
        self.dialect = dialect

    def generate(
        self,
        diff: SchemaDiff,
        project_id: int = 0,
        source_schema: Optional[Dict[str, Any]] = None,
        target_schema: Optional[Dict[str, Any]] = None,
    ) -> GeneratedScripts:
        """Generate all three scripts from a diff.

        Args:
            diff: The schema diff to generate scripts from.
            project_id: Associated project ID.
            source_schema: Full source schema dict (needed for SQLite recreate
                to include unchanged columns).
            target_schema: Full target schema dict.
        """
        warnings: List[str] = []

        up_lines = self._generate_up(diff, warnings, source_schema, target_schema)
        down_lines = self._generate_down(diff, warnings, source_schema)
        verify_lines = self._generate_verify(diff)

        return GeneratedScripts(
            project_id=project_id,
            target_dialect=self.dialect.value,
            up_sql="\n".join(up_lines),
            down_sql="\n".join(down_lines),
            verify_sql="\n".join(verify_lines),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # up.sql
    # ------------------------------------------------------------------

    def _generate_up(
        self,
        diff: SchemaDiff,
        warnings: List[str],
        source_schema: Optional[Dict[str, Any]] = None,
        target_schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate the forward migration DDL."""
        lines = [
            f"-- Migration: up.sql",
            f"-- Generated: {datetime.now(timezone.utc).isoformat()}",
            f"-- Dialect: {self.dialect.value}",
            f"-- Changes: {diff.diff_summary}",
            "",
        ]

        if self.dialect == DatabaseDialect.MYSQL:
            lines.append("SET FOREIGN_KEY_CHECKS = 0;")
            lines.append("")

        # 1. Create new tables (FK dependency order from table_diffs)
        for td in diff.table_diffs:
            if td.diff_type == "added":
                lines.extend(self._create_table_ddl(td))
                lines.append("")

        # 2. Modify existing tables
        source_tables = (source_schema or {}).get("tables", {})
        target_tables = (target_schema or {}).get("tables", {})
        for td in diff.table_diffs:
            if td.diff_type == "modified":
                table_lines = self._alter_table_ddl(
                    td, warnings,
                    source_table_schema=source_tables.get(td.table_name),
                    target_table_schema=target_tables.get(td.table_name),
                )
                if table_lines:
                    lines.extend(table_lines)
                    lines.append("")

        # 3. Drop removed tables — children before parents (FK-aware)
        removed = [td for td in diff.table_diffs if td.diff_type == "removed"]
        removed = self._sort_removed_tables_for_drop(removed, source_schema)
        for td in removed:
            lines.append(f"-- WARNING: Data loss — dropping table '{td.table_name}'")
            lines.append(f"DROP TABLE IF EXISTS {self._quote(td.table_name)};")
            lines.append("")
            warnings.append(f"DROP TABLE {td.table_name}: all data will be lost")

        if self.dialect == DatabaseDialect.MYSQL:
            lines.append("SET FOREIGN_KEY_CHECKS = 1;")
            lines.append("")

        return lines

    def _create_table_ddl(self, td: TableDiff) -> List[str]:
        """Generate CREATE TABLE for an added table."""
        lines = [f"CREATE TABLE {self._quote(td.table_name)} ("]

        col_defs = []
        for cd in td.column_diffs:
            if cd.target_state:
                col_defs.append(self._column_def(cd.target_state))

        lines.append(",\n".join(f"    {c}" for c in col_defs))
        lines.append(");")
        return lines

    def _alter_table_ddl(
        self,
        td: TableDiff,
        warnings: List[str],
        source_table_schema: Optional[Dict[str, Any]] = None,
        target_table_schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate ALTER TABLE statements for a modified table."""
        lines = [f"-- Modify table: {td.table_name}"]

        # Check if SQLite needs table recreate
        needs_recreate = (
            self.dialect == DatabaseDialect.SQLITE
            and any(
                cd.diff_type in ("type_changed", "nullability_changed")
                for cd in td.column_diffs
            )
        )

        if needs_recreate:
            return self._sqlite_recreate(td, warnings, source_table_schema, target_table_schema)

        for cd in td.column_diffs:
            if cd.diff_type == "added" and cd.target_state:
                col = cd.target_state
                nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                default = f" DEFAULT {self._format_default(col['default'])}" if col.get("default") is not None else ""
                lines.append(
                    f"ALTER TABLE {self._quote(td.table_name)} "
                    f"ADD COLUMN {self._quote(cd.column_name)} {col.get('type', 'TEXT')} {nullable}{default};"
                )

            elif cd.diff_type == "removed":
                lines.append(f"-- WARNING: Data loss — dropping column '{cd.column_name}'")
                lines.append(
                    f"ALTER TABLE {self._quote(td.table_name)} "
                    f"DROP COLUMN {self._quote(cd.column_name)};"
                )
                warnings.append(f"DROP COLUMN {td.table_name}.{cd.column_name}: data will be lost")

            elif cd.diff_type == "type_changed" and cd.target_state:
                lines.extend(self._change_type_ddl(td.table_name, cd))

            elif cd.diff_type == "nullability_changed" and cd.target_state:
                nullable = cd.target_state.get("nullable", True)
                if self.dialect == DatabaseDialect.POSTGRESQL:
                    action = "DROP NOT NULL" if nullable else "SET NOT NULL"
                    lines.append(
                        f"ALTER TABLE {self._quote(td.table_name)} "
                        f"ALTER COLUMN {self._quote(cd.column_name)} {action};"
                    )
                elif self.dialect == DatabaseDialect.MYSQL:
                    col = cd.target_state
                    null_str = "NULL" if nullable else "NOT NULL"
                    lines.append(
                        f"ALTER TABLE {self._quote(td.table_name)} "
                        f"MODIFY COLUMN {self._quote(cd.column_name)} {col.get('type', 'TEXT')} {null_str};"
                    )

        # Constraint changes
        for cd in td.constraint_diffs:
            if cd.constraint_type == "index":
                if cd.diff_type == "added" and cd.target_state:
                    cols, unique = cd.target_state
                    prefix = "UNIQUE " if unique else ""
                    col_list = ", ".join(self._quote(c) for c in cols)
                    idx_name = f"idx_{td.table_name}_{'_'.join(cols)}"
                    lines.append(
                        f"CREATE {prefix}INDEX {self._quote(idx_name)} "
                        f"ON {self._quote(td.table_name)} ({col_list});"
                    )
                elif cd.diff_type == "removed" and cd.source_state:
                    cols, _ = cd.source_state
                    idx_name = f"idx_{td.table_name}_{'_'.join(cols)}"
                    lines.append(f"DROP INDEX IF EXISTS {self._quote(idx_name)};")

        return lines

    def _change_type_ddl(self, table_name: str, cd: ColumnDiff) -> List[str]:
        """Generate dialect-specific column type change DDL."""
        old_type = cd.source_state.get("type", "") if cd.source_state else ""
        new_type = cd.target_state.get("type", "") if cd.target_state else ""

        if self.dialect == DatabaseDialect.POSTGRESQL:
            using = f" USING {self._quote(cd.column_name)}::{new_type}"
            return [
                f"ALTER TABLE {self._quote(table_name)} "
                f"ALTER COLUMN {self._quote(cd.column_name)} TYPE {new_type}{using};"
            ]
        elif self.dialect == DatabaseDialect.MYSQL:
            col = cd.target_state or {}
            nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
            return [
                f"ALTER TABLE {self._quote(table_name)} "
                f"MODIFY COLUMN {self._quote(cd.column_name)} {new_type} {nullable};"
            ]
        # SQLite handled by _sqlite_recreate
        return []

    def _sqlite_recreate(
        self,
        td: TableDiff,
        warnings: List[str],
        source_table_schema: Optional[Dict[str, Any]] = None,
        target_table_schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate SQLite table recreate pattern for unsupported ALTER COLUMN.

        Includes ALL columns (changed and unchanged) in the recreated table.
        Requires source/target schemas to know about unchanged columns;
        falls back to diff-only columns with a warning if schemas are unavailable.
        """
        warnings.append(
            f"SQLite table recreate used for '{td.table_name}' "
            "(SQLite does not support ALTER COLUMN)"
        )

        lines = [
            f"-- SQLite: recreate table '{td.table_name}' to apply column changes",
            f"-- (SQLite does not support ALTER COLUMN)",
        ]

        # Build sets of changed column names for quick lookup
        changed_cols = {cd.column_name for cd in td.column_diffs}
        removed_cols = {cd.column_name for cd in td.column_diffs if cd.diff_type == "removed"}

        target_col_defs = []
        select_exprs = []

        # If we have the target schema, use it as the authoritative column list
        # (it includes both changed and unchanged columns)
        if target_table_schema:
            tgt_cols_list = target_table_schema.get("columns", [])
            # Build a lookup of diff info by column name
            diff_by_col = {cd.column_name: cd for cd in td.column_diffs}

            for col in tgt_cols_list:
                col_name = col.get("name", "")
                target_col_defs.append(self._column_def(col))

                cd = diff_by_col.get(col_name)
                if cd and cd.diff_type == "added":
                    # New column — use default or NULL
                    default_val = self._format_default(col.get("default")) if col.get("default") is not None else "NULL"
                    select_exprs.append(f"{default_val} AS {self._quote(col_name)}")
                elif cd and cd.diff_type == "type_changed":
                    # Type changed — CAST
                    select_exprs.append(
                        f"CAST({self._quote(col_name)} AS {col.get('type', 'TEXT')})"
                    )
                else:
                    # Unchanged or minor change (nullability, default) — pass through
                    select_exprs.append(self._quote(col_name))
        else:
            # Fallback: no full schema available, use source schema + diffs
            if source_table_schema:
                src_cols_list = source_table_schema.get("columns", [])
            else:
                src_cols_list = []
                warnings.append(
                    f"No full schema available for '{td.table_name}'; "
                    "recreated table may be missing unchanged columns"
                )

            # First, include unchanged columns from source
            for col in src_cols_list:
                col_name = col.get("name", "")
                if col_name in removed_cols:
                    continue
                if col_name not in changed_cols:
                    target_col_defs.append(self._column_def(col))
                    select_exprs.append(self._quote(col_name))

            # Then, include changed columns from diffs
            for cd in td.column_diffs:
                if cd.diff_type == "removed":
                    continue
                elif cd.diff_type == "added" and cd.target_state:
                    col = cd.target_state
                    target_col_defs.append(self._column_def(col))
                    default_val = self._format_default(col.get("default")) if col.get("default") is not None else "NULL"
                    select_exprs.append(f"{default_val} AS {self._quote(cd.column_name)}")
                elif cd.target_state:
                    col = cd.target_state
                    target_col_defs.append(self._column_def(col))
                    if cd.diff_type == "type_changed":
                        select_exprs.append(
                            f"CAST({self._quote(cd.column_name)} AS {col.get('type', 'TEXT')})"
                        )
                    else:
                        select_exprs.append(self._quote(cd.column_name))

        new_table = f"{td.table_name}__new"
        col_defs = ",\n    ".join(target_col_defs)
        select_list = ", ".join(select_exprs)

        lines.extend([
            f"CREATE TABLE {self._quote(new_table)} (",
            f"    {col_defs}",
            ");",
            f"INSERT INTO {self._quote(new_table)} SELECT {select_list} FROM {self._quote(td.table_name)};",
            f"DROP TABLE {self._quote(td.table_name)};",
            f"ALTER TABLE {self._quote(new_table)} RENAME TO {self._quote(td.table_name)};",
        ])

        return lines

    # ------------------------------------------------------------------
    # down.sql
    # ------------------------------------------------------------------

    def _generate_down(
        self,
        diff: SchemaDiff,
        warnings: List[str],
        source_schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate the rollback DDL (inverse of up.sql)."""
        lines = [
            f"-- Migration: down.sql (rollback)",
            f"-- Generated: {datetime.now(timezone.utc).isoformat()}",
            f"-- Dialect: {self.dialect.value}",
            "",
        ]

        if self.dialect == DatabaseDialect.MYSQL:
            lines.append("SET FOREIGN_KEY_CHECKS = 0;")
            lines.append("")

        # Reverse: drop tables that were added
        for td in diff.table_diffs:
            if td.diff_type == "added":
                lines.append(f"DROP TABLE IF EXISTS {self._quote(td.table_name)};")

        # Reverse: recreate tables that were removed (skeleton only — data is lost)
        for td in diff.table_diffs:
            if td.diff_type == "removed":
                lines.append(f"-- NOTE: Cannot restore data for dropped table '{td.table_name}'")
                lines.extend(self._create_table_from_source(td))
                lines.append("")

        # Reverse: undo modifications
        source_tables = (source_schema or {}).get("tables", {})
        for td in diff.table_diffs:
            if td.diff_type == "modified":
                # SQLite: use table recreate to rollback all column changes
                if self.dialect == DatabaseDialect.SQLITE and td.column_diffs:
                    src_tbl = source_tables.get(td.table_name)
                    lines.extend(self._sqlite_rollback(td, src_tbl))
                    lines.append("")
                    continue

                for cd in td.column_diffs:
                    if cd.diff_type == "added":
                        # Reverse: drop the column that was added
                        lines.append(
                            f"ALTER TABLE {self._quote(td.table_name)} "
                            f"DROP COLUMN {self._quote(cd.column_name)};"
                        )
                    elif cd.diff_type == "removed" and cd.source_state:
                        # Reverse: re-add the column that was dropped
                        col = cd.source_state
                        nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                        lines.append(
                            f"ALTER TABLE {self._quote(td.table_name)} "
                            f"ADD COLUMN {self._quote(cd.column_name)} "
                            f"{col.get('type', 'TEXT')} {nullable};"
                        )
                        lines.append(f"-- NOTE: Data for '{cd.column_name}' cannot be restored")
                    elif cd.diff_type == "type_changed" and cd.source_state:
                        if self.dialect == DatabaseDialect.POSTGRESQL:
                            old_type = cd.source_state.get("type", "TEXT")
                            lines.append(
                                f"ALTER TABLE {self._quote(td.table_name)} "
                                f"ALTER COLUMN {self._quote(cd.column_name)} "
                                f"TYPE {old_type} USING {self._quote(cd.column_name)}::{old_type};"
                            )
                        elif self.dialect == DatabaseDialect.MYSQL:
                            col = cd.source_state
                            nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                            lines.append(
                                f"ALTER TABLE {self._quote(td.table_name)} "
                                f"MODIFY COLUMN {self._quote(cd.column_name)} "
                                f"{col.get('type', 'TEXT')} {nullable};"
                            )

        if self.dialect == DatabaseDialect.MYSQL:
            lines.append("")
            lines.append("SET FOREIGN_KEY_CHECKS = 1;")

        return lines

    def _create_table_from_source(self, td: TableDiff) -> List[str]:
        """Recreate a dropped table from its source column diffs."""
        lines = [f"CREATE TABLE {self._quote(td.table_name)} ("]
        col_defs = []
        for cd in td.column_diffs:
            if cd.source_state:
                col_defs.append(self._column_def(cd.source_state))
        lines.append(",\n".join(f"    {c}" for c in col_defs))
        lines.append(");")
        return lines

    # ------------------------------------------------------------------
    # verify.sql
    # ------------------------------------------------------------------

    def _generate_verify(self, diff: SchemaDiff) -> List[str]:
        """Generate verification queries."""
        lines = [
            f"-- Migration: verify.sql",
            f"-- Generated: {datetime.now(timezone.utc).isoformat()}",
            f"-- Run after migration to verify success",
            "",
        ]

        for td in diff.table_diffs:
            if td.diff_type == "added":
                lines.append(f"-- Verify table '{td.table_name}' was created")
                lines.append(f"SELECT COUNT(*) AS row_count FROM {self._quote(td.table_name)};")
                lines.append("")

            elif td.diff_type == "removed":
                safe_name = self._escape_literal(td.table_name)
                lines.append(f"-- Verify table '{safe_name}' was dropped")
                if self.dialect in (DatabaseDialect.POSTGRESQL, DatabaseDialect.MYSQL):
                    lines.append(
                        f"SELECT NOT EXISTS ("
                        f"SELECT 1 FROM information_schema.tables "
                        f"WHERE table_name = '{safe_name}'"
                        f") AS table_dropped;"
                    )
                elif self.dialect == DatabaseDialect.SQLITE:
                    lines.append(
                        f"SELECT COUNT(*) = 0 AS table_dropped "
                        f"FROM sqlite_master WHERE type='table' AND name='{safe_name}';"
                    )
                lines.append("")

            elif td.diff_type == "modified":
                lines.append(f"-- Verify modifications to '{td.table_name}'")
                lines.append(f"SELECT COUNT(*) AS row_count FROM {self._quote(td.table_name)};")

                for cd in td.column_diffs:
                    # Check NOT NULL constraints hold after nullability change
                    if cd.diff_type == "nullability_changed" and cd.target_state:
                        if not cd.target_state.get("nullable", True):
                            lines.append(
                                f"SELECT COUNT(*) AS null_violations "
                                f"FROM {self._quote(td.table_name)} "
                                f"WHERE {self._quote(cd.column_name)} IS NULL;"
                            )

                    # Verify added column exists in the schema
                    if cd.diff_type == "added":
                        safe_tbl = self._escape_literal(td.table_name)
                        safe_col = self._escape_literal(cd.column_name)
                        lines.append(
                            f"-- Verify column '{cd.column_name}' was added to '{td.table_name}'"
                        )
                        if self.dialect in (DatabaseDialect.POSTGRESQL, DatabaseDialect.MYSQL):
                            lines.append(
                                f"SELECT COUNT(*) AS col_exists "
                                f"FROM information_schema.columns "
                                f"WHERE table_name = '{safe_tbl}' "
                                f"AND column_name = '{safe_col}';"
                                f"  -- Expected: 1"
                            )
                        elif self.dialect == DatabaseDialect.SQLITE:
                            lines.append(
                                f"SELECT COUNT(*) AS col_exists "
                                f"FROM pragma_table_info('{safe_tbl}') "
                                f"WHERE name = '{safe_col}';"
                                f"  -- Expected: 1"
                            )

                lines.append("")

        return lines

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sort_removed_tables_for_drop(
        self,
        removed: List[TableDiff],
        source_schema: Optional[Dict[str, Any]],
    ) -> List[TableDiff]:
        """Return removed tables sorted so FK-dependent children are dropped before parents.

        Without FK-aware ordering, dropping a parent before a child fails when
        FK constraints are enforced (e.g. PostgreSQL, MySQL with FK checks on).
        """
        if not removed or not source_schema:
            return removed

        removed_names = {td.table_name for td in removed}
        source_tables = source_schema.get("tables", {})

        # Build drop-order graph: A → B means "drop A before B"
        # (A is a child that references B, so A must go first)
        successors: Dict[str, set] = defaultdict(set)
        in_degree: Dict[str, int] = {td.table_name: 0 for td in removed}

        for td in removed:
            for fk in source_tables.get(td.table_name, {}).get("foreign_keys", []):
                parent = fk.get("referred_table", "")
                if parent in removed_names and parent != td.table_name:
                    # td (child) must be dropped before parent
                    if parent not in successors[td.table_name]:
                        successors[td.table_name].add(parent)
                        in_degree[parent] = in_degree.get(parent, 0) + 1

        queue = deque(sorted(t for t in in_degree if in_degree[t] == 0))
        td_by_name = {td.table_name: td for td in removed}
        result: List[TableDiff] = []

        while queue:
            name = queue.popleft()
            if name in td_by_name:
                result.append(td_by_name[name])
            for successor in sorted(successors.get(name, [])):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        # Append any remaining (circular FK dependencies — unlikely but safe)
        seen = {td.table_name for td in result}
        result.extend(td for td in removed if td.table_name not in seen)
        return result

    def _sqlite_rollback(
        self,
        td: TableDiff,
        source_table_schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate SQLite table recreate pattern for rolling back a modified table.

        The database is in the post-up state. We recreate the table with the
        original (source) column definitions to reverse the migration.
        Dropped columns are filled with NULL (data is unrecoverable).
        Added columns are omitted from the rollback table.
        """
        lines = [
            f"-- SQLite: recreate table '{td.table_name}' to rollback changes",
            f"-- (SQLite does not support ALTER COLUMN)",
        ]

        changed_cols = {cd.column_name: cd for cd in td.column_diffs}
        added_cols = {cd.column_name for cd in td.column_diffs if cd.diff_type == "added"}

        target_col_defs: List[str] = []
        select_exprs: List[str] = []

        if source_table_schema:
            # Iterate over the original (source) column list
            for col in source_table_schema.get("columns", []):
                col_name = col.get("name", "")
                target_col_defs.append(self._column_def(col))
                cd = changed_cols.get(col_name)
                if cd and cd.diff_type == "removed":
                    # Column was dropped in up.sql — data is gone
                    lines.append(f"-- NOTE: Data for '{col_name}' was lost when the column was dropped")
                    select_exprs.append(f"NULL AS {self._quote(col_name)}")
                elif cd and cd.diff_type == "type_changed" and cd.source_state:
                    # Cast from the post-up type back to the original type
                    old_type = cd.source_state.get("type", "TEXT")
                    select_exprs.append(f"CAST({self._quote(col_name)} AS {old_type})")
                else:
                    select_exprs.append(self._quote(col_name))
        else:
            # No full schema — use source_state from diffs, skipping added columns
            for cd in td.column_diffs:
                if cd.diff_type == "added":
                    continue
                if cd.source_state:
                    col = cd.source_state
                    col_name = cd.column_name
                    target_col_defs.append(self._column_def(col))
                    if cd.diff_type == "removed":
                        select_exprs.append(f"NULL AS {self._quote(col_name)}")
                    elif cd.diff_type == "type_changed":
                        old_type = col.get("type", "TEXT")
                        select_exprs.append(f"CAST({self._quote(col_name)} AS {old_type})")
                    else:
                        select_exprs.append(self._quote(col_name))

        if not target_col_defs:
            lines.append(f"-- WARNING: No column definitions available for rollback of '{td.table_name}'")
            return lines

        rollback_name = f"{td.table_name}__rollback"
        col_defs_str = ",\n    ".join(target_col_defs)
        # select_exprs only covers source (original) columns — added columns are
        # not included because they don't belong in the rollback table, and they
        # are not in source_table_schema / skipped in the diff-only branch.
        select_list = ", ".join(select_exprs)

        lines.extend([
            f"CREATE TABLE {self._quote(rollback_name)} (",
            f"    {col_defs_str}",
            f");",
            f"INSERT INTO {self._quote(rollback_name)} SELECT {select_list} FROM {self._quote(td.table_name)};",
            f"DROP TABLE {self._quote(td.table_name)};",
            f"ALTER TABLE {self._quote(rollback_name)} RENAME TO {self._quote(td.table_name)};",
        ])
        return lines

    def _quote(self, identifier: str) -> str:
        """Quote an identifier based on dialect."""
        if self.dialect == DatabaseDialect.MYSQL:
            return f"`{identifier}`"
        return f'"{identifier}"'

    @staticmethod
    def _escape_literal(value: str) -> str:
        """Escape a string for use in a SQL string literal (single quotes)."""
        return value.replace("'", "''")

    def _column_def(self, col: Dict[str, Any]) -> str:
        """Generate a column definition string."""
        name = self._quote(col.get("name", "unknown"))
        col_type = col.get("type", "TEXT")
        nullable = "" if col.get("nullable", True) else " NOT NULL"
        default = ""
        if col.get("default") is not None:
            default = f" DEFAULT {self._format_default(col['default'])}"
        return f"{name} {col_type}{nullable}{default}"

    def _format_default(self, value) -> str:
        """Format a default value for DDL."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        return f"'{value}'"


async def generate_scripts(
    project,
    target_dialect: str,
    enrich_with_llm: bool = True,
    db=None,
    source_schema: Optional[Dict[str, Any]] = None,
    target_schema: Optional[Dict[str, Any]] = None,
) -> GeneratedScripts:
    """High-level function to generate scripts for a project.

    Args:
        source_schema: Full source schema dict. When provided, SQLite table
            recreate will include unchanged columns correctly.
        target_schema: Full target schema dict.
    """
    diff_data = project.diff_snapshot
    if not diff_data:
        raise ValueError("Project has no diff snapshot")

    from src.migration.schema_comparator import SchemaDiff
    diff = SchemaDiff.from_dict(diff_data)

    dialect = get_dialect_for_database_type(target_dialect)
    generator = ScriptGenerator(dialect)
    result = generator.generate(
        diff,
        project_id=project.id,
        source_schema=source_schema,
        target_schema=target_schema,
    )

    return result
