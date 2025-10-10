"""Connect to user's database based on saved connections"""
import logging
from typing import Optional
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

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

        elif connection.database_type == 'mongodb':
            # MongoDB is not SQL, would need different handling
            raise NotImplementedError("MongoDB queries not yet supported")

        else:
            raise ValueError(f"Unsupported database type: {connection.database_type}")

    @staticmethod
    @asynccontextmanager
    async def get_user_db_session(connection: DatabaseConnection):
        """
        Get an async session to the user's database

        Args:
            connection: DatabaseConnection object with connection details

        Yields:
            AsyncSession connected to user's database
        """
        connection_url = UserDatabaseConnector.build_connection_url(connection)

        logger.info(f"Connecting to user database: {connection.name} ({connection.database_type})")

        # Create async engine
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
