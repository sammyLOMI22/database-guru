"""Elasticsearch client pool using AsyncElasticsearch."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from src.database.models import DatabaseConnection
from src.nosql.base import NoSQLClientPoolMixin

logger = logging.getLogger(__name__)


class ElasticsearchClientPool(NoSQLClientPoolMixin):
    """Singleton pool of AsyncElasticsearch client instances."""

    _instance: Optional["ElasticsearchClientPool"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._clients: Dict[int, Tuple["AsyncElasticsearch", datetime]] = {}
        self._pool_dict = self._clients

    @classmethod
    async def get_instance(cls) -> "ElasticsearchClientPool":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_client(self, connection: DatabaseConnection):
        """Get or create an AsyncElasticsearch client."""
        from elasticsearch import AsyncElasticsearch

        self._cleanup_stale()

        conn_id = connection.id

        if conn_id in self._clients:
            client, _ = self._clients[conn_id]
            self._clients[conn_id] = (client, self._now())
            return client

        host = connection.host or "localhost"
        port = connection.port or 9200

        # Honour an explicit scheme in the host field (e.g. "https://my-cluster").
        # Default to plain HTTP so both HTTP-with-auth and HTTPS-without-auth work.
        if host.startswith("http://") or host.startswith("https://"):
            url = f"{host}:{port}"
        else:
            url = f"http://{host}:{port}"

        auth = None
        if connection.username and connection.password_encrypted:
            auth = (connection.username, connection.password_encrypted)

        client = AsyncElasticsearch(
            url,
            basic_auth=auth,
            request_timeout=10,
        )

        self._clients[conn_id] = (client, self._now())
        self._enforce_max_size()
        logger.info(f"Created Elasticsearch client for connection {conn_id} ({url})")
        return client

    def _close_entry_sync(self, key: int, entry: Tuple) -> None:
        # ES close() is async; schedule fire-and-forget
        client, _ = entry
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(client.close())
        except RuntimeError:
            pass

    async def evict(self, connection_id: int) -> None:
        if connection_id in self._clients:
            client, _ = self._clients.pop(connection_id)
            await client.close()
            logger.info(f"Evicted Elasticsearch client for connection {connection_id}")

    async def close_all(self) -> None:
        for conn_id, (client, _) in list(self._clients.items()):
            await client.close()
        self._clients.clear()
