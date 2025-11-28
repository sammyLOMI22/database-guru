"""Connect to user's database based on saved connections"""
import logging
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import DatabaseConnection

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

        elif connection.database_type == 'mongodb':
            # MongoDB is not SQL, would need different handling
            raise NotImplementedError("MongoDB queries not yet supported")

        else:
            raise ValueError(f"Unsupported database type: {connection.database_type}")

    @staticmethod
    @asynccontextmanager
    async def get_user_db_session(connection: DatabaseConnection):
        """
        Get a session to the user's database

        Args:
            connection: DatabaseConnection object with connection details

        Yields:
            AsyncSession or Session connected to user's database
        """
        connection_url = UserDatabaseConnector.build_connection_url(connection)

        logger.info(f"Connecting to user database: {connection.name} ({connection.database_type})")

        # DuckDB doesn't have an async driver, use sync connection wrapped
        if connection.database_type == 'duckdb':
            # Create sync engine for DuckDB
            engine = create_engine(
                connection_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )

            # Create session factory
            session_factory = sessionmaker(
                engine,
                class_=Session,
                expire_on_commit=False,
            )

            # Create sync session
            session = session_factory()
            try:
                # Wrap sync session to make it work with async context
                yield session
            finally:
                session.close()
                engine.dispose()
                logger.info(f"Disconnected from user database: {connection.name}")
        else:
            # Use async engine for other databases
            engine = create_async_engine(
                connection_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )

            # Create session factory
            async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create and yield session
            async with async_session_factory() as session:
                try:
                    yield session
                finally:
                    await session.close()

            # Dispose engine
            await engine.dispose()
            logger.info(f"Disconnected from user database: {connection.name}")

    @staticmethod
    async def create_session(
        database_type: str,
        database_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Create a database session without context manager
        Caller is responsible for closing the session and disposing the engine

        Args:
            database_type: Type of database (postgresql, mysql, sqlite, duckdb)
            database_name: Database name or file path
            host: Database host (not needed for sqlite/duckdb)
            port: Database port (not needed for sqlite/duckdb)
            username: Database username (not needed for sqlite/duckdb)
            password: Database password (not needed for sqlite/duckdb)

        Returns:
            Tuple of (session, engine, is_sync) - caller must close session and dispose engine
        """
        # Build connection URL
        if database_type == 'sqlite':
            connection_url = f"sqlite+aiosqlite:///{database_name}"
        elif database_type == 'postgresql':
            connection_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database_name}"
        elif database_type == 'mysql':
            connection_url = f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database_name}"
        elif database_type == 'duckdb':
            connection_url = f"duckdb:///{database_name}"
        elif database_type == 'mongodb':
            raise NotImplementedError("MongoDB queries not yet supported")
        else:
            raise ValueError(f"Unsupported database type: {database_type}")

        logger.info(f"Creating session for {database_type} database: {database_name}")

        # DuckDB uses sync engine
        if database_type == 'duckdb':
            engine = create_engine(
                connection_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            session_factory = sessionmaker(
                engine,
                class_=Session,
                expire_on_commit=False,
            )
            session = session_factory()
            return (session, engine, True)  # is_sync=True
        else:
            # Async databases
            engine = create_async_engine(
                connection_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            session = async_session_factory()
            return (session, engine, False)  # is_sync=False
