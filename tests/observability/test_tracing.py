"""Phase 24.3 — OpenTelemetry tracing safety + span attributes."""
from __future__ import annotations

from typing import Iterator

import pytest

from src.config.settings import Settings
from src.observability import tracing


@pytest.fixture(autouse=True)
def _reset_tracing() -> Iterator[None]:
    tracing.shutdown()
    yield
    tracing.shutdown()


def test_disabled_init_is_noop():
    tracing.init_tracing(Settings(OTEL_ENABLED=False), force=True)
    assert tracing.is_enabled() is False
    # Span helpers must still be callable as a context manager.
    with tracing.llm_call_span(provider="p", model="m", agent_type="a") as span:
        span.set_attribute("x", "y")
    with tracing.self_correcting_span() as span:
        span.set_attribute("execution.success", True)


def test_unreachable_exporter_does_not_crash_init():
    """If the OTLP endpoint is unreachable, init_tracing must still leave the
    backend in a healthy state. We point the exporter at a port that's almost
    certainly closed and assert the function returns normally.
    """
    s = Settings(
        OTEL_ENABLED=True,
        OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:1",
        OTEL_TRACES_SAMPLER_RATIO=1.0,
    )
    tracing.init_tracing(s, force=True)
    # Spans must work even without a working exporter.
    with tracing.llm_call_span(provider="ollama", model="m", agent_type="a") as span:
        span.set_attribute("llm.success", True)


def test_llm_span_records_required_attributes_when_enabled():
    """Set up the SDK with an in-memory exporter and verify the attributes
    that TrackedLLMClient is supposed to record are present on the span.
    """
    pytest.importorskip("opentelemetry.sdk")
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Get the tracer directly from our local provider so tests don't fight
    # OpenTelemetry's "TracerProvider can only be set once per process" guard.
    tracing._ENABLED = True
    tracing._INITIALIZED = True
    tracing._TRACER = provider.get_tracer("test")

    with tracing.llm_call_span(
        provider="ollama", model="llama3", agent_type="sql_generator"
    ) as span:
        span.set_attribute("llm.prompt_tokens", 50)
        span.set_attribute("llm.completion_tokens", 10)
        span.set_attribute("llm.cost_usd", 0.001)
        span.set_attribute("llm.success", True)

    spans = exporter.get_finished_spans()
    assert any(s.name == "llm.call" for s in spans), [s.name for s in spans]
    span = next(s for s in spans if s.name == "llm.call")
    attrs = dict(span.attributes)
    assert attrs["llm.provider"] == "ollama"
    assert attrs["llm.model"] == "llama3"
    assert attrs["llm.agent_type"] == "sql_generator"
    assert attrs["llm.prompt_tokens"] == 50
    assert attrs["llm.completion_tokens"] == 10
    assert attrs["llm.cost_usd"] == pytest.approx(0.001)
    assert attrs["llm.success"] is True


def test_self_correcting_span_records_outcome_attributes():
    pytest.importorskip("opentelemetry.sdk")
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    tracing._ENABLED = True
    tracing._INITIALIZED = True
    tracing._TRACER = provider.get_tracer("test")

    with tracing.self_correcting_span(agent_type="self_correcting") as span:
        span.set_attribute("db.dialect", "sqlite")
        span.set_attribute("agent.attempts", 2)
        span.set_attribute("agent.self_corrected", True)
        span.set_attribute("execution.success", True)

    spans = exporter.get_finished_spans()
    span = next(s for s in spans if s.name == "agent.self_correcting")
    attrs = dict(span.attributes)
    assert attrs["agent.type"] == "self_correcting"
    assert attrs["db.dialect"] == "sqlite"
    assert attrs["agent.attempts"] == 2
    assert attrs["agent.self_corrected"] is True
    assert attrs["execution.success"] is True
