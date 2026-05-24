"""Graph Mode API endpoints (Phase 25.2 – 25.6).

Endpoints:

* ``GET  /api/graph/connections/{id}/schema``             — cached or fresh schema.
* ``POST /api/graph/connections/{id}/introspect``         — force-refresh.
* ``POST /api/graph/connections/{id}/ai/schema-summary``  — 2-3 sentence blurb.
* ``POST /api/graph/connections/{id}/query``              — run Cypher.
* ``GET  /api/graph/connections/{id}/history``            — paginated history.
* ``POST /api/graph/connections/{id}/ai/generate-cypher`` — NL → Cypher (25.4).
* ``POST /api/graph/connections/{id}/ai/explain-cypher``  — Cypher → English (25.4).
* ``POST /api/graph/connections/{id}/explore``            — bounded expand (25.5).
* ``POST /api/graph/connections/{id}/ai/modeling-advice`` — guru advice (25.6).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.auth.dependencies import get_optional_user
from src.auth.models import User
from src.config.settings import Settings
from src.database.models import DatabaseConnection, GraphQueryHistory
from src.graph.neo4j.driver_pool import Neo4jDriverPool
from src.graph.neo4j.query_executor import (
    ExecutionResult,
    execute_cypher,
    expand_from_node,
)
from src.graph.neo4j.schema_inspector import Neo4jSchemaInspector
from src.graph.router import is_graph
from src.graph.safety.classifier import GraphQuerySafetyLevel
from src.graph.schema.normalizer import GraphSchema, graph_schema_from_dict
from src.models.schemas import (
    CypherExplainRequest,
    CypherExplainResponse,
    CypherGenerateRequest,
    CypherGenerateResponse,
    GraphAdvisorFinding,
    GraphExploreRequest,
    GraphExploreResponse,
    GraphHistoryItem,
    GraphHistoryResponse,
    GraphIntrospectRequest,
    GraphModelingAdviceResponse,
    GraphQueryBlocked,
    GraphQueryError,
    GraphQueryRequest,
    GraphQueryResult,
    GraphSchemaResponse,
    GraphSchemaSummaryResponse,
    GraphTablePayload,
    GraphVizPayload,
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


# ── Phase 25.3 — Cypher Query Lab ────────────────────────────────────────


async def _record_query_history(
    db: AsyncSession,
    *,
    conn: DatabaseConnection,
    owner_id: Optional[int],
    request: GraphQueryRequest,
    execution: ExecutionResult,
) -> Optional[int]:
    """Persist one ``graph_query_history`` row. Returns the row id.

    Non-fatal — if the write fails we log and continue so a transient
    metadata-DB hiccup never blocks the user's query response.
    """
    safety_level = (
        execution.safety_level.value
        if execution.safety_level
        else GraphQuerySafetyLevel.UNKNOWN.value
    )
    record = GraphQueryHistory(
        connection_id=conn.id,
        owner_id=owner_id,
        source=request.source or "manual",
        cypher=request.cypher,
        prompt=request.prompt,
        safety_level=safety_level,
        blocked_reason=execution.blocked_reason,
        success=execution.success,
        execution_time_ms=execution.execution_time_ms,
        record_count=execution.record_count if execution.success else None,
        truncated=bool(execution.formatted and execution.formatted.truncated),
        error_category=execution.error.category.value if execution.error else None,
        error_message=execution.error.user_message if execution.error else None,
    )
    try:
        async with db.begin_nested():
            db.add(record)
        await db.commit()
        await db.refresh(record)
        return record.id
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to persist graph_query_history row for connection %s: %s",
            conn.id,
            exc,
        )
        return None


@router.post(
    "/connections/{connection_id}/query",
    response_model=GraphQueryResult,
    responses={
        400: {"model": GraphQueryBlocked, "description": "Query blocked by safety classifier"},
        502: {"model": GraphQueryError, "description": "Driver-level execution error"},
    },
)
async def run_graph_query(
    connection_id: int,
    request: GraphQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphQueryResult:
    """Run a Cypher statement against the connection's Neo4j database.

    Three response codes:

    * ``200`` — query passed safety classification and executed cleanly.
    * ``400`` — classifier rejected the query (WRITE/DANGEROUS/ADMIN/UNKNOWN).
                Body is :class:`GraphQueryBlocked` so the Lab can render
                the reason inline.
    * ``502`` — query ran but the driver returned an error (auth, syntax,
                timeout, unknown label, etc.). Body is :class:`GraphQueryError`
                with a category the UI can surface.
    """
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    pool = await Neo4jDriverPool.get_instance()
    driver = await pool.get(
        connection_id=conn.id,
        uri=conn.host or "",
        username=conn.username or "",
        password=conn.password_encrypted or "",
        encrypted=bool(conn.encrypted),
    )

    query_timeout_s = (
        (request.query_timeout_ms or settings.GRAPH_QUERY_TIMEOUT_MS) / 1000
    )
    max_records = request.max_records or settings.GRAPH_MAX_RECORDS

    execution = await execute_cypher(
        driver,
        request.cypher,
        database_name=conn.database_name or "neo4j",
        query_timeout_s=query_timeout_s,
        max_records=max_records,
        max_viz_nodes=settings.GRAPH_MAX_VIZ_NODES,
        max_viz_edges=settings.GRAPH_MAX_VIZ_EDGES,
        allow_apoc=settings.GRAPH_ALLOW_APOC,
        allow_writes=settings.GRAPH_ALLOW_WRITES,
        parameters=request.parameters,
    )

    owner_id = current_user.id if current_user else None
    await _record_query_history(
        db, conn=conn, owner_id=owner_id, request=request, execution=execution
    )

    # ── Blocked: 400 with structured reason ──
    if execution.blocked_reason is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=GraphQueryBlocked(
                connection_id=conn.id,
                safety_level=execution.safety_level.value,
                blocked_reason=execution.blocked_reason,
                reasons=list(execution.safety.reasons),
                procedures=list(execution.safety.procedures),
            ).model_dump(),
        )

    # ── Driver error: 502 with category ──
    if not execution.success:
        err = execution.error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=GraphQueryError(
                connection_id=conn.id,
                safety_level=execution.safety_level.value,
                success=False,
                error_category=(err.category.value if err else "unknown"),
                error_message=(err.user_message if err else "Neo4j rejected the query."),
                error_hint=(err.hint if err else None),
                error_code=(err.code if err else None),
                execution_time_ms=execution.execution_time_ms,
            ).model_dump(),
        )

    # ── Success ──
    formatted = execution.formatted
    if formatted is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query succeeded but produced no formatted result.",
        )
    return GraphQueryResult(
        connection_id=conn.id,
        cypher=execution.cypher,
        safety_level=execution.safety_level.value,
        success=True,
        record_count=execution.record_count,
        execution_time_ms=execution.execution_time_ms,
        truncated=formatted.truncated,
        table=GraphTablePayload(
            columns=list(formatted.table_columns),
            rows=list(formatted.table_rows),
        ),
        graph_viz=GraphVizPayload(
            nodes=[n.to_dict() for n in formatted.nodes],
            edges=[e.to_dict() for e in formatted.edges],
            has_graph=formatted.has_graph,
        ),
        warnings=list(formatted.warnings),
        server_warnings=list(execution.server_warnings),
    )


@router.get(
    "/connections/{connection_id}/history",
    response_model=GraphHistoryResponse,
)
async def get_graph_query_history(
    connection_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphHistoryResponse:
    """Paginated history of Cypher executions for this connection.

    Visibility rules match the schema endpoints: authenticated users see
    their own rows; anonymous callers see only rows with ``owner_id IS NULL``.
    """
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    base = select(GraphQueryHistory).where(
        GraphQueryHistory.connection_id == conn.id
    )
    if current_user is None:
        base = base.where(GraphQueryHistory.owner_id.is_(None))
    else:
        base = base.where(
            (GraphQueryHistory.owner_id.is_(None))
            | (GraphQueryHistory.owner_id == current_user.id)
        )

    total = (
        await db.execute(
            select(func.count()).select_from(base.subquery())
        )
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(GraphQueryHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    items = [
        GraphHistoryItem(
            id=row.id,
            connection_id=row.connection_id,
            source=row.source,
            cypher=row.cypher,
            prompt=row.prompt,
            safety_level=row.safety_level,
            success=row.success,
            execution_time_ms=row.execution_time_ms,
            record_count=row.record_count,
            truncated=row.truncated,
            blocked_reason=row.blocked_reason,
            error_category=row.error_category,
            error_message=row.error_message,
            created_at=(
                row.created_at.isoformat() if row.created_at else ""
            ),
        )
        for row in rows
    ]

    return GraphHistoryResponse(
        connection_id=conn.id,
        items=items,
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


# ── Phase 25.4 — AI Cypher Generation + Explanation ────────────────────


@router.post(
    "/connections/{connection_id}/ai/generate-cypher",
    response_model=CypherGenerateResponse,
)
async def generate_cypher(
    connection_id: int,
    request: CypherGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> CypherGenerateResponse:
    """Convert a natural-language question into a Cypher READ query.

    Uses the cached graph schema as context. Returns 409 if no schema has
    been introspected yet (same guard as the schema-summary endpoint).
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

    from src.graph.neo4j.cypher_generator import get_cypher_generator

    try:
        generator = await get_cypher_generator(db)
        result = await generator.generate(
            question=request.question,
            schema=conn.schema_cache,
            db=db,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Cypher generation failed for connection %s", connection_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cypher generation failed. Check server logs for details.",
        )

    return CypherGenerateResponse(
        connection_id=conn.id,
        cypher=result.cypher,
        question=result.question,
        model=result.model,
        provider=result.provider,
        unknown_labels=result.unknown_labels,
        used_fallback=result.used_fallback,
        error=result.error,
    )


@router.post(
    "/connections/{connection_id}/ai/explain-cypher",
    response_model=CypherExplainResponse,
)
async def explain_cypher(
    connection_id: int,
    request: CypherExplainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> CypherExplainResponse:
    """Explain a Cypher query in plain English.

    Optionally includes cached graph schema context (``include_schema=true``,
    the default) so the explanation references domain labels and types.
    """
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    schema_ctx = conn.schema_cache if request.include_schema else None

    from src.graph.neo4j.cypher_explainer import get_cypher_explainer

    try:
        explainer = await get_cypher_explainer(db)
        result = await explainer.explain(
            cypher=request.cypher,
            schema=schema_ctx,
            db=db,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Cypher explanation failed for connection %s", connection_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cypher explanation failed. Check server logs for details.",
        )

    return CypherExplainResponse(
        connection_id=conn.id,
        explanation=result.explanation,
        cypher=result.cypher,
        model=result.model,
        provider=result.provider,
        used_fallback=result.used_fallback,
    )


# ── Phase 25.5 — Visual Graph Explorer ───────────────────────────────────


@router.post(
    "/connections/{connection_id}/explore",
    response_model=GraphExploreResponse,
    responses={
        400: {
            "model": GraphQueryBlocked,
            "description": "Invalid expand parameters or query blocked by safety classifier",
        },
        502: {"model": GraphQueryError, "description": "Driver-level execution error"},
    },
)
async def explore_graph(
    connection_id: int,
    request: GraphExploreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphExploreResponse:
    """Expand from a starting node 1–3 hops with depth/type/cap filters.

    Same shape as :func:`run_graph_query` but with a smaller request
    surface — the caller never writes Cypher, so we generate it from
    structured fields and run it through the same safety + executor path.

    Error codes mirror ``/query``:

    * ``200`` — expansion succeeded; ``graph_viz`` is the Cytoscape payload.
    * ``400`` — invalid label / property / rel-type / direction. Body uses
                :class:`GraphQueryBlocked` so the same UI banner renders.
    * ``502`` — driver returned an error (auth, syntax, timeout, etc.).
    """
    _ensure_graph_mode(settings)
    conn = await _load_graph_connection(connection_id, db, current_user)

    pool = await Neo4jDriverPool.get_instance()
    driver = await pool.get(
        connection_id=conn.id,
        uri=conn.host or "",
        username=conn.username or "",
        password=conn.password_encrypted or "",
        encrypted=bool(conn.encrypted),
    )

    query_timeout_s = (
        (request.query_timeout_ms or settings.GRAPH_QUERY_TIMEOUT_MS) / 1000
    )
    node_cap = request.node_cap or settings.GRAPH_MAX_VIZ_NODES

    try:
        execution = await expand_from_node(
            driver,
            start_label=request.start_label,
            start_property=request.start_property,
            start_value=request.start_value,
            depth=request.depth,
            rel_types=request.rel_types,
            direction=request.direction,
            node_cap=node_cap,
            database_name=conn.database_name or "neo4j",
            query_timeout_s=query_timeout_s,
            max_viz_nodes=settings.GRAPH_MAX_VIZ_NODES,
            max_viz_edges=settings.GRAPH_MAX_VIZ_EDGES,
            allow_apoc=settings.GRAPH_ALLOW_APOC,
        )
    except ValueError as exc:
        # Invalid label / rel-type / direction — the executor rejected
        # the call before opening a session. 400 with the same
        # GraphQueryBlocked shape so the UI can reuse its banner.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=GraphQueryBlocked(
                connection_id=conn.id,
                safety_level=GraphQuerySafetyLevel.UNKNOWN.value,
                blocked_reason=str(exc),
                reasons=[str(exc)],
                procedures=[],
            ).model_dump(),
        )

    # ── Blocked (defense in depth — expand always generates READ_ONLY,
    # but a future change could regress this) ──
    if execution.blocked_reason is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=GraphQueryBlocked(
                connection_id=conn.id,
                safety_level=execution.safety_level.value,
                blocked_reason=execution.blocked_reason,
                reasons=list(execution.safety.reasons),
                procedures=list(execution.safety.procedures),
            ).model_dump(),
        )

    if not execution.success:
        err = execution.error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=GraphQueryError(
                connection_id=conn.id,
                safety_level=execution.safety_level.value,
                success=False,
                error_category=(err.category.value if err else "unknown"),
                error_message=(err.user_message if err else "Neo4j rejected the query."),
                error_hint=(err.hint if err else None),
                error_code=(err.code if err else None),
                execution_time_ms=execution.execution_time_ms,
            ).model_dump(),
        )

    formatted = execution.formatted
    if formatted is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Expand succeeded but produced no formatted result.",
        )
    return GraphExploreResponse(
        connection_id=conn.id,
        start_label=request.start_label,
        depth=request.depth,
        direction=request.direction,
        rel_types=list(request.rel_types or []),
        safety_level=execution.safety_level.value,
        success=True,
        record_count=execution.record_count,
        execution_time_ms=execution.execution_time_ms,
        truncated=formatted.truncated,
        table=GraphTablePayload(
            columns=list(formatted.table_columns),
            rows=list(formatted.table_rows),
        ),
        graph_viz=GraphVizPayload(
            nodes=[n.to_dict() for n in formatted.nodes],
            edges=[e.to_dict() for e in formatted.edges],
            has_graph=formatted.has_graph,
        ),
        warnings=list(formatted.warnings),
        server_warnings=list(execution.server_warnings),
    )


# ── Phase 25.6 — Guru Advice ────────────────────────────────────────────


@router.post(
    "/connections/{connection_id}/ai/modeling-advice",
    response_model=GraphModelingAdviceResponse,
)
async def modeling_advice(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> GraphModelingAdviceResponse:
    """Run rule-based checks + optional LLM summary on the cached graph schema.

    Returns 409 if no schema has been introspected yet (same guard as the
    schema-summary and generate-cypher endpoints).
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

    from src.graph.ai.modeling_advisor import get_modeling_advisor

    try:
        advisor = await get_modeling_advisor(db)
        result = await advisor.advise(conn.schema_cache, db=db)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Graph modeling advice failed for connection %s; "
            "falling back to rule-only findings.",
            connection_id,
        )
        from src.graph.schema.advisor_rules import run_all_rules

        schema = graph_schema_from_dict(conn.schema_cache)
        findings = run_all_rules(schema)
        return GraphModelingAdviceResponse(
            connection_id=conn.id,
            findings=[GraphAdvisorFinding(**f.to_dict()) for f in findings],
            finding_count=len(findings),
            ai_summary=None,
            model=None,
            provider=None,
            used_fallback=True,
        )

    return GraphModelingAdviceResponse(
        connection_id=conn.id,
        findings=[GraphAdvisorFinding(**f.to_dict()) for f in result.findings],
        finding_count=len(result.findings),
        ai_summary=result.ai_summary,
        model=result.model,
        provider=result.provider,
        used_fallback=result.used_fallback,
    )


__all__ = ["router"]
