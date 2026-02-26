"""Database schema introspection"""
import logging
import re
from typing import Dict, List, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Inspector

from src.core.column_semantics import ColumnSemanticsDetector, ColumnSemanticType

logger = logging.getLogger(__name__)

# Strict allowlist for SQL identifiers used in PRAGMA / SHOW statements
# where bound parameters are not supported.
_SAFE_IDENT_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_$]*$')


def _safe_identifier(name: str) -> str:
    """Validate that *name* is a safe SQL identifier.

    Raises ValueError for anything that doesn't match the allowlist so it
    cannot be used for SQL injection via PRAGMA or SHOW statements.
    """
    if not _SAFE_IDENT_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier rejected: {name!r}")
    return name

# Which extended object types each dialect supports
DIALECT_CAPABILITIES: Dict[str, Dict[str, bool]] = {
    "sqlite":     {"views": True,  "sequences": False, "check_constraints": False, "routines": False, "triggers": True,  "enums": False},
    "postgresql": {"views": True,  "sequences": True,  "check_constraints": True,  "routines": True,  "triggers": True,  "enums": True},
    "mysql":      {"views": True,  "sequences": False, "check_constraints": True,  "routines": True,  "triggers": True,  "enums": False},
    "mssql":      {"views": True,  "sequences": True,  "check_constraints": True,  "routines": True,  "triggers": True,  "enums": False},
    "oracle":     {"views": True,  "sequences": True,  "check_constraints": True,  "routines": True,  "triggers": True,  "enums": False},
    "duckdb":     {"views": True,  "sequences": True,  "check_constraints": False, "routines": False, "triggers": False, "enums": False},
}


def _get_dialect_name(session) -> str:
    """Safely extract the dialect name from a sync or async SQLAlchemy session.

    Works with:
    - Sync sessions (DuckDB): session.bind.dialect.name
    - Async sessions (PostgreSQL, MySQL, etc.): session.get_bind().dialect.name
    """
    # Try direct bind first (sync sessions)
    try:
        if session.bind is not None:
            return session.bind.dialect.name
    except Exception:
        pass

    # Async session: try get_bind() on the underlying sync session
    try:
        sync_session = getattr(session, 'sync_session', None)
        if sync_session is not None:
            bind = sync_session.get_bind()
            if bind is not None:
                return bind.dialect.name
    except Exception:
        pass

    # Last resort: check if session has a cached _db_name attribute
    # (set by SchemaInspector when dialect is known from caller)
    return getattr(session, '_dialect_hint', "unknown")


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
            # Build safe query with validated identifiers
            safe_table = _safe_identifier(table_name)
            safe_col = _safe_identifier(column_name)
            query = text(f'SELECT DISTINCT "{safe_col}" FROM "{safe_table}" WHERE "{safe_col}" IS NOT NULL LIMIT :limit')
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
        include_views: bool = False,
        include_sequences: bool = False,
        include_check_constraints: bool = False,
        include_routines: bool = False,
        include_triggers: bool = False,
        include_enums: bool = False,
    ) -> Dict[str, Any]:
        """
        Get complete database schema information

        Args:
            session: Database session
            schema_name: Schema name (None for default)
            include_samples: Whether to include sample values for key columns (state, status, type, etc.)
            include_views: Include database views
            include_sequences: Include sequences
            include_check_constraints: Include check constraints
            include_routines: Include stored procedures and functions
            include_triggers: Include triggers
            include_enums: Include enum types (PostgreSQL only)

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

            # Extended objects — only fetched when explicitly requested
            db_name = _get_dialect_name(session)
            caps = DIALECT_CAPABILITIES.get(db_name, {})

            if include_views and caps.get("views"):
                schema["views"] = await self.get_views(session, schema_name)
                schema["summary"]["view_count"] = len(schema["views"])

            if include_sequences and caps.get("sequences"):
                schema["sequences"] = await self.get_sequences(session, schema_name)
                schema["summary"]["sequence_count"] = len(schema["sequences"])

            if include_check_constraints and caps.get("check_constraints"):
                schema["check_constraints"] = await self.get_check_constraints(session, schema_name)
                schema["summary"]["check_constraint_count"] = len(schema["check_constraints"])

            if include_routines and caps.get("routines"):
                schema["routines"] = await self.get_routines(session, schema_name)
                schema["summary"]["routine_count"] = len(schema["routines"])

            if include_triggers and caps.get("triggers"):
                schema["triggers"] = await self.get_triggers(session, schema_name)
                schema["summary"]["trigger_count"] = len(schema["triggers"])

            if include_enums and caps.get("enums"):
                schema["enums"] = await self.get_enums(session, schema_name)
                schema["summary"]["enum_count"] = len(schema["enums"])

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
            db_name = _get_dialect_name(session)

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
            db_name = _get_dialect_name(session)

            if db_name == "sqlite":
                # SQLite query using PRAGMA
                safe_name = _safe_identifier(table_name)
                query = f"PRAGMA table_info({safe_name})"
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
                # PostgreSQL/MySQL/DuckDB - use information_schema
                # If schema_name provided, filter by it; otherwise, exclude system schemas
                if schema_name:
                    query = """
                        SELECT
                            column_name,
                            data_type,
                            is_nullable,
                            column_default,
                            character_maximum_length
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        AND table_schema = :schema_name
                        ORDER BY ordinal_position
                    """
                    params = {"table_name": table_name, "schema_name": schema_name}
                else:
                    # No schema specified - exclude system schemas dynamically
                    query = """
                        SELECT
                            column_name,
                            data_type,
                            is_nullable,
                            column_default,
                            character_maximum_length
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        AND table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                        ORDER BY ordinal_position
                    """
                    params = {"table_name": table_name}

                result = await self._execute_query(session, text(query), params)

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
            db_name = _get_dialect_name(session)

            if db_name == "sqlite":
                # SQLite - use PRAGMA
                safe_name = _safe_identifier(table_name)
                query = f"PRAGMA table_info({safe_name})"
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
            db_name = _get_dialect_name(session)

            if db_name == "sqlite":
                # SQLite - use PRAGMA foreign_key_list
                safe_name = _safe_identifier(table_name)
                query = f"PRAGMA foreign_key_list({safe_name})"
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
                safe_name = _safe_identifier(table_name)
                query = f"""
                    SELECT
                        constraint_column_names,
                        constraint_name,
                        constraint_text
                    FROM duckdb_constraints()
                    WHERE table_name = '{safe_name}'
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
        Get indexes for a table with columns and unique constraint info.

        Args:
            session: Database session
            table_name: Table name
            schema_name: Schema name

        Returns:
            List of index dictionaries with:
            - name: Index name
            - columns: List of column names in the index
            - unique: Whether the index has a unique constraint
        """
        try:
            db_name = _get_dialect_name(session)

            if db_name == "sqlite":
                # SQLite - use PRAGMA index_list and index_info
                # First get list of indexes
                safe_name = _safe_identifier(table_name)
                query = f"PRAGMA index_list({safe_name})"
                result = await self._execute_query(session, text(query))

                indexes = []
                for row in result.all():
                    # index_list returns: seq, name, unique, origin, partial
                    index_name = row[1]
                    is_unique = row[2] == 1

                    # Get columns for this index
                    safe_idx = _safe_identifier(index_name)
                    col_query = f"PRAGMA index_info({safe_idx})"
                    col_result = await self._execute_query(session, text(col_query))
                    columns = [col_row[2] for col_row in col_result.all()]  # column name at index 2

                    indexes.append({
                        "name": index_name,
                        "columns": columns,
                        "unique": is_unique,
                    })

                return indexes

            elif db_name == "duckdb":
                # DuckDB - use duckdb_indexes()
                safe_name = _safe_identifier(table_name)
                query = f"""
                    SELECT
                        index_name,
                        is_unique,
                        sql
                    FROM duckdb_indexes()
                    WHERE table_name = '{safe_name}'
                """
                result = await self._execute_query(session, text(query))

                indexes = []
                for row in result.all():
                    index_name = row[0]
                    is_unique = row[1]
                    sql = row[2] if len(row) > 2 else ""

                    # Parse columns from SQL if available
                    columns = self._parse_index_columns_from_sql(sql)

                    indexes.append({
                        "name": index_name,
                        "columns": columns,
                        "unique": is_unique,
                    })

                return indexes

            elif db_name == "mysql":
                # MySQL - use SHOW INDEX
                safe_name = _safe_identifier(table_name)
                query = f"SHOW INDEX FROM {safe_name}"
                result = await self._execute_query(session, text(query))

                # Group by index name
                index_map = {}
                for row in result.all():
                    # SHOW INDEX returns: Table, Non_unique, Key_name, Seq_in_index, Column_name, ...
                    index_name = row[2]
                    is_unique = row[1] == 0  # Non_unique: 0 means unique
                    column_name = row[4]

                    if index_name not in index_map:
                        index_map[index_name] = {
                            "name": index_name,
                            "columns": [],
                            "unique": is_unique,
                        }
                    index_map[index_name]["columns"].append(column_name)

                return list(index_map.values())

            else:
                # PostgreSQL - query pg_indexes with column info
                query = """
                    SELECT
                        i.relname AS index_name,
                        ix.indisunique AS is_unique,
                        array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) AS columns
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    WHERE t.relname = :table_name
                    AND n.nspname = COALESCE(:schema_name, 'public')
                    AND NOT ix.indisprimary
                    GROUP BY i.relname, ix.indisunique
                """

                result = await self._execute_query(session, text(query), {
                    "table_name": table_name,
                    "schema_name": schema_name or "public"
                })

                indexes = []
                for row in result.all():
                    indexes.append({
                        "name": row[0],
                        "columns": list(row[2]) if row[2] else [],
                        "unique": row[1],
                    })

                return indexes

        except Exception as e:
            logger.debug(f"Error getting indexes for {table_name}: {e}")
            return []

    # ========================================================================
    # EXTENDED OBJECT INTROSPECTION (Phase 20 — optional, user-toggled)
    # ========================================================================

    async def get_views(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get database views with their definitions."""
        try:
            db_name = _get_dialect_name(session)

            if db_name == "sqlite":
                query = text("SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name")
                result = await self._execute_query(session, query)
                return [{"name": row[0], "definition": row[1] or ""} for row in result.all()]

            elif db_name == "duckdb":
                query = text("""
                    SELECT table_name, sql
                    FROM duckdb_views()
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY table_name
                """)
                result = await self._execute_query(session, query)
                return [{"name": row[0], "definition": row[1] or ""} for row in result.all()]

            elif db_name == "mysql":
                query = text("""
                    SELECT table_name, view_definition
                    FROM information_schema.views
                    WHERE table_schema = DATABASE()
                    ORDER BY table_name
                """)
                result = await self._execute_query(session, query)
                return [{"name": row[0], "definition": row[1] or ""} for row in result.all()]

            elif db_name == "mssql":
                query = text("""
                    SELECT name, OBJECT_DEFINITION(object_id) AS definition
                    FROM sys.views
                    ORDER BY name
                """)
                result = await self._execute_query(session, query)
                return [{"name": row[0], "definition": row[1] or ""} for row in result.all()]

            elif db_name == "oracle":
                query = text("SELECT view_name, text FROM user_views ORDER BY view_name")
                result = await self._execute_query(session, query)
                return [{"name": row[0], "definition": row[1] or ""} for row in result.all()]

            else:
                # PostgreSQL
                query = text("""
                    SELECT viewname, definition
                    FROM pg_views
                    WHERE schemaname = COALESCE(:schema_name, 'public')
                    ORDER BY viewname
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})
                return [{"name": row[0], "definition": row[1] or ""} for row in result.all()]

        except Exception as e:
            logger.debug(f"Error getting views: {e}")
            return []

    async def get_sequences(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get database sequences."""
        try:
            db_name = _get_dialect_name(session)

            if db_name == "postgresql":
                query = text("""
                    SELECT sequencename, data_type,
                           start_value, increment_by, min_value, max_value
                    FROM pg_sequences
                    WHERE schemaname = COALESCE(:schema_name, 'public')
                    ORDER BY sequencename
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})
                return [
                    {"name": r[0], "data_type": r[1] or "bigint",
                     "start_value": r[2], "increment": r[3],
                     "min_value": r[4], "max_value": r[5]}
                    for r in result.all()
                ]

            elif db_name == "mssql":
                query = text("""
                    SELECT name,
                           CAST(start_value AS BIGINT),
                           CAST(increment AS BIGINT),
                           CAST(minimum_value AS BIGINT),
                           CAST(maximum_value AS BIGINT)
                    FROM sys.sequences
                    ORDER BY name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "data_type": "bigint",
                     "start_value": r[1], "increment": r[2],
                     "min_value": r[3], "max_value": r[4]}
                    for r in result.all()
                ]

            elif db_name == "oracle":
                query = text("""
                    SELECT sequence_name, min_value, max_value,
                           increment_by, last_number
                    FROM user_sequences
                    ORDER BY sequence_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "data_type": "number",
                     "start_value": r[4], "increment": r[3],
                     "min_value": r[1], "max_value": r[2]}
                    for r in result.all()
                ]

            elif db_name == "duckdb":
                query = text("""
                    SELECT sequence_name, start_value, increment_by,
                           min_value, max_value
                    FROM duckdb_sequences()
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY sequence_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "data_type": "bigint",
                     "start_value": r[1], "increment": r[2],
                     "min_value": r[3], "max_value": r[4]}
                    for r in result.all()
                ]

            # sqlite, mysql: no sequence support
            return []

        except Exception as e:
            logger.debug(f"Error getting sequences: {e}")
            return []

    async def get_check_constraints(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get check constraints (excludes system-generated NOT NULL constraints)."""
        try:
            db_name = _get_dialect_name(session)

            if db_name == "postgresql":
                query = text("""
                    SELECT conname, conrelid::regclass::text, pg_get_constraintdef(oid)
                    FROM pg_constraint
                    WHERE contype = 'c'
                    AND connamespace = (
                        SELECT oid FROM pg_namespace
                        WHERE nspname = COALESCE(:schema_name, 'public')
                    )
                    AND conname NOT LIKE '%_not_null'
                    ORDER BY conrelid::regclass::text, conname
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})
                return [
                    {"table_name": r[1], "constraint_name": r[0], "definition": r[2] or ""}
                    for r in result.all()
                ]

            elif db_name == "mysql":
                query = text("""
                    SELECT cc.constraint_name, tc.table_name, cc.check_clause
                    FROM information_schema.check_constraints cc
                    JOIN information_schema.table_constraints tc
                        ON cc.constraint_name = tc.constraint_name
                        AND cc.constraint_schema = tc.constraint_schema
                    WHERE cc.constraint_schema = DATABASE()
                    ORDER BY tc.table_name, cc.constraint_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"table_name": r[1], "constraint_name": r[0], "definition": r[2] or ""}
                    for r in result.all()
                ]

            elif db_name == "mssql":
                query = text("""
                    SELECT cc.name, t.name, cc.definition
                    FROM sys.check_constraints cc
                    JOIN sys.tables t ON cc.parent_object_id = t.object_id
                    ORDER BY t.name, cc.name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"table_name": r[1], "constraint_name": r[0], "definition": r[2] or ""}
                    for r in result.all()
                ]

            elif db_name == "oracle":
                query = text("""
                    SELECT constraint_name, table_name, search_condition
                    FROM user_constraints
                    WHERE constraint_type = 'C'
                    AND generated != 'GENERATED NAME'
                    ORDER BY table_name, constraint_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"table_name": r[1], "constraint_name": r[0], "definition": r[2] or ""}
                    for r in result.all()
                ]

            # sqlite, duckdb: no check constraint introspection
            return []

        except Exception as e:
            logger.debug(f"Error getting check constraints: {e}")
            return []

    async def get_routines(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get stored procedures and functions."""
        try:
            db_name = _get_dialect_name(session)

            if db_name == "postgresql":
                query = text("""
                    SELECT p.proname,
                           CASE WHEN p.prokind = 'p' THEN 'procedure' ELSE 'function' END,
                           l.lanname,
                           pg_get_functiondef(p.oid),
                           pg_get_function_result(p.oid)
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    JOIN pg_language l ON p.prolang = l.oid
                    WHERE n.nspname = COALESCE(:schema_name, 'public')
                    AND l.lanname != 'c'
                    AND l.lanname != 'internal'
                    ORDER BY p.proname
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})
                return [
                    {"name": r[0], "type": r[1], "language": r[2] or "",
                     "definition": r[3] or "", "return_type": r[4] or ""}
                    for r in result.all()
                ]

            elif db_name == "mysql":
                query = text("""
                    SELECT routine_name, routine_type, routine_definition,
                           dtd_identifier
                    FROM information_schema.routines
                    WHERE routine_schema = DATABASE()
                    ORDER BY routine_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "type": (r[1] or "function").lower(),
                     "language": "sql", "definition": r[2] or "",
                     "return_type": r[3] or ""}
                    for r in result.all()
                ]

            elif db_name == "mssql":
                query = text("""
                    SELECT name,
                           CASE WHEN type = 'P' THEN 'procedure'
                                ELSE 'function' END,
                           OBJECT_DEFINITION(object_id)
                    FROM sys.objects
                    WHERE type IN ('P', 'FN', 'TF', 'IF')
                    ORDER BY name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "type": r[1], "language": "tsql",
                     "definition": r[2] or "", "return_type": ""}
                    for r in result.all()
                ]

            elif db_name == "oracle":
                query = text("""
                    SELECT object_name,
                           LOWER(object_type),
                           DBMS_METADATA.GET_DDL(object_type, object_name) AS ddl
                    FROM user_objects
                    WHERE object_type IN ('PROCEDURE', 'FUNCTION')
                    ORDER BY object_name
                """)
                try:
                    result = await self._execute_query(session, query)
                    return [
                        {"name": r[0], "type": r[1], "language": "plsql",
                         "definition": r[2] or "", "return_type": ""}
                        for r in result.all()
                    ]
                except Exception:
                    # DBMS_METADATA may not be available — fall back to user_source
                    query2 = text("""
                        SELECT name, LOWER(type), LISTAGG(text, '') WITHIN GROUP (ORDER BY line)
                        FROM user_source
                        WHERE type IN ('PROCEDURE', 'FUNCTION')
                        GROUP BY name, type
                        ORDER BY name
                    """)
                    result = await self._execute_query(session, query2)
                    return [
                        {"name": r[0], "type": r[1], "language": "plsql",
                         "definition": r[2] or "", "return_type": ""}
                        for r in result.all()
                    ]

            # sqlite, duckdb: no routine support
            return []

        except Exception as e:
            logger.debug(f"Error getting routines: {e}")
            return []

    async def get_triggers(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get database triggers."""
        try:
            db_name = _get_dialect_name(session)

            if db_name == "sqlite":
                query = text("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name")
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "table_name": r[1], "timing": "",
                     "event": "", "definition": r[2] or ""}
                    for r in result.all()
                ]

            elif db_name == "postgresql":
                query = text("""
                    SELECT trigger_name, event_object_table,
                           action_timing, event_manipulation,
                           action_statement
                    FROM information_schema.triggers
                    WHERE trigger_schema = COALESCE(:schema_name, 'public')
                    ORDER BY event_object_table, trigger_name
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})
                return [
                    {"name": r[0], "table_name": r[1], "timing": r[2] or "",
                     "event": r[3] or "", "definition": r[4] or ""}
                    for r in result.all()
                ]

            elif db_name == "mysql":
                query = text("""
                    SELECT trigger_name, event_object_table,
                           action_timing, event_manipulation,
                           action_statement
                    FROM information_schema.triggers
                    WHERE trigger_schema = DATABASE()
                    ORDER BY event_object_table, trigger_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "table_name": r[1], "timing": r[2] or "",
                     "event": r[3] or "", "definition": r[4] or ""}
                    for r in result.all()
                ]

            elif db_name == "mssql":
                query = text("""
                    SELECT t.name, OBJECT_NAME(t.parent_id),
                           te.type_desc,
                           OBJECT_DEFINITION(t.object_id)
                    FROM sys.triggers t
                    JOIN sys.trigger_events te ON t.object_id = te.object_id
                    WHERE t.parent_id != 0
                    ORDER BY OBJECT_NAME(t.parent_id), t.name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "table_name": r[1], "timing": "",
                     "event": r[2] or "", "definition": r[3] or ""}
                    for r in result.all()
                ]

            elif db_name == "oracle":
                query = text("""
                    SELECT trigger_name, table_name,
                           trigger_type, triggering_event,
                           trigger_body
                    FROM user_triggers
                    ORDER BY table_name, trigger_name
                """)
                result = await self._execute_query(session, query)
                return [
                    {"name": r[0], "table_name": r[1], "timing": r[2] or "",
                     "event": r[3] or "", "definition": r[4] or ""}
                    for r in result.all()
                ]

            return []

        except Exception as e:
            logger.debug(f"Error getting triggers: {e}")
            return []

    async def get_enums(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get enum types (PostgreSQL only)."""
        try:
            db_name = _get_dialect_name(session)

            if db_name == "postgresql":
                query = text("""
                    SELECT t.typname,
                           array_agg(e.enumlabel ORDER BY e.enumsortorder)
                    FROM pg_type t
                    JOIN pg_enum e ON t.oid = e.enumtypid
                    JOIN pg_namespace n ON t.typnamespace = n.oid
                    WHERE n.nspname = COALESCE(:schema_name, 'public')
                    GROUP BY t.typname
                    ORDER BY t.typname
                """)
                result = await self._execute_query(session, query, {"schema_name": schema_name or "public"})
                return [
                    {"name": r[0], "values": list(r[1]) if r[1] else []}
                    for r in result.all()
                ]

            return []

        except Exception as e:
            logger.debug(f"Error getting enums: {e}")
            return []

    def _parse_index_columns_from_sql(self, sql: str) -> List[str]:
        """
        Parse column names from CREATE INDEX SQL statement.

        Args:
            sql: CREATE INDEX SQL statement

        Returns:
            List of column names
        """
        if not sql:
            return []

        # Pattern: CREATE ... INDEX ... ON table_name (col1, col2, ...)
        match = re.search(r'\(([^)]+)\)\s*$', sql)
        if match:
            columns_str = match.group(1)
            # Split by comma and clean up
            columns = [col.strip().strip('"').strip('`') for col in columns_str.split(',')]
            return columns
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
