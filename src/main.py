"""Database Guru - Main Application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import Settings
from src.database.connection import get_db_manager, run_alembic_migrations
from src.cache.redis_client import get_redis_cache
from src.core.connection_pool_manager import get_pool_manager_async
from src.middleware.rate_limit import RateLimitMiddleware
from src.api.endpoints import query, health, schema, models, connections, chat, multi_db_query, learned_corrections, result_verification, query_planning, feedback, settings, mappings, tools, cache, pools, lineage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Database Guru...")

    settings = Settings()

    # Initialize database
    logger.info("📊 Initializing database...")
    db_manager = get_db_manager(settings)

    # Run Alembic migrations first (uses sync connection)
    run_alembic_migrations()

    await db_manager.initialize_async()
    await db_manager.create_tables_async()
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

    logger.info("🧙‍♂️ Database Guru is ready!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Database Guru...")
    await cache.disconnect()
    await db_manager.close_async()

    # Close all connection pools
    if pool_manager:
        logger.info("Closing connection pools...")
        await pool_manager.close_all_pools()
        logger.info("✅ Connection pools closed")

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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════╗
    ║        🧙‍♂️ DATABASE GURU 🧙‍♂️         ║
    ║          Starting on port 8000        ║
    ╚══════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
