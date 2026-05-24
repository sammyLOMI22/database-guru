"""Tests for the Phase 25.5 Visual Graph Explorer endpoint + helper.

Covers two layers:

* ``expand_from_node`` (unit): validation of label/property/rel-type
  identifiers, depth clamp, direction-to-arrow mapping, node_cap → Cypher
  ``LIMIT`` propagation. The driver is mocked, so no Neo4j needed.
* ``POST /api/graph/connections/{id}/explore`` (endpoint): happy path,
  invalid identifier 400, driver error 502, soft-deleted 404, graph
  mode disabled 400.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.common import get_settings
from src.api.endpoints.graph import router as graph_router
from src.auth.dependencies import get_optional_user
from src.config.settings import Settings
from src.graph.neo4j.error_classifier import GraphErrorCategory
from src.graph.neo4j.query_executor import (
    EXPAND_MAX_DEPTH,
    EXPAND_MIN_DEPTH,
    expand_from_node,
)
from src.graph.safety.classifier import GraphQuerySafetyLevel


# ── Mock driver helpers (mirror test_query_executor.py) ──────────────────


class _AsyncIterRecords:
    def __init__(self, records: List[Dict[str, Any]]):
        self._records = list(records)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._records:
            raise StopAsyncIteration
        rec = self._records.pop(0)
        wrapper = MagicMock()
        wrapper.data = MagicMock(return_value=rec)
        return wrapper


def _make_result(records, notifications=None):
    iterable = _AsyncIterRecords(records)
    summary = MagicMock()
    summary.notifications = notifications or []

    class _Result:
        def __aiter__(self):
            return iterable.__aiter__()

        async def consume(self):
            return summary

    return _Result()


def _make_driver(*, run_return=None, run_side_effect=None):
    session = MagicMock()
    if run_side_effect is not None:
        session.run = AsyncMock(side_effect=run_side_effect)
    else:
        session.run = AsyncMock(return_value=run_return)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    driver = MagicMock()
    driver.session = MagicMock(return_value=session_cm)
    return driver, session


# ── expand_from_node — unit tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_expand_validates_label_identifier():
    """Invalid Cypher identifiers in start_label must raise before opening a session."""
    driver, _ = _make_driver(run_return=_make_result([]))
    with pytest.raises(ValueError, match="label"):
        await expand_from_node(
            driver,
            start_label="User; DROP DATABASE x",
            start_property="email",
            start_value="a@b.com",
        )
    # No session should have been opened — validation happens first.
    driver.session.assert_not_called()


@pytest.mark.asyncio
async def test_expand_validates_property_identifier():
    driver, _ = _make_driver(run_return=_make_result([]))
    with pytest.raises(ValueError, match="property"):
        await expand_from_node(
            driver,
            start_label="User",
            start_property="email-with-dash",
            start_value="x",
        )


@pytest.mark.asyncio
async def test_expand_validates_rel_type_identifier():
    driver, _ = _make_driver(run_return=_make_result([]))
    with pytest.raises(ValueError, match="relationship"):
        await expand_from_node(
            driver,
            start_label="User",
            start_property="email",
            start_value="x",
            rel_types=["VALID", "BAD TYPE"],
        )


@pytest.mark.asyncio
async def test_expand_rejects_invalid_direction():
    driver, _ = _make_driver(run_return=_make_result([]))
    with pytest.raises(ValueError, match="direction"):
        await expand_from_node(
            driver,
            start_label="User",
            start_property="email",
            start_value="x",
            direction="sideways",
        )


@pytest.mark.asyncio
async def test_expand_clamps_depth_to_max():
    """Depth above EXPAND_MAX_DEPTH should snap to the cap, not pass through."""
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="x",
        depth=99,
    )
    cypher = session.run.call_args.args[0]
    assert f"*1..{EXPAND_MAX_DEPTH}" in cypher


@pytest.mark.asyncio
async def test_expand_clamps_depth_to_min():
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="x",
        depth=0,
    )
    cypher = session.run.call_args.args[0]
    assert f"*1..{EXPAND_MIN_DEPTH}" in cypher


@pytest.mark.asyncio
async def test_expand_direction_out_uses_outgoing_arrow():
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="x",
        direction="out",
    )
    cypher = session.run.call_args.args[0]
    # Outgoing direction => right arrow at the end.
    assert "]->(neighbor)" in cypher
    # And NOT incoming.
    assert "<-[" not in cypher


@pytest.mark.asyncio
async def test_expand_direction_in_uses_incoming_arrow():
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="x",
        direction="in",
    )
    cypher = session.run.call_args.args[0]
    assert "<-[" in cypher
    assert "]->(neighbor)" not in cypher


@pytest.mark.asyncio
async def test_expand_rel_type_filter_injected():
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="x",
        rel_types=["FOLLOWS", "PURCHASED"],
    )
    cypher = session.run.call_args.args[0]
    assert ":FOLLOWS|PURCHASED" in cypher


@pytest.mark.asyncio
async def test_expand_passes_start_value_as_parameter():
    """The start_value must not be string-interpolated into the Cypher
    (otherwise injection is back on the table)."""
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="evil'); DROP DATABASE x; //",
    )
    cypher = session.run.call_args.args[0]
    params = session.run.call_args.args[1]
    assert "DROP DATABASE" not in cypher
    assert params == {"start_value": "evil'); DROP DATABASE x; //"}


@pytest.mark.asyncio
async def test_expand_node_cap_drives_cypher_limit():
    driver, session = _make_driver(run_return=_make_result([]))
    await expand_from_node(
        driver,
        start_label="User",
        start_property="email",
        start_value="x",
        node_cap=25,
        max_viz_nodes=50,
    )
    cypher = session.run.call_args.args[0]
    # Effective cap is min(node_cap, max_viz_nodes) → 25; fetch_limit = 50.
    assert "LIMIT 50" in cypher


# ── Endpoint — happy path + error mapping ────────────────────────────────


def _make_app(*, graph_mode: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(graph_router, prefix="/api")
    app.dependency_overrides[get_optional_user] = lambda: None
    app.dependency_overrides[get_settings] = lambda: Settings(
        GRAPH_MODE_ENABLED=graph_mode
    )
    return app


def _neo4j_conn(*, deleted=False, owner_id=None):
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
    conn.schema_cache = None
    conn.schema_updated_at = datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc)
    return conn


def _override_db(app: FastAPI, conn):
    from src.api.dependencies import get_db

    async def fake_get_db():
        db = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conn)
        db.execute = AsyncMock(return_value=scalar_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        yield db

    app.dependency_overrides[get_db] = fake_get_db


def _success_execution(record_count: int = 2, truncated: bool = False):
    """Build a minimal ExecutionResult-shaped mock for the endpoint."""
    from src.graph.neo4j.query_executor import ExecutionResult
    from src.graph.result_formatter import FormattedResult, GraphVizNode
    from src.graph.safety.classifier import SafetyClassification

    formatted = FormattedResult(
        table_columns=["p"],
        table_rows=[[{"_kind": "path"}], [{"_kind": "path"}]],
        nodes=[
            GraphVizNode(
                id="n1", labels=["User"], properties={"email": "a@b.com"}, display_name="a@b.com"
            ),
            GraphVizNode(
                id="n2", labels=["Order"], properties={"id": "42"}, display_name="42"
            ),
        ],
        edges=[],
        truncated=truncated,
        warnings=["Visualization truncated — only 2 node(s) shown."] if truncated else [],
    )
    return ExecutionResult(
        success=True,
        cypher="MATCH ...",
        safety=SafetyClassification(level=GraphQuerySafetyLevel.READ_ONLY, reasons=[]),
        formatted=formatted,
        execution_time_ms=4.2,
        record_count=record_count,
        server_warnings=[],
    )


class TestExploreEndpoint:
    def test_happy_path_returns_graph_viz(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db(app, conn)

        with patch(
            "src.api.endpoints.graph.expand_from_node",
            new=AsyncMock(return_value=_success_execution()),
        ), patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/explore",
                json={
                    "start_label": "User",
                    "start_property": "email",
                    "start_value": "a@b.com",
                    "depth": 2,
                    "rel_types": ["FOLLOWS"],
                    "direction": "out",
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["connection_id"] == 42
        assert body["start_label"] == "User"
        assert body["depth"] == 2
        assert body["direction"] == "out"
        assert body["rel_types"] == ["FOLLOWS"]
        assert body["safety_level"] == "read_only"
        assert body["success"] is True
        assert body["record_count"] == 2
        assert body["graph_viz"]["has_graph"] is True
        assert len(body["graph_viz"]["nodes"]) == 2
        app.dependency_overrides.clear()

    def test_truncation_banner_propagates(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db(app, conn)

        with patch(
            "src.api.endpoints.graph.expand_from_node",
            new=AsyncMock(return_value=_success_execution(record_count=200, truncated=True)),
        ), patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/explore",
                json={
                    "start_label": "User",
                    "start_property": "email",
                    "start_value": "a@b.com",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["truncated"] is True
        assert any("truncated" in w.lower() for w in body["warnings"])
        app.dependency_overrides.clear()

    def test_invalid_label_returns_400(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db(app, conn)

        # Pydantic schema accepts the string, but expand_from_node's
        # identifier validator raises ValueError → 400.
        with patch(
            "src.api.endpoints.graph.expand_from_node",
            new=AsyncMock(side_effect=ValueError("Invalid label: 'User; DROP'")),
        ), patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/explore",
                json={
                    "start_label": "User; DROP",
                    "start_property": "email",
                    "start_value": "x",
                },
            )

        assert resp.status_code == 400
        body = resp.json()["detail"]
        assert "Invalid label" in body["blocked_reason"]
        assert body["safety_level"] == "unknown"
        app.dependency_overrides.clear()

    def test_invalid_depth_rejected_by_pydantic(self):
        conn = _neo4j_conn()
        app = _make_app()
        _override_db(app, conn)

        with patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/explore",
                json={
                    "start_label": "User",
                    "start_property": "email",
                    "start_value": "x",
                    "depth": 99,
                },
            )
        # FastAPI/Pydantic returns 422 for schema violations.
        assert resp.status_code == 422
        app.dependency_overrides.clear()

    def test_driver_error_returns_502_with_category(self):
        from src.graph.neo4j.error_classifier import ClassifiedError
        from src.graph.neo4j.query_executor import ExecutionResult
        from src.graph.safety.classifier import SafetyClassification

        conn = _neo4j_conn()
        app = _make_app()
        _override_db(app, conn)

        err = ClassifiedError(
            category=GraphErrorCategory.SYNTAX,
            user_message="Bad syntax",
            hint="Check label spelling",
            code="Neo.ClientError.Statement.SyntaxError",
        )
        bad_exec = ExecutionResult(
            success=False,
            cypher="MATCH ...",
            safety=SafetyClassification(level=GraphQuerySafetyLevel.READ_ONLY, reasons=[]),
            error=err,
            execution_time_ms=1.0,
        )

        with patch(
            "src.api.endpoints.graph.expand_from_node",
            new=AsyncMock(return_value=bad_exec),
        ), patch(
            "src.api.endpoints.graph.Neo4jDriverPool.get_instance",
            new=AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=MagicMock()))),
        ):
            resp = TestClient(app).post(
                "/api/graph/connections/42/explore",
                json={
                    "start_label": "User",
                    "start_property": "email",
                    "start_value": "x",
                },
            )

        assert resp.status_code == 502
        body = resp.json()["detail"]
        assert body["error_category"] == "syntax"
        assert body["error_hint"] == "Check label spelling"
        app.dependency_overrides.clear()

    def test_graph_mode_disabled_returns_400(self):
        conn = _neo4j_conn()
        app = _make_app(graph_mode=False)
        _override_db(app, conn)

        resp = TestClient(app).post(
            "/api/graph/connections/42/explore",
            json={
                "start_label": "User",
                "start_property": "email",
                "start_value": "x",
            },
        )
        assert resp.status_code == 400
        assert "disabled" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()

    def test_soft_deleted_connection_returns_404(self):
        conn = _neo4j_conn(deleted=True)
        app = _make_app()
        _override_db(app, conn)

        resp = TestClient(app).post(
            "/api/graph/connections/42/explore",
            json={
                "start_label": "User",
                "start_property": "email",
                "start_value": "x",
            },
        )
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    def test_non_graph_connection_rejected(self):
        conn = _neo4j_conn()
        conn.database_type = "postgresql"
        app = _make_app()
        _override_db(app, conn)

        resp = TestClient(app).post(
            "/api/graph/connections/42/explore",
            json={
                "start_label": "User",
                "start_property": "email",
                "start_value": "x",
            },
        )
        assert resp.status_code == 400
        assert "not a graph database" in resp.json()["detail"]
        app.dependency_overrides.clear()
