"""MongoDB client pool using motor's AsyncIOMotorClient.

Motor clients have built-in connection pooling, so this module manages
client lifecycle (creation, caching, eviction) rather than individual connections.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.database.models import DatabaseConnection

logger = logging.getLogger(__name__)


class MongoClientPool:
    """Singleton pool of motor AsyncIOMotorClient instances, keyed by connection_id."""

    _instance: Optional["MongoClientPool"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._clients: Dict[int, Tuple[AsyncIOMotorClient, str, datetime]] = {}

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
        conn_id = connection.id

        if conn_id in self._clients:
            client, db_name, _ = self._clients[conn_id]
            self._clients[conn_id] = (client, db_name, datetime.utcnow())
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
        self._clients[conn_id] = (client, db_name, datetime.utcnow())
        logger.info(f"Created motor client for connection {conn_id} ({db_name})")

        return client, client[db_name]

    def _build_uri(self, connection: DatabaseConnection) -> str:
        """Build MongoDB connection URI from connection details."""
        host = connection.host or "localhost"
        port = connection.port or 27017
        username = connection.username
        password = connection.password_encrypted  # TODO: decrypt

        if username and password:
            return f"mongodb://{username}:{password}@{host}:{port}/{connection.database_name}"
        return f"mongodb://{host}:{port}/{connection.database_name}"

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
