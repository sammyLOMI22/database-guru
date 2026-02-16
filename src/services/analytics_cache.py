"""Analytics Cache Service (Phase 19.2).

Two-tier cache for computed statistics and detected patterns:
- Local: TTLCache (in-memory, fast, per-process)
- Remote: Redis (optional, shared across processes)

The cache eliminates redundant computation when the same result set
is analyzed multiple times (e.g., same query re-run, or narrative
generation after chart analysis).
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class AnalyticsCache:
    """Two-tier analytics result cache (local TTLCache + optional Redis)."""

    def __init__(
        self,
        maxsize: int = 100,
        ttl: int = 3_600,
        redis_ttl: int = 86_400,
    ):
        """Initialize the analytics cache.

        Args:
            maxsize: Maximum entries in local cache
            ttl: Local cache TTL in seconds (default: 1 hour)
            redis_ttl: Redis cache TTL in seconds (default: 24 hours)
        """
        self._local: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._redis_ttl = redis_ttl

    def _get_redis(self):
        """Lazily get Redis cache, returning None if unavailable."""
        try:
            from src.cache.redis_client import get_redis_cache
            redis = get_redis_cache()
            if redis and redis.redis:
                return redis
        except Exception:
            pass
        return None

    # =====================================================================
    # Result hash
    # =====================================================================

    @staticmethod
    def compute_result_hash(results: List[Dict[str, Any]]) -> str:
        """Compute a fingerprint hash of a result set for cache keying.

        Uses column names, row count, and first/last row values to create
        a short hash that identifies the result set.
        """
        if not results:
            return "empty"
        try:
            first_row = results[0]
            last_row = results[-1] if len(results) > 1 else {}
            fingerprint = {
                "columns": sorted(first_row.keys()),
                "count": len(results),
                "first": {k: str(v) for k, v in list(first_row.items())[:5]},
                "last": {k: str(v) for k, v in list(last_row.items())[:5]},
            }
            return hashlib.md5(
                json.dumps(fingerprint, sort_keys=True).encode()
            ).hexdigest()[:16]
        except Exception:
            return "error"

    # =====================================================================
    # Statistics cache
    # =====================================================================

    async def get_statistics(
        self, result_hash: str, database_type: str
    ) -> Optional[Dict]:
        """Get cached statistics for a result set."""
        key = f"analytics:stats:{database_type}:{result_hash}"

        # Check local cache first
        if key in self._local:
            return self._local[key]

        # Check Redis
        redis = self._get_redis()
        if redis:
            try:
                data = await redis.get(key)
                if data is not None:
                    self._local[key] = data
                    return data
            except Exception as e:
                logger.debug(f"Redis stats lookup failed: {e}")

        return None

    async def set_statistics(
        self, result_hash: str, database_type: str, stats: Dict
    ) -> None:
        """Cache computed statistics."""
        key = f"analytics:stats:{database_type}:{result_hash}"
        self._local[key] = stats

        redis = self._get_redis()
        if redis:
            try:
                await redis.set(key, stats, ttl=self._redis_ttl)
            except Exception as e:
                logger.debug(f"Redis stats write failed: {e}")

    # =====================================================================
    # Patterns cache
    # =====================================================================

    async def get_patterns(self, result_hash: str) -> Optional[Dict]:
        """Get cached pattern detection results."""
        key = f"analytics:patterns:{result_hash}"

        if key in self._local:
            return self._local[key]

        redis = self._get_redis()
        if redis:
            try:
                data = await redis.get(key)
                if data is not None:
                    self._local[key] = data
                    return data
            except Exception as e:
                logger.debug(f"Redis patterns lookup failed: {e}")

        return None

    async def set_patterns(self, result_hash: str, patterns: Dict) -> None:
        """Cache pattern detection results."""
        key = f"analytics:patterns:{result_hash}"
        self._local[key] = patterns

        redis = self._get_redis()
        if redis:
            try:
                await redis.set(key, patterns, ttl=self._redis_ttl)
            except Exception as e:
                logger.debug(f"Redis patterns write failed: {e}")

    # =====================================================================
    # Observability
    # =====================================================================

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache size and capacity for monitoring."""
        return {
            "local_size": len(self._local),
            "local_maxsize": self._local.maxsize,
        }


# =============================================================================
# Module singleton
# =============================================================================

_analytics_cache: Optional[AnalyticsCache] = None


def get_analytics_cache() -> AnalyticsCache:
    """Get or create the global analytics cache singleton."""
    global _analytics_cache
    if _analytics_cache is None:
        try:
            from src.config.settings import Settings
            settings = Settings()
            _analytics_cache = AnalyticsCache(
                maxsize=getattr(settings, "ANALYTICS_CACHE_MAXSIZE", 100),
                ttl=getattr(settings, "ANALYTICS_CACHE_TTL", 3600),
                redis_ttl=getattr(settings, "ANALYTICS_CACHE_REDIS_TTL", 86400),
            )
        except Exception:
            _analytics_cache = AnalyticsCache()
    return _analytics_cache
