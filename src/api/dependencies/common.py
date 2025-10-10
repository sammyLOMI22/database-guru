"""Common API dependencies"""
from functools import lru_cache
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.database.connection import get_db_manager as _get_db_manager, DatabaseManager
from src.cache.redis_client import get_redis_cache, RedisCache
from src.llm.sql_generator import SQLGenerator


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()


def get_db_manager(settings: Settings = Depends(get_settings)) -> DatabaseManager:
    """Get database manager instance"""
    return _get_db_manager(settings)


async def get_db(
    db_manager: DatabaseManager = Depends(get_db_manager)
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency"""
    if not db_manager.async_session_factory:
        await db_manager.initialize_async()

    async with db_manager.get_async_session() as session:
        yield session


def get_cache(settings: Settings = Depends(get_settings)) -> RedisCache:
    """Get Redis cache instance"""
    return get_redis_cache(settings)


def get_sql_generator(settings: Settings = Depends(get_settings)) -> SQLGenerator:
    """Get SQL generator instance"""
    return SQLGenerator(settings)
