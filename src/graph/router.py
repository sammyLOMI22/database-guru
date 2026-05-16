"""Graph router — dispatch by ``database_type`` to the right adapter (Phase 25).

For MVP this is trivial (Neo4j only) but the indirection lets future providers
(Memgraph, Neptune) plug in without touching the API layer.
"""

from __future__ import annotations

from typing import Optional

from src.graph.base import ConnectionTestResult, GraphAdapter, GraphProvider

# Lowercase database_type strings that identify a graph database.
GRAPH_DATABASE_TYPES = {"neo4j"}


def is_graph(database_type: Optional[str]) -> bool:
    """Return True if ``database_type`` should be routed through this package.

    Compared lowercase so callers don't need to normalize.
    """
    if not database_type:
        return False
    return database_type.lower() in GRAPH_DATABASE_TYPES


def get_adapter(database_type: str) -> GraphAdapter:
    """Return the adapter instance for the given graph database type.

    Raises:
        ValueError: when ``database_type`` is not a known graph provider.
    """
    dt = database_type.lower()
    if dt == GraphProvider.NEO4J.value:
        # Local import keeps the optional ``neo4j`` driver dependency lazy —
        # importing this module never forces the Bolt driver to load.
        from src.graph.neo4j.handler import Neo4jGraphAdapter

        return Neo4jGraphAdapter()

    raise ValueError(f"No graph adapter registered for database_type={database_type!r}")


async def test_connection(
    database_type: str,
    uri: str,
    username: str,
    password: str,
    database_name: Optional[str] = None,
    encrypted: bool = False,
    timeout_ms: int = 5000,
) -> ConnectionTestResult:
    """Provider-agnostic connection test. See :meth:`GraphAdapter.test_connection`."""
    adapter = get_adapter(database_type)
    return await adapter.test_connection(
        uri=uri,
        username=username,
        password=password,
        database_name=database_name,
        encrypted=encrypted,
        timeout_ms=timeout_ms,
    )


__all__ = ["GRAPH_DATABASE_TYPES", "is_graph", "get_adapter", "test_connection"]
