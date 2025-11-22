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
    Count rows in a table with optional parameterized filter.

    Useful for validating query expectations and understanding data volume.
    Uses parameterized queries to prevent SQL injection.
    """

    name = "count_rows"
    description = "Count rows in a table, optionally filtered by a column value (parameterized for security)."
    category = ToolCategory.DATA
    cacheable = True
    cache_ttl = 60  # 1 minute - counts change frequently

    # Valid comparison operators for filtering
    ALLOWED_OPERATORS = {"=", "!=", "<>", "<", ">", "<=", ">=", "LIKE", "ILIKE", "IS NULL", "IS NOT NULL"}

    async def execute(
        self,
        table_name: str,
        filter_column: Optional[str] = None,
        filter_value: Optional[Any] = None,
        filter_operator: str = "="
    ) -> ToolResult:
        """
        Count rows in a table with optional parameterized filter.

        Args:
            table_name: Table to count
            filter_column: Optional column to filter on
            filter_value: Optional value to filter by (parameterized, safe from injection)
            filter_operator: Comparison operator (default: "=").
                             Allowed: =, !=, <>, <, >, <=, >=, LIKE, ILIKE, IS NULL, IS NOT NULL

        Returns:
            ToolResult with count:
            {
                "table": "orders",
                "filter": {"column": "status", "operator": "=", "value": "pending"},
                "count": 42
            }
        """
        start = time.time()

        try:
            # Sanitize table name - only allow alphanumeric and underscore
            safe_table = self._sanitize_identifier(table_name)
            if not safe_table:
                return ToolResult(
                    success=False,
                    error="Invalid table name: must contain only alphanumeric characters and underscores",
                    tool_name=self.name,
                    execution_time_ms=self._measure_execution(start),
                )

            # Validate operator
            operator_upper = filter_operator.upper().strip()
            if operator_upper not in self.ALLOWED_OPERATORS:
                return ToolResult(
                    success=False,
                    error=f"Invalid operator: {filter_operator}. Allowed: {', '.join(sorted(self.ALLOWED_OPERATORS))}",
                    tool_name=self.name,
                    execution_time_ms=self._measure_execution(start),
                )

            # Build query with parameterized filter
            filter_info = None
            if filter_column:
                safe_column = self._sanitize_identifier(filter_column)
                if not safe_column:
                    return ToolResult(
                        success=False,
                        error="Invalid column name: must contain only alphanumeric characters and underscores",
                        tool_name=self.name,
                        execution_time_ms=self._measure_execution(start),
                    )

                # Handle NULL comparisons (no parameter needed)
                if operator_upper in ("IS NULL", "IS NOT NULL"):
                    query = text(f'SELECT COUNT(*) as count FROM "{safe_table}" WHERE "{safe_column}" {operator_upper}')
                    params = {}
                else:
                    # Use parameterized query - value is safely bound, not interpolated
                    query = text(f'SELECT COUNT(*) as count FROM "{safe_table}" WHERE "{safe_column}" {operator_upper} :filter_value')
                    params = {"filter_value": filter_value}

                filter_info = {
                    "column": safe_column,
                    "operator": operator_upper,
                    "value": filter_value if operator_upper not in ("IS NULL", "IS NOT NULL") else None
                }
            else:
                query = text(f'SELECT COUNT(*) as count FROM "{safe_table}"')
                params = {}

            result = await self.schema_inspector._execute_query(self.session, query, params)
            row = result.fetchone()
            count = row[0] if row else 0

            return ToolResult(
                success=True,
                data={
                    "table": safe_table,
                    "filter": filter_info,
                    "count": count,
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"count_rows failed: {e}")
            return ToolResult(
                success=False,
                error=f"Query execution failed: {type(e).__name__}",
                tool_name=self.name,
                execution_time_ms=self._measure_execution(start),
            )

    def _sanitize_identifier(self, identifier: str) -> Optional[str]:
        """
        Validate a SQL identifier (table/column name).

        Returns identifier if valid, or None if invalid.
        Only allows alphanumeric characters and underscores.
        REJECTS (not sanitizes) any identifier with invalid characters.
        """
        import re
        if not identifier:
            return None
        # Strip whitespace
        identifier = identifier.strip()
        # REJECT if any invalid characters are present (don't strip them)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            return None
        # Limit length to prevent abuse
        if len(identifier) > 128:
            return None
        return identifier

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
                "filter_column": {
                    "type": "string",
                    "description": "Optional: column to filter on"
                },
                "filter_value": {
                    "type": "any",
                    "description": "Optional: value to filter by (safely parameterized)"
                },
                "filter_operator": {
                    "type": "string",
                    "description": "Comparison operator (default: '='). Allowed: =, !=, <>, <, >, <=, >=, LIKE, ILIKE, IS NULL, IS NOT NULL",
                    "default": "="
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
                    "filter_column": "status",
                    "filter_value": "pending",
                    "result": "count: 42"
                },
                {
                    "table_name": "customers",
                    "filter_column": "state",
                    "filter_value": "CA",
                    "filter_operator": "=",
                    "result": "count: 150"
                },
            ],
        )
