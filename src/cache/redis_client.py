"""Redis cache client for Database Guru"""
import json
import hashlib
import logging
from typing import Any, Optional
from datetime import timedelta

try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None
    RedisError = Exception
    RedisConnectionError = Exception

from src.config.settings import Settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager with connection pooling"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis: Optional[Redis] = None
        self._connection_pool = None

    async def connect(self):
        """Initialize Redis connection pool"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis module not available - caching disabled")
            return

        if not self.settings.REDIS_URL:
            logger.warning("REDIS_URL not configured - caching disabled")
            return

        try:
            # Parse Redis URL
            redis_url = self.settings.REDIS_URL

            # Create connection pool
            self._connection_pool = aioredis.ConnectionPool.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )

            # Create Redis client
            self.redis = aioredis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self.redis.ping()
            logger.info(f"✅ Redis connected: {redis_url}")

        except RedisConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed (caching disabled): {e}")
            self.redis = None
        except Exception as e:
            logger.warning(f"⚠️ Redis initialization error (caching disabled): {e}")
            self.redis = None

    async def disconnect(self):
        """Close Redis connections"""
        if self.redis:
            await self.redis.close()
            await self._connection_pool.disconnect()
            logger.info("Redis disconnected")

    async def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            if self.redis:
                await self.redis.ping()
                return True
            return False
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        try:
            if not self.redis:
                logger.warning("Redis not connected")
                return None

            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)

            logger.debug(f"Cache miss: {key}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize cache value for key {key}: {e}")
            return None
        except RedisError as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (default: settings.CACHE_TTL)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis:
                logger.warning("Redis not connected")
                return False

            # Use default TTL if not specified
            if ttl is None:
                ttl = self.settings.CACHE_TTL

            # Serialize value to JSON
            serialized = json.dumps(value)

            # Set with expiration
            await self.redis.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True

        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value for key {key}: {e}")
            return False
        except RedisError as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            if not self.redis:
                logger.warning("Redis not connected")
                return False

            result = await self.redis.delete(key)
            logger.debug(f"Cache delete: {key} (deleted: {result > 0})")
            return result > 0

        except RedisError as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            if not self.redis:
                return False

            result = await self.redis.exists(key)
            return result > 0

        except RedisError as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern

        Args:
            pattern: Key pattern (e.g., "query:*")

        Returns:
            Number of keys deleted
        """
        try:
            if not self.redis:
                logger.warning("Redis not connected")
                return 0

            # Scan for matching keys
            deleted_count = 0
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
                deleted_count += 1

            logger.info(f"Cleared {deleted_count} keys matching pattern: {pattern}")
            return deleted_count

        except RedisError as e:
            logger.error(f"Redis clear pattern error for {pattern}: {e}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment, or None on error
        """
        try:
            if not self.redis:
                return None

            result = await self.redis.incrby(key, amount)
            return result

        except RedisError as e:
            logger.error(f"Redis increment error for key {key}: {e}")
            return None

    @staticmethod
    def generate_cache_key(*args, prefix: str = "cache") -> str:
        """
        Generate a cache key from arguments

        Args:
            *args: Arguments to hash
            prefix: Key prefix

        Returns:
            Cache key string
        """
        # Create a stable hash from arguments
        key_data = ":".join(str(arg) for arg in args)
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{key_hash}"


# Global Redis cache instance
_redis_cache: Optional[RedisCache] = None


def get_redis_cache(settings: Optional[Settings] = None) -> RedisCache:
    """Get or create the global Redis cache instance"""
    global _redis_cache

    if _redis_cache is None:
        if settings is None:
            settings = Settings()
        _redis_cache = RedisCache(settings)

    return _redis_cache
