"""Cache decorators for Database Guru"""
import functools
import logging
from typing import Callable, Optional, Any
import hashlib
import json

from src.cache.redis_client import get_redis_cache

logger = logging.getLogger(__name__)


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "func",
    include_args: bool = True,
):
    """
    Decorator to cache function results in Redis

    Args:
        ttl: Time-to-live in seconds (None = use default)
        key_prefix: Prefix for cache key
        include_args: Whether to include function arguments in cache key

    Example:
        @cached(ttl=3600, key_prefix="user")
        async def get_user(user_id: str):
            return await fetch_user_from_db(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_redis_cache()

            # Generate cache key
            if include_args:
                # Create stable key from function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_data = ":".join(key_parts)
                key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
                cache_key = f"{key_prefix}:{key_hash}"
            else:
                cache_key = f"{key_prefix}:{func.__name__}"

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_result

            # Execute function
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def cache_query_result(ttl: Optional[int] = 3600):
    """
    Decorator specifically for caching natural language query results

    Args:
        ttl: Time-to-live in seconds

    Example:
        @cache_query_result(ttl=1800)
        async def process_query(nl_query: str):
            return {"sql": "SELECT ...", "results": [...]}
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(nl_query: str, *args, **kwargs):
            cache = get_redis_cache()

            # Generate cache key from query
            query_hash = hashlib.sha256(nl_query.encode()).hexdigest()[:16]
            cache_key = f"query:{query_hash}"

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached result for query: {nl_query[:50]}...")
                # Increment hit counter
                await cache.increment(f"query:hits:{query_hash}")
                return cached_result

            # Execute function
            logger.info(f"Processing new query: {nl_query[:50]}...")
            result = await func(nl_query, *args, **kwargs)

            # Store in cache if result is valid
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
                logger.debug(f"Cached query result: {cache_key}")

            return result

        return wrapper

    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator to invalidate cache after function execution

    Args:
        key_pattern: Pattern of keys to invalidate (e.g., "user:*")

    Example:
        @invalidate_cache("user:*")
        async def update_user(user_id: str, data: dict):
            return await db.update(user_id, data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)

            # Invalidate cache
            cache = get_redis_cache()
            deleted = await cache.clear_pattern(key_pattern)
            logger.info(f"Invalidated {deleted} cache entries matching: {key_pattern}")

            return result

        return wrapper

    return decorator


class CacheNamespace:
    """
    Context manager for namespaced cache operations

    Example:
        async with CacheNamespace("user:123") as cache_ns:
            await cache_ns.set("profile", user_profile)
            profile = await cache_ns.get("profile")
    """

    def __init__(self, namespace: str):
        self.namespace = namespace
        self.cache = get_redis_cache()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def _namespaced_key(self, key: str) -> str:
        """Add namespace prefix to key"""
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from namespaced cache"""
        return await self.cache.get(self._namespaced_key(key))

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in namespaced cache"""
        return await self.cache.set(self._namespaced_key(key), value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from namespaced cache"""
        return await self.cache.delete(self._namespaced_key(key))

    async def clear(self) -> int:
        """Clear all keys in this namespace"""
        pattern = f"{self.namespace}:*"
        return await self.cache.clear_pattern(pattern)
