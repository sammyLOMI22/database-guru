"""Cassandra client pool using cassandra-driver.

The driver is synchronous, so queries are run in a thread pool executor.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from src.database.models import DatabaseConnection

logger = logging.getLogger(__name__)


class CassandraClientPool:
    """Singleton pool of Cassandra Cluster/Session instances."""

    _instance: Optional["CassandraClientPool"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._sessions: Dict[int, Tuple["Session", "Cluster", datetime]] = {}

    @classmethod
    async def get_instance(cls) -> "CassandraClientPool":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_session(self, connection: DatabaseConnection):
        """Get or create a Cassandra session for the given connection.

        Returns a cassandra-driver Session object (sync).
        """
        conn_id = connection.id

        if conn_id in self._sessions:
            session, cluster, _ = self._sessions[conn_id]
            self._sessions[conn_id] = (session, cluster, datetime.utcnow())
            return session

        # Create in thread pool since cassandra-driver is sync
        loop = asyncio.get_running_loop()
        session, cluster = await loop.run_in_executor(
            None, self._create_session, connection
        )

        self._sessions[conn_id] = (session, cluster, datetime.utcnow())
        logger.info(f"Created Cassandra session for connection {conn_id}")
        return session

    def _create_session(self, connection: DatabaseConnection):
        """Create a Cassandra Cluster and Session (sync)."""
        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider

        auth = None
        if connection.username and connection.password_encrypted:
            auth = PlainTextAuthProvider(
                username=connection.username,
                password=connection.password_encrypted,
            )

        cluster = Cluster(
            contact_points=[connection.host or "localhost"],
            port=connection.port or 9042,
            auth_provider=auth,
            connect_timeout=5,
        )

        keyspace = connection.database_name or None
        session = cluster.connect(keyspace)
        return session, cluster

    async def evict(self, connection_id: int) -> None:
        if connection_id in self._sessions:
            session, cluster, _ = self._sessions.pop(connection_id)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, session.shutdown)
            await loop.run_in_executor(None, cluster.shutdown)
            logger.info(f"Evicted Cassandra session for connection {connection_id}")

    async def close_all(self) -> None:
        for conn_id in list(self._sessions.keys()):
            await self.evict(conn_id)
