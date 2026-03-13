"""MongoDB client pool using motor's AsyncIOMotorClient.

Motor clients have built-in connection pooling, so this module manages
client lifecycle (creation, caching, eviction) rather than individual connections.
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import quote_plus

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.database.models import DatabaseConnection
from src.nosql.base import NoSQLClientPoolMixin

logger = logging.getLogger(__name__)


class MongoClientPool(NoSQLClientPoolMixin):
    """Singleton pool of motor AsyncIOMotorClient instances, keyed by connection_id."""

    _instance: Optional["MongoClientPool"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._clients: Dict[int, Tuple[AsyncIOMotorClient, str, datetime]] = {}
        self._pool_dict = self._clients

    @classmethod
    async def get_instance(cls) -> "MongoClientPool":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_client(
        self, connection: DatabaseConnection
    ) -> Tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
        """Get or create a motor client for the given connection.

        Returns:
            Tuple of (client, database) for the connection.
        """
        self._cleanup_stale()

        conn_id = connection.id

        if conn_id in self._clients:
            client, db_name, _ = self._clients[conn_id]
            self._clients[conn_id] = (client, db_name, self._now())
            return client, client[db_name]

        # Build connection URI
        uri = self._build_uri(connection)
        client = AsyncIOMotorClient(
            uri,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )

        db_name = connection.database_name
        self._clients[conn_id] = (client, db_name, self._now())
        self._enforce_max_size()
        logger.info(f"Created motor client for connection {conn_id} ({db_name})")

        return client, client[db_name]

    def _build_uri(self, connection: DatabaseConnection) -> str:
        """Build MongoDB connection URI from connection details.

        Credentials are URL-encoded to handle special characters (@, :, /, %).
        """
        host = connection.host or "localhost"
        port = connection.port or 27017
        username = connection.username
        password = connection.password_encrypted or ""

        if username and password:
            encoded_user = quote_plus(username)
            encoded_pass = quote_plus(password)
            return f"mongodb://{encoded_user}:{encoded_pass}@{host}:{port}/{connection.database_name}"
        return f"mongodb://{host}:{port}/{connection.database_name}"

    def _close_entry_sync(self, key: int, entry: Tuple) -> None:
        client, _, _ = entry
        client.close()

    async def evict(self, connection_id: int) -> None:
        """Close and remove a client from the pool."""
        if connection_id in self._clients:
            client, _, _ = self._clients.pop(connection_id)
            client.close()
            logger.info(f"Evicted motor client for connection {connection_id}")

    async def close_all(self) -> None:
        """Close all clients."""
        for conn_id, (client, _, _) in list(self._clients.items()):
            client.close()
        self._clients.clear()
        logger.info("Closed all motor clients")
