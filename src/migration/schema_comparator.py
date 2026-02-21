"""Schema Diff Engine for Database Migration Toolkit (Phase 20.1)

Compares two database schemas from SchemaCache output and produces a structured diff
with risk classification. Pure deterministic logic — no LLM calls.

Schema dict format (from SchemaCache.get_schema()):
    {
        "tables": {
            "table_name": {
                "columns": [{"name": str, "type": str, "nullable": bool, "default": Any, "max_length": int|None}],
                "primary_keys": [str],
                "foreign_keys": [{"column": str, "referred_table": str, "referred_column": str}],
                "indexes": [{"name": str, "columns": [str], "unique": bool}]
            }
        },
        "relationships": [...],
        "summary": {"table_count": int, "total_columns": int}
    }
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# Type synonyms for normalization (lowercase)
_TYPE_SYNONYMS = {
    # PostgreSQL aliases
    "character varying": "varchar",
    "char varying": "varchar",
    "int4": "integer",
    "int8": "bigint",
    "int2": "smallint",
    "float8": "double precision",
    "float4": "real",
    "bool": "boolean",
    "timestamptz": "timestamp with time zone",
    "timestamp without time zone": "timestamp",
    "serial": "integer",
    "bigserial": "bigint",
    "smallserial": "smallint",
    "text": "text",
    # Oracle aliases
    "varchar2": "varchar",
    "nvarchar2": "varchar",
    "nchar": "char",
    "clob": "text",
    "nclob": "text",
    "number": "numeric",
    "binary_float": "real",
    "binary_double": "double precision",
    "long": "text",
    "long raw": "bytea",
    "raw": "bytea",
    "blob": "bytea",
    "xmltype": "text",
    # SQL Server (MSSQL) aliases
    "nvarchar": "varchar",
    "ntext": "text",
    "bit": "boolean",
    "datetime": "timestamp",
    "datetime2": "timestamp",
    "smalldatetime": "timestamp",
    "datetimeoffset": "timestamp with time zone",
    "uniqueidentifier": "uuid",
    "money": "numeric",
    "smallmoney": "numeric",
    "tinyint": "smallint",
    "image": "bytea",
    "varbinary": "bytea",
    "binary": "bytea",
}

# Types ordered by "width" for narrowing detection
_TYPE_WIDTH = {
    "boolean": 1,
    "smallint": 2,
    "integer": 3,
    "bigint": 4,
    "real": 5,
    "double precision": 6,
    "numeric": 7,
    "text": 100,
}


def _normalize_type(type_str: str) -> str:
    """Normalize a SQL type string for comparison.

    Handles synonym resolution, case normalization, and whitespace.
    Preserves length params (e.g., varchar(255)) for precision comparison.
    """
    if not type_str:
        return ""
    t = type_str.strip().lower()
    # Extract base type and params
    base = t
    params = ""
    if "(" in t:
        idx = t.index("(")
        base = t[:idx].strip()
        params = t[idx:]

    # Resolve synonyms
    base = _TYPE_SYNONYMS.get(base, base)

    return f"{base}{params}" if params else base


def _extract_base_type(normalized: str) -> str:
    """Extract base type without parameters."""
    if "(" in normalized:
        return normalized[:normalized.index("(")].strip()
    return normalized


def _extract_length(normalized: str) -> Optional[int]:
    """Extract length parameter from a type like varchar(255)."""
    if "(" in normalized and ")" in normalized:
        try:
            inner = normalized[normalized.index("(") + 1:normalized.index(")")]
            # Handle precision,scale like numeric(10,2)
            parts = inner.split(",")
            return int(parts[0].strip())
        except (ValueError, IndexError):
            return None
    return None


def _is_type_narrowing(source_type: str, target_type: str) -> bool:
    """Detect if a type change narrows the data range (potential data loss)."""
    src_base = _extract_base_type(source_type)
    tgt_base = _extract_base_type(target_type)

    # Same base type — check length narrowing
    if src_base == tgt_base:
        src_len = _extract_length(source_type)
        tgt_len = _extract_length(target_type)
        if src_len is not None and tgt_len is not None:
            return tgt_len < src_len
        return False

    # Different base types — check width ordering
    src_width = _TYPE_WIDTH.get(src_base)
    tgt_width = _TYPE_WIDTH.get(tgt_base)
    if src_width is not None and tgt_width is not None:
        return tgt_width < src_width

    # Unknown types — assume potentially narrowing to be safe
    return True


@dataclass
class ColumnDiff:
    """Represents a single column-level change."""
    table_name: str
    column_name: str
    diff_type: str  # "added" | "removed" | "type_changed" | "nullability_changed" | "default_changed"
    source_state: Optional[Dict[str, Any]] = None
    target_state: Optional[Dict[str, Any]] = None
    is_breaking: bool = False
    risk_level: str = "low"  # "low" | "medium" | "high" | "critical"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConstraintDiff:
    """Represents a PK, FK, or index change."""
    table_name: str
    constraint_type: str  # "primary_key" | "foreign_key" | "index"
    diff_type: str  # "added" | "removed" | "modified"
    source_state: Optional[Any] = None
    target_state: Optional[Any] = None
    risk_level: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TableDiff:
    """Represents all changes to a single table."""
    table_name: str
    diff_type: str  # "added" | "removed" | "modified"
    column_diffs: List[ColumnDiff] = field(default_factory=list)
    constraint_diffs: List[ConstraintDiff] = field(default_factory=list)
    risk_level: str = "low"

    def __post_init__(self):
        self._update_risk()

    def _update_risk(self):
        if self.diff_type == "removed":
            self.risk_level = "critical"
        elif self.diff_type == "added":
            self.risk_level = "low"
        else:
            # Modified — max risk of all child diffs
            all_risks = (
                [d.risk_level for d in self.column_diffs]
                + [d.risk_level for d in self.constraint_diffs]
            )
            self.risk_level = _max_risk(all_risks) if all_risks else "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "diff_type": self.diff_type,
            "column_diffs": [d.to_dict() for d in self.column_diffs],
            "constraint_diffs": [d.to_dict() for d in self.constraint_diffs],
            "risk_level": self.risk_level,
        }


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _max_risk(risks: List[str]) -> str:
    if not risks:
        return "low"
    return max(risks, key=lambda r: _RISK_ORDER.get(r, 0))


@dataclass
class SchemaDiff:
    """Complete diff between two schemas."""
    source_connection_id: Optional[int] = None
    target_connection_id: Optional[int] = None
    source_fingerprint: str = ""
    target_fingerprint: str = ""
    table_diffs: List[TableDiff] = field(default_factory=list)
    total_breaking_changes: int = 0
    total_safe_changes: int = 0
    overall_risk: str = "low"
    diff_summary: str = ""
    compared_at: str = ""

    def __post_init__(self):
        if not self.compared_at:
            self.compared_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_connection_id": self.source_connection_id,
            "target_connection_id": self.target_connection_id,
            "source_fingerprint": self.source_fingerprint,
            "target_fingerprint": self.target_fingerprint,
            "table_diffs": [t.to_dict() for t in self.table_diffs],
            "total_breaking_changes": self.total_breaking_changes,
            "total_safe_changes": self.total_safe_changes,
            "overall_risk": self.overall_risk,
            "diff_summary": self.diff_summary,
            "compared_at": self.compared_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaDiff":
        """Reconstruct a SchemaDiff from a serialized dict (e.g. project.diff_snapshot)."""
        table_diffs = []
        for td_dict in data.get("table_diffs", []):
            col_diffs = [ColumnDiff(**cd) for cd in td_dict.get("column_diffs", [])]
            constraint_diffs = [ConstraintDiff(**cd) for cd in td_dict.get("constraint_diffs", [])]
            td = TableDiff(
                table_name=td_dict["table_name"],
                diff_type=td_dict["diff_type"],
                column_diffs=col_diffs,
                constraint_diffs=constraint_diffs,
            )
            # __post_init__ recomputes risk_level from children; restore the
            # persisted value so round-trips through JSON are exact.
            if "risk_level" in td_dict:
                td.risk_level = td_dict["risk_level"]
            table_diffs.append(td)

        return cls(
            source_connection_id=data.get("source_connection_id"),
            target_connection_id=data.get("target_connection_id"),
            source_fingerprint=data.get("source_fingerprint", ""),
            target_fingerprint=data.get("target_fingerprint", ""),
            table_diffs=table_diffs,
            total_breaking_changes=data.get("total_breaking_changes", 0),
            total_safe_changes=data.get("total_safe_changes", 0),
            overall_risk=data.get("overall_risk", "low"),
            diff_summary=data.get("diff_summary", ""),
            compared_at=data.get("compared_at", ""),
        )


class SchemaComparator:
    """Compares two SchemaCache dicts and produces a SchemaDiff.

    Usage:
        comparator = SchemaComparator()
        diff = comparator.compare(source_schema, target_schema)
    """

    def compare(
        self,
        source_schema: Dict[str, Any],
        target_schema: Dict[str, Any],
        source_connection_id: Optional[int] = None,
        target_connection_id: Optional[int] = None,
        source_fingerprint: str = "",
        target_fingerprint: str = "",
    ) -> SchemaDiff:
        """Compare two schema dicts and return a SchemaDiff."""
        source_tables = source_schema.get("tables", {})
        target_tables = target_schema.get("tables", {})

        source_names = set(source_tables.keys())
        target_names = set(target_tables.keys())

        table_diffs: List[TableDiff] = []

        # Added tables
        for name in sorted(target_names - source_names):
            target_cols = target_tables[name].get("columns", [])
            col_diffs = [
                ColumnDiff(
                    table_name=name,
                    column_name=c.get("name", ""),
                    diff_type="added",
                    target_state=c,
                    risk_level="low",
                )
                for c in target_cols
            ]
            table_diffs.append(TableDiff(
                table_name=name, diff_type="added", column_diffs=col_diffs,
            ))

        # Removed tables
        for name in sorted(source_names - target_names):
            source_cols = source_tables[name].get("columns", [])
            col_diffs = [
                ColumnDiff(
                    table_name=name,
                    column_name=c.get("name", ""),
                    diff_type="removed",
                    source_state=c,
                    is_breaking=True,
                    risk_level="critical",
                )
                for c in source_cols
            ]
            table_diffs.append(TableDiff(
                table_name=name, diff_type="removed", column_diffs=col_diffs,
            ))

        # Modified tables
        for name in sorted(source_names & target_names):
            col_diffs = self._compare_columns(
                name, source_tables[name], target_tables[name]
            )
            constraint_diffs = self._compare_constraints(
                name, source_tables[name], target_tables[name]
            )
            if col_diffs or constraint_diffs:
                table_diffs.append(TableDiff(
                    table_name=name,
                    diff_type="modified",
                    column_diffs=col_diffs,
                    constraint_diffs=constraint_diffs,
                ))

        # Compute summary stats
        breaking = 0
        safe = 0
        for td in table_diffs:
            for cd in td.column_diffs:
                if cd.is_breaking:
                    breaking += 1
                else:
                    safe += 1
            for cd in td.constraint_diffs:
                if _RISK_ORDER.get(cd.risk_level, 0) >= 2:
                    breaking += 1
                else:
                    safe += 1

        all_risks = [td.risk_level for td in table_diffs]
        overall = _max_risk(all_risks) if all_risks else "low"

        added = sum(1 for t in table_diffs if t.diff_type == "added")
        removed = sum(1 for t in table_diffs if t.diff_type == "removed")
        modified = sum(1 for t in table_diffs if t.diff_type == "modified")

        parts = []
        if added:
            parts.append(f"{added} table{'s' if added != 1 else ''} added")
        if removed:
            parts.append(f"{removed} table{'s' if removed != 1 else ''} removed")
        if modified:
            parts.append(f"{modified} table{'s' if modified != 1 else ''} modified")
        summary = ", ".join(parts) if parts else "No differences found"

        diff = SchemaDiff(
            source_connection_id=source_connection_id,
            target_connection_id=target_connection_id,
            source_fingerprint=source_fingerprint,
            target_fingerprint=target_fingerprint,
            table_diffs=table_diffs,
            total_breaking_changes=breaking,
            total_safe_changes=safe,
            overall_risk=overall if table_diffs else "none",
            diff_summary=summary,
        )

        logger.info(f"Schema diff complete: {summary} (risk={diff.overall_risk})")
        return diff

    def _compare_columns(
        self,
        table_name: str,
        source_table: Dict[str, Any],
        target_table: Dict[str, Any],
    ) -> List[ColumnDiff]:
        """Compare columns between source and target table."""
        source_cols = {c["name"]: c for c in source_table.get("columns", [])}
        target_cols = {c["name"]: c for c in target_table.get("columns", [])}

        diffs: List[ColumnDiff] = []

        # Added columns
        for name in sorted(set(target_cols) - set(source_cols)):
            col = target_cols[name]
            nullable = col.get("nullable", True)
            has_default = col.get("default") is not None
            if not nullable and not has_default:
                risk = "medium"
            else:
                risk = "low"
            diffs.append(ColumnDiff(
                table_name=table_name,
                column_name=name,
                diff_type="added",
                target_state=col,
                risk_level=risk,
            ))

        # Removed columns
        for name in sorted(set(source_cols) - set(target_cols)):
            diffs.append(ColumnDiff(
                table_name=table_name,
                column_name=name,
                diff_type="removed",
                source_state=source_cols[name],
                is_breaking=True,
                risk_level="critical",
            ))

        # Changed columns
        for name in sorted(set(source_cols) & set(target_cols)):
            src = source_cols[name]
            tgt = target_cols[name]

            src_type = _normalize_type(src.get("type", ""))
            tgt_type = _normalize_type(tgt.get("type", ""))

            if src_type != tgt_type:
                narrowing = _is_type_narrowing(src_type, tgt_type)
                diffs.append(ColumnDiff(
                    table_name=table_name,
                    column_name=name,
                    diff_type="type_changed",
                    source_state=src,
                    target_state=tgt,
                    is_breaking=narrowing,
                    risk_level="high" if narrowing else "low",
                ))

            src_nullable = src.get("nullable", True)
            tgt_nullable = tgt.get("nullable", True)
            if src_nullable != tgt_nullable:
                # nullable → NOT NULL is risky; NOT NULL → nullable is safe
                becoming_required = src_nullable and not tgt_nullable
                diffs.append(ColumnDiff(
                    table_name=table_name,
                    column_name=name,
                    diff_type="nullability_changed",
                    source_state=src,
                    target_state=tgt,
                    is_breaking=becoming_required,
                    risk_level="high" if becoming_required else "low",
                ))

            src_default = src.get("default")
            tgt_default = tgt.get("default")
            if str(src_default) != str(tgt_default):
                diffs.append(ColumnDiff(
                    table_name=table_name,
                    column_name=name,
                    diff_type="default_changed",
                    source_state=src,
                    target_state=tgt,
                    risk_level="low",
                ))

        return diffs

    def _compare_constraints(
        self,
        table_name: str,
        source_table: Dict[str, Any],
        target_table: Dict[str, Any],
    ) -> List[ConstraintDiff]:
        """Compare PKs, FKs, and indexes between source and target."""
        diffs: List[ConstraintDiff] = []

        # Primary keys
        src_pks = sorted(source_table.get("primary_keys", []))
        tgt_pks = sorted(target_table.get("primary_keys", []))
        if src_pks != tgt_pks:
            diffs.append(ConstraintDiff(
                table_name=table_name,
                constraint_type="primary_key",
                diff_type="modified",
                source_state=src_pks,
                target_state=tgt_pks,
                risk_level="critical",
            ))

        # Foreign keys
        src_fks = self._fk_set(source_table.get("foreign_keys", []))
        tgt_fks = self._fk_set(target_table.get("foreign_keys", []))
        for fk in sorted(tgt_fks - src_fks):
            diffs.append(ConstraintDiff(
                table_name=table_name,
                constraint_type="foreign_key",
                diff_type="added",
                target_state=fk,
                risk_level="medium",
            ))
        for fk in sorted(src_fks - tgt_fks):
            diffs.append(ConstraintDiff(
                table_name=table_name,
                constraint_type="foreign_key",
                diff_type="removed",
                source_state=fk,
                risk_level="medium",
            ))

        # Indexes
        src_idx = self._index_set(source_table.get("indexes", []))
        tgt_idx = self._index_set(target_table.get("indexes", []))
        for idx in sorted(tgt_idx - src_idx):
            diffs.append(ConstraintDiff(
                table_name=table_name,
                constraint_type="index",
                diff_type="added",
                target_state=idx,
                risk_level="low",
            ))
        for idx in sorted(src_idx - tgt_idx):
            diffs.append(ConstraintDiff(
                table_name=table_name,
                constraint_type="index",
                diff_type="removed",
                source_state=idx,
                risk_level="low",
            ))

        return diffs

    @staticmethod
    def _fk_set(fks: List[Dict]) -> set:
        """Convert FK list to a set of tuples for comparison."""
        result = set()
        for fk in fks:
            result.add((
                fk.get("column", ""),
                fk.get("referred_table", ""),
                fk.get("referred_column", ""),
            ))
        return result

    @staticmethod
    def _index_set(indexes: List[Dict]) -> set:
        """Convert index list to a set of tuples for comparison."""
        result = set()
        for idx in indexes:
            cols = tuple(sorted(idx.get("columns", [])))
            unique = idx.get("unique", False)
            result.add((cols, unique))
        return result
