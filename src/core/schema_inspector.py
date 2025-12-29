"""Database schema introspection"""
import logging
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

                # Add relationships
                for fk in foreign_keys:
                    schema["relationships"].append({
                        "from_table": table_name,
                        "from_column": fk["column"],
                        "to_table": fk["referred_table"],
                        "to_column": fk["referred_column"],
                    })

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

            elif db_name in ["mysql", "duckdb"]:
                # MySQL and DuckDB - use information_schema
                # Simplified query that works for both
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

        lines = ["=" * 50]
        lines.append("AVAILABLE TABLES (USE ONLY THESE):")
        lines.append(", ".join(table_names))
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
                semantic_hint = ""
                if col.get("semantic_type"):
                    sem_type = col["semantic_type"]
                    if sem_type == "location":
                        # Provide location-specific guidance
                        fmt = col.get("value_format", "unknown")
                        subtype = col.get("location_subtype", "")
                        if fmt == "code":
                            semantic_hint = f" [LOCATION:{subtype} - use 2-letter codes like 'CA', 'NY']"
                        elif fmt == "full_name":
                            semantic_hint = f" [LOCATION:{subtype} - use full names like 'California', 'New York']"
                        else:
                            semantic_hint = f" [LOCATION:{subtype}]"
                    elif sem_type == "categorical":
                        semantic_hint = " [CATEGORICAL - use exact enum values]"

                # Add sample values if available (helps LLM understand format)
                sample_hint = ""
                if "sample_values" in col and col["sample_values"]:
                    samples = col["sample_values"]
                    sample_str = ", ".join(repr(s) for s in samples[:5])
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
            lines.append("\nRelationships:")
            for rel in schema["relationships"]:
                lines.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']}"
                )

        # Add reminder at the end
        lines.append("")
        lines.append("=" * 50)
        lines.append(f"REMINDER: Only use tables: {', '.join(table_names)}")
        lines.append("DO NOT use tables from examples if they don't exist above!")
        lines.append("=" * 50)

        return "\n".join(lines)
