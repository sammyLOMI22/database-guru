"""Database connection management"""
from typing import AsyncGenerator
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import asynccontextmanager, contextmanager
import logging

from src.config.settings import Settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None

    def initialize(self):
        """Initialize synchronous database engine and session factory"""
        database_url = self.settings.DATABASE_URL

        # Convert postgres:// to postgresql:// for SQLAlchemy 2.0
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            pool_size=self.settings.DB_POOL_SIZE,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=self.settings.DEBUG,  # Log SQL in debug mode
        )

        # Create session factory
        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        logger.info(f"Database engine initialized: {database_url}")

    async def initialize_async(self):
        """Initialize async database engine and session factory"""
        database_url = self.settings.DATABASE_URL

        # Convert to async driver
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("sqlite://"):
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

        # Create async engine
        self.async_engine = create_async_engine(
            database_url,
            pool_size=self.settings.DB_POOL_SIZE,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=self.settings.DEBUG,
        )

        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        logger.info(f"Async database engine initialized: {database_url}")

    @contextmanager
    def get_session(self):
        """Get a synchronous database session (context manager)"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session (context manager)"""
        if not self.async_session_factory:
            raise RuntimeError("Async database not initialized. Call initialize_async() first.")

        session: AsyncSession = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            if self.async_engine:
                async with self.async_engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return True
            elif self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True
            return False
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def create_tables(self):
        """Create all tables defined in Base models"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    async def create_tables_async(self):
        """Create all tables defined in Base models (async)"""
        if not self.async_engine:
            raise RuntimeError("Async database not initialized")
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (async)")

    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine disposed")
        if self.async_engine:
            # async_engine.dispose() should be awaited, handle in async context
            logger.info("Async database engine should be disposed in async context")

    async def close_async(self):
        """Close async database connections"""
        if self.async_engine:
            await self.async_engine.dispose()
            logger.info("Async database engine disposed")


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager(settings: Settings | None = None) -> DatabaseManager:
    """Get or create the global database manager instance"""
    global _db_manager

    if _db_manager is None:
        if settings is None:
            settings = Settings()
        _db_manager = DatabaseManager(settings)

    return _db_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting async database sessions"""
    db_manager = get_db_manager()

    if not db_manager.async_session_factory:
        await db_manager.initialize_async()

    async with db_manager.get_async_session() as session:
        yield session
