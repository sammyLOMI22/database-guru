"""OpenTelemetry tracing setup (Phase 24.3).

Initializes a TracerProvider with an OTLP HTTP exporter and applies
auto-instrumentation for FastAPI, SQLAlchemy, HTTPX and Redis. Manual spans
are added in two high-value paths only (TrackedLLMClient.generate/chat and
SelfCorrectingAgent.generate_and_execute_with_retry) — see span helpers below.

Design rules enforced here:
- Disabled by default. ``OTEL_ENABLED=False`` makes ``llm_call_span()`` and
  ``self_correcting_span()`` return a no-op context manager so call sites pay
  zero overhead.
- All initialization is wrapped in ``try/except`` and logs a warning on
  failure — the backend must keep serving traffic if the OTLP endpoint is
  down or any instrumentation package is missing.
- Init is idempotent. Calling it twice in the same process (reload, multi
  worker, etc.) does not register duplicate instrumentations.
- No prompt bodies, SQL statements, or row data ever land on a span.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from src.config.settings import Settings

logger = logging.getLogger(__name__)


_INITIALIZED = False
_ENABLED = False
_TRACER: Any = None  # opentelemetry.trace.Tracer


def is_enabled() -> bool:
    return _ENABLED


def init_tracing(
    settings: Optional[Settings] = None,
    *,
    fastapi_app: Any = None,
    force: bool = False,
) -> None:
    """Configure OpenTelemetry. Safe no-op when ``OTEL_ENABLED`` is false.

    Args:
        settings: pydantic settings. Defaults to ``Settings()``.
        fastapi_app: optional FastAPI app to instrument. Pass the live app to
            attach FastAPIInstrumentor.
        force: rebuild even if already initialized (for tests).
    """
    global _INITIALIZED, _ENABLED, _TRACER
    if _INITIALIZED and not force:
        return

    s = settings or Settings()
    if not bool(getattr(s, "OTEL_ENABLED", False)):
        _ENABLED = False
        _INITIALIZED = True
        logger.debug("OTEL disabled — skipping tracer setup.")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import (
            ParentBased,
            TraceIdRatioBased,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("OpenTelemetry SDK unavailable, tracing disabled: %s", e)
        _ENABLED = False
        _INITIALIZED = True
        return

    try:
        ratio = float(getattr(s, "OTEL_TRACES_SAMPLER_RATIO", 0.1))
        ratio = max(0.0, min(1.0, ratio))
        sampler = ParentBased(root=TraceIdRatioBased(ratio))

        resource = Resource.create(
            {
                "service.name": getattr(s, "OTEL_SERVICE_NAME", "database-guru"),
                "service.version": getattr(s, "VERSION", "unknown"),
                "deployment.environment": getattr(s, "ENVIRONMENT", "development"),
            }
        )
        provider = TracerProvider(resource=resource, sampler=sampler)

        endpoint = getattr(s, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318")
        # OTLP HTTP requires the /v1/traces suffix.
        traces_endpoint = endpoint.rstrip("/")
        if not traces_endpoint.endswith("/v1/traces"):
            traces_endpoint = traces_endpoint + "/v1/traces"
        try:
            exporter = OTLPSpanExporter(endpoint=traces_endpoint, timeout=5)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as exporter_err:  # noqa: BLE001
            logger.warning(
                "OTLP exporter init failed (%s) — spans will not be exported "
                "but tracing API remains live.",
                exporter_err,
            )

        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("database-guru")

        _install_auto_instrumentation(fastapi_app)

        _ENABLED = True
        _INITIALIZED = True
        logger.info(
            "OpenTelemetry tracing enabled (endpoint=%s, sample_ratio=%s)",
            traces_endpoint,
            ratio,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("OpenTelemetry init failed, tracing disabled: %s", e)
        _ENABLED = False
        _INITIALIZED = True


def _install_auto_instrumentation(fastapi_app: Any) -> None:
    """Apply available instrumentations once. Each step is independently
    fault-tolerant so a missing package never blocks the rest.
    """
    if fastapi_app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(fastapi_app)
        except Exception as e:  # noqa: BLE001
            logger.warning("FastAPI instrumentation failed: %s", e)

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
    except Exception as e:  # noqa: BLE001
        logger.warning("SQLAlchemy instrumentation failed: %s", e)

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except Exception as e:  # noqa: BLE001
        logger.warning("HTTPX instrumentation failed: %s", e)

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis instrumentation failed: %s", e)


# ---------------------------------------------------------------------------
# Span helpers — kept tiny so call sites stay readable.
# ---------------------------------------------------------------------------

class _NullSpan:
    """No-op span used when tracing is disabled."""

    def __enter__(self) -> "_NullSpan":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def set_attribute(self, *_: Any, **__: Any) -> None:
        return None

    def set_attributes(self, *_: Any, **__: Any) -> None:
        return None

    def record_exception(self, *_: Any, **__: Any) -> None:
        return None

    def set_status(self, *_: Any, **__: Any) -> None:
        return None


def _start_span(name: str) -> Any:
    if not _ENABLED or _TRACER is None:
        return _NullSpan()
    return _TRACER.start_as_current_span(name)


@contextmanager
def llm_call_span(
    *,
    provider: str,
    model: str,
    agent_type: str,
) -> Iterator[Any]:
    """Span for one LLM call. Attributes filled in by the caller via
    ``span.set_attribute(...)`` after the call completes.
    """
    span_cm = _start_span("llm.call")
    span = span_cm.__enter__() if hasattr(span_cm, "__enter__") else span_cm
    try:
        try:
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.agent_type", agent_type)
        except Exception:  # noqa: BLE001
            pass
        yield span
    finally:
        try:
            span_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass


@contextmanager
def self_correcting_span(*, agent_type: str = "self_correcting") -> Iterator[Any]:
    """Span for a SelfCorrectingAgent.generate_and_execute_with_retry run."""
    span_cm = _start_span("agent.self_correcting")
    span = span_cm.__enter__() if hasattr(span_cm, "__enter__") else span_cm
    try:
        try:
            span.set_attribute("agent.type", agent_type)
        except Exception:  # noqa: BLE001
            pass
        yield span
    finally:
        try:
            span_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass


def shutdown() -> None:
    """Flush span buffers on application shutdown."""
    global _INITIALIZED, _ENABLED, _TRACER
    if not _ENABLED:
        return
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        shutdown_fn = getattr(provider, "shutdown", None)
        if shutdown_fn:
            shutdown_fn()
    except Exception as e:  # noqa: BLE001
        logger.debug("OTEL shutdown failed: %s", e)
    _ENABLED = False
    _INITIALIZED = False
    _TRACER = None
