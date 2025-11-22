"""
Query Validation Tools

Tools for validating and testing SQL queries:
- test_query: Test if SQL syntax is valid without executing
- validate_sql: Validate SQL references against schema
- explain_query: Get query execution plan

These tools help catch errors before full execution.

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import time
import re
import logging
from typing import Any, Dict, Optional
from difflib import get_close_matches

from sqlalchemy import text

from src.tools.base import BaseTool, ToolResult, ToolDefinition, ToolCategory
from src.tools.tool_registry import register_tool

logger = logging.getLogger(__name__)


@register_tool
class TestQueryTool(BaseTool):
    """
    Test if a SQL query is syntactically valid without executing it.

    Uses EXPLAIN (on supported databases) or LIMIT 0 wrapper to validate
    without actually running the query.
    """

    name = "test_query"
    description = "Test if SQL syntax is valid without executing. Uses EXPLAIN or LIMIT 0 to validate."
    category = ToolCategory.QUERY
    cacheable = False  # Don't cache - test fresh each time

    async def execute(
        self,
        sql: str,
        database_type: str = "postgresql"
    ) -> ToolResult:
        """
        Test query syntax validity.

        Args:
            sql: SQL query to test
            database_type: Database type (postgresql, mysql, sqlite, duckdb)

        Returns:
            ToolResult indicating validity:
            {
                "sql": "SELECT * FROM orders",
                "valid": true,
                "message": "Query syntax is valid"
            }
        """
        start = time.time()

        try:
            # Determine test method based on database type
            db_lower = database_type.lower()

            if db_lower in ["postgresql", "postgres"]:
                test_sql = f"EXPLAIN {sql}"
            elif db_lower == "mysql":
                test_sql = f"EXPLAIN {sql}"
            elif db_lower == "sqlite":
                # SQLite doesn't have EXPLAIN for syntax check
                # Use subquery with LIMIT 0
                test_sql = f"SELECT * FROM ({sql}) AS _test LIMIT 0"
            elif db_lower == "duckdb":
                test_sql = f"EXPLAIN {sql}"
            else:
                # Default: try EXPLAIN
                test_sql = f"EXPLAIN {sql}"

            query = text(test_sql)
            await self.schema_inspector._execute_query(self.session, query)

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "valid": True,
                    "message": "Query syntax is valid",
                    "database_type": database_type,
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            # Query is invalid - this is expected behavior, not a tool failure
            error_msg = str(e)

            return ToolResult(
                success=True,  # Tool executed successfully, query is just invalid
                data={
                    "sql": sql,
                    "valid": False,
                    "error": error_msg[:500],  # Truncate long errors
                    "message": f"Query has syntax error: {error_msg[:200]}",
                    "database_type": database_type,
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "sql": {
                    "type": "string",
                    "description": "SQL query to test"
                },
                "database_type": {
                    "type": "string",
                    "description": "Database type (postgresql, mysql, sqlite, duckdb)",
                    "default": "postgresql"
                },
            },
            required_params=["sql"],
            examples=[
                {
                    "sql": "SELECT * FROM orders",
                    "result": "valid: true"
                },
                {
                    "sql": "SELEC * FORM orders",
                    "result": "valid: false, error: syntax error near 'SELEC'"
                },
            ],
        )


@register_tool
class ValidateSQLTool(BaseTool):
    """
    Validate SQL references against actual schema.

    Checks if tables and columns exist, suggests corrections for typos.
    More thorough than test_query - validates semantic correctness.
    """

    name = "validate_sql"
    description = "Validate SQL references against actual schema. Checks if tables and columns exist."
    category = ToolCategory.VALIDATION
    cacheable = True
    cache_ttl = 300

    async def execute(self, sql: str) -> ToolResult:
        """
        Validate SQL against schema.

        Args:
            sql: SQL query to validate

        Returns:
            ToolResult with validation results:
            {
                "sql": "SELECT * FROM customerz",
                "valid": false,
                "issues": ["Table 'customerz' not found"],
                "suggestions": ["Did you mean: customers?"]
            }
        """
        start = time.time()

        try:
            schema = await self._get_schema()
            tables = set(schema.get("tables", {}).keys())
            tables_lower = {t.lower(): t for t in tables}

            # Extract table references from SQL
            sql_upper = sql.upper()

            # Find tables after FROM and JOIN
            from_matches = re.findall(
                r'FROM\s+["\']?(\w+)["\']?',
                sql,
                re.IGNORECASE
            )
            join_matches = re.findall(
                r'JOIN\s+["\']?(\w+)["\']?',
                sql,
                re.IGNORECASE
            )

            referenced_tables = set(from_matches + join_matches)

            issues = []
            suggestions = []
            valid_tables = []

            for ref_table in referenced_tables:
                ref_lower = ref_table.lower()

                if ref_lower in tables_lower:
                    valid_tables.append(tables_lower[ref_lower])
                else:
                    issues.append(f"Table '{ref_table}' not found in schema")

                    # Find similar table names
                    matches = get_close_matches(
                        ref_lower,
                        list(tables_lower.keys()),
                        n=3,
                        cutoff=0.6
                    )
                    if matches:
                        actual_names = [tables_lower[m] for m in matches]
                        suggestions.append(
                            f"Did you mean: {', '.join(actual_names)}?"
                        )

            # Extract and validate column references (basic)
            # This is a simplified check - full validation would need SQL parsing
            column_issues = []
            for table in valid_tables:
                table_info = schema.get("tables", {}).get(table, {})
                table_columns = {
                    c.get("name", "").lower()
                    for c in table_info.get("columns", [])
                }

                # Find column references for this table
                # Pattern: table.column or table_alias.column
                col_pattern = rf'{table}\.(\w+)'
                col_matches = re.findall(col_pattern, sql, re.IGNORECASE)

                for col in col_matches:
                    if col.lower() not in table_columns:
                        column_issues.append(
                            f"Column '{col}' not found in table '{table}'"
                        )

            issues.extend(column_issues)

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "valid": len(issues) == 0,
                    "referenced_tables": list(referenced_tables),
                    "valid_tables": valid_tables,
                    "issues": issues,
                    "suggestions": suggestions,
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"validate_sql failed: {e}")
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
                "sql": {
                    "type": "string",
                    "description": "SQL query to validate against schema"
                },
            },
            required_params=["sql"],
            examples=[
                {
                    "sql": "SELECT * FROM customerz",
                    "result": "valid: false, suggestion: 'Did you mean: customers?'"
                },
            ],
        )


@register_tool
class ExplainQueryTool(BaseTool):
    """
    Get the execution plan for a SQL query.

    Shows how the database will execute the query, including:
    - Scan types (sequential, index)
    - Join methods
    - Estimated costs
    """

    name = "explain_query"
    description = "Get the execution plan for a query. Shows how the database will execute it."
    category = ToolCategory.QUERY
    cacheable = True
    cache_ttl = 300

    async def execute(
        self,
        sql: str,
        analyze: bool = False,
        database_type: str = "postgresql"
    ) -> ToolResult:
        """
        Get query execution plan.

        Args:
            sql: SQL query to explain
            analyze: Actually run the query for real statistics (default: False)
            database_type: Database type

        Returns:
            ToolResult with execution plan:
            {
                "sql": "SELECT * FROM orders WHERE status = 'pending'",
                "plan": ["Seq Scan on orders", "Filter: status = 'pending'"],
                "analyzed": false
            }
        """
        start = time.time()

        try:
            db_lower = database_type.lower()

            # Build EXPLAIN query based on database type
            if db_lower in ["postgresql", "postgres"]:
                if analyze:
                    explain_sql = f"EXPLAIN ANALYZE {sql}"
                else:
                    explain_sql = f"EXPLAIN {sql}"
            elif db_lower == "mysql":
                # MySQL EXPLAIN doesn't have ANALYZE option in all versions
                explain_sql = f"EXPLAIN {sql}"
            elif db_lower == "sqlite":
                explain_sql = f"EXPLAIN QUERY PLAN {sql}"
            elif db_lower == "duckdb":
                if analyze:
                    explain_sql = f"EXPLAIN ANALYZE {sql}"
                else:
                    explain_sql = f"EXPLAIN {sql}"
            else:
                explain_sql = f"EXPLAIN {sql}"

            query = text(explain_sql)
            result = await self.schema_inspector._execute_query(self.session, query)

            # Extract plan lines
            plan_rows = []
            for row in result.fetchall():
                # Handle different result formats
                if hasattr(row, '_mapping'):
                    plan_rows.append(str(dict(row._mapping)))
                else:
                    plan_rows.append(str(row[0]) if row else "")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "plan": plan_rows,
                    "analyzed": analyze,
                    "database_type": database_type,
                },
                execution_time_ms=self._measure_execution(start),
                tool_name=self.name,
            )

        except Exception as e:
            logger.error(f"explain_query failed: {e}")
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
                "sql": {
                    "type": "string",
                    "description": "SQL query to explain"
                },
                "analyze": {
                    "type": "boolean",
                    "description": "Actually run for real statistics",
                    "default": False
                },
                "database_type": {
                    "type": "string",
                    "description": "Database type",
                    "default": "postgresql"
                },
            },
            required_params=["sql"],
            examples=[
                {
                    "sql": "SELECT * FROM orders WHERE status = 'pending'",
                    "result": "Seq Scan on orders, Filter: status = 'pending'"
                },
            ],
        )
