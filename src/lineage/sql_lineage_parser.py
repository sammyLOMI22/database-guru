"""
SQL Lineage Parser

Parses SQL queries to extract data lineage information: which source tables
and columns flow through transformations to produce output columns.

Uses sqlparse for SQL parsing, following patterns from multi_db_query_validator.py.
"""

import re
import logging
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Parenthesis, Function, Case
from sqlparse.tokens import Keyword, DML, Whitespace, Punctuation, Name

logger = logging.getLogger(__name__)


class LineageNodeType(Enum):
    """Types of nodes in the lineage graph."""
    SOURCE_TABLE = "source_table"
    SOURCE_COLUMN = "source_column"
    TRANSFORMATION = "transformation"
    OUTPUT_COLUMN = "output_column"


class TransformationType(Enum):
    """Types of transformations applied to data."""
    DIRECT = "direct"
    AGGREGATION = "aggregation"
    EXPRESSION = "expression"
    FUNCTION = "function"


AGGREGATION_FUNCTIONS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "GROUP_CONCAT", "STRING_AGG"}
COMMON_FUNCTIONS = {"COALESCE", "NULLIF", "CAST", "CONVERT", "IFNULL", "NVL",
                    "UPPER", "LOWER", "TRIM", "SUBSTR", "SUBSTRING", "LENGTH",
                    "ROUND", "ABS", "CEIL", "FLOOR", "DATE", "YEAR", "MONTH", "DAY"}


@dataclass
class LineageNode:
    """A node in the lineage graph."""
    id: str
    node_type: LineageNodeType
    label: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    expression: Optional[str] = None
    transformation_type: Optional[TransformationType] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "label": self.label,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "expression": self.expression,
            "transformation_type": self.transformation_type.value if self.transformation_type else None,
        }


@dataclass
class LineageEdge:
    """An edge connecting two nodes in the lineage graph."""
    source_id: str
    target_id: str
    edge_type: str = "data_flow"
    label: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "label": self.label,
        }


@dataclass
class LineageGraph:
    """Complete lineage graph for a SQL query."""
    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    sql: str = ""
    tables_used: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)
    output_columns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "sql": self.sql,
            "tables_used": self.tables_used,
            "columns_used": self.columns_used,
            "output_columns": self.output_columns,
        }


class SQLLineageParser:
    """
    Parses SQL queries to extract column-level data lineage.

    Produces a directed graph from source tables/columns through
    transformations to output columns.
    """

    def __init__(self):
        self._node_counter = 0

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique node ID."""
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def parse(self, sql: str) -> LineageGraph:
        """
        Parse a SQL query and extract lineage information.

        Args:
            sql: SQL query string

        Returns:
            LineageGraph with nodes and edges representing data flow
        """
        self._node_counter = 0

        if not sql or not sql.strip():
            return LineageGraph(sql=sql or "")

        graph = LineageGraph(sql=sql)

        try:
            parsed = sqlparse.parse(sql.strip())
            if not parsed:
                return graph

            stmt = parsed[0]

            # Only handle SELECT statements
            if stmt.get_type() != 'SELECT':
                return graph

            # Extract tables and aliases
            tables, aliases, subquery_tables = self._extract_tables(stmt)
            all_tables = tables | subquery_tables
            graph.tables_used = sorted(all_tables)

            # Create source table nodes
            table_nodes: Dict[str, LineageNode] = {}
            for table in all_tables:
                node = LineageNode(
                    id=self._generate_id("table"),
                    node_type=LineageNodeType.SOURCE_TABLE,
                    label=table,
                    table_name=table,
                )
                graph.nodes.append(node)
                table_nodes[table] = node

            # Extract SELECT columns and build lineage
            select_items = self._extract_select_columns(stmt)

            for item in select_items:
                self._process_select_item(
                    item, tables, aliases, table_nodes, graph
                )

            # Connect orphaned tables (used in JOINs/WHERE but not in SELECT)
            output_nodes = [
                n for n in graph.nodes
                if n.node_type == LineageNodeType.OUTPUT_COLUMN
            ]
            if output_nodes:
                # Find tables that have no edges yet
                connected_table_ids = set()
                for edge in graph.edges:
                    connected_table_ids.add(edge.source_id)

                for table_name, table_node in table_nodes.items():
                    if table_node.id not in connected_table_ids:
                        if table_name in subquery_tables:
                            # Subquery table → filter edge
                            graph.edges.append(LineageEdge(
                                source_id=table_node.id,
                                target_id=output_nodes[0].id,
                                edge_type="filter",
                                label="filters via subquery",
                            ))
                        elif table_name in tables:
                            # Primary table with no output columns → join/filter edge
                            graph.edges.append(LineageEdge(
                                source_id=table_node.id,
                                target_id=output_nodes[0].id,
                                edge_type="join",
                                label="joins",
                            ))

        except Exception as e:
            logger.warning(f"Lineage parsing error: {e}")

        return graph

    def _extract_tables(
        self, stmt: sqlparse.sql.Statement
    ) -> Tuple[Set[str], Dict[str, str], Set[str]]:
        """
        Extract table names and aliases from a SQL statement,
        including tables referenced in WHERE/HAVING subqueries.

        Returns:
            Tuple of (primary table names, alias -> real_name mapping, subquery table names)
        """
        tables: Set[str] = set()
        aliases: Dict[str, str] = {}
        subquery_tables: Set[str] = set()

        from_seen = False
        join_seen = False

        for token in stmt.tokens:
            if token.is_whitespace:
                continue

            if token.ttype is Keyword and token.value.upper() == 'FROM':
                from_seen = True
                continue

            if token.ttype is Keyword and 'JOIN' in token.value.upper():
                join_seen = True
                continue

            if from_seen or join_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tname, alias = self._parse_table_identifier(identifier)
                        if tname:
                            tables.add(tname)
                            if alias:
                                aliases[alias.lower()] = tname
                    from_seen = False
                    join_seen = False

                elif isinstance(token, Identifier):
                    # Check if this is a subquery
                    if self._is_subquery(token):
                        alias = token.get_alias()
                        if alias:
                            tables.add(alias)
                    else:
                        tname, alias = self._parse_table_identifier(token)
                        if tname:
                            tables.add(tname)
                            if alias:
                                aliases[alias.lower()] = tname
                    from_seen = False
                    join_seen = False

                elif token.ttype is Keyword and token.value.upper() in (
                    'WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT', 'UNION'
                ):
                    from_seen = False
                    join_seen = False
                elif token.ttype is Keyword and token.value.upper() in (
                    'INNER', 'LEFT', 'RIGHT', 'OUTER', 'CROSS'
                ):
                    join_seen = True
                    from_seen = False

            # Extract tables from WHERE/HAVING clause subqueries
            if isinstance(token, Where):
                clause_tables = self._extract_tables_from_clause(token)
                # Only add tables not already in FROM/JOIN as subquery tables
                for t in clause_tables:
                    if t not in tables:
                        subquery_tables.add(t)

        return tables, aliases, subquery_tables

    def _extract_tables_from_clause(self, token) -> Set[str]:
        """
        Recursively extract table names from subqueries within a clause
        (WHERE, HAVING, or any parenthesized expression).
        """
        tables: Set[str] = set()

        for sub in token.tokens:
            if isinstance(sub, Parenthesis):
                inner = sub.value.strip('()')
                stripped = inner.strip()
                if stripped.upper().startswith('SELECT'):
                    # This is a subquery - parse it for tables
                    subquery_tables = self._extract_tables_from_subquery(stripped)
                    tables.update(subquery_tables)
                else:
                    # Could be nested parentheses, recurse
                    tables.update(self._extract_tables_from_clause(sub))
            elif isinstance(sub, (IdentifierList, Identifier)):
                # Recurse into identifiers that may contain subqueries
                tables.update(self._extract_tables_from_clause(sub))

        return tables

    def _extract_tables_from_subquery(self, sql: str) -> Set[str]:
        """
        Parse a subquery SQL string and extract all table names,
        including from nested subqueries.
        """
        tables: Set[str] = set()

        try:
            parsed = sqlparse.parse(sql.strip())
            if not parsed:
                return tables

            stmt = parsed[0]
            # Recursively extract tables from the subquery
            primary, _, nested_subquery = self._extract_tables(stmt)
            tables.update(primary)
            tables.update(nested_subquery)
        except Exception as e:
            logger.debug(f"Error parsing subquery for tables: {e}")

        return tables

    def _is_subquery(self, token: Identifier) -> bool:
        """Check if an identifier contains a subquery."""
        for sub in token.tokens:
            if isinstance(sub, Parenthesis):
                inner = sub.value.strip('()')
                if inner.strip().upper().startswith('SELECT'):
                    return True
        return False

    def _parse_table_identifier(
        self, identifier
    ) -> Tuple[Optional[str], Optional[str]]:
        """Parse a table identifier, handling schema.table and aliases."""
        if not isinstance(identifier, Identifier):
            # Simple name token
            name = str(identifier).strip()
            if name and name.upper() not in ('ON', 'AND', 'OR', 'WHERE'):
                return name.lower(), None
            return None, None

        real_name = identifier.get_real_name()
        alias = identifier.get_alias()

        if not real_name:
            return None, None

        # Handle schema-qualified names (schema.table)
        parent = identifier.get_parent_name()
        if parent:
            real_name = real_name  # Use just the table name without schema

        return real_name.lower(), alias.lower() if alias else None

    def _extract_select_columns(
        self, stmt: sqlparse.sql.Statement
    ) -> List[Dict]:
        """
        Extract items from the SELECT clause.

        Returns list of dicts with keys: expression, alias, raw_token
        """
        items = []
        select_seen = False

        for token in stmt.tokens:
            # Skip all whitespace (including newlines)
            if token.is_whitespace:
                continue

            if token.ttype is DML and token.value.upper() == 'SELECT':
                select_seen = True
                continue

            # Skip DISTINCT/ALL
            if select_seen and token.ttype is Keyword and token.value.upper() in ('DISTINCT', 'ALL'):
                continue

            if select_seen:
                if token.ttype is Keyword and token.value.upper() in ('FROM', 'INTO'):
                    break

                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        items.append(self._parse_select_item(identifier))
                    break
                elif isinstance(token, Identifier):
                    items.append(self._parse_select_item(token))
                    break
                elif isinstance(token, Function):
                    # Standalone function like COUNT(*) without alias
                    items.append(self._parse_function_item(token))
                    break
                elif token.ttype is not Punctuation:
                    # Handle bare * or expressions
                    val = token.value.strip()
                    if val:
                        items.append({
                            "expression": val,
                            "alias": None,
                            "table_ref": None,
                            "column_ref": val if val != '*' else None,
                            "is_star": val == '*',
                            "is_function": False,
                            "function_name": None,
                            "function_args": [],
                        })
                    break

        return items

    def _parse_select_item(self, token) -> Dict:
        """Parse a single SELECT item into a structured dict."""
        result = {
            "expression": str(token).strip(),
            "alias": None,
            "table_ref": None,
            "column_ref": None,
            "is_star": False,
            "is_function": False,
            "function_name": None,
            "function_args": [],
        }

        if isinstance(token, Identifier):
            result["alias"] = token.get_alias()
            real_name = token.get_real_name()
            parent = token.get_parent_name()

            # Check for function or CASE expression
            for sub in token.tokens:
                if isinstance(sub, Function):
                    result["is_function"] = True
                    result["function_name"] = sub.get_real_name()
                    result["function_args"] = self._extract_function_args(sub)
                    break
                elif isinstance(sub, Case):
                    result["is_function"] = True
                    result["function_name"] = "CASE"
                    result["function_args"] = self._extract_case_columns(sub)
                    break

            if not result["is_function"]:
                if parent:
                    result["table_ref"] = parent.lower()
                    result["column_ref"] = real_name.lower() if real_name else None
                elif real_name:
                    result["column_ref"] = real_name.lower()

            # Check for star
            if real_name == '*' or str(token).strip().endswith('.*'):
                result["is_star"] = True
                if parent:
                    result["table_ref"] = parent.lower()

        elif hasattr(token, 'value'):
            val = token.value.strip()
            if val == '*':
                result["is_star"] = True

        # Detect expression (CASE, arithmetic, etc.)
        expr_str = result["expression"].upper()
        if not result["is_function"] and not result["is_star"]:
            if any(op in expr_str for op in ['CASE', '+', '-', '*', '/', '||', 'CONCAT']):
                result["is_function"] = True
                if 'CASE' in expr_str:
                    result["function_name"] = "CASE"
                else:
                    result["function_name"] = "EXPR"

        return result

    def _parse_function_item(self, func_token: Function) -> Dict:
        """Parse a standalone Function token (e.g., COUNT(*) without alias)."""
        func_name = func_token.get_real_name() or "FUNC"
        args = self._extract_function_args(func_token)

        return {
            "expression": str(func_token).strip(),
            "alias": None,
            "table_ref": None,
            "column_ref": None,
            "is_star": False,
            "is_function": True,
            "function_name": func_name,
            "function_args": args,
        }

    def _extract_function_args(self, func_token: Function) -> List[str]:
        """Extract argument column references from a function."""
        args = []
        for token in func_token.tokens:
            if isinstance(token, Parenthesis):
                inner = token.value.strip('()')
                # Split by comma for multiple args
                for part in inner.split(','):
                    part = part.strip()
                    if part and part != '*':
                        # Extract column reference (handle table.column)
                        if '.' in part:
                            args.append(part.split('.')[-1].strip().lower())
                        else:
                            col = re.sub(r'\s+(ASC|DESC|NULLS\s+(FIRST|LAST))', '', part, flags=re.IGNORECASE).strip()
                            if col and not col.upper().startswith(('SELECT', 'CASE')):
                                args.append(col.lower())
                    elif part == '*':
                        args.append('*')
        return args

    def _extract_case_columns(self, case_token: Case) -> List[str]:
        """Extract column references from a CASE expression."""
        # Extract columns mentioned in WHEN/THEN clauses
        cols = []
        case_str = str(case_token)
        for match in re.finditer(r'\b([a-zA-Z_]\w*)\b', case_str):
            word = match.group(1)
            keywords = {'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND', 'OR',
                        'NOT', 'IS', 'NULL', 'IN', 'LIKE', 'BETWEEN', 'TRUE', 'FALSE'}
            if word.upper() not in keywords and not word.replace("'", "").isdigit():
                # Skip string literals
                start = match.start()
                if start > 0 and case_str[start - 1] == "'":
                    continue
                cols.append(word.lower())
                break  # Take first column reference
        return cols

    def _process_select_item(
        self,
        item: Dict,
        tables: Set[str],
        aliases: Dict[str, str],
        table_nodes: Dict[str, LineageNode],
        graph: LineageGraph,
    ):
        """Process a single SELECT item and add nodes/edges to the graph."""
        output_label = item["alias"] or item["column_ref"] or item["expression"]
        if not output_label or output_label.strip() == '':
            return

        # Handle SELECT *
        if item["is_star"]:
            target_tables = [item["table_ref"]] if item["table_ref"] else list(tables)
            for tbl in target_tables:
                real_table = aliases.get(tbl, tbl) if tbl else None
                if real_table and real_table in table_nodes:
                    out_node = LineageNode(
                        id=self._generate_id("out"),
                        node_type=LineageNodeType.OUTPUT_COLUMN,
                        label=f"{real_table}.*",
                        table_name=real_table,
                        column_name="*",
                    )
                    graph.nodes.append(out_node)
                    graph.output_columns.append(f"{real_table}.*")
                    graph.edges.append(LineageEdge(
                        source_id=table_nodes[real_table].id,
                        target_id=out_node.id,
                        edge_type="direct",
                        label="all columns",
                    ))
            return

        # Determine transformation type
        if item["is_function"]:
            func_name = (item["function_name"] or "EXPR").upper()
            if func_name in AGGREGATION_FUNCTIONS:
                trans_type = TransformationType.AGGREGATION
            elif func_name in ("CASE", "EXPR"):
                trans_type = TransformationType.EXPRESSION
            else:
                trans_type = TransformationType.FUNCTION
        else:
            trans_type = TransformationType.DIRECT

        # Create output column node
        out_node = LineageNode(
            id=self._generate_id("out"),
            node_type=LineageNodeType.OUTPUT_COLUMN,
            label=output_label,
            column_name=item["alias"] or item["column_ref"],
            expression=item["expression"] if item["is_function"] else None,
        )
        graph.nodes.append(out_node)
        graph.output_columns.append(output_label)

        # For direct column references
        if trans_type == TransformationType.DIRECT:
            source_table = self._resolve_table(item["table_ref"], tables, aliases)
            col_name = item["column_ref"]

            if source_table and source_table in table_nodes:
                # Create source column node
                src_col_node = LineageNode(
                    id=self._generate_id("col"),
                    node_type=LineageNodeType.SOURCE_COLUMN,
                    label=f"{source_table}.{col_name}",
                    table_name=source_table,
                    column_name=col_name,
                )
                graph.nodes.append(src_col_node)
                graph.columns_used.append(f"{source_table}.{col_name}")

                # Edge: table -> source column
                graph.edges.append(LineageEdge(
                    source_id=table_nodes[source_table].id,
                    target_id=src_col_node.id,
                    edge_type="contains",
                ))
                # Edge: source column -> output column
                graph.edges.append(LineageEdge(
                    source_id=src_col_node.id,
                    target_id=out_node.id,
                    edge_type="direct",
                    label=col_name,
                ))
            elif col_name:
                # Column without known table - try to infer
                inferred = self._infer_table_for_column(col_name, tables)
                if inferred and inferred in table_nodes:
                    src_col_node = LineageNode(
                        id=self._generate_id("col"),
                        node_type=LineageNodeType.SOURCE_COLUMN,
                        label=f"{inferred}.{col_name}",
                        table_name=inferred,
                        column_name=col_name,
                    )
                    graph.nodes.append(src_col_node)
                    graph.columns_used.append(f"{inferred}.{col_name}")
                    graph.edges.append(LineageEdge(
                        source_id=table_nodes[inferred].id,
                        target_id=src_col_node.id,
                        edge_type="contains",
                    ))
                    graph.edges.append(LineageEdge(
                        source_id=src_col_node.id,
                        target_id=out_node.id,
                        edge_type="direct",
                        label=col_name,
                    ))
                else:
                    # Unknown source - connect to first table as best guess
                    if tables and table_nodes:
                        first_table = sorted(tables)[0]
                        graph.edges.append(LineageEdge(
                            source_id=table_nodes[first_table].id,
                            target_id=out_node.id,
                            edge_type="direct",
                            label=col_name,
                        ))
                        graph.columns_used.append(col_name)
            return

        # For functions/expressions - create transformation node
        trans_node = LineageNode(
            id=self._generate_id("trans"),
            node_type=LineageNodeType.TRANSFORMATION,
            label=item["function_name"] or "EXPR",
            expression=item["expression"],
            transformation_type=trans_type,
        )
        graph.nodes.append(trans_node)

        # Edge: transformation -> output
        graph.edges.append(LineageEdge(
            source_id=trans_node.id,
            target_id=out_node.id,
            edge_type="produces",
            label=item["function_name"],
        ))

        # Connect source columns to transformation
        func_args = item.get("function_args", [])
        if func_args:
            for arg in func_args:
                if arg == '*':
                    # COUNT(*) - connect all tables
                    for tbl in tables:
                        if tbl in table_nodes:
                            graph.edges.append(LineageEdge(
                                source_id=table_nodes[tbl].id,
                                target_id=trans_node.id,
                                edge_type="feeds",
                                label="*",
                            ))
                    continue

                source_table = self._infer_table_for_column(arg, tables)
                if source_table and source_table in table_nodes:
                    src_col_node = LineageNode(
                        id=self._generate_id("col"),
                        node_type=LineageNodeType.SOURCE_COLUMN,
                        label=f"{source_table}.{arg}",
                        table_name=source_table,
                        column_name=arg,
                    )
                    graph.nodes.append(src_col_node)
                    graph.columns_used.append(f"{source_table}.{arg}")
                    graph.edges.append(LineageEdge(
                        source_id=table_nodes[source_table].id,
                        target_id=src_col_node.id,
                        edge_type="contains",
                    ))
                    graph.edges.append(LineageEdge(
                        source_id=src_col_node.id,
                        target_id=trans_node.id,
                        edge_type="feeds",
                        label=arg,
                    ))
                elif tables and table_nodes:
                    # Best guess: first table
                    first_table = sorted(tables)[0]
                    graph.edges.append(LineageEdge(
                        source_id=table_nodes[first_table].id,
                        target_id=trans_node.id,
                        edge_type="feeds",
                        label=arg,
                    ))
                    graph.columns_used.append(arg)
        else:
            # No explicit args - extract columns from expression
            expr_cols = self._extract_columns_from_expression(item["expression"])
            for col_info in expr_cols:
                tbl = col_info.get("table")
                col = col_info.get("column")
                source_table = self._resolve_table(tbl, tables, aliases) if tbl else self._infer_table_for_column(col, tables)
                if source_table and source_table in table_nodes:
                    src_col_node = LineageNode(
                        id=self._generate_id("col"),
                        node_type=LineageNodeType.SOURCE_COLUMN,
                        label=f"{source_table}.{col}",
                        table_name=source_table,
                        column_name=col,
                    )
                    graph.nodes.append(src_col_node)
                    graph.columns_used.append(f"{source_table}.{col}")
                    graph.edges.append(LineageEdge(
                        source_id=table_nodes[source_table].id,
                        target_id=src_col_node.id,
                        edge_type="contains",
                    ))
                    graph.edges.append(LineageEdge(
                        source_id=src_col_node.id,
                        target_id=trans_node.id,
                        edge_type="feeds",
                        label=col,
                    ))
                elif col and tables and table_nodes:
                    first_table = sorted(tables)[0]
                    graph.edges.append(LineageEdge(
                        source_id=table_nodes[first_table].id,
                        target_id=trans_node.id,
                        edge_type="feeds",
                        label=col,
                    ))
                    graph.columns_used.append(col)

            # If no columns found in expression, connect to all tables
            if not expr_cols and tables:
                for tbl in tables:
                    if tbl in table_nodes:
                        graph.edges.append(LineageEdge(
                            source_id=table_nodes[tbl].id,
                            target_id=trans_node.id,
                            edge_type="feeds",
                        ))

    def _resolve_table(
        self, ref: Optional[str], tables: Set[str], aliases: Dict[str, str]
    ) -> Optional[str]:
        """Resolve a table reference (could be alias) to real table name."""
        if not ref:
            return None
        ref_lower = ref.lower()
        if ref_lower in aliases:
            return aliases[ref_lower]
        if ref_lower in tables:
            return ref_lower
        return None

    def _infer_table_for_column(
        self, column: str, tables: Set[str]
    ) -> Optional[str]:
        """
        Infer which table a column belongs to.
        Without schema information, returns the first table if only one exists.
        """
        if not column or not tables:
            return None
        if len(tables) == 1:
            return list(tables)[0]
        # Cannot infer without schema - return None
        return None

    def _extract_columns_from_expression(self, expression: str) -> List[Dict]:
        """Extract column references from a SQL expression string."""
        columns = []
        if not expression:
            return columns

        # Match table.column or bare column patterns
        # Exclude SQL keywords and function names
        keywords = AGGREGATION_FUNCTIONS | COMMON_FUNCTIONS | {
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'NULL', 'IS',
            'AS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'IN', 'BETWEEN',
            'LIKE', 'TRUE', 'FALSE', 'ASC', 'DESC', 'DISTINCT',
        }

        # Find table.column references
        for match in re.finditer(r'(\w+)\.(\w+)', expression):
            table, col = match.group(1), match.group(2)
            if table.upper() not in keywords and col.upper() not in keywords:
                columns.append({"table": table.lower(), "column": col.lower()})

        # Find bare column references (identifiers not in keywords)
        if not columns:
            for match in re.finditer(r'\b([a-zA-Z_]\w*)\b', expression):
                word = match.group(1)
                if word.upper() not in keywords and not word.isdigit():
                    # Skip string literals and numbers
                    columns.append({"table": None, "column": word.lower()})

        return columns
