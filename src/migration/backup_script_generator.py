"""Backup & Restore Script Generator (Phase 20 - Single Database)

Generates backup.sql (full schema DDL), restore.sql (DROP TABLE cleanup),
and verify.sql (integrity checks) for a single database connection.

No DDL is executed — scripts are returned as strings for download/copy.
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.llm.dialect_registry import DatabaseDialect

logger = logging.getLogger(__name__)


@dataclass
class BackupScripts:
    """Container for generated backup/restore scripts."""
    connection_id: int = 0
    connection_name: str = ""
    dialect: str = ""
    backup_sql: str = ""
    restore_sql: str = ""
    verify_sql: str = ""
    table_count: int = 0
    warnings: List[str] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "connection_name": self.connection_name,
            "dialect": self.dialect,
            "backup_sql": self.backup_sql,
            "restore_sql": self.restore_sql,
            "verify_sql": self.verify_sql,
            "table_count": self.table_count,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
        }


class BackupScriptGenerator:
    """Generate backup/restore DDL scripts from a full schema dict.

    Unlike the migration ScriptGenerator which works from a SchemaDiff,
    this generator works directly from a complete schema snapshot and
    produces self-contained DDL for a single database.
    """

    def __init__(self, dialect: DatabaseDialect):
        self.dialect = dialect

    def generate(
        self,
        schema: Dict[str, Any],
        connection_id: int = 0,
        connection_name: str = "",
    ) -> BackupScripts:
        """Generate backup, restore, and verify scripts from a schema dict."""
        warnings: List[str] = []
        tables = schema.get("tables", {})

        if not tables:
            warnings.append("No tables found in schema — backup scripts are empty")

        # Sort tables: parents before children for CREATE (children first for DROP)
        ordered = self._sort_tables_create_order(tables)

        backup_lines = self._generate_backup(ordered, tables, warnings, connection_name)
        restore_lines = self._generate_restore(list(reversed(ordered)), tables)
        verify_lines = self._generate_verify(ordered, tables)

        return BackupScripts(
            connection_id=connection_id,
            connection_name=connection_name,
            dialect=self.dialect.value,
            backup_sql="\n".join(backup_lines),
            restore_sql="\n".join(restore_lines),
            verify_sql="\n".join(verify_lines),
            table_count=len(tables),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Table ordering
    # ------------------------------------------------------------------

    def _sort_tables_create_order(self, tables: Dict[str, Any]) -> List[str]:
        """Return table names sorted so FK parents come before FK children.

        Uses Kahn's topological sort. Circular FK dependencies (rare) are
        appended at the end in alphabetical order.
        """
        in_degree: Dict[str, int] = {t: 0 for t in tables}
        dependents: Dict[str, set] = defaultdict(set)  # parent → children

        for table_name, table_info in tables.items():
            for fk in table_info.get("foreign_keys", []):
                parent = fk.get("referred_table", "")
                if parent in tables and parent != table_name:
                    if table_name not in dependents[parent]:
                        dependents[parent].add(table_name)
                        in_degree[table_name] = in_degree.get(table_name, 0) + 1

        queue = deque(sorted(t for t in in_degree if in_degree[t] == 0))
        result: List[str] = []

        while queue:
            name = queue.popleft()
            result.append(name)
            for child in sorted(dependents.get(name, [])):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # Append any remaining (circular FK dependencies)
        seen = set(result)
        result.extend(sorted(t for t in tables if t not in seen))
        return result

    # ------------------------------------------------------------------
    # backup.sql
    # ------------------------------------------------------------------

    def _generate_backup(
        self,
        ordered_tables: List[str],
        tables: Dict[str, Any],
        warnings: List[str],
        connection_name: str,
    ) -> List[str]:
        """Generate the full schema DDL backup script."""
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            f"-- Backup: backup.sql",
            f"-- Generated: {now}",
            f"-- Database: {connection_name}",
            f"-- Dialect: {self.dialect.value}",
            f"-- Tables: {len(tables)}",
            f"--",
            f"-- Run this script on an empty database to recreate the full schema.",
            f"-- Data is NOT included — this is a schema-only backup.",
            "",
        ]

        if self.dialect == DatabaseDialect.MYSQL:
            lines += ["SET FOREIGN_KEY_CHECKS = 0;", ""]
        elif self.dialect == DatabaseDialect.MSSQL:
            lines += [
                "-- Disable FK constraints during schema restore",
                "EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';",
                "",
            ]
        elif self.dialect == DatabaseDialect.ORACLE:
            lines += [
                "-- Oracle: run on a fresh schema (no IF NOT EXISTS support without PL/SQL)",
                "",
            ]

        for table_name in ordered_tables:
            table_info = tables.get(table_name, {})
            lines.extend(self._create_table_ddl(table_name, table_info, warnings))
            lines.append("")
            index_lines = self._create_index_ddl(table_name, table_info)
            if index_lines:
                lines.extend(index_lines)

        if self.dialect == DatabaseDialect.MYSQL:
            lines += ["SET FOREIGN_KEY_CHECKS = 1;", ""]
        elif self.dialect == DatabaseDialect.MSSQL:
            lines += [
                "",
                "-- Re-enable FK constraints",
                "EXEC sp_MSforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT ALL';",
                "",
            ]

        return lines

    def _create_table_ddl(
        self,
        table_name: str,
        table_info: Dict[str, Any],
        warnings: List[str],
    ) -> List[str]:
        """Generate CREATE TABLE DDL for one table."""
        columns = table_info.get("columns", [])
        if not columns:
            warnings.append(f"Table '{table_name}' has no columns — skipped")
            return [f"-- WARNING: table '{table_name}' has no column info, skipped"]

        col_defs = [self._column_def(col) for col in columns if col.get("name")]

        pks = table_info.get("primary_keys", [])
        if pks:
            pk_cols = ", ".join(self._quote(c) for c in pks)
            col_defs.append(f"PRIMARY KEY ({pk_cols})")

        for fk in table_info.get("foreign_keys", []):
            fk_col = self._quote(fk["column"])
            ref_table = self._quote(fk["referred_table"])
            ref_col = self._quote(fk["referred_column"])
            col_defs.append(f"FOREIGN KEY ({fk_col}) REFERENCES {ref_table} ({ref_col})")

        body = ",\n".join(f"    {d}" for d in col_defs)

        if self.dialect == DatabaseDialect.ORACLE:
            # Oracle < 23c has no CREATE TABLE IF NOT EXISTS
            return [
                f"CREATE TABLE {self._quote(table_name)} (",
                body,
                ");",
            ]
        elif self.dialect == DatabaseDialect.MSSQL:
            safe = self._escape_literal(table_name)
            return [
                f"IF OBJECT_ID(N'{safe}', N'U') IS NULL",
                f"CREATE TABLE {self._quote(table_name)} (",
                body,
                ");",
            ]
        else:
            return [
                f"CREATE TABLE IF NOT EXISTS {self._quote(table_name)} (",
                body,
                ");",
            ]

    def _create_index_ddl(
        self,
        table_name: str,
        table_info: Dict[str, Any],
    ) -> List[str]:
        """Generate CREATE INDEX statements for a table (skipping PK-only indexes)."""
        lines = []
        pk_set = set(table_info.get("primary_keys", []))

        for idx in table_info.get("indexes", []):
            cols = idx.get("columns", [])
            if not cols or set(cols) == pk_set:
                continue
            unique = idx.get("unique", False)
            prefix = "UNIQUE " if unique else ""
            col_list = ", ".join(self._quote(c) for c in cols)
            idx_name = f"idx_{table_name}_{'_'.join(cols)}"

            if self.dialect == DatabaseDialect.ORACLE:
                lines += [
                    f"CREATE {prefix}INDEX {self._quote(idx_name)}",
                    f"    ON {self._quote(table_name)} ({col_list});",
                    "",
                ]
            elif self.dialect == DatabaseDialect.MSSQL:
                safe_idx = self._escape_literal(idx_name)
                lines += [
                    f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = '{safe_idx}')",
                    f"    CREATE {prefix}INDEX {self._quote(idx_name)} ON {self._quote(table_name)} ({col_list});",
                    "",
                ]
            else:
                lines += [
                    f"CREATE {prefix}INDEX IF NOT EXISTS {self._quote(idx_name)}",
                    f"    ON {self._quote(table_name)} ({col_list});",
                    "",
                ]

        return lines

    # ------------------------------------------------------------------
    # restore.sql
    # ------------------------------------------------------------------

    def _generate_restore(
        self,
        reverse_ordered: List[str],
        tables: Dict[str, Any],
    ) -> List[str]:
        """Generate DROP TABLE script for pre-restore cleanup (children first)."""
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            f"-- Restore: restore.sql",
            f"-- Generated: {now}",
            f"-- Dialect: {self.dialect.value}",
            f"--",
            f"-- Run this script BEFORE applying backup.sql to wipe the existing schema.",
            f"-- WARNING: All data in the listed tables will be permanently deleted.",
            "",
        ]

        if self.dialect == DatabaseDialect.MYSQL:
            lines += ["SET FOREIGN_KEY_CHECKS = 0;", ""]
        elif self.dialect == DatabaseDialect.MSSQL:
            lines += [
                "EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';",
                "",
            ]
        elif self.dialect == DatabaseDialect.ORACLE:
            lines += [
                "BEGIN",
                "  FOR c IN (SELECT owner, constraint_name, table_name FROM all_constraints",
                "            WHERE constraint_type = 'R' AND owner = USER) LOOP",
                "    EXECUTE IMMEDIATE 'ALTER TABLE \"' || c.table_name || '\" DISABLE CONSTRAINT \"' || c.constraint_name || '\"';",
                "  END LOOP;",
                "END;",
                "/",
                "",
            ]

        for table_name in reverse_ordered:
            if self.dialect == DatabaseDialect.ORACLE:
                lines += [
                    f"BEGIN",
                    f"  EXECUTE IMMEDIATE 'DROP TABLE {self._quote(table_name)} CASCADE CONSTRAINTS';",
                    f"EXCEPTION WHEN OTHERS THEN",
                    f"  IF SQLCODE != -942 THEN RAISE; END IF; -- ORA-00942: table does not exist",
                    f"END;",
                    f"/",
                    "",
                ]
            elif self.dialect == DatabaseDialect.MSSQL:
                safe = self._escape_literal(table_name)
                lines += [
                    f"IF OBJECT_ID(N'{safe}', N'U') IS NOT NULL DROP TABLE {self._quote(table_name)};",
                    "",
                ]
            else:
                lines += [f"DROP TABLE IF EXISTS {self._quote(table_name)};", ""]

        if self.dialect == DatabaseDialect.MYSQL:
            lines += ["SET FOREIGN_KEY_CHECKS = 1;", ""]

        return lines

    # ------------------------------------------------------------------
    # verify.sql
    # ------------------------------------------------------------------

    def _generate_verify(
        self,
        ordered_tables: List[str],
        tables: Dict[str, Any],
    ) -> List[str]:
        """Generate verification queries to confirm the backup schema is intact."""
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            f"-- Backup: verify.sql",
            f"-- Generated: {now}",
            f"-- Dialect: {self.dialect.value}",
            f"--",
            f"-- Run after applying backup.sql to verify all tables and columns exist.",
            "",
        ]

        for table_name in ordered_tables:
            table_info = tables.get(table_name, {})
            expected_cols = len([c for c in table_info.get("columns", []) if c.get("name")])
            safe = self._escape_literal(table_name)

            lines.append(f"-- Verify table '{table_name}' ({expected_cols} columns)")

            if self.dialect in (DatabaseDialect.POSTGRESQL, DatabaseDialect.MYSQL):
                lines.append(
                    f"SELECT COUNT(*) AS col_count FROM information_schema.columns"
                    f" WHERE table_name = '{safe}'; -- expected: {expected_cols}"
                )
            elif self.dialect == DatabaseDialect.SQLITE:
                lines.append(
                    f"SELECT COUNT(*) AS col_count FROM pragma_table_info('{safe}');"
                    f" -- expected: {expected_cols}"
                )
            elif self.dialect == DatabaseDialect.MSSQL:
                lines.append(
                    f"SELECT COUNT(*) AS col_count FROM information_schema.columns"
                    f" WHERE table_name = '{safe}'; -- expected: {expected_cols}"
                )
            elif self.dialect == DatabaseDialect.ORACLE:
                lines.append(
                    f"SELECT COUNT(*) AS col_count FROM user_tab_columns"
                    f" WHERE table_name = UPPER('{safe}'); -- expected: {expected_cols}"
                )
            else:
                lines.append(f"SELECT COUNT(*) AS row_count FROM {self._quote(table_name)};")

            lines.append("")

        return lines

    # ------------------------------------------------------------------
    # Helpers (mirrored from ScriptGenerator for consistency)
    # ------------------------------------------------------------------

    def _quote(self, identifier: str) -> str:
        if self.dialect == DatabaseDialect.MYSQL:
            return f"`{identifier}`"
        if self.dialect == DatabaseDialect.MSSQL:
            return f"[{identifier}]"
        return f'"{identifier}"'

    @staticmethod
    def _escape_literal(value: str) -> str:
        return value.replace("'", "''")

    def _column_def(self, col: Dict[str, Any]) -> str:
        name = self._quote(col.get("name", "unknown"))
        col_type = col.get("type", "TEXT")
        nullable = "" if col.get("nullable", True) else " NOT NULL"
        default = ""
        if col.get("default") is not None:
            default = f" DEFAULT {self._format_default(col['default'])}"
        return f"{name} {col_type}{nullable}{default}"

    def _format_default(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        return f"'{self._escape_literal(str(value))}'"
