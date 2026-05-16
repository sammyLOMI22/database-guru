"""Unit tests for Phase 25.2 — Neo4j schema introspection.

We avoid spinning up a live Neo4j instance for these tests (that's covered
by the optional ``@pytest.mark.integration`` suite). Instead we mock the
driver session at the ``run`` boundary and feed canned rows that mirror
what Neo4j 5.x returns from ``CALL db.labels()`` etc.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.graph.neo4j.schema_inspector import (
    MAX_LABELS_TO_COUNT,
    Neo4jSchemaInspector,
)


# ── Mock session plumbing ─────────────────────────────────────────────────


class _StubResult:
    """Stand-in for ``neo4j.AsyncResult`` that exposes only what we use."""

    def __init__(self, records: List[Dict[str, Any]]):
        self._records = records

    async def data(self) -> List[Dict[str, Any]]:
        return list(self._records)

    async def single(self):
        return self._records[0] if self._records else None


def make_driver(query_responses: Dict[str, Any]):
    """Build an AsyncDriver mock whose ``session().run(cypher)`` returns
    a :class:`_StubResult` per matching query prefix.

    ``query_responses`` maps a *substring* of the Cypher to the response.
    The first matching key wins. Callables may be passed for dynamic
    responses (e.g. raise an exception).
    """

    async def run(cypher: str, *args, **kwargs):
        for needle, response in query_responses.items():
            if needle in cypher:
                if callable(response):
                    response = response(cypher)
                if isinstance(response, Exception):
                    raise response
                return _StubResult(response)
        # Unmatched queries return empty results (loud failure would be
        # nicer for development, but inspector deliberately tolerates
        # partial coverage).
        return _StubResult([])

    session = MagicMock()
    session.run = AsyncMock(side_effect=run)

    # async context manager protocol
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    driver = MagicMock()
    driver.session = MagicMock(return_value=session_cm)
    return driver, session


# ── Happy-path introspection ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_introspect_happy_path():
    responses = {
        "db.labels()": [{"label": "User"}, {"label": "Order"}],
        "db.relationshipTypes()": [{"relationshipType": "PURCHASED"}],
        "SHOW INDEXES": [
            {
                "name": "user_email",
                "entityType": "NODE",
                "labelsOrTypes": ["User"],
                "properties": ["email"],
                "type": "RANGE",
                "state": "ONLINE",
            }
        ],
        "SHOW CONSTRAINTS": [
            {
                "name": "user_email_unique",
                "entityType": "NODE",
                "labelsOrTypes": ["User"],
                "properties": ["email"],
                "type": "UNIQUENESS",
            }
        ],
        "db.schema.nodeTypeProperties()": [
            {
                "nodeType": ":`User`",
                "propertyName": "email",
                "propertyTypes": ["String"],
                "mandatory": True,
            },
            {
                "nodeType": ":`Order`",
                "propertyName": "total",
                "propertyTypes": ["Float"],
                "mandatory": False,
            },
        ],
        "db.schema.relTypeProperties()": [
            {
                "relType": ":`PURCHASED`",
                "propertyName": "at",
                "propertyTypes": ["DateTime"],
                "mandatory": False,
            }
        ],
        # MATCH (n:`User`) RETURN count(n) AS c
        "MATCH (n:`User`)": [{"c": 500}],
        "MATCH (n:`Order`)": [{"c": 1200}],
        # Pattern probe
        "MATCH (a)-[r]->(b)": [
            {"sa": ["User"], "rt": "PURCHASED", "tb": ["Order"], "c": 1200}
        ],
        "dbms.components()": [
            {"name": "Neo4j Kernel", "versions": ["5.18.0"], "edition": "enterprise"}
        ],
    }
    driver, _ = make_driver(responses)
    inspector = Neo4jSchemaInspector(driver=driver, database_name="neo4j")

    schema = await inspector.introspect()

    assert schema.provider == "neo4j"
    assert schema.database_name == "neo4j"
    assert {lbl.name for lbl in schema.labels} == {"User", "Order"}
    user = next(l for l in schema.labels if l.name == "User")
    assert user.estimated_count == 500
    assert any(p.name == "email" and p.indexed for p in user.properties)
    assert {r.name for r in schema.relationships} == {"PURCHASED"}
    assert schema.patterns[0].relationship_type == "PURCHASED"
    assert schema.server_version == "5.18.0"
    assert schema.warnings == []


# ── Partial failure / warnings ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_introspect_pattern_probe_failure_adds_warning():
    responses = {
        "db.labels()": [{"label": "User"}],
        "db.relationshipTypes()": [],
        "SHOW INDEXES": [],
        "SHOW CONSTRAINTS": [],
        "db.schema.nodeTypeProperties()": [],
        "db.schema.relTypeProperties()": [],
        "MATCH (a)-[r]->(b)": RuntimeError("pattern probe boom"),
        "dbms.components()": [],
    }
    driver, _ = make_driver(responses)
    inspector = Neo4jSchemaInspector(driver=driver, database_name="neo4j")
    schema = await inspector.introspect()
    assert any("patterns" in w and "boom" in w for w in schema.warnings)
    assert schema.patterns == []


@pytest.mark.asyncio
async def test_introspect_label_count_exceeding_cap_marks_warning():
    responses = {
        "db.labels()": [{"label": "Huge"}],
        "db.relationshipTypes()": [],
        "SHOW INDEXES": [],
        "SHOW CONSTRAINTS": [],
        "db.schema.nodeTypeProperties()": [],
        "db.schema.relTypeProperties()": [],
        "MATCH (n:`Huge`)": [{"c": 50_000_000}],
        "MATCH (a)-[r]->(b)": [],
        "dbms.components()": [],
    }
    driver, _ = make_driver(responses)
    inspector = Neo4jSchemaInspector(
        driver=driver, database_name="neo4j", count_cap=10_000_000
    )
    schema = await inspector.introspect()
    huge = next(l for l in schema.labels if l.name == "Huge")
    assert huge.estimated_count == 10_000_000
    assert any("count > cap" in w for w in schema.warnings)


@pytest.mark.asyncio
async def test_introspect_empty_graph():
    responses = {
        "db.labels()": [],
        "db.relationshipTypes()": [],
        "SHOW INDEXES": [],
        "SHOW CONSTRAINTS": [],
        "db.schema.nodeTypeProperties()": [],
        "db.schema.relTypeProperties()": [],
        "MATCH (a)-[r]->(b)": [],
        "dbms.components()": [
            {"name": "Neo4j Kernel", "versions": ["5.18.0"], "edition": "community"}
        ],
    }
    driver, _ = make_driver(responses)
    schema = await Neo4jSchemaInspector(driver=driver).introspect()
    assert schema.labels == []
    assert schema.relationships == []
    assert schema.patterns == []
    assert schema.edition == "community"
    assert schema.warnings == []


@pytest.mark.asyncio
async def test_introspect_query_timeout_records_warning():
    async def slow(cypher: str):
        if "db.labels" in cypher:
            await asyncio.sleep(5)
        return []

    async def run(cypher: str, *args, **kwargs):
        return _StubResult(await slow(cypher))

    session = MagicMock()
    session.run = AsyncMock(side_effect=run)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    driver = MagicMock()
    driver.session = MagicMock(return_value=session_cm)

    inspector = Neo4jSchemaInspector(
        driver=driver, database_name="neo4j", query_timeout_s=0.05
    )
    schema = await inspector.introspect()
    assert any("timed out" in w for w in schema.warnings)


@pytest.mark.asyncio
async def test_label_count_phase_respects_max():
    """When more than MAX_LABELS_TO_COUNT labels exist, only the first slice
    receives counts and a warning is emitted."""
    labels = [{"label": f"Label{i}"} for i in range(MAX_LABELS_TO_COUNT + 3)]

    async def run(cypher: str, *args, **kwargs):
        if "db.labels()" in cypher:
            return _StubResult(labels)
        if "db.relationshipTypes()" in cypher:
            return _StubResult([])
        if "SHOW INDEXES" in cypher:
            return _StubResult([])
        if "SHOW CONSTRAINTS" in cypher:
            return _StubResult([])
        if "nodeTypeProperties" in cypher:
            return _StubResult([])
        if "relTypeProperties" in cypher:
            return _StubResult([])
        if "MATCH (n:" in cypher and "count(n)" in cypher:
            return _StubResult([{"c": 1}])
        if "MATCH (a)-[r]->(b)" in cypher:
            return _StubResult([])
        if "dbms.components()" in cypher:
            return _StubResult([])
        return _StubResult([])

    session = MagicMock()
    session.run = AsyncMock(side_effect=run)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    driver = MagicMock()
    driver.session = MagicMock(return_value=session_cm)

    schema = await Neo4jSchemaInspector(driver=driver).introspect()
    counted = sum(1 for l in schema.labels if l.estimated_count is not None)
    assert counted == MAX_LABELS_TO_COUNT
    assert any("Counted first" in w for w in schema.warnings)


# ── Integration suite (opt-in) ────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_neo4j_introspection():
    """Spin up against a real Neo4j 5.x instance.

    Requires ``NEO4J_TEST_URI`` (e.g. ``bolt://localhost:7687``) and
    optionally ``NEO4J_TEST_USER`` / ``NEO4J_TEST_PASSWORD``. Skipped when
    unset so the default test run never depends on Docker.
    """
    import os

    uri = os.environ.get("NEO4J_TEST_URI")
    if not uri:
        pytest.skip("NEO4J_TEST_URI not set")

    from src.graph.neo4j.driver_pool import build_driver

    user = os.environ.get("NEO4J_TEST_USER", "neo4j")
    password = os.environ.get("NEO4J_TEST_PASSWORD", "neo4j")
    driver = build_driver(uri, user, password)
    try:
        schema = await Neo4jSchemaInspector(driver=driver).introspect()
    finally:
        await driver.close()

    # Bare minimum: introspection should complete without raising and
    # populate provider + collected_at.
    assert schema.provider == "neo4j"
    assert schema.collected_at is not None
