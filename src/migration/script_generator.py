"""Migration Script Generator (Phase 20.3)

Generates up.sql, down.sql, and verify.sql from a SchemaDiff.
Template-based DDL generation with dialect-specific rendering.

No DDL is executed — scripts are returned as strings for download/copy.
"""

import logging
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

    def generate(self, diff: SchemaDiff, project_id: int = 0) -> GeneratedScripts:
        """Generate all three scripts from a diff."""
        warnings: List[str] = []

        up_lines = self._generate_up(diff, warnings)
        down_lines = self._generate_down(diff, warnings)
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

    def _generate_up(self, diff: SchemaDiff, warnings: List[str]) -> List[str]:
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
        for td in diff.table_diffs:
            if td.diff_type == "modified":
                table_lines = self._alter_table_ddl(td, warnings)
                if table_lines:
                    lines.extend(table_lines)
                    lines.append("")

        # 3. Drop removed tables (reverse FK order)
        removed = [td for td in diff.table_diffs if td.diff_type == "removed"]
        for td in reversed(removed):
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

    def _alter_table_ddl(self, td: TableDiff, warnings: List[str]) -> List[str]:
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
            return self._sqlite_recreate(td, warnings)

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

    def _sqlite_recreate(self, td: TableDiff, warnings: List[str]) -> List[str]:
        """Generate SQLite table recreate pattern for unsupported ALTER COLUMN."""
        warnings.append(
            f"SQLite table recreate used for '{td.table_name}' "
            "(SQLite does not support ALTER COLUMN)"
        )

        lines = [
            f"-- SQLite: recreate table '{td.table_name}' to apply column changes",
            f"-- (SQLite does not support ALTER COLUMN)",
        ]

        # We need both source and target column info
        # Build target column list from diffs
        target_cols = []
        source_col_names = []
        select_exprs = []

        for cd in td.column_diffs:
            if cd.diff_type == "removed":
                # Skip removed columns in new table
                continue
            elif cd.diff_type == "added" and cd.target_state:
                col = cd.target_state
                target_cols.append(self._column_def(col))
                default_val = self._format_default(col.get("default")) if col.get("default") is not None else "NULL"
                select_exprs.append(f"{default_val} AS {self._quote(cd.column_name)}")
            elif cd.target_state:
                col = cd.target_state
                target_cols.append(self._column_def(col))
                source_col_names.append(cd.column_name)
                if cd.diff_type == "type_changed":
                    select_exprs.append(
                        f"CAST({self._quote(cd.column_name)} AS {col.get('type', 'TEXT')})"
                    )
                else:
                    select_exprs.append(self._quote(cd.column_name))

        new_table = f"{td.table_name}__new"
        col_defs = ",\n    ".join(target_cols)
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

    def _generate_down(self, diff: SchemaDiff, warnings: List[str]) -> List[str]:
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
        for td in diff.table_diffs:
            if td.diff_type == "modified":
                for cd in td.column_diffs:
                    if cd.diff_type == "added":
                        # Reverse: drop the column that was added
                        if self.dialect != DatabaseDialect.SQLITE:
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
                lines.append(f"-- Verify table '{td.table_name}' was dropped")
                if self.dialect == DatabaseDialect.POSTGRESQL:
                    lines.append(
                        f"SELECT NOT EXISTS ("
                        f"SELECT 1 FROM information_schema.tables "
                        f"WHERE table_name = '{td.table_name}'"
                        f") AS table_dropped;"
                    )
                elif self.dialect == DatabaseDialect.MYSQL:
                    lines.append(
                        f"SELECT NOT EXISTS ("
                        f"SELECT 1 FROM information_schema.tables "
                        f"WHERE table_name = '{td.table_name}'"
                        f") AS table_dropped;"
                    )
                elif self.dialect == DatabaseDialect.SQLITE:
                    lines.append(
                        f"SELECT COUNT(*) = 0 AS table_dropped "
                        f"FROM sqlite_master WHERE type='table' AND name='{td.table_name}';"
                    )
                lines.append("")

            elif td.diff_type == "modified":
                lines.append(f"-- Verify modifications to '{td.table_name}'")
                lines.append(f"SELECT COUNT(*) AS row_count FROM {self._quote(td.table_name)};")

                # Check NOT NULL constraints hold
                for cd in td.column_diffs:
                    if cd.diff_type == "nullability_changed" and cd.target_state:
                        if not cd.target_state.get("nullable", True):
                            lines.append(
                                f"SELECT COUNT(*) AS null_violations "
                                f"FROM {self._quote(td.table_name)} "
                                f"WHERE {self._quote(cd.column_name)} IS NULL;"
                            )
                lines.append("")

        return lines

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _quote(self, identifier: str) -> str:
        """Quote an identifier based on dialect."""
        if self.dialect == DatabaseDialect.MYSQL:
            return f"`{identifier}`"
        return f'"{identifier}"'

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
    project, target_dialect: str, enrich_with_llm: bool = True, db=None,
) -> GeneratedScripts:
    """High-level function to generate scripts for a project."""
    diff_data = project.diff_snapshot
    if not diff_data:
        raise ValueError("Project has no diff snapshot")

    # Reconstruct SchemaDiff
    from src.migration.schema_comparator import SchemaDiff, TableDiff, ColumnDiff, ConstraintDiff

    table_diffs = []
    for td_dict in diff_data.get("table_diffs", []):
        col_diffs = [ColumnDiff(**cd) for cd in td_dict.get("column_diffs", [])]
        constraint_diffs = [ConstraintDiff(**cd) for cd in td_dict.get("constraint_diffs", [])]
        table_diffs.append(TableDiff(
            table_name=td_dict["table_name"],
            diff_type=td_dict["diff_type"],
            column_diffs=col_diffs,
            constraint_diffs=constraint_diffs,
        ))

    diff = SchemaDiff(
        source_connection_id=diff_data.get("source_connection_id"),
        target_connection_id=diff_data.get("target_connection_id"),
        table_diffs=table_diffs,
        total_breaking_changes=diff_data.get("total_breaking_changes", 0),
        total_safe_changes=diff_data.get("total_safe_changes", 0),
        overall_risk=diff_data.get("overall_risk", "low"),
        diff_summary=diff_data.get("diff_summary", ""),
    )

    dialect = get_dialect_for_database_type(target_dialect)
    generator = ScriptGenerator(dialect)
    result = generator.generate(diff, project_id=project.id)

    return result
