"""
Explain Analyzer - Phase 22.1

Deterministic execution plan parser. Runs EXPLAIN [ANALYZE] against user databases
and parses the output into a structured tree for LLM interpretation.

Supports PostgreSQL, MySQL, SQLite, and DuckDB dialects.
No LLM involvement - pure parsing and heuristic analysis.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.models import DatabaseConnection
from src.core.user_db_connector import UserDatabaseConnector

logger = logging.getLogger(__name__)


@dataclass
class PlanNode:
    """A single node in the execution plan tree."""
    node_type: str
    relation: Optional[str] = None
    cost_startup: Optional[float] = None
    cost_total: Optional[float] = None
    rows_estimated: Optional[int] = None
    rows_actual: Optional[int] = None
    loops: Optional[int] = None
    actual_time_ms: Optional[float] = None
    filter: Optional[str] = None
    index_name: Optional[str] = None
    join_type: Optional[str] = None
    disk_spill: bool = False
    children: List["PlanNode"] = field(default_factory=list)
    raw_text: str = ""
    depth: int = 0

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["children"] = [c.to_dict() if isinstance(c, PlanNode) else c for c in self.children]
        return result


@dataclass
class ExecutionPlan:
    """Parsed execution plan with metadata."""
    dialect: str
    sql: str
    analyzed: bool
    root_node: Optional[PlanNode] = None
    all_nodes: List[PlanNode] = field(default_factory=list)
    total_cost: Optional[float] = None
    total_actual_time_ms: Optional[float] = None
    has_seq_scans: bool = False
    has_disk_spill: bool = False
    has_hash_batches: bool = False
    node_count: int = 0
    seq_scan_tables: List[str] = field(default_factory=list)
    missing_index_hints: List[str] = field(default_factory=list)
    raw_plan: List[str] = field(default_factory=list)
    parsed_at: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.parsed_at is None:
            self.parsed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["root_node"] = self.root_node.to_dict() if self.root_node else None
        result["all_nodes"] = [n.to_dict() if isinstance(n, PlanNode) else n for n in self.all_nodes]
        return result


class ExplainAnalyzer:
    """Runs EXPLAIN on user databases and parses execution plans."""

    def build_explain_sql(self, sql: str, dialect: str, analyze: bool = False) -> str:
        """Build dialect-specific EXPLAIN SQL statement."""
        db_lower = dialect.lower()

        if db_lower in ("postgresql", "postgres"):
            if analyze:
                return f"EXPLAIN (ANALYZE, FORMAT TEXT) {sql}"
            return f"EXPLAIN {sql}"
        elif db_lower == "mysql":
            return f"EXPLAIN {sql}"
        elif db_lower == "sqlite":
            # SQLite doesn't support EXPLAIN ANALYZE; always use EXPLAIN QUERY PLAN
            return f"EXPLAIN QUERY PLAN {sql}"
        elif db_lower == "duckdb":
            if analyze:
                return f"EXPLAIN ANALYZE {sql}"
            return f"EXPLAIN {sql}"
        else:
            return f"EXPLAIN {sql}"

    async def run_explain(
        self,
        connection: DatabaseConnection,
        sql: str,
        analyze: bool = False,
    ) -> ExecutionPlan:
        """
        Run EXPLAIN against the user's database and parse the result.

        Args:
            connection: Database connection to run EXPLAIN on
            sql: SQL query to explain
            analyze: Whether to use EXPLAIN ANALYZE (actually executes query)

        Returns:
            Parsed ExecutionPlan with structured nodes
        """
        dialect = connection.database_type

        # SQLite doesn't support EXPLAIN ANALYZE — force analyze=False
        effective_analyze = analyze and dialect.lower() not in ("sqlite",)

        explain_sql = self.build_explain_sql(sql, dialect, analyze)

        warnings: List[str] = []
        if analyze and not effective_analyze:
            warnings.append(f"{dialect} does not support EXPLAIN ANALYZE; returning cost-based plan only")

        try:
            async with UserDatabaseConnector.get_user_db_session(connection) as session:
                rows = await self._execute_explain(session, explain_sql, dialect)
        except Exception as e:
            logger.error(f"EXPLAIN execution failed on {connection.name}: {e}")
            return ExecutionPlan(
                dialect=dialect,
                sql=sql,
                analyzed=False,
                raw_plan=[f"Error: {str(e)}"],
                warnings=[f"Failed to run EXPLAIN: {str(e)}"],
            )

        plan = self.parse_plan(rows, dialect, sql, effective_analyze)
        if warnings:
            plan.warnings = warnings + plan.warnings
        return plan

    async def _execute_explain(
        self,
        session: Union[AsyncSession, Session],
        explain_sql: str,
        dialect: str,
    ) -> List[Any]:
        """Execute the EXPLAIN query, handling sync/async sessions."""
        query = text(explain_sql)

        if isinstance(session, Session):
            # Sync session (DuckDB, MSSQL, Oracle) - run in thread pool
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: session.execute(query).fetchall()
            )
            return result
        else:
            # Async session (PostgreSQL, MySQL, SQLite)
            result = await session.execute(query)
            return result.fetchall()

    def parse_plan(
        self,
        rows: List[Any],
        dialect: str,
        sql: str,
        analyzed: bool,
    ) -> ExecutionPlan:
        """Parse raw EXPLAIN rows into a structured ExecutionPlan."""
        db_lower = dialect.lower()

        # Extract raw text from rows
        raw_lines = self._extract_raw_lines(rows)

        if db_lower in ("postgresql", "postgres"):
            plan = self._parse_postgresql(raw_lines, sql, analyzed)
        elif db_lower == "mysql":
            plan = self._parse_mysql(rows, sql, analyzed)
        elif db_lower == "sqlite":
            plan = self._parse_sqlite(rows, sql, analyzed)
        elif db_lower == "duckdb":
            plan = self._parse_duckdb(raw_lines, sql, analyzed)
        else:
            plan = ExecutionPlan(
                dialect=dialect,
                sql=sql,
                analyzed=analyzed,
                raw_plan=raw_lines,
                warnings=[f"Unsupported dialect for plan parsing: {dialect}"],
            )

        plan.dialect = dialect
        plan.raw_plan = raw_lines

        # Generate deterministic warnings
        plan.warnings = self._extract_deterministic_warnings(plan)

        return plan

    def _extract_raw_lines(self, rows: List[Any]) -> List[str]:
        """Convert result rows to raw text lines."""
        lines = []
        for row in rows:
            if hasattr(row, "_mapping"):
                lines.append(str(dict(row._mapping)))
            elif isinstance(row, (tuple, list)):
                # For PostgreSQL text format, the plan is in the first column
                lines.append(str(row[0]) if row else "")
            else:
                lines.append(str(row))
        return lines

    # -------------------------------------------------------------------------
    # PostgreSQL Parser
    # -------------------------------------------------------------------------

    # Regex for PostgreSQL plan nodes
    _PG_NODE_RE = re.compile(
        r"^(\s*)"          # indentation
        r"(->)?\s*"        # optional arrow
        r"(.+?)"           # node type + relation
        r"\s*\("           # open paren
        r"cost=(\d+\.?\d*)\.\.(\d+\.?\d*)"  # startup..total cost
        r"\s+rows=(\d+)"  # estimated rows
        r"\s+width=(\d+)"  # width
        r"\)"              # close paren
        r"(.*)"            # rest of line (actual time, etc.)
    )

    _PG_ACTUAL_RE = re.compile(
        r"\(actual time=(\d+\.?\d*)\.\.(\d+\.?\d*)"
        r"\s+rows=(\d+)"
        r"\s+loops=(\d+)\)"
    )

    def _parse_postgresql(self, lines: List[str], sql: str, analyzed: bool) -> ExecutionPlan:
        """Parse PostgreSQL EXPLAIN [ANALYZE] text output."""
        nodes: List[PlanNode] = []
        node_stack: List[Tuple[int, PlanNode]] = []  # (indent_level, node)

        for line in lines:
            match = self._PG_NODE_RE.match(line)
            if not match:
                # Check for extra info lines (Filter, Sort Key, etc.)
                self._pg_annotate_last_node(nodes, line)
                continue

            indent = len(match.group(1))
            node_desc = match.group(3).strip()
            cost_startup = float(match.group(4))
            cost_total = float(match.group(5))
            rows_est = int(match.group(6))
            rest = match.group(8)

            # Parse node type and relation
            node_type, relation, index_name, join_type = self._pg_parse_node_desc(node_desc)

            node = PlanNode(
                node_type=node_type,
                relation=relation,
                cost_startup=cost_startup,
                cost_total=cost_total,
                rows_estimated=rows_est,
                index_name=index_name,
                join_type=join_type,
                raw_text=line.strip(),
                depth=indent,
            )

            # Parse actual time if ANALYZE was used
            actual_match = self._PG_ACTUAL_RE.search(rest)
            if actual_match:
                node.actual_time_ms = float(actual_match.group(2))
                node.rows_actual = int(actual_match.group(3))
                node.loops = int(actual_match.group(4))

            # Build tree structure based on indentation
            while node_stack and node_stack[-1][0] >= indent:
                node_stack.pop()
            if node_stack:
                node_stack[-1][1].children.append(node)
            node_stack.append((indent, node))
            nodes.append(node)

        root = nodes[0] if nodes else None
        seq_scan_tables = [n.relation for n in nodes if n.node_type == "Seq Scan" and n.relation]

        plan = ExecutionPlan(
            dialect="postgresql",
            sql=sql,
            analyzed=analyzed,
            root_node=root,
            all_nodes=nodes,
            total_cost=root.cost_total if root else None,
            total_actual_time_ms=root.actual_time_ms if root and root.actual_time_ms else None,
            has_seq_scans=bool(seq_scan_tables),
            has_disk_spill=any(n.disk_spill for n in nodes),
            node_count=len(nodes),
            seq_scan_tables=seq_scan_tables,
        )

        return plan

    def _pg_parse_node_desc(self, desc: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """Parse a PostgreSQL node description like 'Hash Join' or 'Seq Scan on orders'."""
        relation = None
        index_name = None
        join_type = None

        # "Seq Scan on orders"
        on_match = re.match(r"(.+?)\s+on\s+(\S+)", desc)
        if on_match:
            node_type = on_match.group(1).strip()
            relation = on_match.group(2).strip()
        else:
            node_type = desc.strip()

        # "Index Scan using idx_orders_status on orders"
        using_match = re.match(r"(.+?)\s+using\s+(\S+)\s+on\s+(\S+)", desc)
        if using_match:
            node_type = using_match.group(1).strip()
            index_name = using_match.group(2).strip()
            relation = using_match.group(3).strip()

        # Join types
        for jt in ("Hash Join", "Merge Join", "Nested Loop"):
            if node_type.startswith(jt):
                join_type = jt
                break

        return node_type, relation, index_name, join_type

    def _pg_annotate_last_node(self, nodes: List[PlanNode], line: str) -> None:
        """Annotate the most recent node with extra info (Filter, Sort Key, etc.)."""
        if not nodes:
            return
        last = nodes[-1]
        stripped = line.strip()

        if stripped.startswith("Filter:"):
            last.filter = stripped[len("Filter:"):].strip()
        elif stripped.startswith("Index Cond:"):
            last.filter = stripped[len("Index Cond:"):].strip()
        elif "Sort Method: external" in stripped:
            last.disk_spill = True
        elif re.search(r"Batches:\s*(\d+)", stripped):
            batch_match = re.search(r"Batches:\s*(\d+)", stripped)
            if batch_match and int(batch_match.group(1)) > 1:
                last.disk_spill = True
        elif stripped.startswith("Rows Removed by Filter:"):
            # Store for warning generation
            last.raw_text += f" | {stripped}"

    # -------------------------------------------------------------------------
    # MySQL Parser
    # -------------------------------------------------------------------------

    def _parse_mysql(self, rows: List[Any], sql: str, analyzed: bool) -> ExecutionPlan:
        """Parse MySQL EXPLAIN output (tabular format)."""
        nodes: List[PlanNode] = []
        seq_scan_tables = []

        for row in rows:
            # MySQL EXPLAIN returns rows with named columns
            if hasattr(row, "_mapping"):
                row_dict = dict(row._mapping)
            elif isinstance(row, dict):
                row_dict = row
            else:
                # Positional: id, select_type, table, partitions, type, possible_keys, key, key_len, ref, rows, filtered, Extra
                cols = ["id", "select_type", "table", "partitions", "type",
                        "possible_keys", "key", "key_len", "ref", "rows", "filtered", "Extra"]
                row_dict = {}
                for i, col in enumerate(cols):
                    if i < len(row):
                        row_dict[col] = row[i]

            table = row_dict.get("table", "")
            access_type = str(row_dict.get("type", "")).upper()
            key_used = row_dict.get("key")
            rows_est = row_dict.get("rows")
            extra = str(row_dict.get("Extra", ""))

            # Map MySQL access types to node types
            if access_type == "ALL":
                node_type = "Full Table Scan"
                seq_scan_tables.append(table)
            elif access_type in ("INDEX", "INDEX_MERGE"):
                node_type = "Full Index Scan"
            elif access_type in ("RANGE", "REF", "EQ_REF", "CONST", "SYSTEM"):
                node_type = f"Index Lookup ({access_type})"
            else:
                node_type = f"Access ({access_type})"

            disk_spill = "Using temporary" in extra or "Using filesort" in extra

            node = PlanNode(
                node_type=node_type,
                relation=table,
                rows_estimated=int(rows_est) if rows_est else None,
                index_name=key_used,
                disk_spill=disk_spill,
                filter=extra if extra else None,
                raw_text=str(row_dict),
            )
            nodes.append(node)

        root = nodes[0] if nodes else None
        return ExecutionPlan(
            dialect="mysql",
            sql=sql,
            analyzed=analyzed,
            root_node=root,
            all_nodes=nodes,
            has_seq_scans=bool(seq_scan_tables),
            has_disk_spill=any(n.disk_spill for n in nodes),
            node_count=len(nodes),
            seq_scan_tables=seq_scan_tables,
        )

    # -------------------------------------------------------------------------
    # SQLite Parser
    # -------------------------------------------------------------------------

    def _parse_sqlite(self, rows: List[Any], sql: str, analyzed: bool) -> ExecutionPlan:
        """Parse SQLite EXPLAIN QUERY PLAN output."""
        nodes: List[PlanNode] = []
        seq_scan_tables = []

        for row in rows:
            # SQLite EXPLAIN QUERY PLAN returns (id, parent, notused, detail)
            if isinstance(row, (tuple, list)) and len(row) >= 4:
                detail = str(row[3])
            elif hasattr(row, "_mapping"):
                row_dict = dict(row._mapping)
                detail = str(row_dict.get("detail", row_dict.get("p", "")))
            else:
                detail = str(row)

            # Parse detail string
            node_type, relation, index_name = self._sqlite_parse_detail(detail)

            if node_type == "SCAN":
                seq_scan_tables.append(relation or "unknown")

            node = PlanNode(
                node_type=node_type,
                relation=relation,
                index_name=index_name,
                raw_text=detail,
            )
            nodes.append(node)

        root = nodes[0] if nodes else None
        return ExecutionPlan(
            dialect="sqlite",
            sql=sql,
            analyzed=analyzed,
            root_node=root,
            all_nodes=nodes,
            has_seq_scans=bool(seq_scan_tables),
            node_count=len(nodes),
            seq_scan_tables=seq_scan_tables,
        )

    def _sqlite_parse_detail(self, detail: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Parse a SQLite EXPLAIN QUERY PLAN detail string."""
        # "SCAN TABLE orders" or "SCAN orders"
        scan_match = re.match(r"SCAN\s+(?:TABLE\s+)?(\S+)", detail, re.IGNORECASE)
        if scan_match:
            return "SCAN", scan_match.group(1), None

        # "SEARCH TABLE orders USING INTEGER PRIMARY KEY" — check before general index
        pk_match = re.match(
            r"SEARCH\s+(?:TABLE\s+)?(\S+)\s+USING\s+INTEGER\s+PRIMARY\s+KEY",
            detail, re.IGNORECASE
        )
        if pk_match:
            return "SEARCH", pk_match.group(1), "PRIMARY KEY"

        # "SEARCH TABLE orders USING INDEX idx_status (status=?)"
        # or "SEARCH orders USING COVERING INDEX idx_status"
        search_match = re.match(
            r"SEARCH\s+(?:TABLE\s+)?(\S+)\s+USING\s+(?:(?:COVERING\s+)?INDEX\s+)?(\S+)",
            detail, re.IGNORECASE
        )
        if search_match:
            return "SEARCH", search_match.group(1), search_match.group(2)

        # "USE TEMP B-TREE FOR ORDER BY"
        if "TEMP B-TREE" in detail.upper():
            return "TEMP B-TREE", None, None

        return detail.strip(), None, None

    # -------------------------------------------------------------------------
    # DuckDB Parser
    # -------------------------------------------------------------------------

    def _parse_duckdb(self, lines: List[str], sql: str, analyzed: bool) -> ExecutionPlan:
        """Parse DuckDB EXPLAIN text output."""
        nodes: List[PlanNode] = []
        seq_scan_tables = []

        # DuckDB EXPLAIN format uses box-drawing characters and indentation
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("┌") or stripped.startswith("└") or stripped.startswith("─"):
                continue

            # Remove box-drawing prefixes
            cleaned = re.sub(r"^[│├└─>\s]+", "", stripped)
            if not cleaned:
                continue

            node_type, relation = self._duckdb_parse_line(cleaned)
            if not node_type:
                continue

            is_seq_scan = node_type.upper() in ("SEQ_SCAN", "TABLE_SCAN", "SCAN")
            if is_seq_scan and relation:
                seq_scan_tables.append(relation)

            node = PlanNode(
                node_type=node_type,
                relation=relation,
                raw_text=cleaned,
            )
            nodes.append(node)

        root = nodes[0] if nodes else None
        return ExecutionPlan(
            dialect="duckdb",
            sql=sql,
            analyzed=analyzed,
            root_node=root,
            all_nodes=nodes,
            has_seq_scans=bool(seq_scan_tables),
            node_count=len(nodes),
            seq_scan_tables=seq_scan_tables,
        )

    def _duckdb_parse_line(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse a DuckDB plan line into node_type and relation."""
        # Common patterns: "HASH_JOIN", "SEQ_SCAN orders", "FILTER"
        parts = line.split()
        if not parts:
            return None, None

        node_type = parts[0]
        relation = parts[1] if len(parts) > 1 else None

        # Skip decorative/info lines
        if node_type.startswith("[") or node_type == "EC:":
            return None, None

        return node_type, relation

    # -------------------------------------------------------------------------
    # Deterministic Warnings
    # -------------------------------------------------------------------------

    def _extract_deterministic_warnings(self, plan: ExecutionPlan) -> List[str]:
        """Generate rule-based warnings from the parsed plan."""
        warnings = []

        for node in plan.all_nodes:
            # Sequential scan warnings
            if node.node_type in ("Seq Scan", "Full Table Scan", "SCAN") and node.relation:
                if node.filter:
                    rows_removed_match = re.search(r"Rows Removed by Filter:\s*(\d+)", node.raw_text)
                    if rows_removed_match:
                        removed = int(rows_removed_match.group(1))
                        if removed > 100:
                            warnings.append(
                                f"Sequential scan on '{node.relation}' with filter removed "
                                f"{removed:,} rows — consider adding an index on the filtered column"
                            )
                    else:
                        warnings.append(
                            f"Sequential scan on '{node.relation}' with filter — "
                            f"consider adding an index on the filtered column"
                        )
                elif node.rows_estimated and node.rows_estimated > 1000:
                    warnings.append(
                        f"Sequential scan on '{node.relation}' "
                        f"(est. {node.rows_estimated:,} rows) — may benefit from an index"
                    )

            # Disk spill warnings
            if node.disk_spill:
                if node.join_type:
                    warnings.append(
                        f"{node.join_type} on '{node.relation or 'unknown'}' is spilling to disk — "
                        f"consider increasing work_mem"
                    )
                else:
                    warnings.append(
                        f"'{node.node_type}' is spilling to disk — "
                        f"consider increasing work_mem or adding an index"
                    )

            # Nested loop with high loop count
            if node.node_type == "Nested Loop" and node.loops and node.loops > 100:
                warnings.append(
                    f"Nested Loop with {node.loops:,} iterations — "
                    f"consider rewriting with a JOIN or adding an index"
                )

            # MySQL-specific: Using filesort / Using temporary
            if node.filter and isinstance(node.filter, str):
                if "Using filesort" in node.filter:
                    warnings.append(
                        f"Filesort on '{node.relation or 'unknown'}' — "
                        f"consider adding an index to avoid sorting"
                    )
                if "Using temporary" in node.filter:
                    warnings.append(
                        f"Temporary table used for '{node.relation or 'unknown'}' — "
                        f"review GROUP BY / DISTINCT usage"
                    )

        # SQLite: SCAN without index
        if plan.dialect == "sqlite":
            for node in plan.all_nodes:
                if node.node_type == "SCAN" and node.relation:
                    warnings.append(
                        f"Full table scan on '{node.relation}' — "
                        f"consider adding an index"
                    )
                if node.node_type == "TEMP B-TREE":
                    warnings.append(
                        "Temporary B-tree used for sorting — "
                        "consider adding an index on the ORDER BY columns"
                    )

        return warnings
