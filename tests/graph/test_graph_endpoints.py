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

    def test_corrupt_cache_falls_back_to_fresh_introspection(self):
        # A cache payload missing required keys (no "labels", no "provider"
        # — anything that breaks graph_schema_from_dict). The endpoint
        # logs a warning and silently re-introspects rather than 500-ing.
        # This is the most likely real-world failure when a future schema
        # migration changes the cache shape.
        bad_cache = {"unexpected": "shape", "labels": [{"missing_name": True}]}
        conn = _neo4j_conn(schema_cache=bad_cache)
        app = _make_app()
        _override_db(app, conn)

        fresh = _sample_schema()
        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(return_value=fresh),
        ):
            resp = TestClient(app).get("/api/graph/connections/42/schema")

        assert resp.status_code == 200
        body = resp.json()
        # Served from fresh introspection, not the broken cache.
        assert body["cached"] is False
        assert body["label_count"] == 2
        # Cache was healed in-place — next request will hit the cache path.
        assert conn.schema_cache["label_count"] == 2
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

        # The driver's exception text — which we must NOT echo to the
        # caller, because Neo4j errors can embed the connection URI
        # (potentially with credentials). Use a value that would be
        # obviously bad to leak so a regression is visible.
        leaky_msg = "boom @ bolt://user:hunter2@host:7687"
        with patch(
            "src.api.endpoints.graph._run_introspection",
            new=AsyncMock(side_effect=RuntimeError(leaky_msg)),
        ):
            resp = TestClient(app).post("/api/graph/connections/42/introspect")

        assert resp.status_code == 502
        detail = resp.json()["detail"]
        # Sanitized body is generic and points at server logs.
        assert "Neo4j introspection failed" in detail
        assert "server logs" in detail.lower()
        # Defense in depth: the raw exception text never appears in body.
        assert "hunter2" not in detail
        assert "bolt://" not in detail
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

    def test_summarizer_failure_returns_fallback_not_500(self):
        # Lock in the "fallback, not 500" contract: if the summarizer
        # pipeline raises (router lookup error, missing provider config,
        # internal try/except regressed in a future change), the endpoint
        # still returns a 200 with a deterministic fallback blurb so the
        # Overview card renders something useful.
        conn = _neo4j_conn(schema_cache=_sample_schema().to_dict())
        app = _make_app()
        _override_db(app, conn)

        async def boom(_db):
            raise RuntimeError("model router exploded")

        with patch(
            "src.graph.ai.schema_summarizer.get_graph_schema_summarizer",
            new=boom,
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/ai/schema-summary"
            )

        assert resp.status_code == 200
        body = resp.json()
        # Used the deterministic fallback string from graph_prompts.
        assert body["used_fallback"] is True
        assert body["summary"]
        assert body["model"] is None
        assert body["provider"] is None
        app.dependency_overrides.clear()


# ── Phase 25.3 — /query endpoint ──────────────────────────────────────────


def _override_db_with_history(app: FastAPI, conn):
    """DB override that supports the connection lookup + history insert + count."""
    from src.api.dependencies import get_db

    def make_db():
        db = MagicMock()
        # First execute() — connection lookup. Subsequent execute() calls (history
        # insert, count, fetch) all return empty/zero scalars so the endpoint
        # works against an in-memory stand-in. We use a side_effect list so
        # we don't have to introspect the SQL.
        def fake_scalar_one_or_none():
            return conn

        conn_lookup_result = MagicMock()
        conn_lookup_result.scalar_one_or_none = fake_scalar_one_or_none

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        fetch_result = MagicMock()
        fetch_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        results = [
            conn_lookup_result,  # _load_graph_connection
            count_result,         # count() for history
            fetch_result,         # rows for history
        ]
        results_iter = iter(results)

        async def execute(*args, **kwargs):
            try:
                return next(results_iter)
            except StopIteration:
                return MagicMock()

        db.execute = execute
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
        return db

    async def fake_get_db():
        yield make_db()

    app.dependency_overrides[get_db] = fake_get_db


class TestRunGraphQueryEndpoint:
    def test_blocked_write_returns_400_with_reason(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db_with_history(app, conn)

        with patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=MagicMock())
            )),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/query",
                json={"cypher": "CREATE (n:User {name: 'Alice'})"},
            )

        assert resp.status_code == 400, resp.text
        detail = resp.json()["detail"]
        assert detail["safety_level"] == "write"
        assert "read-only" in detail["blocked_reason"].lower()
        assert detail["connection_id"] == 42
        app.dependency_overrides.clear()

    def test_read_query_executes_and_returns_payload(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db_with_history(app, conn)

        from src.graph.neo4j.query_executor import ExecutionResult
        from src.graph.result_formatter import FormattedResult
        from src.graph.safety.classifier import (
            GraphQuerySafetyLevel,
            SafetyClassification,
        )

        formatted = FormattedResult(
            table_columns=["name"],
            table_rows=[["Alice"]],
            nodes=[],
            edges=[],
        )
        canned = ExecutionResult(
            success=True,
            cypher="MATCH (u) RETURN u.name AS name",
            safety=SafetyClassification(level=GraphQuerySafetyLevel.READ_ONLY),
            formatted=formatted,
            record_count=1,
            execution_time_ms=12.3,
            server_warnings=["Deprecated: foo"],
        )

        with patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ), patch(
            "src.api.endpoints.graph.execute_cypher",
            new=AsyncMock(return_value=canned),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/query",
                json={"cypher": "MATCH (u) RETURN u.name AS name"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["safety_level"] == "read_only"
        assert body["record_count"] == 1
        assert body["table"]["columns"] == ["name"]
        assert body["table"]["rows"] == [["Alice"]]
        assert body["graph_viz"]["has_graph"] is False
        assert body["server_warnings"] == ["Deprecated: foo"]
        app.dependency_overrides.clear()

    def test_driver_error_returns_502_with_category(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db_with_history(app, conn)

        from src.graph.neo4j.error_classifier import (
            ClassifiedError,
            GraphErrorCategory,
        )
        from src.graph.neo4j.query_executor import ExecutionResult
        from src.graph.safety.classifier import (
            GraphQuerySafetyLevel,
            SafetyClassification,
        )

        canned = ExecutionResult(
            success=False,
            cypher="MATCH (n) RETURN n",
            safety=SafetyClassification(level=GraphQuerySafetyLevel.READ_ONLY),
            error=ClassifiedError(
                category=GraphErrorCategory.AUTH,
                user_message="Authentication failed.",
                hint="Check credentials.",
            ),
            execution_time_ms=5.0,
        )

        with patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ), patch(
            "src.api.endpoints.graph.execute_cypher",
            new=AsyncMock(return_value=canned),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/query",
                json={"cypher": "MATCH (n) RETURN n"},
            )

        assert resp.status_code == 502, resp.text
        detail = resp.json()["detail"]
        assert detail["error_category"] == "auth"
        assert detail["safety_level"] == "read_only"
        assert "Authentication" in detail["error_message"]
        app.dependency_overrides.clear()

    def test_kill_switch_blocks_query(self):
        conn = _neo4j_conn()
        app = _make_app(graph_mode=False)
        _override_db_with_history(app, conn)

        resp = TestClient(app).post(
            "/api/graph/connections/42/query",
            json={"cypher": "MATCH (n) RETURN n"},
        )
        assert resp.status_code == 400
        assert "GRAPH_MODE_ENABLED" in resp.json()["detail"]
        app.dependency_overrides.clear()


class TestGraphHistoryEndpoint:
    def test_history_empty_returns_zero_total(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db_with_history(app, conn)

        resp = TestClient(app).get("/api/graph/connections/42/history")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["connection_id"] == 42
        assert body["items"] == []
        assert body["total"] == 0
        assert body["limit"] == 50
        assert body["offset"] == 0
        app.dependency_overrides.clear()

    def test_history_kill_switch_blocks(self):
        conn = _neo4j_conn()
        app = _make_app(graph_mode=False)
        _override_db_with_history(app, conn)

        resp = TestClient(app).get("/api/graph/connections/42/history")
        assert resp.status_code == 400
        app.dependency_overrides.clear()
