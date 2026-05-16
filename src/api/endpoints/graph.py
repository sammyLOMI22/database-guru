"""Graph Mode API endpoints (Phase 25.2).

Phase 25.2 ships three endpoints:

* ``GET  /api/graph/connections/{id}/schema``        — cached or fresh schema.
* ``POST /api/graph/connections/{id}/introspect``    — force-refresh.
* ``POST /api/graph/connections/{id}/ai/schema-summary`` — 2-3 sentence blurb.

Later sub-phases extend this module with ``/query``, ``/explore``, AI
Cypher generation/explanation, and modeling-advice routes. Endpoint
ordering / prefix is fixed now so frontend clients won't need to retarget.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.auth.dependencies import get_optional_user
from src.auth.models import User
from src.config.settings import Settings
from src.database.models import DatabaseConnection
from src.graph.neo4j.driver_pool import Neo4jDriverPool
from src.graph.neo4j.schema_inspector import Neo4jSchemaInspector
from src.graph.router import is_graph
from src.graph.schema.normalizer import GraphSchema, graph_schema_from_dict
from src.models.schemas import (
    GraphIntrospectRequest,
    GraphSchemaResponse,
    GraphSchemaSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


# ── Helpers ───────────────────────────────────────────────────────────────


def _ensure_graph_mode(settings: Settings) -> None:
    if not settings.GRAPH_MODE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Graph Mode is disabled (GRAPH_MODE_ENABLED=False).",
        )


async def _load_graph_connection(
    connection_id: int,
    db: AsyncSession,
    current_user: Optional[User],
) -> DatabaseConnection:
    """Fetch a non-deleted Neo4j connection the user is allowed to see.

    Visibility rules match :func:`list_connections` — authenticated users
    see their own + unowned; anonymous users see only unowned. Soft-deleted
    rows are 404.
    """
    result = await db.execute(
        select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if conn is None or conn.is_deleted:
        raise HTTPException(status_code=404, detail="Connection not found")

    if not is_graph(conn.database_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Connection {connection_id} is a {conn.database_type!r} database, "
                "not a graph database — use the standard schema endpoints."
            ),
        )

    if current_user is None:
        if conn.owner_id is not None:
            raise HTTPException(status_code=404, detail="Connection not found")
    else:
        if conn.owner_id is not None and conn.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Connection not found")

    return conn


def _to_schema_response(
    conn: DatabaseConnection,
    schema: GraphSchema,
    *,
    cached: bool,
) -> GraphSchemaResponse:
    """Thin wrapper around ``GraphSchema.to_response_payload`` for the
    endpoint layer. Kept as a helper so the call sites read cleanly; the
    real shaping lives on the dataclass.
    """
    payload = schema.to_response_payload(
        connection_id=conn.id,
        schema_updated_at=(
            conn.schema_updated_at.isoformat() if conn.schema_updated_at else None
        ),
        cached=cached,
    )
    return GraphSchemaResponse(**payload)


async def _run_introspection(
    conn: DatabaseConnection,
    *,
    overall_timeout_ms: Optional[int],
    query_timeout_ms: Optional[int],
    settings: Settings,
) -> GraphSchema:
    """Acquire a pooled driver and introspect the graph.

    Persists nothing here — the caller is responsible for writing the
    result back to ``DatabaseConnection.schema_cache`` so cache-write logic
    lives in one place.
    """
    pool = await Neo4jDriverPool.get_instance()
    driver = await pool.get(
        connection_id=conn.id,
        uri=conn.host or "",
        username=conn.username or "",
        password=conn.password_encrypted or "",
        encrypted=bool(conn.encrypted),
    )

    overall = (overall_timeout_ms or settings.GRAPH_INTROSPECTION_TIMEOUT_MS) / 1000
    query_to = (query_timeout_ms or settings.GRAPH_QUERY_TIMEOUT_MS) / 1000

    inspector = Neo4jSchemaInspector(
        driver=driver,
        database_name=conn.database_name or "neo4j",
        query_timeout_s=query_to,
        overall_timeout_s=overall,
        count_cap=settings.GRAPH_INTROSPECTION_COUNT_CAP,
    )
    return await inspector.introspect()


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get(
    "/connections/{connection_id}/schema",
    response_model=GraphSchemaResponse,
)
async def get_graph_schema(
    connection_id: int,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphSchemaResponse:
    """Return the cached graph schema, or introspect when ``refresh=True``.

    Behavior:

    * ``schema_cache`` populated → returned with ``cached=True`` unless
      ``refresh=true`` query param forces a live introspection.
    * ``schema_cache`` empty → introspect, persist, return with
      ``cached=False``.
    * Introspection failure → 502 with the underlying error message.
    """
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    if conn.schema_cache and not refresh:
        try:
            schema = graph_schema_from_dict(conn.schema_cache)
            return _to_schema_response(conn, schema, cached=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Cached graph schema for connection %s was unreadable, "
                "falling back to fresh introspection: %s",
                connection_id,
                exc,
            )
            # Fall through to introspect.

    try:
        schema = await _run_introspection(
            conn,
            overall_timeout_ms=None,
            query_timeout_ms=None,
            settings=settings,
        )
    except Exception:  # noqa: BLE001
        # Don't echo the driver's exception string — Neo4j's
        # ServiceUnavailable / AuthError / ConfigurationError can embed
        # the connection URI (which may include user:pass) verbatim. The
        # full trace is captured server-side by logger.exception.
        logger.exception("Graph introspection failed for connection %s", connection_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Neo4j introspection failed. Check server logs for details.",
        )

    conn.schema_cache = schema.to_dict()
    conn.schema_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conn)

    return _to_schema_response(conn, schema, cached=False)


@router.post(
    "/connections/{connection_id}/introspect",
    response_model=GraphSchemaResponse,
)
async def introspect_graph(
    connection_id: int,
    payload: GraphIntrospectRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphSchemaResponse:
    """Force a fresh introspection and bust the cached schema."""
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    overall = payload.overall_timeout_ms if payload else None
    qtimeout = payload.query_timeout_ms if payload else None

    try:
        schema = await _run_introspection(
            conn,
            overall_timeout_ms=overall,
            query_timeout_ms=qtimeout,
            settings=settings,
        )
    except Exception:  # noqa: BLE001
        # See get_graph_schema above for why exc is not in the body.
        logger.exception("Graph introspection failed for connection %s", connection_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Neo4j introspection failed. Check server logs for details.",
        )

    conn.schema_cache = schema.to_dict()
    conn.schema_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conn)

    return _to_schema_response(conn, schema, cached=False)


@router.post(
    "/connections/{connection_id}/ai/schema-summary",
    response_model=GraphSchemaSummaryResponse,
)
async def graph_schema_summary(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphSchemaSummaryResponse:
    """Generate (or fetch) a 2-3 sentence LLM summary of the graph schema.

    Uses cached schema when available; if no cache exists yet, returns a
    409 with a hint to call ``/introspect`` first. We deliberately don't
    auto-introspect here so the LLM call is fast and predictable.
    """
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    if not conn.schema_cache:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No cached graph schema. Call POST /api/graph/connections/"
                f"{connection_id}/introspect first."
            ),
        )

    # Lazy import — keeps the LLM stack out of the import graph for tests
    # that only need schema endpoints.
    from src.graph.ai.schema_summarizer import (
        GraphSchemaSummary,
        get_graph_schema_summarizer,
    )
    from src.llm.prompts.graph_prompts import fallback_schema_summary

    # Defensive guard around the whole summarizer pipeline. The summarizer
    # is *supposed* to catch its own timeouts/errors and return a fallback
    # GraphSchemaSummary — but if get_graph_schema_summarizer() itself
    # raises (router lookup failure, missing provider config, etc.), or if
    # a future contributor inadvertently regresses the summarizer's
    # internal try/except, we still want the Overview card to render a
    # blurb rather than a 500. Failing closed here would force the
    # frontend to special-case the AI endpoint when none of the schema
    # endpoints fail in this way.
    try:
        summarizer = await get_graph_schema_summarizer(db)
        summary = await summarizer.summarize(conn.schema_cache, db=db)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Graph schema summarizer failed for connection %s; "
            "returning deterministic fallback.",
            connection_id,
        )
        summary = GraphSchemaSummary(
            summary=fallback_schema_summary(conn.schema_cache),
            model=None,
            provider=None,
            used_fallback=True,
        )

    return GraphSchemaSummaryResponse(
        connection_id=conn.id,
        summary=summary.summary,
        model=summary.model,
        provider=summary.provider,
        used_fallback=summary.used_fallback,
    )


__all__ = ["router"]
