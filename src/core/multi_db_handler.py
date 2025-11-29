"""Multi-database handler for querying across multiple databases"""
import logging
import asyncio
from asyncio import Semaphore
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection
from src.core.user_db_connector import UserDatabaseConnector
from src.core.schema_inspector import SchemaInspector
from src.core.executor import SQLExecutor
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
from src.llm.sql_generator import SQLGenerator
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class MultiDatabaseHandler:
    """Handle queries across multiple database connections"""

    def __init__(self):
        self.schema_inspector = SchemaInspector()

    async def _introspect_single_database(self, conn: DatabaseConnection) -> Dict[str, Any]:
        """
        Introspect schema for a single database connection

        Args:
            conn: DatabaseConnection to introspect

        Returns:
            Dict with database info and schema, or error info
        """
        try:
            async with UserDatabaseConnector.get_user_db_session(conn) as user_db:
                # Get schema for this database (with caching)
                from src.core.schema_cache import SchemaCache

                schema_data = await SchemaCache.get_schema(
                    connection_id=conn.id,
                    connection_name=conn.name,
                    user_db_session=user_db,
                    force_refresh=False  # Multi-DB queries use cache by default
                )

                # Convert schema tables from dict to list format
                tables_dict = schema_data.get("tables", {})
                tables_list = []
                for table_name, table_info in tables_dict.items():
                    tables_list.append({
                        "name": table_name,
                        **table_info  # Spread the columns, foreign_keys, etc.
                    })

                # Add database context
                db_info = {
                    "connection_id": conn.id,
                    "name": conn.name,
                    "database_type": conn.database_type,
                    "database_name": conn.database_name,
                    "tables": tables_list,
                    "table_count": len(tables_list),
                }

                logger.info(
                    f"Added schema for database '{conn.name}': {db_info['table_count']} tables"
                )

                return db_info

        except Exception as e:
            logger.error(f"Failed to get schema for database '{conn.name}': {e}")
            # Return error info but allow other databases to continue
            return {
                "connection_id": conn.id,
                "name": conn.name,
                "database_type": conn.database_type,
                "error": str(e),
                "tables": [],
                "table_count": 0,
            }

    async def build_combined_schema(
        self, connections: List[DatabaseConnection]
    ) -> Dict[str, Any]:
        """
        Build a combined schema from multiple database connections (parallelized)

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

        # OPTIMIZATION: Introspect all databases in parallel using asyncio.gather
        # This reduces total time from N × connection_time to max(connection_time)
        logger.info(f"Introspecting {len(connections)} database(s) in parallel...")

        introspection_tasks = [
            self._introspect_single_database(conn)
            for conn in connections
        ]

        # Gather results (will wait for all to complete, but they run concurrently)
        db_infos = await asyncio.gather(*introspection_tasks, return_exceptions=True)

        # Process results
        for i, db_info in enumerate(db_infos):
            # Handle exceptions from gather
            if isinstance(db_info, Exception):
                conn = connections[i]
                logger.error(f"Exception introspecting database '{conn.name}': {db_info}")
                db_info = {
                    "connection_id": conn.id,
                    "name": conn.name,
                    "database_type": conn.database_type,
                    "error": str(db_info),
                    "tables": [],
                    "table_count": 0,
                }

            combined_schema["databases"].append(db_info)
            combined_schema["total_tables"] += db_info.get("table_count", 0)

            # Count columns
            for table in db_info.get("tables", []):
                combined_schema["total_columns"] += len(
                    table.get("columns", [])
                )

        logger.info(
            f"✓ Schema introspection complete: {combined_schema['total_tables']} tables "
            f"across {len(connections)} database(s)"
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
                        # Handle both old format (constrained_columns) and new format (column)
                        from_col = fk.get('column') or fk.get('constrained_columns', 'unknown')
                        to_col = fk.get('referred_column') or fk.get('referred_columns', 'unknown')
                        to_table = fk.get('referred_table', 'unknown')
                        lines.append(
                            f"    - {from_col} -> {to_table}.{to_col}"
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

    async def _execute_single_query_task(
        self,
        connection: DatabaseConnection,
        question: str,
        sql: str,
        schema: str,
        sql_generator: SQLGenerator,
        combined_schema_data: Dict[str, Any],
        allow_write: bool = False,
        model_used: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Internal helper method to execute a single database query with self-correction
        Used for parallel execution in multi-database queries

        Args:
            connection: Database connection
            question: Natural language question
            sql: Pre-generated SQL (can be empty for agent to generate)
            schema: Schema for this database
            sql_generator: SQL generator instance
            combined_schema_data: Full schema data for all databases
            allow_write: Allow write operations
            model_used: LLM model name for tracking

        Returns:
            Dict with execution results and metadata (NOT including QueryHistory record)
        """
        try:
            # Get individual schema for this database
            db_schema = None
            db_schema_dict = None
            for db_info in combined_schema_data.get("databases", []):
                if db_info.get("connection_id") == connection.id:
                    # Store schema dict for location normalization
                    db_schema_dict = {"tables": db_info.get("tables", {})}
                    # Format schema for this specific database
                    db_schema = self._format_single_db_schema(db_schema_dict)
                    break

            # Execute query with self-correction
            exec_result = await self.execute_query_with_self_correction(
                connection=connection,
                question=question,
                schema=db_schema or schema,
                sql_generator=sql_generator,
                initial_sql=sql,
                allow_write=allow_write,
                schema_dict=db_schema_dict,
                model=model_used,
            )

            # Return result with connection metadata
            return {
                **exec_result,
                "connection_id": connection.id,
                "connection_name": connection.name,
                "database_type": connection.database_type,
                "model_used": model_used,
            }

        except Exception as e:
            logger.error(f"Failed to execute query on database '{connection.name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "database_name": connection.name,
                "connection_id": connection.id,
                "database_type": connection.database_type,
                "model_used": model_used,
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "total_attempts": 0,
                "attempts": [],
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
        schema_dict: Optional[Dict] = None,
        model: Optional[str] = None,
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
            schema_dict: Optional schema dict for location normalization
            model: Optional model name to use for SQL generation

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
                        model=model,
                    )
                else:
                    # Generate SQL and execute with retry
                    result = await agent.generate_and_execute_with_retry(
                        question=question,
                        schema=schema,
                        session=user_db,
                        database_type=connection.database_type,
                        allow_write=allow_write,
                        schema_dict=schema_dict,
                        model=model,
                        schema_inspector=self.schema_inspector,  # Pass for tool-using agent
                        connection_id=connection.id,  # Pass for tool-using agent
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
                        "total_attempts": result.get("total_attempts", 0),
                        "attempts": result.get("attempts", []),
                        # Option 2: Observability fields
                        "agent_trace": result.get("agent_trace"),
                        "query_plan": result.get("query_plan"),
                        "self_corrected": result.get("self_corrected", False),
                        "verification_warnings": result.get("verification_warnings", []),
                        "used_planning": result.get("used_planning", False),
                        # fix_methods removed - not needed in response, causes serialization errors
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error") or result.get("final_error", "Unknown error"),
                        "sql": result.get("sql"),
                        "database_name": connection.name,
                        "connection_id": connection.id,
                        "data": [],
                        "row_count": 0,
                        "execution_time_ms": 0,
                        "total_attempts": result.get("total_attempts", 0),
                        "attempts": result.get("attempts", []),
                        # Option 2: Observability fields (even on failure)
                        "agent_trace": result.get("agent_trace"),
                        "query_plan": result.get("query_plan"),
                        "self_corrected": result.get("self_corrected", False),
                        "verification_warnings": result.get("verification_warnings", []),
                        "used_planning": result.get("used_planning", False),
                        # fix_methods removed - not needed in response, causes serialization errors
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
                "total_attempts": 0,
                "attempts": [],
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

                # Add sample values if available (helps LLM understand format)
                if "sample_values" in col and col["sample_values"]:
                    samples = col["sample_values"]
                    sample_str = ", ".join(repr(s) for s in samples[:5])
                    col_def += f"  // Examples: {sample_str}"

                lines.append(col_def)

            if table.get("foreign_keys"):
                lines.append("  Foreign Keys:")
                for fk in table["foreign_keys"]:
                    # Handle both old format (constrained_columns) and new format (column)
                    from_col = fk.get('column') or fk.get('constrained_columns', 'unknown')
                    to_col = fk.get('referred_column') or fk.get('referred_columns', 'unknown')
                    to_table = fk.get('referred_table', 'unknown')
                    lines.append(
                        f"    - {from_col} -> {to_table}.{to_col}"
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
        Execute multiple queries across different databases IN PARALLEL

        Args:
            queries: List of dicts with 'connection_id' and 'sql' keys
            connections: List of available DatabaseConnection objects
            allow_write: Whether to allow write operations

        Returns:
            List of execution results, one per query
        """
        import time

        # Start timing for metrics
        start_time = time.time()

        # Create connection lookup
        conn_lookup = {conn.id: conn for conn in connections}

        # FIX #1: Add semaphore for max concurrent operations (prevents resource exhaustion)
        settings = Settings()
        max_parallel = settings.MAX_PARALLEL_DATABASES
        semaphore = Semaphore(max_parallel)

        # FIX #6: Metrics tracking
        metrics = {
            "total_queries": len(queries),
            "max_concurrent": max_parallel,
            "actual_concurrent": min(len(queries), max_parallel),
            "successful_queries": 0,
            "failed_queries": 0,
            "elapsed_ms": 0,
            "average_query_time_ms": 0,
        }

        logger.info(
            f"Parallel execution throttled to {max_parallel} concurrent databases "
            f"(executing {len(queries)} queries)"
        )

        # FIX #3: Track metadata for each task (preserves connection context on exceptions)
        tasks = []
        task_metadata = []  # Store connection info for error handling

        for query_info in queries:
            conn_id = query_info.get("connection_id")
            sql = query_info.get("sql")

            if not conn_id or not sql:
                # For missing data, create a resolved future with error
                async def error_result(msg):
                    return {
                        "success": False,
                        "error": msg,
                        "data": [],
                    }
                tasks.append(error_result("Missing connection_id or sql"))
                task_metadata.append({"connection": None, "query_info": query_info})
                continue

            connection = conn_lookup.get(conn_id)
            if not connection:
                async def conn_error():
                    return {
                        "success": False,
                        "error": f"Connection ID {conn_id} not found",
                        "data": [],
                    }
                tasks.append(conn_error())
                task_metadata.append({"connection": None, "query_info": query_info})
                continue

            # FIX #1 & #4: Wrap task with semaphore for throttling + timeout protection
            async def execute_with_semaphore(conn, sql_query, allow_w):
                async with semaphore:
                    try:
                        # FIX #4: Add timeout wrapper to prevent semaphore slot from being held forever
                        # Use QUERY_TIMEOUT_SECONDS + 5 second buffer to allow for cleanup
                        timeout = settings.QUERY_TIMEOUT_SECONDS + 5
                        return await asyncio.wait_for(
                            self.execute_query_on_database(
                                connection=conn, sql=sql_query, allow_write=allow_w
                            ),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        # FIX #4: Handle timeout gracefully - don't hold semaphore
                        logger.warning(
                            f"Query timed out after {timeout}s for database '{conn.name}' "
                            f"(ID: {conn.id})"
                        )
                        return {
                            "success": False,
                            "error": f"Query execution timed out after {timeout} seconds",
                            "database_name": conn.name,
                            "connection_id": conn.id,
                            "database_type": conn.database_type,
                            "data": [],
                            "row_count": 0,
                            "execution_time_ms": timeout * 1000,
                        }

            # Add query execution task with semaphore throttling
            tasks.append(execute_with_semaphore(connection, sql, allow_write))
            task_metadata.append({"connection": connection, "query_info": query_info})

        # Execute all queries in parallel (handles both async and sync/DuckDB via executor)
        # return_exceptions=True ensures one failure doesn't stop others
        logger.info(f"Executing {len(tasks)} database queries in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate elapsed time
        elapsed = time.time() - start_time
        metrics["elapsed_ms"] = round(elapsed * 1000, 2)

        # FIX #3: Handle any exceptions from gather, preserving connection context
        processed_results = []
        total_query_time_ms = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Get connection metadata for this task
                metadata = task_metadata[i]
                connection = metadata.get("connection")

                # FIX #6: Track failed query
                metrics["failed_queries"] += 1

                # Build error message with connection context
                if connection:
                    error_msg = (
                        f"Exception in query for database '{connection.name}' "
                        f"(ID: {connection.id}, Type: {connection.database_type}): {result}"
                    )
                    logger.error(error_msg)
                    processed_results.append({
                        "success": False,
                        "error": str(result),
                        "database_name": connection.name,
                        "connection_id": connection.id,
                        "database_type": connection.database_type,
                        "data": [],
                        "row_count": 0,
                        "execution_time_ms": 0,
                    })
                else:
                    # No connection info available (validation error)
                    logger.error(f"Exception in parallel query {i}: {result}")
                    processed_results.append({
                        "success": False,
                        "error": str(result),
                        "data": [],
                    })
            else:
                # FIX #6: Track successful/failed queries and timing
                if result.get("success"):
                    metrics["successful_queries"] += 1
                else:
                    metrics["failed_queries"] += 1

                # Track query execution time for average
                query_time = result.get("execution_time_ms", 0)
                total_query_time_ms += query_time

                processed_results.append(result)

        # Calculate average query time
        if processed_results:
            metrics["average_query_time_ms"] = round(total_query_time_ms / len(processed_results), 2)

        # Calculate estimated sequential time (sum of all query times)
        estimated_sequential_ms = total_query_time_ms
        if estimated_sequential_ms > 0 and metrics["elapsed_ms"] > 0:
            speedup = estimated_sequential_ms / metrics["elapsed_ms"]
            metrics["estimated_sequential_ms"] = round(estimated_sequential_ms, 2)
            metrics["speedup"] = round(speedup, 2)

        # FIX #6: Log metrics
        logger.info(
            f"✓ Parallel execution complete: {metrics['successful_queries']}/{metrics['total_queries']} succeeded "
            f"in {metrics['elapsed_ms']}ms (avg: {metrics['average_query_time_ms']}ms/query)"
        )

        if metrics.get("speedup"):
            logger.info(
                f"⚡ Speedup: {metrics['speedup']:.1f}x faster than sequential "
                f"({metrics['estimated_sequential_ms']}ms → {metrics['elapsed_ms']}ms)"
            )

        # Store metrics in first result for API consumers (optional)
        if processed_results:
            processed_results[0]["_parallel_execution_metrics"] = metrics

        return processed_results

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
