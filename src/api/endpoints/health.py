"""Health check endpoints for Database Guru"""
import logging
from fastapi import APIRouter, Depends, status

from src.models.schemas import HealthCheckResponse
from src.api.dependencies import get_settings, get_db_manager, get_cache, get_sql_generator
from src.config.settings import Settings
from src.database.connection import DatabaseManager
from src.cache.redis_client import RedisCache
from src.llm.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
async def health_check(
    settings: Settings = Depends(get_settings),
    db_manager: DatabaseManager = Depends(get_db_manager),
    cache: RedisCache = Depends(get_cache),
    sql_generator: SQLGenerator = Depends(get_sql_generator),
):
    """
    Comprehensive health check for all services

    Returns:
        - Overall status
        - Individual service status (database, cache, LLM)
        - API version
    """
    services = {}

    # Check database
    try:
        if not db_manager.async_engine:
            await db_manager.initialize_async()
        db_healthy = await db_manager.health_check()
        services["database"] = db_healthy
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = False

    # Check cache
    try:
        if not cache.redis:
            await cache.connect()
        cache_healthy = await cache.health_check()
        services["cache"] = cache_healthy
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        services["cache"] = False

    # Check LLM
    try:
        if not sql_generator.ollama.client:
            await sql_generator.initialize()
        llm_healthy = await sql_generator.ollama.health_check()
        services["llm"] = llm_healthy
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        services["llm"] = False

    # Determine overall status
    all_healthy = all(services.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.VERSION,
        services=services,
    )


@router.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint"""
    return {
        "name": "Database Guru",
        "message": "Your AI Database Expert is ready! 🧙‍♂️",
        "docs": "/docs",
        "health": "/health",
    }
