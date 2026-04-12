"""Database Guru - Main Application"""
import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import Settings
from src.database.connection import get_db_manager, run_alembic_migrations
from src.cache.redis_client import get_redis_cache
from src.core.connection_pool_manager import get_pool_manager_async
from src.middleware.rate_limit import RateLimitMiddleware
from src.api.endpoints import query, health, schema, models, connections, chat, multi_db_query, learned_corrections, result_verification, query_planning, feedback, settings, mappings, tools, cache, pools, lineage, files, llm_usage, migration, performance, auth, audit, dml, llm_providers
from src.core.file_source_session import FileSourceDuckDBSession
from src.core.file_source_handler import cleanup_expired_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


FILE_CLEANUP_INTERVAL_SECONDS = 3600  # Run every hour


async def _file_expiration_task(db_manager):
    """Background task that periodically cleans up expired file sources."""
    while True:
        try:
            await asyncio.sleep(FILE_CLEANUP_INTERVAL_SECONDS)
            async with db_manager.get_async_session() as db:
                cleaned = await cleanup_expired_files(db)
                if cleaned:
                    logger.info(f"File expiration task: cleaned {cleaned} expired files")
        except asyncio.CancelledError:
            logger.info("File expiration task cancelled")
            break
        except Exception as e:
            logger.error(f"File expiration task error: {e}")
            # Back off before retrying to avoid tight-loop on persistent errors
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Database Guru...")

    settings = Settings()
    settings.check_jwt_secret()

    # Initialize database
    logger.info("📊 Initializing database...")
    db_manager = get_db_manager(settings)

    # Run Alembic migrations (skip if entrypoint already handled them)
    if os.environ.get("MIGRATIONS_HANDLED") != "1":
        try:
            run_alembic_migrations()
        except Exception as e:
            logger.error(f"Alembic migrations failed: {e}")
            raise
    else:
        logger.info("Migrations already handled by entrypoint, skipping")

    await db_manager.initialize_async()
    await db_manager.create_tables_async()

    # Seed default LLM model configs for cost tracking (Phase 16)
    try:
        from src.services.llm_cost_service import LLMCostService
        async with db_manager.get_async_session() as db:
            await LLMCostService.ensure_default_configs(db)
        logger.info("✅ LLM model configs seeded")
    except Exception as e:
        logger.warning(f"Failed to seed LLM model configs: {e}")

    # Initialize LLM provider registry (Phase 15)
    try:
        from src.llm.providers.registry import initialize_registry_from_settings
        provider_registry = initialize_registry_from_settings()
        logger.info(
            f"✅ LLM provider registry ready: {provider_registry.list_available()} "
            f"(security_level={provider_registry.security_level})"
        )
    except Exception as e:
        logger.warning(f"Failed to initialize LLM provider registry: {e}")

    logger.info("✅ Database ready")

    # Initialize cache
    logger.info("💾 Initializing Redis cache...")
    cache = get_redis_cache(settings)
    await cache.connect()
    logger.info("✅ Cache ready")

    # Initialize connection pool manager
    if settings.ENABLE_CONNECTION_POOLING:
        logger.info("🏊 Initializing connection pool manager...")
        pool_manager = await get_pool_manager_async(settings)
        logger.info("✅ Connection pooling enabled")

        # Optional: Pre-warm pools for active connections
        # This can be enabled later if needed for production optimization
        # from sqlalchemy import select
        # from src.database.models import DatabaseConnection
        # async with db_manager.get_async_session() as db:
        #     result = await db.execute(
        #         select(DatabaseConnection).where(DatabaseConnection.is_active == True)
        #     )
        #     active_connections = result.scalars().all()
        #     for conn in active_connections:
        #         try:
        #             await pool_manager.warm_pool(conn)
        #             logger.info(f"Pre-warmed pool for {conn.name}")
        #         except Exception as e:
        #             logger.warning(f"Failed to pre-warm pool for {conn.name}: {e}")
    else:
        logger.warning("⚠️  Connection pooling is DISABLED")
        pool_manager = None

    # Start background file expiration cleanup task
    file_cleanup_task = asyncio.create_task(_file_expiration_task(db_manager))
    logger.info("🗑️  File expiration cleanup task started (runs every hour)")

    logger.info("🧙‍♂️ Database Guru is ready!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Database Guru...")

    # Cancel background tasks
    file_cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await file_cleanup_task

    # Close DuckDB file source session
    await FileSourceDuckDBSession.reset_session()
    logger.info("✅ DuckDB file source session closed")

    await cache.disconnect()
    await db_manager.close_async()

    # Close all connection pools
    if pool_manager:
        logger.info("Closing connection pools...")
        await pool_manager.close_all_pools()
        logger.info("✅ Connection pools closed")

    # Close NoSQL client pools
    logger.info("Closing NoSQL client pools...")
    from src.nosql.mongodb.client_pool import MongoClientPool
    from src.nosql.redis.client_pool import RedisClientPool
    from src.nosql.cassandra.client_pool import CassandraClientPool
    from src.nosql.dynamodb.client_pool import DynamoDBClientPool
    from src.nosql.elasticsearch.client_pool import ElasticsearchClientPool

    for pool_cls in [MongoClientPool, RedisClientPool, CassandraClientPool, DynamoDBClientPool, ElasticsearchClientPool]:
        if pool_cls._instance is not None:
            await pool_cls._instance.close_all()
    logger.info("✅ NoSQL client pools closed")

    logger.info("👋 Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="Database Guru",
    description="AI-powered database expert that converts natural language to SQL",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in Settings().CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    calls=500,  # Increased to 500 to support concurrent polling from multiple components
    period=60,  # per 60 seconds
)

# Include routers
app.include_router(health.router)
app.include_router(query.router, prefix="/api")
app.include_router(schema.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(connections.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(multi_db_query.router, prefix="/api")
app.include_router(learned_corrections.router)
app.include_router(result_verification.router, prefix="/api")
app.include_router(query_planning.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(mappings.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(cache.router, prefix="/api")
app.include_router(pools.router, prefix="/api")
app.include_router(lineage.router, prefix="/api")
app.include_router(files.router, prefix="/api")  # Phase 13: CSV & Excel file support
app.include_router(llm_usage.router, prefix="/api")  # Phase 16: LLM usage monitoring
app.include_router(migration.router, prefix="/api")  # Phase 20: Migration Toolkit
app.include_router(performance.router, prefix="/api")  # Phase 22: Performance Guru
app.include_router(auth.router, prefix="/api")  # Phase 21: Security & Auth
app.include_router(audit.router, prefix="/api")  # Phase 21: Audit logging
app.include_router(dml.router, prefix="/api")  # Phase 18: Edit Mode & DML
app.include_router(llm_providers.router, prefix="/api")  # Phase 15: LLM Provider Management

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════╗
    ║        🧙‍♂️ DATABASE GURU 🧙‍♂️         ║
    ║          Starting on port 8000        ║
    ╚══════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
