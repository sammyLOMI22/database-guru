"""Unit tests for the Cypher query executor (Phase 25.3).

We mock the neo4j ``AsyncDriver`` so the suite runs without a live
Neo4j. The executor's contract — classify, run, format, classify-errors,
never raise — is what we lock down here.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.graph.neo4j.error_classifier import GraphErrorCategory
from src.graph.neo4j.query_executor import execute_cypher
from src.graph.safety.classifier import GraphQuerySafetyLevel


# ── Mock driver helpers ──────────────────────────────────────────────────


class _AsyncIterRecords:
    """Async iterator over a list of dicts, each wrapped to expose ``data()``."""

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
    """Build a fake ``AsyncResult`` that supports both ``async for`` and ``consume()``."""
    iterable = _AsyncIterRecords(records)

    summary = MagicMock()
    summary.notifications = notifications or []

    # We need ``result`` to look like an async iterator AND have ``consume()``.
    class _Result:
        def __aiter__(self):
            return iterable.__aiter__()

        async def consume(self):
            return summary

    return _Result()


def _make_driver(*, run_side_effect=None, run_return=None, slow_seconds=None):
    session = MagicMock()
    if slow_seconds is not None:
        async def slow_run(*args, **kwargs):
            await asyncio.sleep(slow_seconds)
            return run_return
        session.run = AsyncMock(side_effect=slow_run)
    elif run_side_effect is not None:
        session.run = AsyncMock(side_effect=run_side_effect)
    else:
        session.run = AsyncMock(return_value=run_return)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    driver = MagicMock()
    driver.session = MagicMock(return_value=session_cm)
    return driver, session


# ── Safety gate ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_write_query_blocked_with_reason():
    driver, _ = _make_driver(run_return=_make_result([]))
    result = await execute_cypher(driver, "CREATE (n:User {name: 'Alice'})")
    assert result.success is False
    assert result.safety_level == GraphQuerySafetyLevel.WRITE
    assert result.blocked_reason
    assert "read-only" in result.blocked_reason.lower()
    # Driver session should never have been opened.
    driver.session.assert_not_called()


@pytest.mark.asyncio
async def test_dangerous_query_blocked():
    driver, _ = _make_driver(run_return=_make_result([]))
    result = await execute_cypher(driver, "DROP DATABASE x")
    assert result.success is False
    assert result.safety_level == GraphQuerySafetyLevel.DANGEROUS


@pytest.mark.asyncio
async def test_unknown_query_blocked():
    driver, _ = _make_driver(run_return=_make_result([]))
    result = await execute_cypher(driver, "")
    assert result.success is False
    assert result.safety_level == GraphQuerySafetyLevel.UNKNOWN


# ── Happy path ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_query_succeeds_and_returns_table():
    driver, session = _make_driver(
        run_return=_make_result([{"name": "Alice"}, {"name": "Bob"}])
    )
    result = await execute_cypher(driver, "MATCH (u:User) RETURN u.name AS name")
    assert result.success is True
    assert result.safety_level == GraphQuerySafetyLevel.READ_ONLY
    assert result.record_count == 2
    assert result.formatted is not None
    assert result.formatted.table_columns == ["name"]
    assert result.formatted.table_rows == [["Alice"], ["Bob"]]
    assert result.formatted.has_graph is False


@pytest.mark.asyncio
async def test_session_opens_with_read_access_constant():
    """Even with allow_writes=True (post-MVP), sessions must be READ in 25.3."""
    from neo4j import READ_ACCESS

    driver, _ = _make_driver(run_return=_make_result([{"c": 1}]))
    await execute_cypher(driver, "MATCH (n) RETURN count(n) AS c")
    driver.session.assert_called_once()
    kwargs = driver.session.call_args.kwargs
    assert kwargs.get("default_access_mode") == READ_ACCESS


@pytest.mark.asyncio
async def test_database_name_passed_through():
    driver, _ = _make_driver(run_return=_make_result([{"x": 1}]))
    await execute_cypher(
        driver, "MATCH (n) RETURN 1 AS x", database_name="neo4j-prod"
    )
    kwargs = driver.session.call_args.kwargs
    assert kwargs["database"] == "neo4j-prod"


# ── Record cap ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_max_records_caps_and_flags_truncated():
    records = [{"i": i} for i in range(50)]
    driver, _ = _make_driver(run_return=_make_result(records))
    result = await execute_cypher(
        driver, "MATCH (n) RETURN n.i AS i", max_records=10
    )
    assert result.success is True
    assert result.record_count == 10
    assert result.formatted.truncated is True


# ── Timeout ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_query_timeout_returns_classified_error():
    driver, _ = _make_driver(
        slow_seconds=0.5, run_return=_make_result([])
    )
    result = await execute_cypher(
        driver, "MATCH (n) RETURN n", query_timeout_s=0.1
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.category == GraphErrorCategory.TIMEOUT


# ── Driver errors ────────────────────────────────────────────────────────


class _FakeAuthError(Exception):
    pass


# Give it the right class name for the heuristic.
_FakeAuthError.__name__ = "AuthError"


@pytest.mark.asyncio
async def test_auth_error_classified():
    driver, _ = _make_driver(run_side_effect=_FakeAuthError("bad creds"))
    result = await execute_cypher(driver, "MATCH (n) RETURN n")
    assert result.success is False
    assert result.error is not None
    assert result.error.category == GraphErrorCategory.AUTH


@pytest.mark.asyncio
async def test_unknown_driver_error_does_not_raise():
    """Anything that's not asyncio.TimeoutError must be caught."""
    driver, _ = _make_driver(run_side_effect=RuntimeError("kaboom"))
    result = await execute_cypher(driver, "MATCH (n) RETURN n")
    assert result.success is False
    assert result.error is not None
    # The category may be UNKNOWN — what matters is we didn't raise.
    assert result.error.user_message


# ── Server warnings ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_server_notifications_surface_in_warnings():
    note = {"title": "Deprecated syntax", "description": "Use MATCH (n) instead."}
    driver, _ = _make_driver(
        run_return=_make_result([{"x": 1}], notifications=[note])
    )
    result = await execute_cypher(driver, "MATCH (n) RETURN 1 AS x")
    assert result.success is True
    assert any("Deprecated" in w for w in result.server_warnings)
