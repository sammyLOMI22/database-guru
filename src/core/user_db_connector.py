"""Connect to user's database based on saved connections"""
import logging
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import DatabaseConnection
from src.core.connection_pool_manager import get_pool_manager_async

logger = logging.getLogger(__name__)


class UserDatabaseConnector:
    """Manages connections to user's databases"""

    @staticmethod
    def build_connection_url(connection: DatabaseConnection) -> str:
        """Build SQLAlchemy connection URL from connection details"""

        if connection.database_type == 'sqlite':
            # SQLite - async driver
            return f"sqlite+aiosqlite:///{connection.database_name}"

        elif connection.database_type == 'postgresql':
            # PostgreSQL - async driver
            password = connection.password_encrypted or ""  # TODO: decrypt
            return f"postgresql+asyncpg://{connection.username}:{password}@{connection.host}:{connection.port}/{connection.database_name}"

        elif connection.database_type == 'mysql':
            # MySQL - async driver
            password = connection.password_encrypted or ""  # TODO: decrypt
            return f"mysql+aiomysql://{connection.username}:{password}@{connection.host}:{connection.port}/{connection.database_name}"

        elif connection.database_type == 'duckdb':
            # DuckDB - uses duckdb-engine for SQLAlchemy support
            # Format: duckdb:///path/to/database.duckdb or duckdb:///:memory:
            return f"duckdb:///{connection.database_name}"

        elif connection.database_type == 'mssql':
            # SQL Server - uses pymssql (sync driver, no ODBC required)
            password = connection.password_encrypted or ""  # TODO: decrypt
            port = connection.port or 1433
            return f"mssql+pymssql://{connection.username}:{password}@{connection.host}:{port}/{connection.database_name}"

        elif connection.database_type == 'oracle':
            # Oracle - uses python-oracledb in thin mode (no Oracle Client required)
            # database_name is treated as the service name
            password = connection.password_encrypted or ""  # TODO: decrypt
            port = connection.port or 1521
            return f"oracle+oracledb://{connection.username}:{password}@{connection.host}:{port}/?service_name={connection.database_name}"

        elif connection.database_type in ('mongodb', 'redis', 'cassandra', 'dynamodb', 'elasticsearch'):
            # NoSQL databases use their own client pools in src/nosql/
            # They are routed via src.nosql.router before reaching this method
            raise ValueError(
                f"{connection.database_type} does not use SQLAlchemy URLs. "
                "NoSQL connections are routed through src.nosql.router."
            )

        else:
            raise ValueError(f"Unsupported database type: {connection.database_type}")

    @staticmethod
    @asynccontextmanager
    async def get_user_db_session(connection: DatabaseConnection):
        """
        Get a session to the user's database using connection pooling.

        Args:
            connection: DatabaseConnection object with connection details

        Yields:
            AsyncSession or Session connected to user's database
        """
        logger.info(f"Getting pooled session for database: {connection.name} ({connection.database_type})")

        # Get pool manager instance
        pool_manager = await get_pool_manager_async()

        # Get or create pool for this connection (metrics updated in get_pool())
        pool_entry = await pool_manager.get_pool(connection)

        # DuckDB, MSSQL (pymssql), and Oracle (oracledb sync) use sync sessions
        if connection.database_type in ('duckdb', 'mssql', 'oracle'):
            # Create sync session from pool
            session = pool_entry.session_factory()
            try:
                # Wrap sync session to make it work with async context
                yield session
            finally:
                session.close()
                pool_entry.metrics.total_checkins += 1
                logger.debug(f"Returned session to pool: {connection.name}")
        else:
            # Use async session for other databases
            async with pool_entry.session_factory() as session:
                try:
                    yield session
                finally:
                    pool_entry.metrics.total_checkins += 1
                    logger.debug(f"Returned session to pool: {connection.name}")
