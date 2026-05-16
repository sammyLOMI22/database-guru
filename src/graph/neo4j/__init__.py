"""Neo4j adapter — Bolt protocol via the official async driver (Phase 25)."""

from src.graph.neo4j.handler import Neo4jGraphAdapter  # noqa: F401

__all__ = ["Neo4jGraphAdapter"]
