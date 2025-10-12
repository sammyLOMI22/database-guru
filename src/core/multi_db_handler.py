"""Multi-database handler for querying across multiple databases"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.core.user_db_connector import UserDatabaseConnector
from src.core.schema_inspector import SchemaInspector
from src.core.executor import SQLExecutor
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
from src.llm.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


class MultiDatabaseHandler:
    """Handle queries across multiple database connections"""

    def __init__(self):
        self.schema_inspector = SchemaInspector()

    async def build_combined_schema(
        self, connections: List[DatabaseConnection]
    ) -> Dict[str, Any]:
        """
        Build a combined schema from multiple database connections

        Args:
            connections: List of DatabaseConnection objects

        Returns:
            Dict with combined schema information including database prefixes
        """
        combined_schema = {
            "databases": [],
            "total_tables": 0,
            "total_columns": 0,
        }

        for conn in connections:
            try:
                async with UserDatabaseConnector.get_user_db_session(conn) as user_db:
                    # Get schema for this database
                    schema_data = await self.schema_inspector.get_full_schema(user_db)

                    # Add database context
                    db_info = {
                        "connection_id": conn.id,
                        "name": conn.name,
                        "database_type": conn.database_type,
                        "database_name": conn.database_name,
                        "tables": schema_data.get("tables", []),
                        "table_count": len(schema_data.get("tables", [])),
                    }

                    combined_schema["databases"].append(db_info)
                    combined_schema["total_tables"] += db_info["table_count"]

                    # Count columns
                    for table in schema_data.get("tables", []):
                        combined_schema["total_columns"] += len(
                            table.get("columns", [])
                        )

                logger.info(
                    f"Added schema for database '{conn.name}': {db_info['table_count']} tables"
                )

            except Exception as e:
                logger.error(f"Failed to get schema for database '{conn.name}': {e}")
                # Add error info but continue with other databases
                combined_schema["databases"].append(
                    {
                        "connection_id": conn.id,
                        "name": conn.name,
                        "database_type": conn.database_type,
                        "error": str(e),
                        "tables": [],
                        "table_count": 0,
                    }
                )

        return combined_schema

    def format_schema_for_llm(self, combined_schema: Dict[str, Any]) -> str:
        """
        Format combined schema for LLM consumption

        Args:
            combined_schema: Combined schema from build_combined_schema()

        Returns:
            Formatted string with database prefixes for LLM
        """
        lines = []
        lines.append(
            f"# Multi-Database Schema ({combined_schema['total_tables']} tables across {len(combined_schema['databases'])} databases)\n"
        )

        for db_info in combined_schema["databases"]:
            if "error" in db_info:
                lines.append(
                    f"\n--- Database: {db_info['name']} (ERROR: {db_info['error']}) ---\n"
                )
                continue

            lines.append(
                f"\n--- Database: {db_info['name']} ({db_info['database_type']}) ---"
            )
            lines.append(f"Database Name: {db_info['database_name']}")
            lines.append(f"Connection ID: {db_info['connection_id']}")
            lines.append(f"Tables: {db_info['table_count']}\n")

            for table in db_info["tables"]:
                table_name = table["name"]
                lines.append(f"Table: {db_info['name']}.{table_name}")

                # Add columns
                columns = []
                for col in table.get("columns", []):
                    col_def = f"  - {col['name']} ({col['type']})"
                    if col.get("nullable") is False:
                        col_def += " NOT NULL"
                    if col.get("primary_key"):
                        col_def += " PRIMARY KEY"
                    columns.append(col_def)

                lines.extend(columns)

                # Add foreign keys if any
                if table.get("foreign_keys"):
                    lines.append("  Foreign Keys:")
                    for fk in table["foreign_keys"]:
                        lines.append(
                            f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
                        )

                # Add indexes if any
                if table.get("indexes"):
                    lines.append(f"  Indexes: {len(table['indexes'])}")

                lines.append("")  # Empty line between tables

        return "\n".join(lines)

    async def execute_query_on_database(
        self,
        connection: DatabaseConnection,
        sql: str,
        allow_write: bool = False,
        max_rows: int = 1000,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute a SQL query on a specific database (WITHOUT self-correction)

        Args:
            connection: DatabaseConnection to execute query on
            sql: SQL query to execute
            allow_write: Whether to allow write operations
            max_rows: Maximum number of rows to return
            timeout_seconds: Query timeout in seconds

        Returns:
            Dict with execution results
        """
        try:
            async with UserDatabaseConnector.get_user_db_session(connection) as user_db:
                executor = SQLExecutor(
                    max_rows=max_rows,
                    timeout_seconds=timeout_seconds,
                    allow_write=allow_write,
                )

                result = await executor.execute_query(user_db, sql)
                result["database_name"] = connection.name
                result["connection_id"] = connection.id

                return result

        except Exception as e:
            logger.error(
                f"Failed to execute query on database '{connection.name}': {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "database_name": connection.name,
                "connection_id": connection.id,
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0,
            }

    async def execute_query_with_self_correction(
        self,
        connection: DatabaseConnection,
        question: str,
        schema: str,
        sql_generator: SQLGenerator,
        initial_sql: Optional[str] = None,
        allow_write: bool = False,
        max_rows: int = 1000,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute a SQL query on a specific database WITH self-correction

        Args:
            connection: DatabaseConnection to execute query on
            question: Original natural language question
            schema: Database schema for this specific connection
            sql_generator: SQLGenerator instance for generating/fixing SQL
            initial_sql: Optional pre-generated SQL (if None, will generate)
            allow_write: Whether to allow write operations
            max_rows: Maximum number of rows to return
            timeout_seconds: Query timeout in seconds
            max_retries: Maximum number of retry attempts

        Returns:
            Dict with execution results including correction attempts
        """
        try:
            async with UserDatabaseConnector.get_user_db_session(connection) as user_db:
                # Get schema for this specific database if not provided
                if not schema:
                    schema_data = await self.schema_inspector.get_full_schema(user_db)
                    schema = self._format_single_db_schema(schema_data)

                # Initialize self-correcting agent
                agent = SelfCorrectingSQLAgent(
                    sql_generator=sql_generator,
                    max_retries=max_retries,
                    enable_diagnostics=True,
                )

                # If initial SQL provided, use direct retry approach
                if initial_sql:
                    # Execute with retry logic
                    result = await agent.execute_with_retry(
                        sql=initial_sql,
                        schema=schema,
                        session=user_db,
                        database_type=connection.database_type,
                        question=question,
                    )
                else:
                    # Generate SQL and execute with retry
                    result = await agent.generate_and_execute_with_retry(
                        question=question,
                        schema=schema,
                        session=user_db,
                        database_type=connection.database_type,
                        allow_write=allow_write,
                    )

                # Add connection metadata
                if result.get("success"):
                    exec_result = result.get("result", {})
                    return {
                        "success": True,
                        "sql": result.get("sql"),
                        "data": exec_result.get("data", []),
                        "row_count": exec_result.get("row_count", 0),
                        "execution_time_ms": exec_result.get("execution_time_ms", 0),
                        "database_name": connection.name,
                        "connection_id": connection.id,
                        "correction_attempts": result.get("attempts", 0),
                        "corrections": result.get("corrections", []),
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("final_error", "Unknown error"),
                        "sql": result.get("sql"),
                        "database_name": connection.name,
                        "connection_id": connection.id,
                        "data": [],
                        "row_count": 0,
                        "execution_time_ms": 0,
                        "correction_attempts": result.get("attempts", 0),
                        "corrections": result.get("corrections", []),
                    }

        except Exception as e:
            logger.error(
                f"Failed to execute query with self-correction on database '{connection.name}': {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "database_name": connection.name,
                "connection_id": connection.id,
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "correction_attempts": 0,
                "corrections": [],
            }

    def _format_single_db_schema(self, schema_data: Dict[str, Any]) -> str:
        """Format schema data for a single database for LLM consumption"""
        lines = []
        for table in schema_data.get("tables", []):
            lines.append(f"Table: {table['name']}")
            for col in table.get("columns", []):
                col_def = f"  - {col['name']} ({col['type']})"
                if col.get("nullable") is False:
                    col_def += " NOT NULL"
                if col.get("primary_key"):
                    col_def += " PRIMARY KEY"
                lines.append(col_def)

            if table.get("foreign_keys"):
                lines.append("  Foreign Keys:")
                for fk in table["foreign_keys"]:
                    lines.append(
                        f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
                    )
            lines.append("")

        return "\n".join(lines)

    async def execute_multi_database_query(
        self,
        queries: List[Dict[str, Any]],
        connections: List[DatabaseConnection],
        allow_write: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple queries across different databases

        Args:
            queries: List of dicts with 'connection_id' and 'sql' keys
            connections: List of available DatabaseConnection objects
            allow_write: Whether to allow write operations

        Returns:
            List of execution results, one per query
        """
        # Create connection lookup
        conn_lookup = {conn.id: conn for conn in connections}

        results = []
        for query_info in queries:
            conn_id = query_info.get("connection_id")
            sql = query_info.get("sql")

            if not conn_id or not sql:
                results.append(
                    {
                        "success": False,
                        "error": "Missing connection_id or sql",
                        "data": [],
                    }
                )
                continue

            connection = conn_lookup.get(conn_id)
            if not connection:
                results.append(
                    {
                        "success": False,
                        "error": f"Connection ID {conn_id} not found",
                        "data": [],
                    }
                )
                continue

            # Execute query
            result = await self.execute_query_on_database(
                connection=connection, sql=sql, allow_write=allow_write
            )
            results.append(result)

        return results

    def parse_multi_database_sql(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Parse LLM output that may contain multiple SQL queries for different databases

        Expected format:
        DATABASE: database_name
        SELECT ...;

        DATABASE: another_database
        SELECT ...;

        Args:
            llm_output: Raw output from LLM

        Returns:
            List of dicts with 'database_name' and 'sql' keys
        """
        queries = []
        current_db = None
        current_sql_lines = []

        for line in llm_output.split("\n"):
            line = line.strip()

            # Check for database marker
            if line.upper().startswith("DATABASE:"):
                # Save previous query if exists
                if current_db and current_sql_lines:
                    queries.append(
                        {
                            "database_name": current_db,
                            "sql": "\n".join(current_sql_lines).strip(),
                        }
                    )
                    current_sql_lines = []

                # Extract new database name
                current_db = line.split(":", 1)[1].strip()

            elif line and current_db:
                # Collect SQL lines
                current_sql_lines.append(line)

        # Save last query
        if current_db and current_sql_lines:
            queries.append(
                {"database_name": current_db, "sql": "\n".join(current_sql_lines).strip()}
            )

        # If no database markers found, treat entire output as single query
        if not queries and llm_output.strip():
            queries.append({"database_name": None, "sql": llm_output.strip()})

        return queries

    def map_database_names_to_connections(
        self, queries: List[Dict[str, Any]], connections: List[DatabaseConnection]
    ) -> List[Dict[str, Any]]:
        """
        Map database names in queries to connection IDs

        Args:
            queries: List of queries with 'database_name' field
            connections: List of DatabaseConnection objects

        Returns:
            List of queries with 'connection_id' field added
        """
        # Create name lookup (case-insensitive)
        name_to_conn = {conn.name.lower(): conn for conn in connections}

        mapped_queries = []
        for query in queries:
            db_name = query.get("database_name")

            # Try to match database name to connection
            connection = None
            if db_name:
                connection = name_to_conn.get(db_name.lower())

            # If no match or no database specified, use first connection as default
            if not connection and connections:
                connection = connections[0]
                logger.warning(
                    f"Could not find connection for database '{db_name}', using default: {connection.name}"
                )

            if connection:
                mapped_queries.append(
                    {
                        **query,
                        "connection_id": connection.id,
                        "connection_name": connection.name,
                    }
                )
            else:
                # No connections available
                mapped_queries.append(
                    {**query, "connection_id": None, "error": "No connections available"}
                )

        return mapped_queries
