"""Cassandra schema inspector - queries system_schema tables.

Cassandra has proper keyspace/table/column metadata, making schema
introspection straightforward compared to other NoSQL databases.
"""
import asyncio
import logging
from typing import Any, Dict

from src.nosql.base import NoSQLSchemaInspector

logger = logging.getLogger(__name__)


class CassandraSchemaInspector(NoSQLSchemaInspector):
    """Inspect Cassandra schema from system_schema tables."""

    def __init__(self, session, keyspace: str):
        self.session = session  # cassandra-driver Session (sync)
        self.keyspace = keyspace

    async def get_schema(self, connection: Any = None) -> Dict[str, Any]:
        """Query system_schema for table and column metadata."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_schema_sync)

    def _get_schema_sync(self) -> Dict[str, Any]:
        """Synchronous schema introspection."""
        tables = {}

        # Get tables in keyspace
        rows = self.session.execute(
            "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s",
            [self.keyspace],
        )

        for row in rows:
            table_name = row.table_name
            columns = self._get_columns(table_name)
            tables[table_name] = {
                "columns": columns,
                "row_count": 0,  # Cassandra doesn't expose row count cheaply
            }

        return {
            "tables": tables,
            "database_type": "cassandra",
            "keyspace": self.keyspace,
        }

    def _get_columns(self, table_name: str):
        """Get columns for a table from system_schema."""
        rows = self.session.execute(
            "SELECT column_name, type, kind FROM system_schema.columns "
            "WHERE keyspace_name = %s AND table_name = %s",
            [self.keyspace, table_name],
        )

        columns = []
        for row in rows:
            columns.append({
                "name": row.column_name,
                "type": row.type,
                "nullable": True,  # Cassandra columns are always nullable
                "kind": row.kind,  # partition_key, clustering, regular, static
            })

        return columns

    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Format Cassandra schema for CQL generation prompts."""
        keyspace = schema.get("keyspace", "unknown")
        lines = [f"DATABASE: Apache Cassandra (CQL)", f"Keyspace: {keyspace}", ""]

        tables = schema.get("tables", {})
        for table_name, table_info in tables.items():
            lines.append(f"Table: {table_name}")
            columns = table_info.get("columns", [])
            if columns:
                pk_cols = [c for c in columns if c.get("kind") == "partition_key"]
                ck_cols = [c for c in columns if c.get("kind") == "clustering"]
                reg_cols = [c for c in columns if c.get("kind") in ("regular", "static")]

                if pk_cols:
                    pk_str = ", ".join(f"{c['name']} ({c['type']})" for c in pk_cols)
                    lines.append(f"  Partition Key: {pk_str}")
                if ck_cols:
                    ck_str = ", ".join(f"{c['name']} ({c['type']})" for c in ck_cols)
                    lines.append(f"  Clustering Columns: {ck_str}")
                if reg_cols:
                    lines.append("  Columns:")
                    for col in reg_cols:
                        lines.append(f"    - {col['name']}: {col['type']}")
            lines.append("")

        lines.append("CQL Notes:")
        lines.append("- Must include partition key in WHERE clause")
        lines.append("- Use ALLOW FILTERING only when necessary")
        lines.append("- No JOIN, no subqueries")
        lines.append("- Aggregations: COUNT, SUM, AVG, MIN, MAX")

        return "\n".join(lines)
