"""Database Guru - Main Application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import Settings
from src.database.connection import get_db_manager
from src.cache.redis_client import get_redis_cache
from src.middleware.rate_limit import RateLimitMiddleware
from src.api.endpoints import query, health, schema, models, connections, chat, multi_db_query

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
    await db_manager.initialize_async()
    await db_manager.create_tables_async()
    logger.info("✅ Database ready")

    # Initialize cache
    logger.info("💾 Initializing Redis cache...")
    cache = get_redis_cache(settings)
    await cache.connect()
    logger.info("✅ Cache ready")

    logger.info("🧙‍♂️ Database Guru is ready!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Database Guru...")
    await cache.disconnect()
    await db_manager.close_async()
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
    calls=100,  # 100 requests
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

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════╗
    ║        🧙‍♂️ DATABASE GURU 🧙‍♂️         ║
    ║          Starting on port 8000        ║
    ╚══════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
