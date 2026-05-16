"""Neo4j schema introspection (Phase 25.2).

Runs the spec §5.2 procedures (``db.labels``, ``db.relationshipTypes``,
``db.schema.nodeTypeProperties``, ``db.schema.relTypeProperties``,
``SHOW INDEXES``, ``SHOW CONSTRAINTS``) plus sampled pattern + count
discovery, then converts the raw rows into a :class:`GraphSchema` via
:mod:`src.graph.schema.normalizer`.

Design constraints:

* **Per-query timeout** — every Cypher call is wrapped in
  ``asyncio.wait_for`` so a single slow procedure cannot blow the entire
  introspection budget.
* **Partial failure tolerance** — when an individual probe fails we append
  a warning to ``GraphSchema.warnings`` and continue, rather than aborting.
  Operators inspecting a degraded DB still get the labels/relationships we
  did manage to read.
* **Large-graph guard** — per-label ``count(n)`` queries are skipped when
  the count cap is reached; the schema explorer still shows the label, just
  without an exact size.
* **No mutations** — every query runs in a ``READ`` session so the
  introspection path is safe even against connections the user has flagged
  ``read_only=True`` at the driver level.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from neo4j import AsyncDriver

from src.graph.schema.normalizer import (
    GraphIndex,
    GraphNodeLabel,
    GraphRelationshipType,
    GraphSchema,
    build_indexed_property_lookup,
    normalize_constraints,
    normalize_indexes,
    normalize_node_type_properties,
    normalize_patterns,
    normalize_rel_type_properties,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Per-query timeout fallback; caller can override via constructor.
DEFAULT_QUERY_TIMEOUT_S = 5.0
DEFAULT_OVERALL_TIMEOUT_S = 30.0
DEFAULT_COUNT_CAP = 10_000_000
# Cap on how many labels we per-label-count; very wide schemas degrade gracefully.
MAX_LABELS_TO_COUNT = 100
# Cap on how many relationship patterns we sample.
MAX_PATTERN_SAMPLES = 100


# ── Public API ────────────────────────────────────────────────────────────


class Neo4jSchemaInspector:
    """Introspect a Neo4j database into a :class:`GraphSchema`.

    Stateless: a single instance can be reused across connections — all
    per-call state (warnings, timing) lives in the local scope of
    :meth:`introspect`.
    """

    def __init__(
        self,
        driver: AsyncDriver,
        database_name: str = "neo4j",
        *,
        query_timeout_s: float = DEFAULT_QUERY_TIMEOUT_S,
        overall_timeout_s: float = DEFAULT_OVERALL_TIMEOUT_S,
        count_cap: int = DEFAULT_COUNT_CAP,
    ):
        self.driver = driver
        self.database_name = database_name or "neo4j"
        self.query_timeout_s = max(0.5, query_timeout_s)
        self.overall_timeout_s = max(self.query_timeout_s, overall_timeout_s)
        self.count_cap = max(0, count_cap)

    async def introspect(self) -> GraphSchema:
        """Run the full introspection pipeline and return a GraphSchema."""
        start = time.perf_counter()
        warnings: List[str] = []

        # Server version (best-effort, non-fatal)
        server_version, edition = await self._fetch_server_components(warnings)

        # Phase 1: cheap parallel probes — labels, rel types, indexes, constraints,
        # node-property rows, rel-property rows.
        (
            labels_rows,
            rel_type_rows,
            index_rows,
            constraint_rows,
            node_prop_rows,
            rel_prop_rows,
        ) = await asyncio.gather(
            self._safe_query(
                "labels",
                "CALL db.labels() YIELD label RETURN label",
                warnings,
                default=[],
            ),
            self._safe_query(
                "relationshipTypes",
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
                warnings,
                default=[],
            ),
            self._safe_query(
                "indexes",
                "SHOW INDEXES YIELD name, entityType, labelsOrTypes, properties, type, state",
                warnings,
                default=[],
            ),
            self._safe_query(
                "constraints",
                "SHOW CONSTRAINTS YIELD name, entityType, labelsOrTypes, properties, type",
                warnings,
                default=[],
            ),
            self._safe_query(
                "nodeTypeProperties",
                "CALL db.schema.nodeTypeProperties() "
                "YIELD nodeType, propertyName, propertyTypes, mandatory "
                "RETURN nodeType, propertyName, propertyTypes, mandatory",
                warnings,
                default=[],
            ),
            self._safe_query(
                "relTypeProperties",
                "CALL db.schema.relTypeProperties() "
                "YIELD relType, propertyName, propertyTypes, mandatory "
                "RETURN relType, propertyName, propertyTypes, mandatory",
                warnings,
                default=[],
            ),
        )

        # Normalize indexes & constraints first so we can mark indexed properties.
        indexes = normalize_indexes(index_rows)
        constraints = normalize_constraints(constraint_rows)

        node_indexed = build_indexed_property_lookup(indexes, "NODE")
        rel_indexed = build_indexed_property_lookup(indexes, "RELATIONSHIP")

        label_properties = normalize_node_type_properties(node_prop_rows, node_indexed)
        rel_properties = normalize_rel_type_properties(rel_prop_rows, rel_indexed)

        # Build labels (start with names from db.labels(), augmented with discovered
        # properties; labels seen in property rows but not db.labels() are appended
        # so we never lose data).
        label_names = sorted({row["label"] for row in labels_rows if row.get("label")})
        for label in label_properties.keys():
            if label not in label_names:
                label_names.append(label)
        labels = [
            GraphNodeLabel(
                name=name,
                properties=label_properties.get(name, []),
            )
            for name in label_names
        ]

        rel_type_names = sorted(
            {row["relationshipType"] for row in rel_type_rows if row.get("relationshipType")}
        )
        for rel_name in rel_properties.keys():
            if rel_name not in rel_type_names:
                rel_type_names.append(rel_name)
        relationships = [
            GraphRelationshipType(
                name=name,
                properties=rel_properties.get(name, []),
            )
            for name in rel_type_names
        ]

        # Phase 2: counts + patterns (subject to budget).
        elapsed = time.perf_counter() - start
        remaining = self.overall_timeout_s - elapsed
        if remaining > 0:
            await self._populate_counts(labels, warnings, deadline_s=remaining)

        elapsed = time.perf_counter() - start
        remaining = self.overall_timeout_s - elapsed
        if remaining > 0:
            patterns = await self._sample_patterns(warnings)
        else:
            patterns = []
            warnings.append(
                "Skipped relationship pattern sampling — overall introspection timeout exceeded."
            )

        schema = GraphSchema(
            provider="neo4j",
            database_name=self.database_name,
            labels=labels,
            relationships=relationships,
            patterns=patterns,
            indexes=indexes,
            constraints=constraints,
            warnings=warnings,
            server_version=server_version,
            edition=edition,
        )

        total_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Neo4j introspection on %r: labels=%d rels=%d patterns=%d indexes=%d "
            "constraints=%d warnings=%d (%.0f ms)",
            self.database_name,
            len(labels),
            len(relationships),
            len(patterns),
            len(indexes),
            len(constraints),
            len(warnings),
            total_ms,
        )
        return schema

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _fetch_server_components(
        self, warnings: List[str]
    ) -> tuple[Optional[str], Optional[str]]:
        rows = await self._safe_query(
            "components",
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions, edition LIMIT 1",
            warnings,
            default=[],
        )
        if not rows:
            return None, None
        row = rows[0]
        versions = row.get("versions") or []
        version = versions[0] if versions else None
        return version, row.get("edition")

    async def _populate_counts(
        self,
        labels: List[GraphNodeLabel],
        warnings: List[str],
        *,
        deadline_s: float,
    ) -> None:
        """Fill in ``estimated_count`` for the first ``MAX_LABELS_TO_COUNT`` labels.

        Uses a hard deadline so this phase can't dominate the overall budget.
        """
        if not labels:
            return
        deadline = time.monotonic() + deadline_s
        skipped = 0
        counted = 0

        for label in labels[:MAX_LABELS_TO_COUNT]:
            if time.monotonic() >= deadline:
                skipped = len(labels) - counted
                break
            # Backtick-escape the label name to support spaces / Unicode labels.
            safe_label = label.name.replace("`", "``")
            cypher = f"MATCH (n:`{safe_label}`) RETURN count(n) AS c"
            rows = await self._safe_query(
                f"count({label.name})",
                cypher,
                warnings,
                default=[],
                log_level=logging.DEBUG,
            )
            if rows:
                count = rows[0].get("c")
                if isinstance(count, int):
                    if self.count_cap and count > self.count_cap:
                        warnings.append(
                            f"Label {label.name!r}: count > cap ({self.count_cap:,}); "
                            f"reporting as cap value."
                        )
                        label.estimated_count = self.count_cap
                    else:
                        label.estimated_count = count
                    counted += 1

        if len(labels) > MAX_LABELS_TO_COUNT:
            warnings.append(
                f"Counted first {MAX_LABELS_TO_COUNT} labels of {len(labels)} — "
                "remaining labels have no estimated_count."
            )
        if skipped > 0:
            warnings.append(
                f"Count probe deadline exceeded; skipped {skipped} labels."
            )

    async def _sample_patterns(self, warnings: List[str]) -> list:
        """Sample (source)-[rel]->(target) patterns, ordered by frequency."""
        cypher = (
            "MATCH (a)-[r]->(b) "
            "WITH labels(a) AS sa, type(r) AS rt, labels(b) AS tb, count(*) AS c "
            "RETURN sa, rt, tb, c "
            "ORDER BY c DESC "
            f"LIMIT {MAX_PATTERN_SAMPLES}"
        )
        rows = await self._safe_query(
            "patterns",
            cypher,
            warnings,
            default=[],
        )
        return normalize_patterns(rows)

    async def _safe_query(
        self,
        op_label: str,
        cypher: str,
        warnings: List[str],
        *,
        default: T,
        log_level: int = logging.INFO,
    ) -> T:
        """Run a single read-only Cypher statement under a timeout.

        Returns ``default`` and appends a human-readable warning if the call
        fails or times out. Never raises into the caller — partial failure
        is a first-class outcome of introspection.
        """
        try:
            return await asyncio.wait_for(
                self._run_records(cypher),
                timeout=self.query_timeout_s,
            )  # type: ignore[return-value]
        except asyncio.TimeoutError:
            warnings.append(
                f"{op_label}: query timed out after {self.query_timeout_s:.1f}s."
            )
            logger.log(log_level, "Neo4j introspection timeout: %s", op_label)
            return default
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{op_label}: query failed — {exc}")
            logger.log(log_level, "Neo4j introspection error (%s): %s", op_label, exc)
            return default

    async def _run_records(self, cypher: str) -> List[Dict[str, Any]]:
        """Execute a Cypher statement in a READ session and return record dicts."""
        async with self.driver.session(
            database=self.database_name,
            default_access_mode="r",  # type: ignore[arg-type]
        ) as session:
            result = await session.run(cypher)
            records = await result.data()
            return list(records)


# ── Functional façade ─────────────────────────────────────────────────────


async def introspect(
    driver: AsyncDriver,
    database_name: str = "neo4j",
    *,
    query_timeout_s: float = DEFAULT_QUERY_TIMEOUT_S,
    overall_timeout_s: float = DEFAULT_OVERALL_TIMEOUT_S,
    count_cap: int = DEFAULT_COUNT_CAP,
) -> GraphSchema:
    """Convenience wrapper — instantiates the inspector and runs it."""
    inspector = Neo4jSchemaInspector(
        driver=driver,
        database_name=database_name,
        query_timeout_s=query_timeout_s,
        overall_timeout_s=overall_timeout_s,
        count_cap=count_cap,
    )
    return await inspector.introspect()


__all__ = [
    "DEFAULT_COUNT_CAP",
    "DEFAULT_OVERALL_TIMEOUT_S",
    "DEFAULT_QUERY_TIMEOUT_S",
    "MAX_LABELS_TO_COUNT",
    "MAX_PATTERN_SAMPLES",
    "Neo4jSchemaInspector",
    "introspect",
]
