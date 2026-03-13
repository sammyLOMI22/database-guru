"""Redis client pool using redis.asyncio.

redis-py manages its own internal connection pool, so this module
manages client lifecycle (creation, caching, eviction).
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

import redis.asyncio as aioredis

from src.database.models import DatabaseConnection
from src.nosql.base import NoSQLClientPoolMixin

logger = logging.getLogger(__name__)


class RedisClientPool(NoSQLClientPoolMixin):
    """Singleton pool of async Redis client instances, keyed by connection_id."""

    _instance: Optional["RedisClientPool"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._clients: Dict[int, Tuple[aioredis.Redis, datetime]] = {}
        self._pool_dict = self._clients

    @classmethod
    async def get_instance(cls) -> "RedisClientPool":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_client(self, connection: DatabaseConnection) -> aioredis.Redis:
        """Get or create an async Redis client for the given connection."""
        self._cleanup_stale()

        conn_id = connection.id

        if conn_id in self._clients:
            client, _ = self._clients[conn_id]
            self._clients[conn_id] = (client, self._now())
            return client

        host = connection.host or "localhost"
        port = connection.port or 6379
        password = connection.password_encrypted or None
        db_num = 0
        try:
            db_num = int(connection.database_name)
        except (ValueError, TypeError):
            pass

        client = aioredis.Redis(
            host=host,
            port=port,
            password=password,
            db=db_num,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=10,
        )

        self._clients[conn_id] = (client, self._now())
        self._enforce_max_size()
        logger.info(f"Created Redis client for connection {conn_id} ({host}:{port})")
        return client

    def _close_entry_sync(self, key: int, entry: Tuple) -> None:
        # Redis aclose() is async; schedule fire-and-forget
        client, _ = entry
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(client.aclose())
        except RuntimeError:
            pass  # No event loop — client will be GC'd

    async def evict(self, connection_id: int) -> None:
        """Close and remove a client from the pool."""
        if connection_id in self._clients:
            client, _ = self._clients.pop(connection_id)
            await client.aclose()
            logger.info(f"Evicted Redis client for connection {connection_id}")

    async def close_all(self) -> None:
        """Close all clients."""
        for conn_id, (client, _) in list(self._clients.items()):
            await client.aclose()
        self._clients.clear()
