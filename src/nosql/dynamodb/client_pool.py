"""DynamoDB client pool using aioboto3.

Auth is mapped from DatabaseConnection fields:
  username -> AWS access_key_id
  password_encrypted -> AWS secret_access_key
  host -> AWS region
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from src.database.models import DatabaseConnection
from src.nosql.base import NoSQLClientPoolMixin

logger = logging.getLogger(__name__)


class DynamoDBClientPool(NoSQLClientPoolMixin):
    """Singleton pool managing aioboto3 sessions for DynamoDB."""

    _instance: Optional["DynamoDBClientPool"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._sessions: Dict[int, Tuple["aioboto3.Session", str, datetime]] = {}
        self._pool_dict = self._sessions

    @classmethod
    async def get_instance(cls) -> "DynamoDBClientPool":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_session(self, connection: DatabaseConnection):
        """Get or create an aioboto3 Session for the given connection.

        Returns an aioboto3.Session (use as async context manager for client).
        """
        import aioboto3

        self._cleanup_stale()

        conn_id = connection.id
        region = connection.host or "us-east-1"

        if conn_id in self._sessions:
            session, _, _ = self._sessions[conn_id]
            self._sessions[conn_id] = (session, region, self._now())
            return session, region

        session = aioboto3.Session(
            aws_access_key_id=connection.username,
            aws_secret_access_key=connection.password_encrypted,
            region_name=region,
        )

        self._sessions[conn_id] = (session, region, self._now())
        self._enforce_max_size()
        logger.info(f"Created DynamoDB session for connection {conn_id} ({region})")
        return session, region

    async def evict(self, connection_id: int) -> None:
        if connection_id in self._sessions:
            self._sessions.pop(connection_id)
            logger.info(f"Evicted DynamoDB session for connection {connection_id}")

    async def close_all(self) -> None:
        """Close all sessions."""
        self._sessions.clear()
        logger.info("Closed all DynamoDB sessions")
