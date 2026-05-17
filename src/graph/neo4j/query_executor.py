"""Execute a single Cypher statement under safety + resource caps (Phase 25.3).

Composes the safety classifier, the driver session, and the result
formatter. The executor:

* Refuses any classification above ``READ_ONLY`` (MVP — controlled by
  ``GRAPH_ALLOW_WRITES``).
* Opens the session with ``default_access_mode=READ_ACCESS`` so even
  if the classifier missed something the server will refuse the write.
* Enforces ``GRAPH_QUERY_TIMEOUT_MS`` via ``asyncio.wait_for`` and
  ``GRAPH_MAX_RECORDS`` by stopping the record stream once the cap is
  reached.
* Catches every driver exception and runs it through
  :func:`classify_error` so callers get a structured payload.

Returns an :class:`ExecutionResult`; never raises into the API layer.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from neo4j import READ_ACCESS, AsyncDriver

from src.graph.neo4j.error_classifier import (
    ClassifiedError,
    GraphErrorCategory,
    classify_error,
)
from src.graph.result_formatter import FormattedResult, format_records
from src.graph.safety.classifier import (
    GraphQuerySafetyLevel,
    SafetyClassification,
    classify,
    explain_blocked,
)

logger = logging.getLogger(__name__)


DEFAULT_QUERY_TIMEOUT_S = 10.0
DEFAULT_MAX_RECORDS = 1000
DEFAULT_MAX_VIZ_NODES = 200
DEFAULT_MAX_VIZ_EDGES = 500


@dataclass
class ExecutionResult:
    """Structured outcome of a Cypher execution.

    The executor always returns this object — never raises. ``success``
    is the single field callers should branch on.
    """

    success: bool
    cypher: str
    safety: SafetyClassification
    formatted: Optional[FormattedResult] = None
    error: Optional[ClassifiedError] = None
    execution_time_ms: float = 0.0
    record_count: int = 0
    blocked_reason: Optional[str] = None
    server_warnings: List[str] = field(default_factory=list)

    @property
    def safety_level(self) -> GraphQuerySafetyLevel:
        return self.safety.level


# ── Public API ────────────────────────────────────────────────────────────


async def execute_cypher(
    driver: AsyncDriver,
    cypher: str,
    *,
    database_name: str = "neo4j",
    query_timeout_s: float = DEFAULT_QUERY_TIMEOUT_S,
    max_records: int = DEFAULT_MAX_RECORDS,
    max_viz_nodes: int = DEFAULT_MAX_VIZ_NODES,
    max_viz_edges: int = DEFAULT_MAX_VIZ_EDGES,
    allow_apoc: bool = False,
    allow_writes: bool = False,
    parameters: Optional[Dict[str, Any]] = None,
) -> ExecutionResult:
    """Run ``cypher`` against ``driver`` with safety + caps applied.

    Args:
        driver: Pooled neo4j ``AsyncDriver``.
        cypher: Raw statement (parameters substituted server-side).
        database_name: Target database — usually ``"neo4j"``.
        query_timeout_s: Per-statement wall-clock cap.
        max_records: Hard cap on records pulled from the result stream.
        max_viz_nodes/max_viz_edges: Caps passed to the formatter.
        allow_apoc: Surfaces ``GRAPH_ALLOW_APOC`` to the safety classifier.
        allow_writes: When False (MVP), anything classified above
            READ_ONLY is blocked. The flag exists for the post-MVP
            "confirm write" flow but is not wired to the API yet.
        parameters: Cypher parameters dict (preferred over string interp).
    """
    # 1) Classify first — cheap, no I/O.
    safety = classify(cypher, allow_apoc=allow_apoc)
    if safety.level != GraphQuerySafetyLevel.READ_ONLY and not allow_writes:
        reason = explain_blocked(safety.level, safety.reasons)
        return ExecutionResult(
            success=False,
            cypher=cypher,
            safety=safety,
            blocked_reason=reason,
        )

    # 2) Execute under a wall-clock timeout. The driver itself takes a
    #    per-transaction ``timeout`` kwarg, but ``wait_for`` is the only
    #    way to cap the whole flow (driver timeout doesn't include
    #    streaming time).
    start = time.perf_counter()
    try:
        records, record_count, truncated, server_warnings = await asyncio.wait_for(
            _run_and_stream(
                driver=driver,
                cypher=cypher,
                parameters=parameters or {},
                database_name=database_name,
                max_records=max_records,
            ),
            timeout=max(0.5, query_timeout_s),
        )
    except asyncio.TimeoutError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        classified = classify_error(exc)
        return ExecutionResult(
            success=False,
            cypher=cypher,
            safety=safety,
            error=classified,
            execution_time_ms=elapsed,
        )
    except Exception as exc:  # noqa: BLE001
        # Important: log the full trace server-side but never echo
        # ``str(exc)`` to the API caller — the driver embeds URIs.
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception("Cypher execution failed: %s", type(exc).__name__)
        classified = classify_error(exc)
        return ExecutionResult(
            success=False,
            cypher=cypher,
            safety=safety,
            error=classified,
            execution_time_ms=elapsed,
        )

    elapsed = (time.perf_counter() - start) * 1000

    formatted = format_records(
        records,
        max_nodes=max_viz_nodes,
        max_edges=max_viz_edges,
        truncated_records=truncated,
    )

    return ExecutionResult(
        success=True,
        cypher=cypher,
        safety=safety,
        formatted=formatted,
        execution_time_ms=elapsed,
        record_count=record_count,
        server_warnings=server_warnings,
    )


# ── Internals ─────────────────────────────────────────────────────────────


async def _run_and_stream(
    *,
    driver: AsyncDriver,
    cypher: str,
    parameters: Dict[str, Any],
    database_name: str,
    max_records: int,
):
    """Open a READ session, stream up to ``max_records`` records, return
    ``(records, count, truncated, warnings)``.

    Always uses ``default_access_mode=READ_ACCESS`` — even when the
    caller passes ``allow_writes=True`` MVP only reads. Will change in a
    future phase when write-mode lands.
    """
    async with driver.session(
        database=database_name,
        default_access_mode=READ_ACCESS,
    ) as session:
        result = await session.run(cypher, parameters)
        records: List[Dict[str, Any]] = []
        truncated = False

        # Stream record by record so we can stop early at the cap.
        async for record in result:
            if len(records) >= max_records:
                truncated = True
                break
            records.append(record.data())

        # ``consume()`` returns a ``ResultSummary`` with notifications
        # (Neo4j warnings) and counters. We only surface notifications
        # so the UI can hint at deprecations or missing labels.
        warnings_out: List[str] = []
        try:
            summary = await result.consume()
            notifications = getattr(summary, "notifications", None) or []
            for note in notifications:
                title = (
                    note.get("title") if isinstance(note, dict) else getattr(note, "title", None)
                )
                desc = (
                    note.get("description")
                    if isinstance(note, dict)
                    else getattr(note, "description", None)
                )
                if title and desc:
                    warnings_out.append(f"{title}: {desc}")
                elif desc:
                    warnings_out.append(str(desc))
        except Exception:  # noqa: BLE001
            # Consume failures are non-fatal — records are already collected.
            pass

        return records, len(records), truncated, warnings_out


__all__ = [
    "DEFAULT_MAX_RECORDS",
    "DEFAULT_MAX_VIZ_EDGES",
    "DEFAULT_MAX_VIZ_NODES",
    "DEFAULT_QUERY_TIMEOUT_S",
    "ExecutionResult",
    "execute_cypher",
]
