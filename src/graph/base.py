"""Abstract base classes for graph database support (Phase 25).

Each graph provider implements :class:`GraphAdapter`. The MVP ships a single
adapter (Neo4j); the Protocol exists so additional providers can drop in
without touching call sites in ``src/api/endpoints/graph.py`` or the chat
pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable


class GraphProvider(str, Enum):
    """Supported graph providers. MVP: NEO4J only."""

    NEO4J = "neo4j"


@dataclass
class ConnectionTestResult:
    """Result of a :meth:`GraphAdapter.test_connection` call.

    Designed to be JSON-serializable for direct return from the API.
    """

    success: bool
    provider: str
    message: str
    server_version: Optional[str] = None
    database_name: Optional[str] = None
    edition: Optional[str] = None
    latency_ms: Optional[float] = None
    error_code: Optional[str] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "provider": self.provider,
            "message": self.message,
            "server_version": self.server_version,
            "database_name": self.database_name,
            "edition": self.edition,
            "latency_ms": self.latency_ms,
            "error_code": self.error_code,
            "details": self.details,
        }


@runtime_checkable
class GraphAdapter(Protocol):
    """Provider-agnostic graph database adapter."""

    provider: GraphProvider

    async def test_connection(
        self,
        uri: str,
        username: str,
        password: str,
        database_name: Optional[str] = None,
        encrypted: bool = False,
        timeout_ms: int = 5000,
    ) -> ConnectionTestResult:
        """Open a short-lived session and verify connectivity + auth.

        Implementations MUST:

        * Never log the password or full credentialed URI.
        * Use a server-side timeout no larger than ``timeout_ms``.
        * Run only read-only / metadata queries (no graph mutation).
        * Return a :class:`ConnectionTestResult` even on failure — exceptions
          are converted to ``success=False`` with a human-readable ``message``.
        """
        ...

    # Phases 25.2+ extend the Protocol with introspect_schema(),
    # execute_query(), explain_query(), etc. Intentionally omitted from MVP
    # so 25.1 stays self-contained.


__all__ = [
    "ConnectionTestResult",
    "GraphAdapter",
    "GraphProvider",
]
