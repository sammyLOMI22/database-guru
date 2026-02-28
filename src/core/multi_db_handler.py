"""Multi-database handler for querying across multiple databases"""
import logging
import asyncio
from asyncio import Semaphore
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection, FileSource
from src.core.user_db_connector import UserDatabaseConnector
from src.core.schema_inspector import SchemaInspector
from src.core.executor import SQLExecutor
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent
from src.llm.sql_generator import SQLGenerator
from src.llm.multi_db_query_validator import (
    MultiDatabaseQueryValidator,
    MultiDatabaseValidationResult,
    DatabaseQueryAssessment,
    QueryCapability,
)
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class MultiDatabaseHandler:
    """Handle queries across multiple database connections"""

    def __init__(self):
        self.schema_inspector = SchemaInspector()

    async def _introspect_nosql_database(self, conn: DatabaseConnection) -> Dict[str, Any]:
        """Introspect schema for a NoSQL database via its native schema inspector."""
        from datetime import datetime

        db_type = conn.database_type.lower()

        # Check schema cache first (30-minute TTL)
        cached = conn.schema_cache
        if cached and isinstance(cached, dict) and cached.get("tables"):
            updated_at = conn.schema_updated_at
            if updated_at:
                age = (datetime.utcnow() - updated_at).total_seconds()
                if age < 1800:
                    tables_dict = cached.get("tables", {})
                    tables_list = [{"name": name, **info} for name, info in tables_dict.items()]
                    logger.info(f"Using cached NoSQL schema for '{conn.name}' ({int(age)}s old)")
                    return {
                        "connection_id": conn.id,
                        "name": conn.name,
                        "database_type": conn.database_type,
                        "database_name": conn.database_name,
                        "tables": tables_list,
                        "table_count": len(tables_list),
                    }

        # Fresh introspection via per-DB inspector
        schema_dict = None
        if db_type == "mongodb":
            from src.nosql.mongodb.client_pool import MongoClientPool
            from src.nosql.mongodb.schema_inspector import MongoSchemaInspector
            pool = await MongoClientPool.get_instance()
            _, mongo_db = await pool.get_client(conn)
            inspector = MongoSchemaInspector(mongo_db)
            schema_dict = await inspector.get_schema()
        elif db_type == "redis":
            from src.nosql.redis.client_pool import RedisClientPool
            from src.nosql.redis.schema_inspector import RedisSchemaInspector
            pool = await RedisClientPool.get_instance()
            client = await pool.get_client(conn)
            inspector = RedisSchemaInspector(client)
            schema_dict = await inspector.get_schema()
        elif db_type == "cassandra":
            from src.nosql.cassandra.client_pool import CassandraClientPool
            from src.nosql.cassandra.schema_inspector import CassandraSchemaInspector
            pool = await CassandraClientPool.get_instance()
            session = await pool.get_client(conn)
            inspector = CassandraSchemaInspector(session, conn.database_name)
            schema_dict = await inspector.get_schema()
        elif db_type == "dynamodb":
            from src.nosql.dynamodb.client_pool import DynamoDBClientPool
            from src.nosql.dynamodb.schema_inspector import DynamoDBSchemaInspector
            pool = await DynamoDBClientPool.get_instance()
            client = await pool.get_client(conn)
            inspector = DynamoDBSchemaInspector(client)
            schema_dict = await inspector.get_schema()
        elif db_type == "elasticsearch":
            from src.nosql.elasticsearch.client_pool import ElasticsearchClientPool
            from src.nosql.elasticsearch.schema_inspector import ElasticsearchSchemaInspector
            pool = await ElasticsearchClientPool.get_instance()
            client = await pool.get_client(conn)
            inspector = ElasticsearchSchemaInspector(client)
            schema_dict = await inspector.get_schema()
        else:
            raise ValueError(f"Unknown NoSQL type: {db_type}")

        tables_dict = schema_dict.get("tables", {})
        tables_list = [{"name": name, **info} for name, info in tables_dict.items()]

        logger.info(f"Introspected NoSQL schema for '{conn.name}': {len(tables_list)} collections/indices")

        return {
            "connection_id": conn.id,
            "name": conn.name,
            "database_type": conn.database_type,
            "database_name": conn.database_name,
            "tables": tables_list,
            "table_count": len(tables_list),
        }

    async def _introspect_single_database(self, conn: DatabaseConnection) -> Dict[str, Any]:
        """
        Introspect schema for a single database connection

        Args:
            conn: DatabaseConnection to introspect

        Returns:
            Dict with database info and schema, or error info
        """
        try:
            # Route NoSQL databases to their own schema inspectors
            from src.nosql.router import is_nosql
            if is_nosql(conn.database_type):
                return await self._introspect_nosql_database(conn)

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
        self,
        connections: List[DatabaseConnection],
        file_sources: Optional[List[FileSource]] = None,
    ) -> Dict[str, Any]:
        """
        Build a combined schema from multiple database connections and file sources (parallelized)

        Args:
            connections: List of DatabaseConnection objects
            file_sources: Optional list of FileSource objects (Phase 13: CSV/Excel files)

        Returns:
            Dict with combined schema information including database prefixes and file sources
        """
        combined_schema = {
            "databases": [],
            "file_sources": [],  # Phase 13: CSV/Excel file sources
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
            f"✓ Database schema introspection complete: {combined_schema['total_tables']} tables "
            f"across {len(connections)} database(s)"
        )

        # Phase 13: Add file source schemas
        if file_sources:
            await self._add_file_source_schemas(combined_schema, file_sources)

        return combined_schema

    async def _add_file_source_schemas(
        self,
        combined_schema: Dict[str, Any],
        file_sources: List[FileSource],
    ) -> None:
        """
        Add file source schemas to combined schema (Phase 13).

        Args:
            combined_schema: Combined schema dict to update in place
            file_sources: List of FileSource objects
        """
        from src.core.file_source_session import FileSourceDuckDBSession

        for file_source in file_sources:
            if file_source.processing_status != 'ready':
                logger.warning(
                    f"Skipping file source '{file_source.name}' - status: {file_source.processing_status}"
                )
                continue

            try:
                # Get schema from DuckDB session (lazy loads table if needed)
                schema = await FileSourceDuckDBSession.get_table_schema(file_source)

                file_schema = {
                    "source_id": file_source.id,
                    "name": file_source.name,
                    "source_type": "file",
                    "file_type": file_source.file_type,
                    "original_filename": file_source.original_filename,
                    "duckdb_table_name": file_source.duckdb_table_name,
                    "tables": [{
                        "name": file_source.duckdb_table_name,
                        "columns": schema.get("columns", []),
                        "row_count": schema.get("row_count", 0),
                    }],
                }

                combined_schema["file_sources"].append(file_schema)
                combined_schema["total_tables"] += 1
                combined_schema["total_columns"] += len(schema.get("columns", []))

                logger.info(
                    f"Added file source schema: '{file_source.name}' "
                    f"({len(schema.get('columns', []))} columns, {schema.get('row_count', 0)} rows)"
                )

            except Exception as e:
                logger.error(f"Failed to get schema for file source '{file_source.name}': {e}")
                combined_schema["file_sources"].append({
                    "source_id": file_source.id,
                    "name": file_source.name,
                    "source_type": "file",
                    "error": str(e),
                    "tables": [],
                })

    async def execute_file_query(
        self,
        sql: str,
        file_sources: List[FileSource],
        max_rows: int = 1000,
    ) -> Dict[str, Any]:
        """
        Execute SQL query against file sources via DuckDB (Phase 13).

        Args:
            sql: SQL query to execute
            file_sources: List of FileSource objects that may be referenced
            max_rows: Maximum rows to return

        Returns:
            Dict with success, data, columns, row_count, error
        """
        from src.core.file_source_session import FileSourceDuckDBSession

        try:
            result = await FileSourceDuckDBSession.execute_query(
                sql=sql,
                file_sources=file_sources,
                max_rows=max_rows,
            )

            # Add source type indicator
            result["source_type"] = "file"

            if result.get("success"):
                logger.info(
                    f"File query executed successfully: {result.get('row_count', 0)} rows"
                )
            else:
                logger.error(f"File query failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Failed to execute file query: {e}")
            return {
                "success": False,
                "error": str(e),
                "source_type": "file",
                "data": [],
                "columns": [],
                "row_count": 0,
            }

    def format_schema_for_llm(self, combined_schema: Dict[str, Any]) -> str:
        """
        Format combined schema for LLM consumption

        Args:
            combined_schema: Combined schema from build_combined_schema()

        Returns:
            Formatted string with database prefixes and file sources for LLM
        """
        lines = []

        # Count sources
        db_count = len(combined_schema.get('databases', []))
        file_count = len(combined_schema.get('file_sources', []))
        total_tables = combined_schema.get('total_tables', 0)

        if file_count > 0:
            lines.append(
                f"# Data Sources ({total_tables} tables across {db_count} databases and {file_count} files)\n"
            )
        else:
            lines.append(
                f"# Multi-Database Schema ({total_tables} tables across {db_count} databases)\n"
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

        # Phase 13: Add file sources to LLM prompt
        file_sources = combined_schema.get("file_sources", [])
        if file_sources:
            lines.append("\n## FILE SOURCES (CSV/Excel uploads)")
            lines.append("These are uploaded files queryable as SQL tables via DuckDB.\n")

            for file_source in file_sources:
                if "error" in file_source:
                    lines.append(
                        f"\n--- File: {file_source['name']} (ERROR: {file_source['error']}) ---\n"
                    )
                    continue

                lines.append(f"\n--- File: {file_source['name']} ({file_source['file_type'].upper()}) ---")
                lines.append(f"Original Filename: {file_source['original_filename']}")
                lines.append(f"Query as table: {file_source['duckdb_table_name']}")

                for table in file_source.get("tables", []):
                    lines.append(f"Row Count: {table.get('row_count', 'unknown')}")
                    lines.append("Columns:")

                    for col in table.get("columns", []):
                        col_name = col.get("name", "unknown")
                        col_type = col.get("type", "VARCHAR")
                        col_def = f"  - {col_name} ({col_type})"

                        # Add sample values if available
                        samples = col.get("sample_values", [])
                        if samples:
                            sample_str = ", ".join(repr(s) for s in samples[:3])
                            col_def += f"  // Examples: {sample_str}"

                        lines.append(col_def)

                lines.append("")

            # Add cross-source guidance if both DBs and files present
            if combined_schema.get("databases") and file_sources:
                lines.append("\n## CROSS-SOURCE QUERY GUIDANCE")
                lines.append("When querying across databases and files:")
                lines.append("- Database tables: Prefix with database connection name (e.g., db_name.table)")
                lines.append("- File tables: Use the DuckDB table name directly (e.g., file_1_sales)")
                lines.append("- Generate SEPARATE queries for databases vs files - they use different engines")
                lines.append("- For file queries, use: FILE_SOURCE: file_name prefix")
                lines.append("")

        # Add NoSQL guidance if mixed sources
        nosql_types = {"mongodb", "redis", "cassandra", "dynamodb", "elasticsearch"}
        nosql_dbs = [
            db for db in combined_schema.get("databases", [])
            if db.get("database_type") in nosql_types and "error" not in db
        ]
        if nosql_dbs:
            lines.append("\n## NoSQL DATA SOURCES")
            lines.append("These databases use native query languages (NOT SQL).")
            lines.append("Generate SEPARATE native queries for each NoSQL source.\n")
            for db in nosql_dbs:
                lines.append(f"- {db['name']} ({db['database_type']}): Use native {db['database_type']} query syntax")
            lines.append("")

        return "\n".join(lines)

    async def validate_multi_database_query(
        self,
        question: str,
        connections: List[DatabaseConnection],
        base_sql: Optional[str] = None,
        combined_schema: Optional[Dict[str, Any]] = None,
    ) -> MultiDatabaseValidationResult:
        """
        Pre-flight validation for multi-database queries.

        Assesses each database's capability to answer the query:
        - FULL: Can answer completely with original SQL
        - PARTIAL: Can answer with modified SQL (alternatives found)
        - CANNOT: Cannot answer (missing required tables/columns)

        Args:
            question: Natural language question
            connections: List of target database connections
            base_sql: Optional pre-generated SQL to validate
            combined_schema: Optional pre-built combined schema (saves introspection)

        Returns:
            MultiDatabaseValidationResult with per-database assessments
        """
        logger.info(f"Validating query across {len(connections)} database(s)")

        # Build combined schema if not provided
        if combined_schema is None:
            combined_schema = await self.build_combined_schema(connections)

        # Convert combined schema to validator format
        # Validator expects: {conn_id: {"name": ..., "database_type": ..., "tables": {...}}}
        schemas_for_validator: Dict[int, Dict[str, Any]] = {}
        connection_names: Dict[int, str] = {}

        for db_info in combined_schema.get("databases", []):
            conn_id = db_info.get("connection_id")
            if conn_id is None:
                continue

            # Skip databases with errors
            if "error" in db_info:
                logger.warning(f"Skipping validation for {db_info.get('name')}: {db_info.get('error')}")
                continue

            connection_names[conn_id] = db_info.get("name", f"Database {conn_id}")

            # Convert tables list to dict format for validator
            tables_dict = {}
            for table in db_info.get("tables", []):
                table_name = table.get("name", "")
                tables_dict[table_name] = {
                    "columns": table.get("columns", []),
                    "foreign_keys": table.get("foreign_keys", []),
                }

            schemas_for_validator[conn_id] = {
                "name": db_info.get("name"),
                "database_type": db_info.get("database_type"),
                "tables": tables_dict,
            }

            # Debug: Log tables and any location-related columns found
            for tbl_name, tbl_info in tables_dict.items():
                cols = tbl_info.get("columns", [])
                col_names = [c.get("name", c) if isinstance(c, dict) else c for c in cols]
                loc_cols = [c for c in col_names if any(sub in c.lower() for sub in ['state', 'city', 'region'])]
                if loc_cols:
                    logger.info(f"Validator schema - DB {conn_id} table '{tbl_name}' has location columns: {loc_cols}")

        # If no base SQL provided, use question-based validation
        # The validator will analyze the question to detect location references,
        # table mentions, etc. and check if the schema can support them
        if not base_sql:
            logger.info("No base SQL provided - using question-based validation")
            base_sql = ""  # Validator will use _extract_requirements_from_question

        # Create validator and assess
        validator = MultiDatabaseQueryValidator(schemas_for_validator)
        result = validator.assess_query(
            question=question,
            base_sql=base_sql,
            connection_names=connection_names,
        )

        # Log summary
        summary = result.get_summary()
        logger.info(
            f"Validation complete: {summary['full']} full, "
            f"{summary['partial']} partial, {summary['cannot']} cannot"
        )

        return result

    def _convert_schema_for_validation(
        self,
        combined_schema: Dict[str, Any]
    ) -> tuple[Dict[int, Dict[str, Any]], Dict[int, str]]:
        """
        Convert combined schema format to validator format.

        Returns:
            Tuple of (schemas_dict, connection_names_dict)
        """
        schemas: Dict[int, Dict[str, Any]] = {}
        names: Dict[int, str] = {}

        for db_info in combined_schema.get("databases", []):
            conn_id = db_info.get("connection_id")
            if conn_id is None or "error" in db_info:
                continue

            names[conn_id] = db_info.get("name", f"Database {conn_id}")

            tables_dict = {}
            for table in db_info.get("tables", []):
                table_name = table.get("name", "")
                tables_dict[table_name] = {
                    "columns": table.get("columns", []),
                    "foreign_keys": table.get("foreign_keys", []),
                }

            schemas[conn_id] = {
                "name": db_info.get("name"),
                "database_type": db_info.get("database_type"),
                "tables": tables_dict,
            }

        return schemas, names

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
        row_limit: int = 100,
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
            # Route NoSQL databases to their own pipeline
            from src.nosql.router import is_nosql, execute_nosql_query

            if is_nosql(connection.database_type):
                nosql_result = await execute_nosql_query(
                    question=question,
                    connection=connection,
                    model=model_used,
                    allow_write=allow_write,
                    row_limit=row_limit,
                )
                return {
                    **nosql_result,
                    "connection": connection,
                    "model_used": model_used,
                    "database_name": connection.name,
                    "connection_id": connection.id,
                }

            # ALWAYS get full schema directly from database for accurate WHERE validation
            # The combined_schema_data may not have columns in the right format
            db_schema_dict = None
            async with UserDatabaseConnector.get_user_db_session(connection) as user_db:
                schema_data = await self.schema_inspector.get_full_schema(user_db)
                db_schema_dict = schema_data  # Full schema for WHERE column validation
                db_schema = self._format_single_db_schema(schema_data)
                logger.info(f"[SCHEMA_DEBUG] Got schema for {connection.name} with {len(schema_data.get('tables', {}))} tables, schema_dict is not None: {db_schema_dict is not None}")

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
                row_limit=row_limit,
            )

            # Return result with connection metadata
            return {
                **exec_result,
                "connection": connection,  # Include connection for later QueryHistory creation
                "model_used": model_used,
            }

        except Exception as e:
            logger.error(f"Failed to execute query on database '{connection.name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "database_name": connection.name,
                "connection_id": connection.id,
                "connection": connection,
                "model_used": model_used,
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "total_attempts": 0,
                "attempts": [],
            }

    async def _execute_single_file_query_task(
        self,
        file_source: FileSource,
        question: str,
        schema: str,
        sql_generator: "SQLGenerator",
        model_used: str = "unknown",
        row_limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Execute a query against a file source via DuckDB (Phase 13).

        Generates SQL using the LLM against the file's schema,
        then executes via DuckDB.
        """
        import time
        from src.core.file_source_session import FileSourceDuckDBSession

        start_time = time.time()

        try:
            # Build a focused schema string for this file source
            file_schema = await FileSourceDuckDBSession.get_table_schema(file_source)
            schema_lines = [
                f"Table: {file_source.duckdb_table_name}",
                f"Row Count: {file_schema.get('row_count', 'unknown')}",
                "Columns:",
            ]
            for col in file_schema.get("columns", []):
                col_def = f"  - {col['name']} ({col['type']})"
                samples = col.get("sample_values", [])
                if samples:
                    col_def += f"  // Examples: {', '.join(repr(s) for s in samples[:3])}"
                schema_lines.append(col_def)
            file_schema_text = "\n".join(schema_lines)

            # Generate SQL using the LLM
            sql_result = await sql_generator.generate_sql(
                question=question,
                schema=file_schema_text,
                model=model_used,
            )

            generated_sql = sql_result.get("sql", "") if isinstance(sql_result, dict) else str(sql_result)

            if not generated_sql:
                return {
                    "success": False,
                    "error": "Failed to generate SQL for file source",
                    "source_type": "file",
                    "file_source": file_source,
                    "connection_name": f"📄 {file_source.name}",
                    "database_type": "duckdb",
                    "model_used": model_used,
                    "data": [],
                    "row_count": 0,
                }

            # Execute via DuckDB
            exec_result = await self.execute_file_query(
                sql=generated_sql,
                file_sources=[file_source],
                max_rows=row_limit,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            if exec_result.get("success"):
                return {
                    "success": True,
                    "sql": generated_sql,
                    "data": exec_result.get("data", []),
                    "columns": exec_result.get("columns", []),
                    "row_count": exec_result.get("row_count", 0),
                    "execution_time_ms": round(elapsed_ms, 2),
                    "source_type": "file",
                    "file_source": file_source,
                    "connection_name": f"📄 {file_source.name}",
                    "database_type": "duckdb",
                    "model_used": model_used,
                    "total_attempts": 1,
                    "attempts": [],
                }
            else:
                return {
                    "success": False,
                    "error": exec_result.get("error", "Unknown DuckDB error"),
                    "sql": generated_sql,
                    "source_type": "file",
                    "file_source": file_source,
                    "connection_name": f"📄 {file_source.name}",
                    "database_type": "duckdb",
                    "model_used": model_used,
                    "data": [],
                    "row_count": 0,
                    "execution_time_ms": round(elapsed_ms, 2),
                }

        except Exception as e:
            logger.error(f"Failed to execute query on file source '{file_source.name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "source_type": "file",
                "file_source": file_source,
                "connection_name": f"📄 {file_source.name}",
                "database_type": "duckdb",
                "model_used": model_used,
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
        schema_dict: Optional[Dict] = None,
        model: Optional[str] = None,
        row_limit: int = 100,
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
            row_limit: Maximum rows for SQL LIMIT clause (1-10000, default 100)

        Returns:
            Dict with execution results including correction attempts
        """
        logger.info(f"🔍 [SCHEMA_DEBUG] execute_query_with_self_correction received schema_dict is not None: {schema_dict is not None}")
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
                        schema_dict=schema_dict,  # Pass for WHERE column validation
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
                        row_limit=row_limit,
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
                        "fix_methods": result.get("fix_methods", {}),  # For attempt formatting
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
                        "fix_methods": result.get("fix_methods", {}),
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
        """Format schema data for a single database for LLM consumption

        Handles both formats:
        - Dict format: {"tables": {"orders": {...}, "customers": {...}}}
        - List format: {"tables": [{"name": "orders", ...}, {"name": "customers", ...}]}
        """
        lines = []
        tables_data = schema_data.get("tables", {})

        # Handle both dict and list formats for tables
        if isinstance(tables_data, dict):
            # Dict format from get_full_schema: {"orders": {...}, "customers": {...}}
            table_items = [(name, info) for name, info in tables_data.items()]
        else:
            # List format: [{"name": "orders", ...}, {"name": "customers", ...}]
            table_items = [(t.get("name", "unknown"), t) for t in tables_data]

        for table_name, table_info in table_items:
            lines.append(f"Table: {table_name}")

            # Handle columns - can be list or dict
            columns = table_info.get("columns", [])
            if isinstance(columns, dict):
                # Dict format: {"id": {"type": "INTEGER"}, ...}
                col_items = [(name, info) for name, info in columns.items()]
            else:
                # List format: [{"name": "id", "type": "INTEGER"}, ...]
                col_items = [(c.get("name", "unknown"), c) for c in columns]

            for col_name, col_info in col_items:
                col_type = col_info.get("type", "UNKNOWN") if isinstance(col_info, dict) else str(col_info)
                col_def = f"  - {col_name} ({col_type})"

                if isinstance(col_info, dict):
                    if col_info.get("nullable") is False:
                        col_def += " NOT NULL"
                    if col_info.get("primary_key"):
                        col_def += " PRIMARY KEY"

                    # Add sample values if available (helps LLM understand format)
                    if "sample_values" in col_info and col_info["sample_values"]:
                        samples = col_info["sample_values"]
                        sample_str = ", ".join(repr(s) for s in samples[:5])
                        col_def += f"  // Examples: {sample_str}"

                lines.append(col_def)

            # Handle foreign keys
            fks = table_info.get("foreign_keys", [])
            if fks:
                lines.append("  Foreign Keys:")
                for fk in fks:
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
