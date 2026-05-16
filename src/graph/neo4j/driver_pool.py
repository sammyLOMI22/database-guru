"""Neo4j async driver pool keyed by ``DatabaseConnection.id`` (Phase 25).

Phase 25.1 only needs short-lived drivers for the connection-test endpoint,
but we already provide a long-lived pool so Phase 25.2+ (introspection,
query execution) can reuse it without rewriting lifecycle management.

The official ``neo4j`` Python driver maintains its own internal connection
pool per ``Driver`` instance, so this module is responsible for **driver
caching**, not socket-level pooling.

Caching semantics (mirrors ``src/nosql/base.NoSQLClientPoolMixin``):

* Drivers are evicted after ``IDLE_TTL_SECONDS`` of inactivity.
* Pool capped at ``MAX_POOL_SIZE``; LRU eviction enforces the cap.
* Driver is closed on eviction and on application shutdown.

Phase 25.1 entry point: :func:`build_driver` — a one-shot driver factory used
by the connection-test endpoint that *does not* register in the pool, so an
unverified connection never leaks resources on retry.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)

# Pool tunables — keep aligned with src/nosql/base.py constants so operators
# only learn one mental model.
MAX_POOL_SIZE = 20
IDLE_TTL_SECONDS = 1800  # 30 minutes


# URIs whose scheme already encodes TLS. When the user toggles "encrypted=False"
# in the UI but supplies one of these schemes, the driver rejects ``encrypted``
# kwarg as conflicting — so we strip it.
_TLS_URI_SCHEMES = ("neo4j+s://", "neo4j+ssc://", "bolt+s://", "bolt+ssc://")


def uri_scheme_forces_tls(uri: str) -> bool:
    """Return True when the URI scheme already encodes encryption.

    Used by callers to decide whether to pass ``encrypted=`` to the driver
    (the driver raises ``ConfigurationError`` if both are set).
    """
    if not uri:
        return False
    return uri.lower().startswith(_TLS_URI_SCHEMES)


def sanitize_uri_for_log(uri: str) -> str:
    """Strip embedded ``user:pass@`` from a URI so it's safe to log."""
    if not uri:
        return ""
    # bolt://user:pass@host:port → bolt://***@host:port
    return re.sub(r"(?P<scheme>\w+(?:\+\w+)?://)([^@/]+@)", r"\g<scheme>***@", uri)


def build_driver(
    uri: str,
    username: str,
    password: str,
    *,
    encrypted: bool = False,
    connection_timeout_s: float = 5.0,
) -> AsyncDriver:
    """Construct (but do not pool) an async Neo4j driver.

    Caller is responsible for ``await driver.close()``. Used by the connection
    test endpoint, which never wants a long-lived driver for an unverified
    connection.

    Args:
        uri: Bolt URI (``bolt://``, ``neo4j://``, ``neo4j+s://``, ...).
        username: Neo4j user.
        password: Neo4j password (never logged).
        encrypted: When True, request TLS. Ignored if the URI scheme already
            encodes TLS (see :func:`uri_scheme_forces_tls`).
        connection_timeout_s: Bolt connect timeout (seconds).

    Raises:
        ValueError: ``uri`` is empty or whitespace.
    """
    if not uri or not uri.strip():
        raise ValueError("Neo4j URI is required")

    kwargs: dict = {
        "auth": (username, password),
        "connection_timeout": connection_timeout_s,
    }
    if not uri_scheme_forces_tls(uri):
        kwargs["encrypted"] = bool(encrypted)

    logger.debug(
        "Building Neo4j driver for %s (encrypted=%s)",
        sanitize_uri_for_log(uri),
        encrypted or uri_scheme_forces_tls(uri),
    )
    return AsyncGraphDatabase.driver(uri, **kwargs)


class Neo4jDriverPool:
    """Singleton cache of async Neo4j drivers keyed by connection_id.

    Phase 25.1 leaves this in place for forward use; the connection-test
    endpoint deliberately uses :func:`build_driver` instead so unverified
    credentials never enter the pool.

    Thread/coroutine safety: ``_singleton_lock`` (class-level) guards
    instance creation. ``_mutation_lock`` (per-instance) guards every read
    that's followed by a write — without it two coroutines could race past
    the cache-miss check in :meth:`get` and both call :func:`build_driver`,
    silently leaking one of the drivers. All mutations to ``_drivers`` go
    through the lock.
    """

    _instance: Optional["Neo4jDriverPool"] = None
    _singleton_lock = asyncio.Lock()

    def __init__(self) -> None:
        # connection_id → (driver, last_used)
        self._drivers: Dict[int, Tuple[AsyncDriver, datetime]] = {}
        self._mutation_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "Neo4jDriverPool":
        async with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    async def get(
        self,
        connection_id: int,
        uri: str,
        username: str,
        password: str,
        *,
        encrypted: bool = False,
    ) -> AsyncDriver:
        async with self._mutation_lock:
            await self._cleanup_stale_locked()

            entry = self._drivers.get(connection_id)
            if entry is not None:
                driver, _ = entry
                self._drivers[connection_id] = (driver, self._now())
                return driver

            driver = build_driver(uri, username, password, encrypted=encrypted)
            self._drivers[connection_id] = (driver, self._now())
            await self._enforce_max_size_locked()
            logger.info("Cached Neo4j driver for connection %s", connection_id)
            return driver

    async def close(self, connection_id: int) -> None:
        """Close and remove a single driver. Idempotent."""
        async with self._mutation_lock:
            await self._close_locked(connection_id)

    async def close_all(self) -> None:
        """Close every cached driver. Call on application shutdown."""
        async with self._mutation_lock:
            ids = list(self._drivers.keys())
            for cid in ids:
                await self._close_locked(cid)

    # ── Locked helpers (callers MUST hold _mutation_lock) ───────────────

    async def _close_locked(self, connection_id: int) -> None:
        entry = self._drivers.pop(connection_id, None)
        if entry is None:
            return
        driver, _ = entry
        try:
            await driver.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing Neo4j driver %s: %s", connection_id, exc)

    async def _cleanup_stale_locked(self) -> None:
        now = self._now()
        stale = [
            cid
            for cid, (_, last_used) in self._drivers.items()
            if (now - last_used).total_seconds() > IDLE_TTL_SECONDS
        ]
        for cid in stale:
            await self._close_locked(cid)
            logger.info("Evicted idle Neo4j driver for connection %s", cid)

    async def _enforce_max_size_locked(self) -> None:
        while len(self._drivers) > MAX_POOL_SIZE:
            lru_id = min(self._drivers, key=lambda c: self._drivers[c][1])
            await self._close_locked(lru_id)
            logger.info("Evicted LRU Neo4j driver for connection %s (pool full)", lru_id)


__all__ = [
    "IDLE_TTL_SECONDS",
    "MAX_POOL_SIZE",
    "Neo4jDriverPool",
    "build_driver",
    "sanitize_uri_for_log",
    "uri_scheme_forces_tls",
]
