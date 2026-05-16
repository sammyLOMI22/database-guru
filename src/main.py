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
from src.middleware.request_context import RequestContextMiddleware
from src.observability.logging_config import configure_logging
from src.observability import metrics as observability_metrics
from src.observability import tracing as observability_tracing
from src.api.endpoints import query, health, schema, models, connections, chat, multi_db_query, learned_corrections, result_verification, query_planning, feedback, mappings, tools, cache, pools, lineage, files, llm_usage, migration, performance, auth, audit, admin_users, dml, llm_providers, graph
from src.api.endpoints import settings as settings_endpoints
from src.core.file_source_session import FileSourceDuckDBSession
from src.core.file_source_handler import cleanup_expired_files

# Single module-level Settings instance — read once and shared across the
# logging, CORS, lifespan, and middleware setup blocks so we don't re-parse the
# environment 4-5 times during import. Lifespan still uses its own local copy
# in case env was reloaded between import and startup (e.g. in tests).
_settings = Settings()

# Configure structured logging (Phase 24.1). Re-applied after migrations below.
configure_logging(_settings)
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
    settings.check_auth_hardening()

    # Initialize Prometheus collectors (Phase 24.2). No-op if METRICS_ENABLED=False.
    observability_metrics.init_metrics(settings)

    # Initialize OpenTelemetry tracing (Phase 24.3). No-op if OTEL_ENABLED=False;
    # exporter/instrumentation failures degrade to warnings — never crash startup.
    observability_tracing.init_tracing(settings, fastapi_app=app)

    # Initialize database
    logger.info("📊 Initializing database...")
    db_manager = get_db_manager(settings)

    await db_manager.initialize_async()
    await db_manager.create_tables_async()

    # Run Alembic migrations (skip if entrypoint already handled them)
    # Runs AFTER create_tables_async() so baseline tables exist for index migrations.
    # On a fresh DB, tables are created by ORM and we stamp alembic to head.
    if os.environ.get("MIGRATIONS_HANDLED") != "1":
        try:
            run_alembic_migrations()
        except Exception as e:
            logger.warning(f"Alembic migrations skipped ({e}), stamping head")
            try:
                from alembic.config import Config as AlembicConfig
                from alembic import command as alembic_command
                alembic_cfg = AlembicConfig(
                    os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
                )
                alembic_command.stamp(alembic_cfg, "head")
                logger.info("Alembic stamped to head")
            except Exception as stamp_err:
                logger.warning(f"Failed to stamp alembic head: {stamp_err}")
    else:
        logger.info("Migrations already handled by entrypoint, skipping")

    # Re-apply logging config — alembic's fileConfig() disables all existing
    # loggers and resets the root logger to WARNING, suppressing all subsequent
    # INFO messages from the application.
    configure_logging(settings, force=True)

    # Seed default LLM model configs for cost tracking (Phase 16)
    try:
        from src.services.llm_cost_service import LLMCostService
        async with db_manager.get_async_session() as db:
            await LLMCostService.ensure_default_configs(db)
        logger.info("✅ LLM model configs seeded")
    except Exception as e:
        logger.warning(f"Failed to seed LLM model configs: {e}")

    # Initialize LLM provider registry (Phase 15)
    # Use rebuild_registry_from_db so that DB-persisted provider configs
    # (API keys, endpoints, enabled flags) take effect at startup — not just
    # env-based defaults.
    try:
        from src.llm.providers.registry import rebuild_registry_from_db
        async with db_manager.get_async_session() as db:
            provider_registry = await rebuild_registry_from_db(db, settings)
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

    # Flush any pending OTEL spans (Phase 24.3).
    observability_tracing.shutdown()

    logger.info("👋 Goodbye!")


def create_app(settings: Settings) -> FastAPI:
    """Build a FastAPI app from an explicit Settings instance.

    Factored out so tests can construct a self-contained app with a chosen
    `ADMIN_UI_ENABLED` (or other) flag without relying on `importlib.reload`
    + env-var patching, which races with Pydantic BaseSettings' env-read.
    """
    app = FastAPI(
        title="Database Guru",
        description="AI-powered database expert that converts natural language to SQL",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — X-Request-ID and traceparent are exposed so browser clients can
    # surface them in the LastRequestBadge / SystemHealthPanel for log + trace
    # correlation.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "traceparent"],
    )

    # Rate limiting (500/min, supports concurrent polling from the dashboard).
    app.add_middleware(RateLimitMiddleware, calls=500, period=60)

    # Request-scoped context (request_id, user_id) for structured logs.
    # Added last so it becomes the outermost wrapper and runs first.
    app.add_middleware(RequestContextMiddleware, settings=settings)

    # Routers
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
    app.include_router(settings_endpoints.router, prefix="/api")
    app.include_router(tools.router, prefix="/api")
    app.include_router(cache.router, prefix="/api")
    app.include_router(pools.router, prefix="/api")
    app.include_router(lineage.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(llm_usage.router, prefix="/api")
    app.include_router(migration.router, prefix="/api")
    app.include_router(performance.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    # /api/audit/logs/me is per-user and predates the admin UI; keep it mounted
    # regardless of ADMIN_UI_ENABLED so end users can always see their own
    # activity. The admin-only routes (logs list, facets) and user CRUD are
    # gated behind the kill-switch.
    app.include_router(audit.router, prefix="/api")
    if settings.ADMIN_UI_ENABLED:
        app.include_router(audit.admin_router, prefix="/api")
        app.include_router(admin_users.router, prefix="/api")
    app.include_router(dml.router, prefix="/api")
    app.include_router(llm_providers.router, prefix="/api")
    # Phase 25 — Graph Mode (Neo4j). Mounted unconditionally; per-endpoint
    # guards reject calls when GRAPH_MODE_ENABLED is False so the kill-switch
    # behaves the same as for create/test in connections.py.
    app.include_router(graph.router, prefix="/api")

    # /metrics endpoint, gated by METRICS_EXPOSE_ENDPOINT. Mounted at import
    # time (not in lifespan) so reverse-proxies can scrape it as soon as the
    # worker comes up. The handler returns 404 when METRICS_ENABLED is false,
    # so toggling either flag suffices to hide the endpoint.
    if settings.METRICS_EXPOSE_ENDPOINT:
        app.add_api_route(
            "/metrics",
            observability_metrics.metrics_endpoint,
            methods=["GET"],
            include_in_schema=False,
        )

    return app


# Module-level instance used by uvicorn / `python -m src.main`.
app = create_app(_settings)

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════╗
    ║        🧙‍♂️ DATABASE GURU 🧙‍♂️         ║
    ║          Starting on port 8000        ║
    ╚══════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
