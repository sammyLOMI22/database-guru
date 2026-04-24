"""Phase 24.2 — Prometheus metrics behaviour and /metrics endpoint gating."""
from __future__ import annotations

import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from src.observability import metrics


@pytest.fixture(autouse=True)
def _reset_metrics() -> Iterator[None]:
    metrics.reset_for_test()
    yield
    metrics.reset_for_test()


def _enable(monkeypatch, *, expose: bool = True) -> None:
    monkeypatch.setenv("METRICS_ENABLED", "true")
    monkeypatch.setenv("METRICS_EXPOSE_ENDPOINT", "true" if expose else "false")
    # Force re-import so main.py reads the env-var overrides.
    import importlib
    import src.main as _m
    importlib.reload(_m)
    return _m


def _disable(monkeypatch) -> None:
    monkeypatch.delenv("METRICS_ENABLED", raising=False)
    monkeypatch.delenv("METRICS_EXPOSE_ENDPOINT", raising=False)


def test_helpers_are_noop_when_disabled():
    # Module import alone must not register any prometheus collectors.
    metrics.record_http_request("GET", "/x", 200, 0.1)
    metrics.record_llm_call(
        provider="ollama", model="m", agent_type="a", success=True, duration_s=0.1
    )
    metrics.record_sql_query(dialect="postgresql", success=True, duration_s=0.05)
    metrics.record_pool_checkout("postgresql")
    metrics.record_cache_hit("redis")
    assert metrics.is_enabled() is False


def test_init_metrics_creates_collectors(monkeypatch):
    monkeypatch.setenv("METRICS_ENABLED", "true")
    metrics.init_metrics(force=True)
    assert metrics.is_enabled() is True

    metrics.record_http_request("GET", "/api/x", 200, 0.123)
    metrics.record_llm_call(
        provider="ollama",
        model="llama3",
        agent_type="sql_generator",
        success=True,
        duration_s=2.0,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
    )
    metrics.record_sql_query(dialect="sqlite", success=True, duration_s=0.05)
    metrics.record_pool_checkout("sqlite")
    metrics.set_pool_size("sqlite", 3)
    metrics.record_cache_hit("redis")
    metrics.record_cache_miss("redis")

    from prometheus_client import generate_latest

    body = generate_latest(metrics._REGISTRY).decode()
    for needle in (
        'dbguru_http_requests_total{method="GET",route="/api/x",status="200"} 1.0',
        'dbguru_llm_calls_total{agent_type="sql_generator",model="llama3",provider="ollama",success="true"} 1.0',
        'dbguru_llm_tokens_total{direction="input",model="llama3",provider="ollama"} 100.0',
        'dbguru_llm_tokens_total{direction="output",model="llama3",provider="ollama"} 50.0',
        'dbguru_llm_cost_usd_total{model="llama3",provider="ollama"} 0.01',
        'dbguru_sql_query_duration_seconds_count{dialect="sqlite",success="true"} 1.0',
        'dbguru_connection_pool_checkouts_total{dialect="sqlite"} 1.0',
        'dbguru_connection_pool_size{dialect="sqlite"} 3.0',
        'dbguru_cache_hits_total{cache="redis"} 1.0',
        'dbguru_cache_misses_total{cache="redis"} 1.0',
    ):
        assert needle in body, f"missing metric line: {needle}"


def test_metrics_endpoint_exposes_when_enabled(monkeypatch):
    main = _enable(monkeypatch)
    with TestClient(main.app) as client:
        # Generate some traffic so counters have something to show.
        client.get("/health")
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "dbguru_http_requests_total" in r.text


def test_metrics_endpoint_404_when_endpoint_disabled(monkeypatch):
    monkeypatch.setenv("METRICS_ENABLED", "true")
    monkeypatch.setenv("METRICS_EXPOSE_ENDPOINT", "false")
    import importlib
    import src.main as _m
    importlib.reload(_m)
    with TestClient(_m.app) as client:
        r = client.get("/metrics")
        # Route is not mounted at all → FastAPI returns 404.
        assert r.status_code == 404


def test_metrics_endpoint_404_when_metrics_disabled_completely(monkeypatch):
    _disable(monkeypatch)
    import importlib
    import src.main as _m
    importlib.reload(_m)
    with TestClient(_m.app) as client:
        r = client.get("/metrics")
        assert r.status_code == 404


def test_route_label_uses_template_not_raw_path(monkeypatch):
    main = _enable(monkeypatch)
    with TestClient(main.app) as client:
        # Hit a non-existent path with a unique segment. If the metric labelled
        # by the raw path, cardinality would explode. Our middleware records
        # under the matched route ("" for unmatched), but never the raw path.
        unique = f"/no-such/{os.getpid()}-{id(client)}"
        client.get(unique)
        r = client.get("/metrics")
        assert r.status_code == 200
        # The raw path must not appear in any metric label value.
        assert unique not in r.text
