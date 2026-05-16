"""Tests for the Phase 25.2 graph API endpoints.

Covers:

* ``GET /api/graph/connections/{id}/schema`` — cache hit, refresh, 400 when
  pointed at a non-graph connection, 400 when ``GRAPH_MODE_ENABLED=False``,
  404 for missing / soft-deleted rows.
* ``POST /api/graph/connections/{id}/introspect`` — fresh introspection
  populates ``schema_cache`` + ``schema_updated_at``.
* ``POST /api/graph/connections/{id}/ai/schema-summary`` — returns summarizer
  output; 409 when no cache exists.

We don't spin up a real Neo4j here — the introspection path is exercised by
patching :func:`src.api.endpoints.graph._run_introspection` so the tests
stay deterministic and fast.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.common import get_settings
from src.api.endpoints.graph import router as graph_router
from src.auth.dependencies import get_optional_user
from src.config.settings import Settings
from src.graph.schema.normalizer import (
    GraphNodeLabel,
    GraphProperty,
    GraphRelationshipPattern,
    GraphRelationshipType,
    GraphSchema,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _make_app(*, graph_mode: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(graph_router, prefix="/api")
    app.dependency_overrides[get_optional_user] = lambda: None
    app.dependency_overrides[get_settings] = lambda: Settings(
        GRAPH_MODE_ENABLED=graph_mode
    )
    return app


def _neo4j_conn(*, schema_cache=None, deleted=False, owner_id=None):
    conn = MagicMock()
    conn.id = 42
    conn.name = "graph-prod"
    conn.database_type = "neo4j"
    conn.database_name = "neo4j"
    conn.host = "bolt://localhost:7687"
    conn.port = None
    conn.username = "neo4j"
    conn.password_encrypted = "secret"
    conn.encrypted = False
    conn.read_only = True
    conn.owner_id = owner_id
    conn.is_deleted = deleted
    conn.schema_cache = schema_cache
    conn.schema_updated_at = datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc)
    return conn


def _sql_conn():
    conn = _neo4j_conn()
    conn.database_type = "postgresql"
    return conn


def _sample_schema() -> GraphSchema:
    return GraphSchema(
        provider="neo4j",
        database_name="neo4j",
        labels=[
            GraphNodeLabel(
                name="User",
                estimated_count=10,
                properties=[GraphProperty(name="email", types=["String"])],
            ),
            GraphNodeLabel(name="Order", estimated_count=5),
        ],
        relationships=[GraphRelationshipType(name="PURCHASED")],
        patterns=[
            GraphRelationshipPattern(
                source_labels=["User"],
                relationship_type="PURCHASED",
                target_labels=["Order"],
                estimated_count=5,
            )
        ],
    )


def _patch_db_load(conn):
    """Patch SQLAlchemy session.execute().scalar_one_or_none() to yield conn."""
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none = MagicMock(return_value=conn)
    return scalar_result


def _override_db(app: FastAPI, conn):
    from src.api.dependencies import get_db

    async def fake_get_db():
        db = MagicMock()
        db.execute = AsyncMock(return_value=_patch_db_load(conn))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    app.dependency_overrides[get_db] = fake_get_db


# ── Tests ─────────────────────────────────────────────────────────────────


class TestGetSchemaEndpoint:
    def test_cached_schema_returned_without_introspection(self):
        cached = _sample_schema().to_dict()
        conn = _neo4j_conn(schema_cache=cached)
        app = _make_app()
        _override_db(app, conn)

        client = TestClient(app)
        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(side_effect=AssertionError("must not introspect when cached")),
        ):
            resp = client.get("/api/graph/connections/42/schema")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["cached"] is True
        assert body["label_count"] == 2
        assert body["connection_id"] == 42
        app.dependency_overrides.clear()

    def test_refresh_param_forces_introspection(self):
        cached = _sample_schema().to_dict()
        conn = _neo4j_conn(schema_cache=cached)
        app = _make_app()
        _override_db(app, conn)

        fresh = _sample_schema()
        # mutate fresh so we can prove it overwrote the cached version
        fresh.labels.append(GraphNodeLabel(name="Comment"))

        client = TestClient(app)
        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(return_value=fresh),
        ):
            resp = client.get("/api/graph/connections/42/schema?refresh=true")

        assert resp.status_code == 200
        body = resp.json()
        assert body["cached"] is False
        assert body["label_count"] == 3
        # Persisted to the conn object
        assert conn.schema_cache["label_count"] == 3
        assert conn.schema_updated_at is not None
        app.dependency_overrides.clear()

    def test_empty_cache_triggers_introspection(self):
        conn = _neo4j_conn(schema_cache=None)
        app = _make_app()
        _override_db(app, conn)

        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(return_value=_sample_schema()),
        ):
            resp = TestClient(app).get("/api/graph/connections/42/schema")

        assert resp.status_code == 200
        assert resp.json()["cached"] is False
        app.dependency_overrides.clear()

    def test_non_graph_connection_rejected(self):
        conn = _sql_conn()
        app = _make_app()
        _override_db(app, conn)

        resp = TestClient(app).get("/api/graph/connections/42/schema")
        assert resp.status_code == 400
        assert "not a graph database" in resp.json()["detail"]
        app.dependency_overrides.clear()

    def test_soft_deleted_returns_404(self):
        conn = _neo4j_conn(deleted=True, schema_cache=_sample_schema().to_dict())
        app = _make_app()
        _override_db(app, conn)

        resp = TestClient(app).get("/api/graph/connections/42/schema")
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    def test_missing_connection_returns_404(self):
        app = _make_app()
        _override_db(app, None)
        resp = TestClient(app).get("/api/graph/connections/42/schema")
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    def test_graph_mode_disabled_returns_400(self):
        conn = _neo4j_conn(schema_cache=_sample_schema().to_dict())
        app = _make_app(graph_mode=False)
        _override_db(app, conn)
        resp = TestClient(app).get("/api/graph/connections/42/schema")
        assert resp.status_code == 400
        assert "disabled" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()


class TestIntrospectEndpoint:
    def test_introspect_persists_fresh_schema(self):
        conn = _neo4j_conn(schema_cache=None)
        app = _make_app()
        _override_db(app, conn)

        fresh = _sample_schema()
        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(return_value=fresh),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/introspect",
                json={"overall_timeout_ms": 5000},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["cached"] is False
        assert body["label_count"] == 2
        # Cache busted + updated
        assert conn.schema_cache is not None
        assert conn.schema_updated_at is not None
        app.dependency_overrides.clear()

    def test_introspect_propagates_driver_failure_as_502(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db(app, conn)

        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(side_effect=RuntimeError("driver boom")),
        ):
            resp = TestClient(app).post("/api/graph/connections/42/introspect")

        assert resp.status_code == 502
        assert "driver boom" in resp.json()["detail"]
        app.dependency_overrides.clear()


class TestSchemaSummaryEndpoint:
    def test_returns_summary_from_summarizer(self):
        conn = _neo4j_conn(schema_cache=_sample_schema().to_dict())
        app = _make_app()
        _override_db(app, conn)

        fake_summarizer = MagicMock()

        async def _summarize(*args, **kwargs):
            return MagicMock(
                summary="Social graph of users and orders.",
                model="llama3",
                provider="ollama",
                used_fallback=False,
            )

        fake_summarizer.summarize = _summarize

        async def fake_get_summarizer(_db):
            return fake_summarizer

        with patch(
            "src.graph.ai.schema_summarizer.get_graph_schema_summarizer",
            new=fake_get_summarizer,
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/ai/schema-summary"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["summary"].startswith("Social graph")
        assert body["used_fallback"] is False
        app.dependency_overrides.clear()

    def test_no_cache_returns_409(self):
        conn = _neo4j_conn(schema_cache=None)
        app = _make_app()
        _override_db(app, conn)

        resp = TestClient(app).post(
            "/api/graph/connections/42/ai/schema-summary"
        )
        assert resp.status_code == 409
        assert "introspect" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()
