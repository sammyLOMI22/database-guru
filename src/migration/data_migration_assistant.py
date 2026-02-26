"""Data Migration Assistant (Phase 20.4)

Generates INSERT INTO ... SELECT queries for data migration between
source and target schemas. Includes column mapping, batching, and
validation queries.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.migration.schema_comparator import (
    SchemaDiff, TableDiff, ColumnDiff,
    _normalize_type, _extract_base_type,
)
from src.llm.dialect_registry import DatabaseDialect, get_dialect_for_database_type
from src.migration.sql_helpers import quote_identifier

logger = logging.getLogger(__name__)


@dataclass
class ColumnMapping:
    """Mapping between a source column and target column."""
    source_col: Optional[str] = None  # None if new column with default
    target_col: str = ""
    transform_expression: str = ""  # e.g. "CAST(col AS TEXT)", "'default'"
    requires_llm: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TableDataMigration:
    """Data migration plan for a single table."""
    source_table: str = ""
    target_table: str = ""
    column_mappings: List[ColumnMapping] = field(default_factory=list)
    insert_sql: str = ""
    batched_insert_sql: str = ""
    count_verify_sql: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_table": self.source_table,
            "target_table": self.target_table,
            "column_mappings": [m.to_dict() for m in self.column_mappings],
            "insert_sql": self.insert_sql,
            "batched_insert_sql": self.batched_insert_sql,
            "count_verify_sql": self.count_verify_sql,
            "warnings": self.warnings,
        }


@dataclass
class DataMigrationPlan:
    """Complete data migration plan across all tables."""
    project_id: int = 0
    table_migrations: List[TableDataMigration] = field(default_factory=list)
    batch_size: int = 1000
    recommended_order: List[str] = field(default_factory=list)
    total_tables_with_data: int = 0
    llm_used: bool = False
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "table_migrations": [t.to_dict() for t in self.table_migrations],
            "batch_size": self.batch_size,
            "recommended_order": self.recommended_order,
            "total_tables_with_data": self.total_tables_with_data,
            "llm_used": self.llm_used,
            "generated_at": self.generated_at,
        }


class DataMigrationAssistant:
    """Generates INSERT INTO SELECT queries for data migration."""

    def __init__(self, dialect: DatabaseDialect, batch_size: int = 1000):
        self.dialect = dialect
        self.batch_size = batch_size

    def generate_plan(
        self,
        diff: SchemaDiff,
        source_schema: Optional[Dict[str, Any]] = None,
        target_schema: Optional[Dict[str, Any]] = None,
        project_id: int = 0,
    ) -> DataMigrationPlan:
        """Generate a data migration plan from a schema diff.

        Only modified tables need data migration.
        Added tables have no source data; removed tables have no target.
        """
        plan = DataMigrationPlan(
            project_id=project_id,
            batch_size=self.batch_size,
        )

        # Get source/target column info from schemas if available
        source_tables = (source_schema or {}).get("tables", {})
        target_tables = (target_schema or {}).get("tables", {})

        for td in diff.table_diffs:
            if td.diff_type != "modified":
                continue

            # Build column mappings from the diff
            src_cols = {c["name"]: c for c in source_tables.get(td.table_name, {}).get("columns", [])}
            tgt_cols = {c["name"]: c for c in target_tables.get(td.table_name, {}).get("columns", [])}

            # If we don't have full schema info, derive from diffs
            if not src_cols and not tgt_cols:
                migration = self._generate_from_diffs(td)
            else:
                migration = self._generate_from_schemas(td, src_cols, tgt_cols)

            if migration.column_mappings:
                plan.table_migrations.append(migration)

        plan.total_tables_with_data = len(plan.table_migrations)
        plan.recommended_order = [tm.source_table for tm in plan.table_migrations]

        return plan

    def _generate_from_schemas(
        self,
        td: TableDiff,
        src_cols: Dict[str, Dict],
        tgt_cols: Dict[str, Dict],
    ) -> TableDataMigration:
        """Generate migration with full schema info available."""
        mappings: List[ColumnMapping] = []
        warnings: List[str] = []

        for tgt_name, tgt_col in tgt_cols.items():
            if tgt_name in src_cols:
                src_col = src_cols[tgt_name]
                src_type = _normalize_type(src_col.get("type", ""))
                tgt_type = _normalize_type(tgt_col.get("type", ""))

                if src_type == tgt_type:
                    # Direct mapping
                    mappings.append(ColumnMapping(
                        source_col=tgt_name,
                        target_col=tgt_name,
                        transform_expression=self._quote(tgt_name),
                    ))
                else:
                    # Type changed — add CAST
                    raw_tgt_type = tgt_col.get("type", "TEXT")
                    mappings.append(ColumnMapping(
                        source_col=tgt_name,
                        target_col=tgt_name,
                        transform_expression=f"CAST({self._quote(tgt_name)} AS {raw_tgt_type})",
                    ))
            else:
                # New column — use default or NULL
                default = tgt_col.get("default")
                nullable = tgt_col.get("nullable", True)
                if default is not None:
                    expr = self._format_default(default)
                elif nullable:
                    expr = "NULL"
                else:
                    expr = "NULL"
                    warnings.append(
                        f"Column '{tgt_name}' is NOT NULL with no default — "
                        f"using NULL placeholder (will fail if constraint is enforced)"
                    )

                mappings.append(ColumnMapping(
                    source_col=None,
                    target_col=tgt_name,
                    transform_expression=f"{expr} AS {self._quote(tgt_name)}",
                    requires_llm=default is None and not nullable,
                ))

        return self._build_table_migration(td.table_name, mappings, warnings)

    def _generate_from_diffs(self, td: TableDiff) -> TableDataMigration:
        """Generate migration from diff info only (no full schema)."""
        mappings: List[ColumnMapping] = []
        warnings: List[str] = []

        # Track columns that changed or were added
        changed_cols = set()
        for cd in td.column_diffs:
            changed_cols.add(cd.column_name)

            if cd.diff_type == "added" and cd.target_state:
                col = cd.target_state
                default = col.get("default")
                nullable = col.get("nullable", True)
                if default is not None:
                    expr = self._format_default(default)
                elif nullable:
                    expr = "NULL"
                else:
                    expr = "NULL"
                    warnings.append(f"New NOT NULL column '{cd.column_name}' has no default")

                mappings.append(ColumnMapping(
                    source_col=None,
                    target_col=cd.column_name,
                    transform_expression=f"{expr} AS {self._quote(cd.column_name)}",
                ))

            elif cd.diff_type == "removed":
                # Dropped column — skip it
                continue

            elif cd.diff_type == "type_changed" and cd.target_state:
                tgt_type = cd.target_state.get("type", "TEXT")
                mappings.append(ColumnMapping(
                    source_col=cd.column_name,
                    target_col=cd.column_name,
                    transform_expression=f"CAST({self._quote(cd.column_name)} AS {tgt_type})",
                ))

            else:
                # Unchanged or minor change — direct pass-through
                mappings.append(ColumnMapping(
                    source_col=cd.column_name,
                    target_col=cd.column_name,
                    transform_expression=self._quote(cd.column_name),
                ))

        return self._build_table_migration(td.table_name, mappings, warnings)

    def _build_table_migration(
        self,
        table_name: str,
        mappings: List[ColumnMapping],
        warnings: List[str],
    ) -> TableDataMigration:
        """Build a TableDataMigration with SQL from mappings.

        Uses a staging table pattern: SELECT from the original table and
        INSERT INTO a staging table ({table}__new) to avoid self-referencing
        INSERT issues. The caller is expected to rename after verification.
        """
        if not mappings:
            return TableDataMigration(source_table=table_name, target_table=f"{table_name}__new")

        target_cols = ", ".join(self._quote(m.target_col) for m in mappings)
        select_exprs = ", ".join(m.transform_expression for m in mappings)

        staging_name = f"{table_name}__new"
        q_source = self._quote(table_name)
        q_target = self._quote(staging_name)
        insert_sql = f"INSERT INTO {q_target} ({target_cols})\nSELECT {select_exprs}\nFROM {q_source};"

        # Batched version — this is batch 0 (OFFSET 0).
        # To migrate all rows, run this statement repeatedly with
        # OFFSET 0, {batch_size}, {batch_size*2}, ... until 0 rows are inserted.
        batch_header = (
            f"-- Batch template: run with OFFSET 0, {self.batch_size}, "
            f"{self.batch_size * 2}, ... until 0 rows inserted.\n"
        )
        if self.dialect == DatabaseDialect.POSTGRESQL:
            batched = (
                f"{batch_header}"
                f"INSERT INTO {q_target} ({target_cols})\n"
                f"SELECT {select_exprs}\n"
                f"FROM {q_source}\n"
                f"ORDER BY ctid\n"
                f"LIMIT {self.batch_size} OFFSET 0;"
            )
        elif self.dialect == DatabaseDialect.MSSQL:
            batched = (
                f"{batch_header}"
                f"INSERT INTO {q_target} ({target_cols})\n"
                f"SELECT {select_exprs}\n"
                f"FROM {q_source}\n"
                f"ORDER BY (SELECT NULL)\n"
                f"OFFSET 0 ROWS FETCH NEXT {self.batch_size} ROWS ONLY;"
            )
        elif self.dialect == DatabaseDialect.ORACLE:
            batched = (
                f"{batch_header}"
                f"INSERT INTO {q_target} ({target_cols})\n"
                f"SELECT {select_exprs}\n"
                f"FROM {q_source}\n"
                f"ORDER BY ROWID\n"
                f"OFFSET 0 ROWS FETCH NEXT {self.batch_size} ROWS ONLY;"
            )
        else:
            # MySQL, SQLite, DuckDB
            batched = (
                f"{batch_header}"
                f"INSERT INTO {q_target} ({target_cols})\n"
                f"SELECT {select_exprs}\n"
                f"FROM {q_source}\n"
                f"LIMIT {self.batch_size} OFFSET 0;"
            )

        count_verify = (
            f"-- Verify row count matches\n"
            f"SELECT\n"
            f"  (SELECT COUNT(*) FROM {q_source}) AS source_count,\n"
            f"  (SELECT COUNT(*) FROM {q_target}) AS target_count;"
        )

        return TableDataMigration(
            source_table=table_name,
            target_table=staging_name,
            column_mappings=mappings,
            insert_sql=insert_sql,
            batched_insert_sql=batched,
            count_verify_sql=count_verify,
            warnings=warnings,
        )

    def _quote(self, identifier: str) -> str:
        return quote_identifier(identifier, self.dialect)

    def _format_default(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        return f"'{str(value).replace(chr(39), chr(39) + chr(39))}'"


async def generate_data_migration_plan(
    project,
    batch_size: int = 1000,
    db=None,
    source_schema: Optional[Dict[str, Any]] = None,
    target_schema: Optional[Dict[str, Any]] = None,
) -> DataMigrationPlan:
    """High-level function to generate a data migration plan."""
    diff_data = project.diff_snapshot
    if not diff_data:
        raise ValueError("Project has no diff snapshot")

    from src.migration.schema_comparator import SchemaDiff
    diff = SchemaDiff.from_dict(diff_data)

    dialect_str = project.target_dialect or "postgresql"
    dialect = get_dialect_for_database_type(dialect_str)

    assistant = DataMigrationAssistant(dialect=dialect, batch_size=batch_size)
    return assistant.generate_plan(
        diff,
        source_schema=source_schema,
        target_schema=target_schema,
        project_id=project.id,
    )
