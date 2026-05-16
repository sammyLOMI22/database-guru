"""Graph database support (Phase 25 — Graph Mode).

This package adds graph databases as a first-class database type, beginning
with Neo4j. Mirrors the layout of ``src/nosql`` so future providers
(Memgraph, Neptune, ArangoDB) can drop in alongside the ``neo4j`` submodule.

Public entry points:

* :func:`src.graph.router.is_graph`          — type check for routing.
* :func:`src.graph.router.test_connection`   — adapter-agnostic connection test.
* :class:`src.graph.base.GraphAdapter`       — Protocol every provider implements.
"""

from src.graph.base import (  # noqa: F401
    ConnectionTestResult,
    GraphAdapter,
    GraphProvider,
)
