"""Database schema introspection"""
import logging
import re
from typing import Dict, List, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Inspector

from src.core.column_semantics import ColumnSemanticsDetector, ColumnSemanticType

logger = logging.getLogger(__name__)


class SchemaInspector:
    """
    Introspect database schema to discover tables, columns, and relationships
    """

    def __init__(self):
        """Initialize schema inspector"""
        self.semantics_detector = ColumnSemanticsDetector()

    async def _execute_query(self, session, query, params=None):
        """
        Execute a query handling both sync and async sessions

        Args:
            session: Database session (async or sync)
            query: SQL query (text object)
            params: Optional query parameters

        Returns:
            Result object
        """
        is_async = isinstance(session, AsyncSession)

        if is_async:
            if params:
                return await session.execute(query, params)
            else:
                return await session.execute(query)
        else:
            # Sync session (e.g., DuckDB)
            if params:
                return session.execute(query, params)
            else:
                return session.execute(query)

    async def sample_column_values(
        self,
        session: AsyncSession,
        table_name: str,
        column_name: str,
        limit: int = 5,
    ) -> List[Any]:
        """
        Sample distinct values from a column to understand data format

        This helps the LLM understand:
        - Whether states are stored as codes (NY, CA) or full names (New York, California)
        - Whether statuses are lowercase or capitalized
        - Typical value ranges

        Args:
            session: Database session
            table_name: Name of table
            column_name: Name of column to sample
            limit: Maximum number of distinct values to return

        Returns:
            List of sample values
        """
        try:
            # Build safe query with quoted identifiers
            query = text(f'SELECT DISTINCT "{column_name}" FROM "{table_name}" WHERE "{column_name}" IS NOT NULL LIMIT :limit')
            result = await self._execute_query(session, query, {"limit": limit})

            # Extract values
            values = [row[0] for row in result.fetchall()]
            return values

        except Exception as e:
            logger.debug(f"Failed to sample values from {table_name}.{column_name}: {e}")
            return []

    async def get_full_schema(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
        include_samples: bool = True,
    ) -> Dict[str, Any]:
        """
        Get complete database schema information

        Args:
            session: Database session
            schema_name: Schema name (None for default)
            include_samples: Whether to include sample values for key columns (state, status, type, etc.)

        Returns:
            Dictionary with tables, columns, relationships, indexes, and sample values
        """
        try:
            # Get table information
            tables = await self.get_tables(session, schema_name)

            # Build schema structure
            schema = {
                "tables": {},
                "relationships": [],
                "summary": {
                    "table_count": len(tables),
                    "total_columns": 0,
                },
            }

            # Columns to sample (helps LLM understand data formats and values)
            # Location columns: state, country, region, city, address - for geographic queries
            # Domain columns: status, type, category - for enumerated/filter values
            sample_column_keywords = [
                # Location-related (helps with "shipped to New York" type queries)
                'state', 'country', 'region', 'city', 'address',
                # Domain-related (helps understand valid filter values)
                'status', 'type', 'category'
            ]

            for table_name in tables:
                # Get columns
                columns = await self.get_columns(session, table_name, schema_name)

                # Get primary keys
                primary_keys = await self.get_primary_keys(session, table_name, schema_name)

                # Get foreign keys
                foreign_keys = await self.get_foreign_keys(session, table_name, schema_name)

                # Get indexes
                indexes = await self.get_indexes(session, table_name, schema_name)

                # Sample values for key columns and detect semantic types
                if include_samples:
                    for column in columns:
                        col_name = column.get("name", "").lower()
                        col_type = column.get("type", "")

                        # Check if this is a column we should sample
                        if any(keyword in col_name for keyword in sample_column_keywords):
                            samples = await self.sample_column_values(
                                session, table_name, column["name"], limit=5
                            )
                            if samples:
                                column["sample_values"] = samples
                                logger.info(f"📊 Sampled {table_name}.{column['name']}: {samples}")

                                # Detect semantic type based on name, type, and sample values
                                semantics = self.semantics_detector.detect(
                                    column["name"], col_type, samples
                                )
                                column["semantic_type"] = semantics.semantic_type.value
                                if semantics.location_subtype:
                                    column["location_subtype"] = semantics.location_subtype
                                if semantics.value_format:
                                    column["value_format"] = semantics.value_format
                                column["semantic_confidence"] = semantics.confidence

                                logger.info(
                                    f"🧠 Detected {table_name}.{column['name']}: "
                                    f"{semantics.semantic_type.value} "
                                    f"(format={semantics.value_format}, conf={semantics.confidence:.2f})"
                                )

                schema["tables"][table_name] = {
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "indexes": indexes,
                }

                schema["summary"]["total_columns"] += len(columns)

            # Second pass: Add relationships only for FKs where referred_table exists
            # This filters out orphan FKs (referencing non-existent tables)
            for table_name, table_info in schema["tables"].items():
                valid_fks = []
                for fk in table_info.get("foreign_keys", []):
                    referred_table = fk.get("referred_table", "")
                    if referred_table in schema["tables"]:
                        # FK references a valid table - add relationship
                        schema["relationships"].append({
                            "from_table": table_name,
                            "from_column": fk["column"],
                            "to_table": referred_table,
                            "to_column": fk["referred_column"],
                        })
                        valid_fks.append(fk)
                    else:
                        # Orphan FK - table doesn't exist, log warning
                        logger.warning(
                            f"⚠️ Orphan FK detected: {table_name}.{fk['column']} -> "
                            f"{referred_table}.{fk['referred_column']} "
                            f"(table '{referred_table}' does not exist)"
                        )
                # Update foreign_keys to only include valid ones
                table_info["foreign_keys"] = valid_fks

            return schema

        except Exception as e:
            logger.error(f"Error introspecting schema: {e}", exc_info=True)
            raise

    async def get_tables(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[str]:
        """
        Get list of table names

        Args:
            session: Database session
            schema_name: Schema name

        Returns:
            List of table names
        """
        try:
            # Detect database type
            db_name = session.bind.dialect.name if session.bind else "unknown"

            if db_name == "sqlite":
                # SQLite query
                query = text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table'
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                result = await self._execute_query(session, query)
            elif db_name == "duckdb":
                # DuckDB uses information_schema
                query = text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                result = await self._execute_query(session, query)
            else:
                # PostgreSQL/MySQL query
                query = text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = COALESCE(:schema_name, 'public')
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})

            tables = [row[0] for row in result.all()]
            logger.debug(f"Found {len(tables)} tables in {db_name} database")
            return tables

        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []

    async def get_columns(
        self,
        session: AsyncSession,
        table_name: str,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get column information for a table

        Args:
            session: Database session
            table_name: Table name
            schema_name: Schema name

        Returns:
            List of column dictionaries
        """
        try:
            db_name = session.bind.dialect.name if session.bind else "unknown"

            if db_name == "sqlite":
                # SQLite query using PRAGMA
                query = f"PRAGMA table_info({table_name})"
                result = await self._execute_query(session, text(query))

                columns = []
                for row in result.all():
                    # SQLite PRAGMA returns: cid, name, type, notnull, dflt_value, pk
                    columns.append({
                        "name": row[1],  # name
                        "type": row[2],  # type
                        "nullable": row[3] == 0,  # notnull (0 = nullable)
                        "default": row[4],  # dflt_value
                        "max_length": None,  # Not available in SQLite
                    })
            else:
                # PostgreSQL/MySQL query
                query = """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    AND table_schema = COALESCE(:schema_name, 'public')
                    ORDER BY ordinal_position
                """

                result = await self._execute_query(session, text(query), {
                        "table_name": table_name,
                        "schema_name": schema_name or "public"
                    })

                columns = []
                for row in result.all():
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "default": row[3],
                        "max_length": row[4],
                    })

            return columns

        except Exception as e:
            logger.error(f"Error getting columns for {table_name}: {e}")
            return []

    async def get_primary_keys(
        self,
        session: AsyncSession,
        table_name: str,
        schema_name: Optional[str] = None,
    ) -> List[str]:
        """
        Get primary key columns for a table

        Args:
            session: Database session
            table_name: Table name
            schema_name: Schema name

        Returns:
            List of primary key column names
        """
        try:
            db_name = session.bind.dialect.name if session.bind else "unknown"

            if db_name == "sqlite":
                # SQLite - use PRAGMA
                query = f"PRAGMA table_info({table_name})"
                result = await self._execute_query(session, text(query))
                # pk column is at index 5, returns 1 if primary key
                return [row[1] for row in result.all() if row[5] == 1]

            elif db_name in ["mysql", "duckdb"]:
                # MySQL and DuckDB - use information_schema
                query = """
                    SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_name = :table_name
                    AND constraint_name = 'PRIMARY'
                    ORDER BY ordinal_position
                """
                result = await self._execute_query(session, text(query), {"table_name": table_name})
                return [row[0] for row in result.all()]

            else:
                # PostgreSQL - use pg_index
                query = """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = :table_name::regclass
                    AND i.indisprimary
                """
                result = await self._execute_query(session, text(query), {"table_name": table_name})
                return [row[0] for row in result.all()]

        except Exception as e:
            logger.debug(f"Error getting primary keys for {table_name}: {e}")
            return []

    async def get_foreign_keys(
        self,
        session: AsyncSession,
        table_name: str,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Get foreign key constraints for a table

        Args:
            session: Database session
            table_name: Table name
            schema_name: Schema name

        Returns:
            List of foreign key dictionaries
        """
        try:
            db_name = session.bind.dialect.name if session.bind else "unknown"

            if db_name == "sqlite":
                # SQLite - use PRAGMA foreign_key_list
                query = f"PRAGMA foreign_key_list({table_name})"
                result = await self._execute_query(session, text(query))

                foreign_keys = []
                for row in result.all():
                    # SQLite PRAGMA returns: id, seq, table, from, to, on_update, on_delete, match
                    foreign_keys.append({
                        "column": row[3],  # from column
                        "referred_table": row[2],  # table
                        "referred_column": row[4],  # to column
                        "constraint_name": f"fk_{table_name}_{row[0]}",  # Generate name
                    })
                return foreign_keys

            elif db_name == "duckdb":
                # DuckDB - use duckdb_constraints() function
                # information_schema.key_column_usage doesn't have referenced_table_name in DuckDB
                query = f"""
                    SELECT
                        constraint_column_names,
                        constraint_name,
                        constraint_text
                    FROM duckdb_constraints()
                    WHERE table_name = '{table_name}'
                    AND constraint_type = 'FOREIGN KEY'
                """
                result = await self._execute_query(session, text(query))

                foreign_keys = []
                for row in result.all():
                    # Parse FK info from constraint_text: "FOREIGN KEY (customer_id) REFERENCES customers(id)"
                    constraint_text = row[2] if len(row) > 2 else ""
                    constraint_name = row[1] if len(row) > 1 else ""
                    source_columns = row[0] if row[0] else []

                    # Extract referenced table and column from constraint_text
                    fk_match = re.search(
                        r'FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)',
                        constraint_text,
                        re.IGNORECASE
                    )
                    if fk_match and source_columns:
                        referred_table = fk_match.group(1)
                        referred_columns = [c.strip() for c in fk_match.group(2).split(',')]

                        # Map each source column to its referred column
                        for i, src_col in enumerate(source_columns):
                            ref_col = referred_columns[i] if i < len(referred_columns) else referred_columns[0]
                            foreign_keys.append({
                                "column": src_col,
                                "referred_table": referred_table,
                                "referred_column": ref_col,
                                "constraint_name": constraint_name,
                            })

                return foreign_keys

            elif db_name == "mysql":
                # MySQL - use information_schema with referenced_table_name
                query = """
                    SELECT
                        kcu.column_name,
                        kcu.referenced_table_name,
                        kcu.referenced_column_name,
                        kcu.constraint_name
                    FROM information_schema.key_column_usage AS kcu
                    WHERE kcu.table_name = :table_name
                    AND kcu.referenced_table_name IS NOT NULL
                """
                result = await self._execute_query(session, text(query), {"table_name": table_name})

                foreign_keys = []
                for row in result.all():
                    foreign_keys.append({
                        "column": row[0],
                        "referred_table": row[1],
                        "referred_column": row[2],
                        "constraint_name": row[3],
                    })
                return foreign_keys

            else:
                # PostgreSQL - use information_schema with proper joins
                query = """
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = :table_name
                    AND tc.table_schema = COALESCE(:schema_name, 'public')
                """

                result = await self._execute_query(session, text(query), {
                        "table_name": table_name,
                        "schema_name": schema_name or "public"
                    })

                foreign_keys = []
                for row in result.all():
                    foreign_keys.append({
                        "column": row[0],
                        "referred_table": row[1],
                        "referred_column": row[2],
                        "constraint_name": row[3],
                    })

                return foreign_keys

        except Exception as e:
            logger.debug(f"Error getting foreign keys for {table_name}: {e}")
            return []

    async def get_indexes(
        self,
        session: AsyncSession,
        table_name: str,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get indexes for a table

        Args:
            session: Database session
            table_name: Table name
            schema_name: Schema name

        Returns:
            List of index dictionaries
        """
        try:
            query = """
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = :table_name
                AND schemaname = COALESCE(:schema_name, 'public')
            """

            result = await self._execute_query(session, text(query), {
                    "table_name": table_name,
                    "schema_name": schema_name or "public"
                })

            indexes = []
            for row in result.all():
                indexes.append({
                    "name": row[0],
                    "definition": row[1],
                })

            return indexes

        except Exception as e:
            logger.debug(f"Error getting indexes for {table_name}: {e}")
            return []

    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """
        Format schema information for LLM prompt

        Args:
            schema: Schema dictionary from get_full_schema()

        Returns:
            Formatted string for LLM
        """
        # Get table names for prominent display
        table_names = list(schema["tables"].keys())

        # Collect all columns for summary
        all_columns = set()
        table_columns = {}
        for table_name, table_info in schema["tables"].items():
            cols = [col["name"] for col in table_info.get("columns", [])]
            table_columns[table_name] = cols
            all_columns.update(cols)

        lines = ["=" * 50]
        lines.append("AVAILABLE TABLES (USE ONLY THESE):")
        lines.append(", ".join(table_names))
        lines.append("=" * 50)

        # Add compact column summary - helps LLM see at a glance what exists
        lines.append("")
        lines.append("QUICK COLUMN REFERENCE (table.column):")
        for table_name in table_names:
            cols = table_columns.get(table_name, [])
            col_list = ", ".join(cols[:8])  # Limit to first 8 for readability
            if len(cols) > 8:
                col_list += f", ... ({len(cols)} total)"
            lines.append(f"  {table_name}: {col_list}")

        # Check for commonly expected columns that DON'T exist
        common_missing = []
        expected_columns = ['state', 'city', 'country', 'address', 'location', 'region', 'zip', 'postal_code']
        for col in expected_columns:
            if col not in all_columns and col.lower() not in [c.lower() for c in all_columns]:
                common_missing.append(col)

        if common_missing:
            lines.append("")
            lines.append("⚠️ NOTE: These commonly expected columns DO NOT EXIST in this database:")
            lines.append(f"   {', '.join(common_missing)}")
            lines.append("   If the query requires these columns, respond with CANNOT_ANSWER.")

        lines.append("")
        lines.append("=" * 50)
        lines.append("")
        lines.append("Database Schema:\n")

        # Add summary
        lines.append(f"Table Count: {schema['summary']['table_count']}")
        lines.append(f"Total Columns: {schema['summary']['total_columns']}\n")

        # Add table details
        for table_name, table_info in schema["tables"].items():
            lines.append(f"\nTable: {table_name}")

            # Columns
            lines.append("  Columns:")
            for col in table_info["columns"]:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                pk_marker = " [PK]" if col["name"] in table_info["primary_keys"] else ""

                # Add semantic type hint if detected (helps LLM understand column purpose)
                # Phase 3: Expanded column semantics beyond just locations
                semantic_hint = ""
                sample_values = col.get("sample_values", [])
                if col.get("semantic_type"):
                    sem_type = col["semantic_type"]
                    if sem_type == "location":
                        # Provide location-specific guidance
                        # NOTE: Use parentheses, not square brackets, to avoid LLM confusion
                        # with SQL Server's [identifier] syntax
                        fmt = col.get("value_format", "unknown")
                        subtype = col.get("location_subtype", "")
                        if fmt == "code":
                            semantic_hint = f" (location:{subtype}, use 2-letter codes like 'CA', 'NY')"
                        elif fmt == "full_name":
                            semantic_hint = f" (location:{subtype}, use full names like 'California', 'New York')"
                        else:
                            semantic_hint = f" (location:{subtype})"
                    elif sem_type == "categorical":
                        # Phase 3: Show actual valid values for categorical columns
                        if sample_values:
                            valid_values = ", ".join(repr(s) for s in sample_values[:8])
                            semantic_hint = f" (enum, valid values: {valid_values})"
                        else:
                            semantic_hint = " (categorical, use exact enum values)"
                    elif sem_type == "temporal":
                        semantic_hint = " (date/time)"
                    elif sem_type == "boolean":
                        semantic_hint = " (boolean, use 0/1 or TRUE/FALSE)"
                    elif sem_type == "identifier":
                        semantic_hint = " (primary/foreign key)"

                # Add sample values if available (helps LLM understand format)
                # Skip if already shown in semantic hint (for categorical)
                sample_hint = ""
                if sample_values and sem_type != "categorical":
                    sample_str = ", ".join(repr(s) for s in sample_values[:5])
                    sample_hint = f"  // Examples: {sample_str}"

                lines.append(f"    - {col['name']}: {col['type']} {nullable}{pk_marker}{semantic_hint}{sample_hint}")

            # Foreign keys
            if table_info["foreign_keys"]:
                lines.append("  Foreign Keys:")
                for fk in table_info["foreign_keys"]:
                    lines.append(
                        f"    - {fk['column']} -> {fk['referred_table']}.{fk['referred_column']}"
                    )

        # Add relationships summary
        if schema["relationships"]:
            lines.append("\nRelationships (Foreign Keys):")
            for rel in schema["relationships"]:
                lines.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']}"
                )

        # Add common join paths for multi-hop relationships
        # This helps LLMs understand how to connect tables that aren't directly related
        join_paths = self._build_join_paths(schema)
        if join_paths:
            lines.append("\nCOMMON JOIN PATHS (use these for multi-table queries):")
            for path in join_paths:
                lines.append(f"  {path}")

        # Phase 2: Add enriched schema context (bridge tables, inferred relationships)
        enriched_context = self.get_enriched_schema_context(schema)
        if enriched_context:
            lines.append(enriched_context)

        # Add reminder at the end
        lines.append("")
        lines.append("=" * 50)
        lines.append(f"REMINDER: Only use tables: {', '.join(table_names)}")
        lines.append("DO NOT use tables from examples if they don't exist above!")
        lines.append("For multi-table queries, use the JOIN PATHS or JOIN EXAMPLES above!")
        lines.append("=" * 50)

        return "\n".join(lines)

    def _build_join_paths(self, schema: Dict[str, Any]) -> List[str]:
        """
        Build common join paths from relationships.

        This helps LLMs understand multi-hop joins like:
        products -> order_items -> orders -> customers

        Args:
            schema: Schema dictionary with relationships

        Returns:
            List of join path descriptions
        """
        if not schema.get("relationships"):
            return []

        # Build adjacency graph from relationships
        graph = {}  # table -> [(related_table, from_col, to_col), ...]
        for rel in schema["relationships"]:
            from_table = rel["from_table"]
            to_table = rel["to_table"]
            from_col = rel["from_column"]
            to_col = rel["to_column"]

            if from_table not in graph:
                graph[from_table] = []
            graph[from_table].append((to_table, from_col, to_col))

            # Also add reverse for bidirectional traversal
            if to_table not in graph:
                graph[to_table] = []
            graph[to_table].append((from_table, to_col, from_col))

        paths = []
        tables = list(schema["tables"].keys())

        # Find paths between common table pairs (2-3 hops)
        for start in tables:
            for end in tables:
                if start >= end:  # Avoid duplicates
                    continue

                # Find path using BFS (max 4 hops for complex schemas)
                path = self._find_join_path(graph, start, end, max_hops=4)
                if path and len(path) > 2:  # Only show multi-hop paths
                    path_str = self._format_join_path(path)
                    if path_str:
                        paths.append(path_str)

        return paths[:15]  # Limit to avoid overwhelming the prompt

    def _find_join_path(
        self,
        graph: Dict[str, List],
        start: str,
        end: str,
        max_hops: int = 3
    ) -> List[tuple]:
        """BFS to find shortest path between two tables."""
        from collections import deque

        if start not in graph:
            return []

        queue = deque([(start, [(start, None, None)])])
        visited = {start}

        while queue:
            current, path = queue.popleft()

            if current == end:
                return path

            if len(path) > max_hops:
                continue

            for neighbor, from_col, to_col in graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [(neighbor, from_col, to_col)]
                    queue.append((neighbor, new_path))

        return []

    def _format_join_path(self, path: List[tuple]) -> str:
        """Format a join path for display."""
        if len(path) < 2:
            return ""

        parts = []
        for i, (table, from_col, to_col) in enumerate(path):
            if i == 0:
                parts.append(table)
            else:
                prev_table = path[i-1][0]
                parts.append(f"JOIN {table} ON {prev_table}.{from_col} = {table}.{to_col}")

        return " -> ".join([path[0][0]] + [p[0] for p in path[1:]]) + f"\n    ({' '.join(parts[1:])})"

    def filter_schema_for_query(
        self,
        schema: Dict[str, Any],
        question: str,
        include_neighbors: bool = True,
        max_neighbor_hops: int = 1,
    ) -> Dict[str, Any]:
        """
        Filter schema to only include tables relevant to the query.

        This addresses the PR review feedback about schema context optimization:
        For large databases, passing the full schema hits context limits and
        confuses the LLM. This method filters to only relevant tables + neighbors.

        Args:
            schema: Full schema dictionary from get_full_schema()
            question: Natural language question to analyze
            include_neighbors: Include tables connected via foreign keys
            max_neighbor_hops: How many FK hops to include (1 = direct neighbors only)

        Returns:
            Filtered schema dictionary with only relevant tables
        """
        try:
            from src.llm.required_data_detector import RequiredDataDetector

            # Detect required tables from the question
            detector = RequiredDataDetector(schema)
            result = detector.detect_required_data(question)

            # Start with detected tables
            relevant_tables = set(result.tables_required)

            # If no tables detected, include all tables (fallback)
            if not relevant_tables:
                logger.debug("No specific tables detected, using full schema")
                return schema

            # Add neighbor tables if enabled (for potential JOINs)
            if include_neighbors:
                neighbors = self._find_neighbor_tables(
                    schema, relevant_tables, max_hops=max_neighbor_hops
                )
                relevant_tables.update(neighbors)
                logger.debug(
                    f"Added {len(neighbors)} neighbor tables: {neighbors}"
                )

            # Build filtered schema
            filtered_schema = {
                "tables": {},
                "relationships": [],
                "summary": {
                    "table_count": len(relevant_tables),
                    "total_columns": 0,
                    "filtered_from": len(schema.get("tables", {})),
                },
            }

            # Copy relevant tables
            for table_name in relevant_tables:
                if table_name in schema.get("tables", {}):
                    table_info = schema["tables"][table_name]
                    filtered_schema["tables"][table_name] = table_info
                    filtered_schema["summary"]["total_columns"] += len(
                        table_info.get("columns", [])
                    )

            # Copy relevant relationships
            for rel in schema.get("relationships", []):
                if (rel["from_table"] in relevant_tables or
                    rel["to_table"] in relevant_tables):
                    filtered_schema["relationships"].append(rel)

            logger.info(
                f"Filtered schema: {len(relevant_tables)} tables from "
                f"{len(schema.get('tables', {}))} total "
                f"(question: '{question[:50]}...')"
            )

            return filtered_schema

        except ImportError:
            logger.warning("RequiredDataDetector not available, using full schema")
            return schema
        except Exception as e:
            logger.warning(f"Schema filtering failed: {e}, using full schema")
            return schema

    def _find_neighbor_tables(
        self,
        schema: Dict[str, Any],
        seed_tables: set,
        max_hops: int = 1,
    ) -> set:
        """
        Find tables connected to seed tables via foreign keys.

        Uses BFS to find neighbors up to max_hops away.

        Args:
            schema: Schema dictionary
            seed_tables: Starting set of tables
            max_hops: Maximum FK hops to traverse

        Returns:
            Set of neighbor table names (excluding seed tables)
        """
        if not schema.get("relationships"):
            return set()

        # Build adjacency graph
        graph = {}
        for rel in schema["relationships"]:
            from_table = rel["from_table"]
            to_table = rel["to_table"]

            if from_table not in graph:
                graph[from_table] = set()
            graph[from_table].add(to_table)

            if to_table not in graph:
                graph[to_table] = set()
            graph[to_table].add(from_table)

        # BFS to find neighbors
        neighbors = set()
        current_level = set(seed_tables)

        for hop in range(max_hops):
            next_level = set()
            for table in current_level:
                if table in graph:
                    for neighbor in graph[table]:
                        if neighbor not in seed_tables and neighbor not in neighbors:
                            next_level.add(neighbor)
                            neighbors.add(neighbor)
            current_level = next_level
            if not current_level:
                break

        return neighbors

    # ========================================================================
    # PHASE 2: ENRICHED SCHEMA BUILDER - Bridge Tables & Inferred Relationships
    # ========================================================================

    def _detect_bridge_tables(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect bridge/junction tables that connect two other tables (many-to-many).

        Bridge tables typically have:
        - 2+ foreign keys pointing to other tables
        - Few or no columns besides the FK columns
        - Names often contain both table names (e.g., order_items, user_roles)

        Args:
            schema: Schema dictionary

        Returns:
            List of bridge table info with connected tables
        """
        bridge_tables = []

        for table_name, table_info in schema.get("tables", {}).items():
            fks = table_info.get("foreign_keys", [])
            columns = table_info.get("columns", [])

            # A bridge table typically has 2+ FKs
            if len(fks) < 2:
                continue

            # Get non-FK column count (excluding common audit columns)
            audit_columns = {"id", "created_at", "updated_at", "created_by", "updated_by"}
            fk_columns = {fk["column"] for fk in fks}
            pk_columns = set(table_info.get("primary_keys", []))

            other_columns = [
                col for col in columns
                if col["name"] not in fk_columns
                and col["name"] not in pk_columns
                and col["name"].lower() not in audit_columns
            ]

            # Bridge tables typically have few or no non-FK columns
            # or the extra columns are quantity/metadata (like order_items.quantity)
            is_bridge = len(other_columns) <= 3

            if is_bridge:
                referred_tables = [fk["referred_table"] for fk in fks]
                bridge_tables.append({
                    "table": table_name,
                    "connects": referred_tables,
                    "foreign_keys": fks,
                    "extra_columns": [col["name"] for col in other_columns],
                })

        return bridge_tables

    def _infer_relationships(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Infer potential relationships based on column naming conventions.

        Many databases have columns like 'customer_id', 'user_id', 'product_id'
        that reference other tables even without explicit FK constraints.

        Args:
            schema: Schema dictionary

        Returns:
            List of inferred relationships (not already in explicit FKs)
        """
        # Get existing explicit relationships
        existing_rels = set()
        for rel in schema.get("relationships", []):
            key = (rel["from_table"], rel["from_column"], rel["to_table"])
            existing_rels.add(key)

        # Build set of table names (singular and plural forms)
        table_names = set(schema.get("tables", {}).keys())
        table_singular = {}
        for table in table_names:
            # Handle common pluralization
            singular = table.rstrip("s") if table.endswith("s") else table
            table_singular[singular.lower()] = table
            table_singular[table.lower()] = table

        inferred = []

        for table_name, table_info in schema.get("tables", {}).items():
            for col in table_info.get("columns", []):
                col_name = col["name"].lower()

                # Check for *_id pattern
                if col_name.endswith("_id"):
                    # Extract potential table name (e.g., "customer_id" -> "customer")
                    potential_table = col_name[:-3]  # Remove "_id"

                    # Check if referenced table exists
                    if potential_table in table_singular:
                        referred_table = table_singular[potential_table]

                        # Skip self-references and existing explicit relationships
                        if referred_table == table_name:
                            continue

                        key = (table_name, col["name"], referred_table)
                        if key in existing_rels:
                            continue

                        # Find likely PK column in referred table
                        referred_info = schema["tables"].get(referred_table, {})
                        referred_pks = referred_info.get("primary_keys", [])
                        referred_col = referred_pks[0] if referred_pks else "id"

                        inferred.append({
                            "from_table": table_name,
                            "from_column": col["name"],
                            "to_table": referred_table,
                            "to_column": referred_col,
                            "inferred": True,
                            "reason": f"Column '{col['name']}' matches table '{referred_table}'"
                        })

        return inferred

    def get_enriched_schema_context(self, schema: Dict[str, Any]) -> str:
        """
        Build enriched schema context with bridge tables and inferred relationships.

        This provides additional context for the LLM to understand:
        1. Which tables are bridge/junction tables (many-to-many)
        2. Potential relationships even without explicit FK constraints
        3. Clear guidance on how to join tables

        Args:
            schema: Schema dictionary

        Returns:
            Formatted string with enriched relationship information
        """
        lines = []

        # Detect bridge tables
        bridge_tables = self._detect_bridge_tables(schema)
        if bridge_tables:
            lines.append("")
            lines.append("BRIDGE TABLES (for many-to-many relationships):")
            for bt in bridge_tables:
                connects = " ↔ ".join(bt["connects"])
                lines.append(f"  • {bt['table']} connects: {connects}")
                if bt["extra_columns"]:
                    lines.append(f"    (also has: {', '.join(bt['extra_columns'])})")
            lines.append("")

        # Infer relationships
        inferred_rels = self._infer_relationships(schema)
        if inferred_rels:
            lines.append("INFERRED RELATIONSHIPS (from column naming conventions):")
            for rel in inferred_rels:
                lines.append(
                    f"  • {rel['from_table']}.{rel['from_column']} → "
                    f"{rel['to_table']}.{rel['to_column']} (likely FK)"
                )
            lines.append("")

        # Generate explicit join examples for common patterns
        all_rels = schema.get("relationships", []) + inferred_rels
        if all_rels:
            lines.append("JOIN EXAMPLES (use these exact patterns):")
            seen_pairs = set()
            for rel in all_rels[:10]:  # Limit to 10 examples
                pair = (rel["from_table"], rel["to_table"])
                if pair in seen_pairs or (pair[1], pair[0]) in seen_pairs:
                    continue
                seen_pairs.add(pair)

                lines.append(
                    f"  • {rel['from_table']} JOIN {rel['to_table']}: "
                    f"ON {rel['from_table']}.{rel['from_column']} = "
                    f"{rel['to_table']}.{rel['to_column']}"
                )
            lines.append("")

        return "\n".join(lines)
