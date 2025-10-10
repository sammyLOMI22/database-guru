"""Database schema introspection"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Inspector

logger = logging.getLogger(__name__)


class SchemaInspector:
    """
    Introspect database schema to discover tables, columns, and relationships
    """

    def __init__(self):
        """Initialize schema inspector"""
        pass

    async def get_full_schema(
        self,
        session: AsyncSession,
        schema_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get complete database schema information

        Args:
            session: Database session
            schema_name: Schema name (None for default)

        Returns:
            Dictionary with tables, columns, relationships, indexes
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

            for table_name in tables:
                # Get columns
                columns = await self.get_columns(session, table_name, schema_name)

                # Get primary keys
                primary_keys = await self.get_primary_keys(session, table_name, schema_name)

                # Get foreign keys
                foreign_keys = await self.get_foreign_keys(session, table_name, schema_name)

                # Get indexes
                indexes = await self.get_indexes(session, table_name, schema_name)

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
            # PostgreSQL query
            query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = COALESCE(:schema_name, 'public')
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """

            result = await session.execute(
                text(query),
                {"schema_name": schema_name or "public"}
            )

            tables = [row[0] for row in result.fetchall()]
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

            result = await session.execute(
                text(query),
                {
                    "table_name": table_name,
                    "schema_name": schema_name or "public"
                }
            )

            columns = []
            for row in result.fetchall():
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
            query = """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid
                    AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = :table_name::regclass
                AND i.indisprimary
            """

            result = await session.execute(
                text(query),
                {"table_name": table_name}
            )

            return [row[0] for row in result.fetchall()]

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

            result = await session.execute(
                text(query),
                {
                    "table_name": table_name,
                    "schema_name": schema_name or "public"
                }
            )

            foreign_keys = []
            for row in result.fetchall():
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

            result = await session.execute(
                text(query),
                {
                    "table_name": table_name,
                    "schema_name": schema_name or "public"
                }
            )

            indexes = []
            for row in result.fetchall():
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
        lines = ["Database Schema:\n"]

        # Add summary
        lines.append(f"Tables: {schema['summary']['table_count']}")
        lines.append(f"Total Columns: {schema['summary']['total_columns']}\n")

        # Add table details
        for table_name, table_info in schema["tables"].items():
            lines.append(f"\nTable: {table_name}")

            # Columns
            lines.append("  Columns:")
            for col in table_info["columns"]:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                pk_marker = " [PK]" if col["name"] in table_info["primary_keys"] else ""
                lines.append(f"    - {col['name']}: {col['type']} {nullable}{pk_marker}")

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

        return "\n".join(lines)
