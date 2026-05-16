"""Prometheus metrics (Phase 24.2).

Defines bounded-cardinality collectors and the helpers that the rest of the
codebase calls when an HTTP request, an LLM call, a SQL query, a pool checkout,
or a cache lookup completes. When ``METRICS_ENABLED=False`` every helper is a
cheap no-op so existing call sites pay nothing.

Label policy (kept tight on purpose — Prometheus cardinality is permanent):
- HTTP: method, route_template (never raw path), status (3-digit string)
- LLM:  provider, model, agent_type, success
- SQL:  dialect, success
- pool: dialect
- cache: cache_name (a short enum, not a key)
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from src.config.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public state
# ---------------------------------------------------------------------------

_ENABLED = False
_INITIALIZED = False
_REGISTRY: Any = None

# Histogram buckets tuned for the workloads we actually see. HTTP requests are
# usually <1s, SQL queries can be a few seconds, LLM calls minutes.
_HTTP_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_SQL_BUCKETS = (0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
_LLM_BUCKETS = (0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0)


class _Noop:
    """Stand-in for a Counter/Histogram/Gauge when metrics are disabled."""

    def labels(self, *_: Any, **__: Any) -> "_Noop":
        return self

    def inc(self, *_: Any, **__: Any) -> None:
        return None

    def dec(self, *_: Any, **__: Any) -> None:
        return None

    def observe(self, *_: Any, **__: Any) -> None:
        return None

    def set(self, *_: Any, **__: Any) -> None:
        return None


# Module-level handles that callers import. They start as no-ops so importing
# this module is safe even if init_metrics() is never called.
http_requests_total: Any = _Noop()
http_request_duration_seconds: Any = _Noop()

llm_calls_total: Any = _Noop()
llm_latency_seconds: Any = _Noop()
llm_tokens_total: Any = _Noop()
llm_cost_usd_total: Any = _Noop()

sql_query_duration_seconds: Any = _Noop()

connection_pool_checkouts_total: Any = _Noop()
connection_pool_size: Any = _Noop()
connection_pool_max_size: Any = _Noop()

cache_hits_total: Any = _Noop()
cache_misses_total: Any = _Noop()


def is_enabled() -> bool:
    return _ENABLED


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_metrics(settings: Optional[Settings] = None, *, force: bool = False) -> None:
    """Create the Prometheus collectors. Idempotent.

    Safe to call when METRICS_ENABLED is False — leaves the no-op handles in
    place. Pass force=True to rebuild collectors (used by tests).
    """
    global _ENABLED, _INITIALIZED, _REGISTRY
    global http_requests_total, http_request_duration_seconds
    global llm_calls_total, llm_latency_seconds, llm_tokens_total, llm_cost_usd_total
    global sql_query_duration_seconds
    global connection_pool_checkouts_total, connection_pool_size, connection_pool_max_size
    global cache_hits_total, cache_misses_total

    if _INITIALIZED and not force:
        return

    s = settings or Settings()
    if not bool(getattr(s, "METRICS_ENABLED", False)):
        _ENABLED = False
        _INITIALIZED = True
        return

    try:
        from prometheus_client import (  # type: ignore
            Counter,
            Gauge,
            Histogram,
            CollectorRegistry,
            REGISTRY,
        )
    except Exception as e:  # pragma: no cover - dep is in requirements
        logger.warning("prometheus-client unavailable, metrics disabled: %s", e)
        _ENABLED = False
        _INITIALIZED = True
        return

    # Default to the global registry so the standard /metrics handler picks it
    # up. Tests can pass a fresh CollectorRegistry by setting
    # ``settings.METRICS_REGISTRY`` (not exposed in pydantic — used via force).
    registry = getattr(s, "METRICS_REGISTRY", None) or REGISTRY
    _REGISTRY = registry

    if force:
        # Drop any previously-registered collectors with our names so we can
        # rebuild. prometheus-client does not allow duplicate names on the
        # same registry, so we walk the names_to_collectors map directly.
        for name in list(getattr(registry, "_names_to_collectors", {}).keys()):
            if name.startswith("dbguru_"):
                col = registry._names_to_collectors[name]
                try:
                    registry.unregister(col)
                except Exception:
                    pass

    http_requests_total = Counter(
        "dbguru_http_requests_total",
        "HTTP requests handled by Database Guru.",
        ("method", "route", "status"),
        registry=registry,
    )
    http_request_duration_seconds = Histogram(
        "dbguru_http_request_duration_seconds",
        "HTTP request latency in seconds.",
        ("method", "route"),
        buckets=_HTTP_BUCKETS,
        registry=registry,
    )

    llm_calls_total = Counter(
        "dbguru_llm_calls_total",
        "LLM calls by provider/model/agent.",
        ("provider", "model", "agent_type", "success"),
        registry=registry,
    )
    llm_latency_seconds = Histogram(
        "dbguru_llm_latency_seconds",
        "LLM call latency in seconds.",
        ("provider", "model", "agent_type"),
        buckets=_LLM_BUCKETS,
        registry=registry,
    )
    llm_tokens_total = Counter(
        "dbguru_llm_tokens_total",
        "LLM token counts (direction=input|output).",
        ("provider", "model", "direction"),
        registry=registry,
    )
    llm_cost_usd_total = Counter(
        "dbguru_llm_cost_usd_total",
        "Estimated LLM cost in USD.",
        ("provider", "model"),
        registry=registry,
    )

    sql_query_duration_seconds = Histogram(
        "dbguru_sql_query_duration_seconds",
        "Executed SQL query duration in seconds.",
        ("dialect", "success"),
        buckets=_SQL_BUCKETS,
        registry=registry,
    )

    connection_pool_checkouts_total = Counter(
        "dbguru_connection_pool_checkouts_total",
        "Cumulative pool checkouts.",
        ("dialect",),
        registry=registry,
    )
    connection_pool_size = Gauge(
        "dbguru_connection_pool_size",
        "Current pool size (active + idle).",
        ("dialect",),
        registry=registry,
    )
    connection_pool_max_size = Gauge(
        "dbguru_connection_pool_max_size",
        "Configured pool capacity (sum of total_capacity per dialect).",
        ("dialect",),
        registry=registry,
    )

    cache_hits_total = Counter(
        "dbguru_cache_hits_total",
        "Cache hits.",
        ("cache",),
        registry=registry,
    )
    cache_misses_total = Counter(
        "dbguru_cache_misses_total",
        "Cache misses.",
        ("cache",),
        registry=registry,
    )

    _ENABLED = True
    _INITIALIZED = True
    logger.info("Prometheus metrics initialized (registry=%s)", id(registry))


# ---------------------------------------------------------------------------
# Recording helpers — call sites import these instead of touching collectors
# directly so toggling the feature only requires checking _ENABLED here.
# ---------------------------------------------------------------------------

def record_http_request(method: str, route: str, status_code: int, duration_s: float) -> None:
    if not _ENABLED:
        return
    status = str(status_code)
    http_requests_total.labels(method=method, route=route, status=status).inc()
    http_request_duration_seconds.labels(method=method, route=route).observe(duration_s)


def record_llm_call(
    *,
    provider: str,
    model: str,
    agent_type: str,
    success: bool,
    duration_s: float,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
) -> None:
    if not _ENABLED:
        return
    success_label = "true" if success else "false"
    llm_calls_total.labels(
        provider=provider, model=model, agent_type=agent_type, success=success_label
    ).inc()
    llm_latency_seconds.labels(
        provider=provider, model=model, agent_type=agent_type
    ).observe(max(0.0, duration_s))
    if input_tokens is not None:
        llm_tokens_total.labels(provider=provider, model=model, direction="input").inc(max(0, int(input_tokens)))
    if output_tokens is not None:
        llm_tokens_total.labels(provider=provider, model=model, direction="output").inc(max(0, int(output_tokens)))
    if cost_usd is not None:
        llm_cost_usd_total.labels(provider=provider, model=model).inc(max(0.0, float(cost_usd)))


def record_sql_query(*, dialect: str, success: bool, duration_s: float) -> None:
    if not _ENABLED:
        return
    sql_query_duration_seconds.labels(
        dialect=dialect, success="true" if success else "false"
    ).observe(max(0.0, duration_s))


def record_pool_checkout(dialect: str) -> None:
    if not _ENABLED:
        return
    connection_pool_checkouts_total.labels(dialect=dialect).inc()


def set_pool_size(dialect: str, size: int) -> None:
    if not _ENABLED:
        return
    connection_pool_size.labels(dialect=dialect).set(size)


def set_pool_max_size(dialect: str, max_size: int) -> None:
    if not _ENABLED:
        return
    connection_pool_max_size.labels(dialect=dialect).set(max_size)


def record_cache_hit(cache: str) -> None:
    if not _ENABLED:
        return
    cache_hits_total.labels(cache=cache).inc()


def record_cache_miss(cache: str) -> None:
    if not _ENABLED:
        return
    cache_misses_total.labels(cache=cache).inc()


# ---------------------------------------------------------------------------
# Endpoint handler
# ---------------------------------------------------------------------------

async def _refresh_pool_gauges() -> None:
    """Pull the live pool sizes from ConnectionPoolManager into our gauges
    just before serving a /metrics scrape. Cheap and avoids needing every
    pool checkin/checkout to push.
    """
    if not _ENABLED:
        return
    try:
        from src.core.connection_pool_manager import _pool_manager_instance
        manager = _pool_manager_instance
        if manager is None:
            return
        snapshot = await manager.get_pool_metrics_snapshot()
        sizes: dict[str, int] = {}
        capacities: dict[str, int] = {}
        for entry in snapshot:
            d = entry["dialect"]
            sizes[d] = sizes.get(d, 0) + entry["active"] + entry["idle"]
            capacities[d] = capacities.get(d, 0) + entry["total_capacity"]
        for dialect, size in sizes.items():
            set_pool_size(dialect, size)
        for dialect, cap in capacities.items():
            set_pool_max_size(dialect, cap)
    except Exception as e:  # noqa: BLE001
        logger.debug("pool gauge refresh failed: %s", e)


async def metrics_endpoint() -> Any:
    """ASGI/FastAPI handler for GET /metrics.

    Returns a 404 when metrics are disabled so the surface area is identical
    to a server that never knew about Prometheus.
    """
    from fastapi import Response  # local import keeps fastapi optional in tests
    # Initialize lazily if the lifespan startup hook has not run yet (e.g.
    # tests using TestClient without a context-manager scope).
    if not _INITIALIZED:
        init_metrics()
    if not _ENABLED:
        return Response(status_code=404)
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST  # type: ignore
    except Exception:
        return Response(status_code=404)
    await _refresh_pool_gauges()
    body = generate_latest(_REGISTRY) if _REGISTRY is not None else generate_latest()
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)


def reset_for_test() -> None:
    """Test helper: drop all dbguru_* collectors and reset module state."""
    global _ENABLED, _INITIALIZED, _REGISTRY
    if _REGISTRY is not None:
        for name in list(getattr(_REGISTRY, "_names_to_collectors", {}).keys()):
            if name.startswith("dbguru_"):
                try:
                    _REGISTRY.unregister(_REGISTRY._names_to_collectors[name])
                except Exception:
                    pass
    _ENABLED = False
    _INITIALIZED = False
    _REGISTRY = None
    # Reset module-level handles back to no-ops.
    g = globals()
    for h in (
        "http_requests_total",
        "http_request_duration_seconds",
        "llm_calls_total",
        "llm_latency_seconds",
        "llm_tokens_total",
        "llm_cost_usd_total",
        "sql_query_duration_seconds",
        "connection_pool_checkouts_total",
        "connection_pool_size",
        "connection_pool_max_size",
        "cache_hits_total",
        "cache_misses_total",
    ):
        g[h] = _Noop()
