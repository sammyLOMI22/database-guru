"""
Schema Exploration Tools

Tools for exploring and understanding database schema:
- search_schema: Find tables/columns by keyword
- get_table_info: Get detailed table information
- find_columns: Find tables containing a column
- get_relationships: Get foreign key relationships

These tools leverage SchemaCache from feedback-system-update
for 99% reduction in schema introspection time.

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import time
import logging
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

from src.tools.base import BaseTool, ToolResult, ToolDefinition, ToolCategory
from src.tools.tool_registry import register_tool

logger = logging.getLogger(__name__)


@register_tool
class SearchSchemaTool(BaseTool):
    """
    Search for tables and columns matching a keyword.

    Supports both exact and fuzzy matching to handle typos.
    Essential for understanding schema before query generation.
    """

    name = "search_schema"
    description = "Search for tables and columns matching a keyword. Returns matching table names and column names with their tables."
    category = ToolCategory.SCHEMA
    cacheable = True
    cache_ttl = 600  # 10 minutes - schema changes infrequently

    async def execute(
        self,
        keyword: str,
        fuzzy: bool = True,
        threshold: float = 0.6
    ) -> ToolResult:
        """
        Search schema for matching tables and columns.

        Args:
            keyword: Search term
            fuzzy: Enable fuzzy matching for typos
            threshold: Minimum similarity for fuzzy matches (0.0-1.0)

        Returns:
            ToolResult with matches:
            {
                "tables": [{"name": "customers", "match_type": "exact"}],
                "columns": [{"table": "orders", "column": "customer_id", "type": "integer"}]
            }
        """
        start = time.time()

        try:
            schema = await self._get_schema()

            matches = {
                "tables": [],
                "columns": [],
                "keyword": keyword,
            }
            keyword_lower = keyword.lower()

            for table_name, table_info in schema.get("tables", {}).items():
                table_lower = table_name.lower()

                # Check table name
                if keyword_lower in table_lower:
                    matches["tables"].append({
                        "name": table_name,
                        "match_type": "exact" if keyword_lower == table_lower else "contains",
                    })
                elif fuzzy:
                    ratio = SequenceMatcher(None, keyword_lower, table_lower).ratio()
                    if ratio >= threshold:
                        matches["tables"].append({
                            "name": table_name,
                            "match_type": "fuzzy",
                            "similarity": round(ratio, 2),
                        })

                # Check columns
                for column in table_info.get("columns", []):
                    col_name = column.get("name", "")
                    col_lower = col_name.lower()

                    if keyword_lower in col_lower:
                        matches["columns"].append({
                            "table": table_name,
                            "column": col_name,
                            "type": column.get("type", "unknown"),
                            "match_type": "exact" if keyword_lower == col_lower else "contains",
                        })
                    elif fuzzy:
                        ratio = SequenceMatcher(None, keyword_lower, col_lower).ratio()
                        if ratio >= threshold:
                            matches["columns"].append({
                                "table": table_name,
                                "column": col_name,
                                "type": column.get("type", "unknown"),
                                "match_type": "fuzzy",
                                "similarity": round(ratio, 2),
                            })

            return ToolResult(
                success=True,
                data=matches,
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"search_schema failed: {e}")
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
                "keyword": {
                    "type": "string",
                    "description": "Search term to find in table/column names"
                },
                "fuzzy": {
                    "type": "boolean",
                    "description": "Enable fuzzy matching for typos",
                    "default": True
                },
                "threshold": {
                    "type": "number",
                    "description": "Minimum similarity for fuzzy matches (0.0-1.0)",
                    "default": 0.6
                },
            },
            required_params=["keyword"],
            examples=[
                {
                    "keyword": "customer",
                    "result": "Tables: customers; Columns: customer_id in orders"
                },
                {
                    "keyword": "prodct",
                    "fuzzy": True,
                    "result": "Tables: products (fuzzy 0.86)"
                },
            ],
        )


@register_tool
class GetTableInfoTool(BaseTool):
    """
    Get detailed information about a specific table.

    Returns columns, types, constraints, and foreign keys.
    Essential for understanding table structure before querying.
    """

    name = "get_table_info"
    description = "Get detailed schema information for a specific table including columns, types, constraints, and foreign keys."
    category = ToolCategory.SCHEMA
    cacheable = True
    cache_ttl = 600

    async def execute(self, table_name: str) -> ToolResult:
        """
        Get detailed table information.

        Args:
            table_name: Name of the table to inspect

        Returns:
            ToolResult with table info:
            {
                "table_name": "orders",
                "columns": [...],
                "primary_key": "id",
                "relationships": [...],
                "indexes": [...]
            }
        """
        start = time.time()

        try:
            schema = await self._get_schema()
            tables = schema.get("tables", {})

            # Case-insensitive lookup
            actual_name = None
            for name in tables:
                if name.lower() == table_name.lower():
                    actual_name = name
                    break

            if not actual_name:
                available = list(tables.keys())
                return ToolResult(
                    success=False,
                    error=f"Table '{table_name}' not found. Available tables: {available}",
                    tool_name=self.name,
                    execution_time_ms=self._measure_execution(start),
                )

            table_info = tables[actual_name]

            # Get relationships from foreign keys
            relationships = []
            for fk in schema.get("foreign_keys", []):
                if fk.get("source_table") == actual_name:
                    relationships.append({
                        "type": "outgoing",
                        "column": fk.get("source_column"),
                        "references": f"{fk.get('target_table')}.{fk.get('target_column')}",
                    })
                elif fk.get("target_table") == actual_name:
                    relationships.append({
                        "type": "incoming",
                        "from": f"{fk.get('source_table')}.{fk.get('source_column')}",
                        "column": fk.get("target_column"),
                    })

            result_data = {
                "table_name": actual_name,
                "columns": table_info.get("columns", []),
                "primary_key": table_info.get("primary_key"),
                "relationships": relationships,
                "indexes": table_info.get("indexes", []),
                "row_count_estimate": table_info.get("row_count"),
            }

            return ToolResult(
                success=True,
                data=result_data,
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"get_table_info failed: {e}")
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
                    "description": "Name of the table to inspect"
                },
            },
            required_params=["table_name"],
            examples=[
                {
                    "table_name": "orders",
                    "result": "Columns: id, customer_id, total, created_at; FK: customer_id -> customers.id"
                },
            ],
        )


@register_tool
class FindColumnsTool(BaseTool):
    """
    Find all tables that contain a column with the given name.

    Useful for finding where specific data lives across the schema.
    Helps with join discovery and query planning.
    """

    name = "find_columns"
    description = "Find all tables that contain a column with the given name. Useful for finding where data lives."
    category = ToolCategory.SCHEMA
    cacheable = True
    cache_ttl = 600

    async def execute(
        self,
        column_name: str,
        exact: bool = False
    ) -> ToolResult:
        """
        Find tables containing the specified column.

        Args:
            column_name: Column name to search for
            exact: Require exact match (default: contains match)

        Returns:
            ToolResult with found columns:
            {
                "column_name": "state",
                "found_in": [
                    {"table": "customers", "column": "state", "type": "varchar"},
                    {"table": "orders", "column": "shipping_state", "type": "varchar"}
                ]
            }
        """
        start = time.time()

        try:
            schema = await self._get_schema()

            results = []
            column_lower = column_name.lower()

            for table_name, table_info in schema.get("tables", {}).items():
                for column in table_info.get("columns", []):
                    col_name = column.get("name", "")

                    if exact:
                        match = col_name.lower() == column_lower
                    else:
                        match = column_lower in col_name.lower()

                    if match:
                        results.append({
                            "table": table_name,
                            "column": col_name,
                            "type": column.get("type", "unknown"),
                            "nullable": column.get("nullable", True),
                        })

            return ToolResult(
                success=True,
                data={
                    "column_name": column_name,
                    "found_in": results,
                    "count": len(results),
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"find_columns failed: {e}")
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
                "column_name": {
                    "type": "string",
                    "description": "Column name to search for"
                },
                "exact": {
                    "type": "boolean",
                    "description": "Require exact match",
                    "default": False
                },
            },
            required_params=["column_name"],
            examples=[
                {
                    "column_name": "state",
                    "result": "Found in: customers.state, orders.shipping_state"
                },
            ],
        )


@register_tool
class GetRelationshipsTool(BaseTool):
    """
    Get foreign key relationships between tables.

    Shows how tables can be joined and suggests join conditions.
    Essential for multi-table query planning.
    """

    name = "get_relationships"
    description = "Get all foreign key relationships for a table or between two tables. Shows how tables can be joined."
    category = ToolCategory.SCHEMA
    cacheable = True
    cache_ttl = 600

    async def execute(
        self,
        table_name: Optional[str] = None,
        target_table: Optional[str] = None
    ) -> ToolResult:
        """
        Get table relationships and join suggestions.

        Args:
            table_name: Table to get relationships for (optional)
            target_table: Specific target table (optional)

        Returns:
            ToolResult with relationships:
            {
                "relationships": [...],
                "join_suggestions": [{"sql_hint": "orders.customer_id = customers.id"}]
            }
        """
        start = time.time()

        try:
            schema = await self._get_schema()
            all_fks = schema.get("foreign_keys", [])

            # If no filters, return all relationships
            if table_name is None and target_table is None:
                return ToolResult(
                    success=True,
                    data={
                        "all_relationships": all_fks,
                        "count": len(all_fks),
                    },
                    execution_time_ms=self._measure_execution(start),
                    tool_name=self.name,
                )

            # Filter relationships
            results = []
            for fk in all_fks:
                source = fk.get("source_table", "").lower()
                target = fk.get("target_table", "").lower()

                if table_name:
                    table_lower = table_name.lower()
                    if source == table_lower or target == table_lower:
                        if target_table:
                            target_lower = target_table.lower()
                            if source == target_lower or target == target_lower:
                                results.append(fk)
                        else:
                            results.append(fk)

            # Generate join suggestions
            join_suggestions = []
            for fk in results:
                join_suggestions.append({
                    "type": "direct",
                    "sql_hint": f"{fk['source_table']}.{fk['source_column']} = {fk['target_table']}.{fk['target_column']}",
                    "source": fk['source_table'],
                    "target": fk['target_table'],
                })

            return ToolResult(
                success=True,
                data={
                    "table": table_name,
                    "target": target_table,
                    "relationships": results,
                    "join_suggestions": join_suggestions,
                    "count": len(results),
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"get_relationships failed: {e}")
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
                    "description": "Table to get relationships for"
                },
                "target_table": {
                    "type": "string",
                    "description": "Optional: specific target table to find path to"
                },
            },
            required_params=[],
            examples=[
                {
                    "table_name": "orders",
                    "result": "FK: customer_id -> customers.id, product_id -> products.id"
                },
                {
                    "table_name": "orders",
                    "target_table": "customers",
                    "result": "Join: orders.customer_id = customers.id"
                },
            ],
        )
