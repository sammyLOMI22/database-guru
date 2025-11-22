"""
Data Sampling Tools

Tools for exploring and sampling database data:
- get_sample_data: Get sample rows from a table
- get_column_values: Get distinct values from a column
- count_rows: Count rows with optional filter

These tools help understand data format before query generation.
Essential for knowing if states are 'CA' vs 'California', etc.

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import time
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from src.tools.base import BaseTool, ToolResult, ToolDefinition, ToolCategory
from src.tools.tool_registry import register_tool

logger = logging.getLogger(__name__)


@register_tool
class GetSampleDataTool(BaseTool):
    """
    Get sample rows from a table to understand data format.

    Essential for understanding what data looks like before querying.
    """

    name = "get_sample_data"
    description = "Get sample rows from a table to understand data format and content."
    category = ToolCategory.DATA
    cacheable = True
    cache_ttl = 300  # 5 minutes - data can change more frequently

    async def execute(
        self,
        table_name: str,
        limit: int = 5,
        columns: Optional[List[str]] = None
    ) -> ToolResult:
        """
        Get sample rows from a table.

        Args:
            table_name: Table to sample from
            limit: Number of rows to return (default: 5, max: 20)
            columns: Optional list of specific columns to include

        Returns:
            ToolResult with sample data:
            {
                "table": "customers",
                "columns": ["id", "name", "state"],
                "rows": [{"id": 1, "name": "John", "state": "CA"}],
                "row_count": 5
            }
        """
        start = time.time()

        try:
            # Limit to prevent excessive data retrieval
            limit = min(limit, 20)

            # Build query
            if columns:
                # Sanitize column names (basic protection)
                safe_columns = [c.replace('"', '').replace("'", "") for c in columns]
                cols = ", ".join(f'"{c}"' for c in safe_columns)
            else:
                cols = "*"

            # Safe table name
            safe_table = table_name.replace('"', '').replace("'", "")

            query = text(f'SELECT {cols} FROM "{safe_table}" LIMIT :limit')
            result = await self.schema_inspector._execute_query(
                self.session, query, {"limit": limit}
            )

            rows = result.fetchall()
            column_names = list(result.keys()) if hasattr(result, 'keys') else []

            # Convert rows to dicts, handling various types
            row_dicts = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(column_names):
                    value = row[i]
                    # Convert non-serializable types to string
                    if hasattr(value, 'isoformat'):  # datetime
                        value = value.isoformat()
                    elif isinstance(value, bytes):
                        value = value.decode('utf-8', errors='replace')
                    row_dict[col] = value
                row_dicts.append(row_dict)

            return ToolResult(
                success=True,
                data={
                    "table": safe_table,
                    "columns": column_names,
                    "rows": row_dicts,
                    "row_count": len(row_dicts),
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"get_sample_data failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
                execution_time_ms=self._measure_execution(start),
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {
                    "type": "string",
                    "description": "Table to sample from"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of rows (default: 5, max: 20)",
                    "default": 5
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific columns to include"
                },
            },
            required_params=["table_name"],
            examples=[
                {
                    "table_name": "customers",
                    "limit": 3,
                    "result": "[{id: 1, name: 'John', state: 'CA'}, ...]"
                },
            ],
        )


@register_tool
class GetColumnValuesTool(BaseTool):
    """
    Get distinct values from a column.

    Essential for understanding data format:
    - Are states stored as 'CA' or 'California'?
    - Are statuses 'pending', 'PENDING', or 'Pending'?
    """

    name = "get_column_values"
    description = "Get distinct values from a column. Essential for understanding data format (e.g., 'CA' vs 'California')."
    category = ToolCategory.DATA
    cacheable = True
    cache_ttl = 300

    async def execute(
        self,
        table_name: str,
        column_name: str,
        limit: int = 20
    ) -> ToolResult:
        """
        Get distinct values from a column.

        Args:
            table_name: Table containing the column
            column_name: Column to get values from
            limit: Maximum number of distinct values (default: 20, max: 50)

        Returns:
            ToolResult with values:
            {
                "table": "customers",
                "column": "state",
                "distinct_values": ["CA", "NY", "TX"],
                "count": 3
            }
        """
        start = time.time()

        try:
            # Limit for performance
            limit = min(limit, 50)

            # Use schema_inspector's existing method if available
            if hasattr(self.schema_inspector, 'sample_column_values'):
                values = await self.schema_inspector.sample_column_values(
                    self.session, table_name, column_name, limit
                )
            else:
                # Fallback to direct query
                safe_table = table_name.replace('"', '').replace("'", "")
                safe_column = column_name.replace('"', '').replace("'", "")

                query = text(
                    f'SELECT DISTINCT "{safe_column}" FROM "{safe_table}" '
                    f'WHERE "{safe_column}" IS NOT NULL LIMIT :limit'
                )
                result = await self.schema_inspector._execute_query(
                    self.session, query, {"limit": limit}
                )
                values = [row[0] for row in result.fetchall()]

            # Convert non-serializable values
            clean_values = []
            for v in values:
                if hasattr(v, 'isoformat'):
                    clean_values.append(v.isoformat())
                elif isinstance(v, bytes):
                    clean_values.append(v.decode('utf-8', errors='replace'))
                else:
                    clean_values.append(v)

            return ToolResult(
                success=True,
                data={
                    "table": table_name,
                    "column": column_name,
                    "distinct_values": clean_values,
                    "count": len(clean_values),
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"get_column_values failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
                execution_time_ms=self._measure_execution(start),
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {
                    "type": "string",
                    "description": "Table containing the column"
                },
                "column_name": {
                    "type": "string",
                    "description": "Column to get values from"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max distinct values (default: 20, max: 50)",
                    "default": 20
                },
            },
            required_params=["table_name", "column_name"],
            examples=[
                {
                    "table_name": "customers",
                    "column_name": "state",
                    "result": "['CA', 'NY', 'TX', 'FL', ...]"
                },
                {
                    "table_name": "orders",
                    "column_name": "status",
                    "result": "['pending', 'shipped', 'delivered', 'cancelled']"
                },
            ],
        )


@register_tool
class CountRowsTool(BaseTool):
    """
    Count rows in a table with optional WHERE filter.

    Useful for validating query expectations and understanding data volume.
    """

    name = "count_rows"
    description = "Count rows in a table, optionally with a WHERE condition."
    category = ToolCategory.DATA
    cacheable = True
    cache_ttl = 60  # 1 minute - counts change frequently

    async def execute(
        self,
        table_name: str,
        where_clause: Optional[str] = None
    ) -> ToolResult:
        """
        Count rows in a table.

        Args:
            table_name: Table to count
            where_clause: Optional WHERE condition (without WHERE keyword)

        Returns:
            ToolResult with count:
            {
                "table": "orders",
                "where": "status = 'pending'",
                "count": 42
            }
        """
        start = time.time()

        try:
            safe_table = table_name.replace('"', '').replace("'", "")

            # Security check for WHERE clause
            if where_clause:
                # Block dangerous keywords
                dangerous = [
                    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
                    "TRUNCATE", "CREATE", "GRANT", "REVOKE",
                    ";", "--", "/*", "*/"
                ]
                where_upper = where_clause.upper()
                for keyword in dangerous:
                    if keyword in where_upper:
                        return ToolResult(
                            success=False,
                            error=f"WHERE clause contains blocked keyword: {keyword}",
                            tool_name=self.name,
                            execution_time_ms=self._measure_execution(start),
                        )

                query = text(f'SELECT COUNT(*) as count FROM "{safe_table}" WHERE {where_clause}')
            else:
                query = text(f'SELECT COUNT(*) as count FROM "{safe_table}"')

            result = await self.schema_inspector._execute_query(self.session, query)
            row = result.fetchone()
            count = row[0] if row else 0

            return ToolResult(
                success=True,
                data={
                    "table": safe_table,
                    "where": where_clause,
                    "count": count,
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"count_rows failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
                execution_time_ms=self._measure_execution(start),
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {
                    "type": "string",
                    "description": "Table to count rows in"
                },
                "where_clause": {
                    "type": "string",
                    "description": "Optional WHERE condition (without WHERE keyword)"
                },
            },
            required_params=["table_name"],
            examples=[
                {
                    "table_name": "orders",
                    "result": "count: 1000"
                },
                {
                    "table_name": "orders",
                    "where_clause": "status = 'pending'",
                    "result": "count: 42"
                },
            ],
        )
