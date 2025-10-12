"""Database initialization script"""
import asyncio
import logging
from src.config.settings import Settings
from src.database.connection import get_db_manager
from src.database.models import (
    QueryHistory,
    DatabaseConnection,
    QueryCache,
    UserFeedback,
    ChatSession,
    ChatMessage,
    LearnedCorrection,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database tables"""
    settings = Settings()
    db_manager = get_db_manager(settings)

    logger.info("Initializing database...")

    # Initialize async engine
    await db_manager.initialize_async()

    # Create tables
    await db_manager.create_tables_async()

    # Health check
    is_healthy = await db_manager.health_check()
    if is_healthy:
        logger.info("✅ Database initialized successfully!")
    else:
        logger.error("❌ Database health check failed")

    # Clean up
    await db_manager.close_async()


def init_database_sync():
    """Initialize database tables (synchronous version)"""
    settings = Settings()
    db_manager = get_db_manager(settings)

    logger.info("Initializing database (sync)...")

    # Initialize engine
    db_manager.initialize()

    # Create tables
    db_manager.create_tables()

    logger.info("✅ Database initialized successfully!")

    # Clean up
    db_manager.close()


if __name__ == "__main__":
    # Run async initialization
    asyncio.run(init_database())
