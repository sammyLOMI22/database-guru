"""DuckDB session manager for file-based queries

Phase 13: CSV & Excel File Support

Manages a shared in-memory DuckDB session for querying uploaded files.
Tables are lazily loaded when first accessed to optimize memory usage.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

import duckdb

from src.config.settings import Settings

logger = logging.getLogger(__name__)


class FileSourceDuckDBSession:
    """
    Manages DuckDB sessions for file-based queries.

    Uses a shared in-memory DuckDB database that persists across requests.
    Tables are lazily loaded when first accessed.

    Thread Safety:
    - DuckDB operations are wrapped in asyncio.run_in_executor()
    - A lock protects table creation to prevent race conditions

    Singleton Pattern:
    - Single DuckDB connection shared across the application
    - Tables loaded on-demand and cached in memory
    """

    _instance: Optional[duckdb.DuckDBPyConnection] = None
    _loaded_tables: Set[str] = set()
    _lock: asyncio.Lock = asyncio.Lock()
    _table_metadata: Dict[str, Dict[str, Any]] = {}
    _settings: Optional[Settings] = None

    @classmethod
    def _get_settings(cls) -> Settings:
        """Get settings, creating if needed."""
        if cls._settings is None:
            cls._settings = Settings()
        return cls._settings

    @classmethod
    def get_session(cls) -> duckdb.DuckDBPyConnection:
        """
        Get or create shared DuckDB session.

        Returns:
            DuckDB connection instance
        """
        if cls._instance is None:
            settings = cls._get_settings()
            cls._instance = duckdb.connect(':memory:')

            # Configure memory limit
            memory_limit = settings.DUCKDB_FILE_MEMORY_LIMIT
            cls._instance.execute(f"SET memory_limit='{memory_limit}'")

            # Configure threads
            threads = settings.DUCKDB_FILE_THREADS
            cls._instance.execute(f"SET threads={threads}")

            # Load Excel extension
            try:
                cls._instance.execute("INSTALL excel; LOAD excel;")
                logger.debug("Loaded DuckDB Excel extension")
            except Exception as e:
                logger.warning(f"Failed to load Excel extension: {e}")

            logger.info(
                f"FileSourceDuckDBSession initialized with in-memory database "
                f"(memory_limit={memory_limit}, threads={threads})"
            )

        return cls._instance

    @classmethod
    async def ensure_table_loaded(
        cls,
        file_source: "FileSource",  # Forward reference
    ) -> str:
        """
        Ensure file is loaded as DuckDB table, return table name.

        Uses lazy loading - table is created on first access.
        Subsequent calls return immediately if table exists.

        Args:
            file_source: FileSource model instance

        Returns:
            The DuckDB table name
        """
        table_name = file_source.duckdb_table_name

        async with cls._lock:
            if table_name in cls._loaded_tables:
                logger.debug(f"Table '{table_name}' already loaded")
                return table_name

            # Load table in executor (DuckDB is sync)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                cls._load_table_sync,
                file_source.file_path,
                file_source.file_type,
                file_source.sheet_name,
                table_name,
            )

            cls._loaded_tables.add(table_name)
            logger.info(
                f"Loaded file '{file_source.original_filename}' as table '{table_name}'"
            )

        return table_name

    @classmethod
    def _load_table_sync(
        cls,
        file_path: str,
        file_type: str,
        sheet_name: Optional[str],
        table_name: str,
    ) -> None:
        """Synchronously load file into DuckDB table."""
        session = cls.get_session()

        try:
            if file_type == 'csv':
                session.execute(f"""
                    CREATE OR REPLACE TABLE "{table_name}" AS
                    SELECT * FROM read_csv_auto('{file_path}', header=true, all_varchar=false)
                """)
            elif file_type in ('xlsx', 'xls'):
                sheet = sheet_name or 'Sheet1'
                session.execute(f"""
                    CREATE OR REPLACE TABLE "{table_name}" AS
                    SELECT * FROM read_excel('{file_path}', sheet='{sheet}')
                """)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Get row count for metadata
            result = session.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
            row_count = result[0] if result else 0
            cls._table_metadata[table_name] = {'row_count': row_count}

            logger.debug(f"Created table '{table_name}' with {row_count} rows")

        except Exception as e:
            logger.error(f"Failed to load table '{table_name}': {e}")
            raise

    @classmethod
    async def execute_query(
        cls,
        sql: str,
        file_sources: List["FileSource"],
        max_rows: int = 1000,
    ) -> Dict[str, Any]:
        """
        Execute SQL query against file tables.

        Ensures all referenced tables are loaded before execution.

        Args:
            sql: SQL query to execute
            file_sources: List of FileSource instances that may be referenced
            max_rows: Maximum rows to return

        Returns:
            Dict with success, data, columns, row_count, error
        """
        # Ensure all tables are loaded
        for fs in file_sources:
            await cls.ensure_table_loaded(fs)

        # Execute query in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            cls._execute_sync,
            sql,
            max_rows,
        )
        return result

    @classmethod
    def _execute_sync(cls, sql: str, max_rows: int) -> Dict[str, Any]:
        """Execute query synchronously."""
        session = cls.get_session()

        try:
            result = session.execute(sql)

            if result.description:
                columns = [desc[0] for desc in result.description]
                rows = result.fetchmany(max_rows + 1)

                # Check if truncated
                truncated = len(rows) > max_rows
                if truncated:
                    rows = rows[:max_rows]

                # Convert to list of dicts
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        # Convert to JSON-serializable
                        if hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        row_dict[col] = val
                    data.append(row_dict)

                return {
                    'success': True,
                    'data': data,
                    'columns': columns,
                    'row_count': len(data),
                    'truncated': truncated,
                    'error': None,
                }
            else:
                return {
                    'success': True,
                    'data': [],
                    'columns': [],
                    'row_count': 0,
                    'truncated': False,
                    'error': None,
                }

        except Exception as e:
            logger.error(f"DuckDB query error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'columns': [],
                'row_count': 0,
                'truncated': False,
            }

    @classmethod
    async def get_table_schema(
        cls,
        file_source: "FileSource",
    ) -> Dict[str, Any]:
        """
        Get schema for a file table.

        Args:
            file_source: FileSource instance

        Returns:
            Dict with columns, row_count, sample_values
        """
        await cls.ensure_table_loaded(file_source)

        loop = asyncio.get_event_loop()
        schema = await loop.run_in_executor(
            None,
            cls._get_schema_sync,
            file_source.duckdb_table_name,
        )
        return schema

    @classmethod
    def _get_schema_sync(cls, table_name: str) -> Dict[str, Any]:
        """Get schema synchronously."""
        session = cls.get_session()

        # Get column info using DESCRIBE
        result = session.execute(f'DESCRIBE "{table_name}"')
        columns = []
        for row in result.fetchall():
            columns.append({
                'name': row[0],
                'type': str(row[1]).upper(),
                'nullable': row[2] == 'YES' if len(row) > 2 else True,
            })

        # Get row count
        count_result = session.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
        row_count = count_result[0] if count_result else 0

        # Get sample values for each column
        sample_values = {}
        for col in columns:
            try:
                col_name = col['name']
                sample_result = session.execute(f"""
                    SELECT DISTINCT "{col_name}"
                    FROM "{table_name}"
                    WHERE "{col_name}" IS NOT NULL
                    LIMIT 5
                """)
                values = []
                for sample_row in sample_result.fetchall():
                    val = sample_row[0]
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    values.append(val)
                sample_values[col_name] = values
                col['sample_values'] = values
            except Exception as e:
                logger.debug(f"Failed to get samples for column {col['name']}: {e}")
                sample_values[col['name']] = []
                col['sample_values'] = []

        return {
            'columns': columns,
            'row_count': row_count,
            'sample_values': sample_values,
        }

    @classmethod
    async def unload_table(cls, table_name: str) -> None:
        """
        Remove table from DuckDB session.

        Args:
            table_name: The table name to unload
        """
        async with cls._lock:
            if table_name in cls._loaded_tables:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    cls._drop_table_sync,
                    table_name,
                )
                cls._loaded_tables.discard(table_name)
                cls._table_metadata.pop(table_name, None)
                logger.info(f"Unloaded table '{table_name}'")

    @classmethod
    def _drop_table_sync(cls, table_name: str) -> None:
        """Synchronously drop table."""
        session = cls.get_session()
        try:
            session.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        except Exception as e:
            logger.warning(f"Failed to drop table '{table_name}': {e}")

    @classmethod
    async def reset_session(cls) -> None:
        """
        Reset the DuckDB session (for testing or cleanup).

        Closes the current connection and clears all state.
        """
        async with cls._lock:
            if cls._instance:
                try:
                    cls._instance.close()
                except Exception as e:
                    logger.warning(f"Error closing DuckDB session: {e}")

            cls._instance = None
            cls._loaded_tables.clear()
            cls._table_metadata.clear()
            logger.info("FileSourceDuckDBSession reset")

    @classmethod
    def get_loaded_tables(cls) -> List[str]:
        """
        Get list of currently loaded tables.

        Returns:
            List of table names
        """
        return list(cls._loaded_tables)

    @classmethod
    def get_table_metadata(cls, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a loaded table.

        Args:
            table_name: The table name

        Returns:
            Dict with row_count, or None if not loaded
        """
        return cls._table_metadata.get(table_name)

    @classmethod
    async def is_table_loaded(cls, table_name: str) -> bool:
        """
        Check if a table is currently loaded.

        Args:
            table_name: The table name to check

        Returns:
            True if loaded, False otherwise
        """
        return table_name in cls._loaded_tables


# Type hint import for forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.database.models import FileSource
