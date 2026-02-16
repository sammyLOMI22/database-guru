"""Tests for Phase 19.2: Analytics Caching Layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.analytics_cache import AnalyticsCache, get_analytics_cache


# =============================================================================
# Result Hash Tests
# =============================================================================

class TestResultHash:
    """Test result hash computation for cache keying."""

    def test_empty_results_returns_empty(self):
        assert AnalyticsCache.compute_result_hash([]) == "empty"

    def test_deterministic_hash(self):
        results = [{"name": "Alice", "value": 100}, {"name": "Bob", "value": 200}]
        h1 = AnalyticsCache.compute_result_hash(results)
        h2 = AnalyticsCache.compute_result_hash(results)
        assert h1 == h2

    def test_different_results_different_hash(self):
        r1 = [{"name": "Alice", "value": 100}]
        r2 = [{"name": "Bob", "value": 200}]
        assert AnalyticsCache.compute_result_hash(r1) != AnalyticsCache.compute_result_hash(r2)

    def test_hash_is_16_chars(self):
        results = [{"a": 1, "b": 2}]
        h = AnalyticsCache.compute_result_hash(results)
        assert len(h) == 16

    def test_different_row_count_different_hash(self):
        r1 = [{"x": 1}]
        r2 = [{"x": 1}, {"x": 2}]
        assert AnalyticsCache.compute_result_hash(r1) != AnalyticsCache.compute_result_hash(r2)

    def test_single_row_no_last_row(self):
        """Single-row result should still produce a valid hash."""
        results = [{"col": "val"}]
        h = AnalyticsCache.compute_result_hash(results)
        assert isinstance(h, str) and len(h) == 16

    def test_non_serializable_values(self):
        """Non-serializable values should not crash, returns error hash."""
        results = [{"obj": object()}]
        h = AnalyticsCache.compute_result_hash(results)
        # str() conversion in fingerprint handles it, or falls back to "error"
        assert isinstance(h, str)


# =============================================================================
# Local Cache Tests
# =============================================================================

class TestLocalCache:
    """Test in-memory TTLCache tier."""

    @pytest.fixture
    def cache(self):
        return AnalyticsCache(maxsize=10, ttl=3600, redis_ttl=86400)

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache):
        result = await cache.get_statistics("nonexistent", "sqlite")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get_statistics(self, cache):
        stats = {"row_count": 42, "revenue": {"type": "numeric", "avg": 100}}
        await cache.set_statistics("hash1", "postgresql", stats)
        result = await cache.get_statistics("hash1", "postgresql")
        assert result == stats

    @pytest.mark.asyncio
    async def test_different_db_type_different_key(self, cache):
        stats_pg = {"row_count": 10}
        stats_mysql = {"row_count": 20}
        await cache.set_statistics("hash1", "postgresql", stats_pg)
        await cache.set_statistics("hash1", "mysql", stats_mysql)
        assert await cache.get_statistics("hash1", "postgresql") == stats_pg
        assert await cache.get_statistics("hash1", "mysql") == stats_mysql

    @pytest.mark.asyncio
    async def test_patterns_cache_miss(self, cache):
        assert await cache.get_patterns("missing") is None

    @pytest.mark.asyncio
    async def test_set_then_get_patterns(self, cache):
        patterns = {"trend": "upward", "anomalies": 2}
        await cache.set_patterns("hash2", patterns)
        result = await cache.get_patterns("hash2")
        assert result == patterns

    def test_cache_stats(self, cache):
        stats = cache.get_cache_stats()
        assert stats["local_size"] == 0
        assert stats["local_maxsize"] == 10

    @pytest.mark.asyncio
    async def test_cache_stats_after_insert(self, cache):
        await cache.set_statistics("h1", "pg", {"row_count": 1})
        await cache.set_patterns("h1", {"trend": "up"})
        stats = cache.get_cache_stats()
        assert stats["local_size"] == 2


# =============================================================================
# Redis Fallback Tests
# =============================================================================

class TestRedisFallback:
    """Test that Redis failures gracefully fall back to local-only."""

    @pytest.fixture
    def cache(self):
        return AnalyticsCache(maxsize=10, ttl=3600)

    @pytest.mark.asyncio
    async def test_redis_unavailable_still_works(self, cache):
        """When Redis is unavailable, local cache still functions."""
        with patch.object(cache, "_get_redis", return_value=None):
            await cache.set_statistics("h1", "pg", {"row_count": 5})
            result = await cache.get_statistics("h1", "pg")
            assert result == {"row_count": 5}

    @pytest.mark.asyncio
    async def test_redis_get_error_falls_back(self, cache):
        """When Redis get raises, fall back to local cache."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))
        mock_redis.redis = True

        with patch.object(cache, "_get_redis", return_value=mock_redis):
            # Set locally first
            cache._local["analytics:stats:pg:h1"] = {"row_count": 10}
            result = await cache.get_statistics("h1", "pg")
            # Should get from local since Redis failed
            assert result == {"row_count": 10}

    @pytest.mark.asyncio
    async def test_redis_set_error_does_not_crash(self, cache):
        """When Redis set raises, local cache still stores."""
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(side_effect=Exception("Redis down"))
        mock_redis.redis = True

        with patch.object(cache, "_get_redis", return_value=mock_redis):
            await cache.set_statistics("h2", "pg", {"row_count": 7})
            # Local cache should still have it
            assert cache._local["analytics:stats:pg:h2"] == {"row_count": 7}

    @pytest.mark.asyncio
    async def test_redis_hit_populates_local(self, cache):
        """When Redis returns data, it should populate local cache."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value={"row_count": 99})
        mock_redis.redis = True

        with patch.object(cache, "_get_redis", return_value=mock_redis):
            result = await cache.get_statistics("h3", "sqlite")
            assert result == {"row_count": 99}
            # Should now be in local cache
            assert cache._local["analytics:stats:sqlite:h3"] == {"row_count": 99}


# =============================================================================
# Narrator Integration Tests
# =============================================================================

class TestNarratorIntegration:
    """Test that ResultNarrator integrates with AnalyticsCache."""

    @pytest.mark.asyncio
    async def test_narrator_uses_cache_on_hit(self):
        """Narrator should skip _extract_statistics when cache has data."""
        from src.llm.result_narrator import ResultNarrator

        mock_cache = MagicMock()
        cached_stats = {"row_count": 5, "value": {"type": "numeric", "avg": 150}}
        mock_cache.get_statistics = AsyncMock(return_value=cached_stats)
        mock_cache.set_statistics = AsyncMock()

        narrator = ResultNarrator(
            ollama_client=MagicMock(),
            model="mistral:7b",
            analytics_cache=mock_cache,
        )

        results = [{"value": 100}, {"value": 200}]
        with patch.object(narrator, "_extract_statistics") as mock_extract:
            stats = await narrator._get_or_compute_statistics(results, "postgresql")
            mock_extract.assert_not_called()
            assert stats == cached_stats

    @pytest.mark.asyncio
    async def test_narrator_computes_and_caches_on_miss(self):
        """Narrator should compute and cache statistics on cache miss."""
        from src.llm.result_narrator import ResultNarrator

        mock_cache = MagicMock()
        mock_cache.get_statistics = AsyncMock(return_value=None)
        mock_cache.set_statistics = AsyncMock()

        narrator = ResultNarrator(
            ollama_client=MagicMock(),
            model="mistral:7b",
            analytics_cache=mock_cache,
        )

        results = [{"revenue": 100}, {"revenue": 200}]
        stats = await narrator._get_or_compute_statistics(results, "postgresql")
        assert "row_count" in stats
        mock_cache.set_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_narrator_works_without_cache(self):
        """Narrator should work normally when no cache is available."""
        from src.llm.result_narrator import ResultNarrator

        narrator = ResultNarrator(
            ollama_client=MagicMock(),
            model="mistral:7b",
            analytics_cache=None,
        )
        # Prevent lazy init from finding the singleton
        narrator._analytics_cache = None

        with patch("src.llm.result_narrator.ResultNarrator._get_cache", return_value=None):
            results = [{"revenue": 100}, {"revenue": 200}]
            stats = await narrator._get_or_compute_statistics(results, "sqlite")
            assert "row_count" in stats


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingleton:
    """Test module-level singleton."""

    def test_get_analytics_cache_returns_instance(self):
        import src.services.analytics_cache as mod
        old = mod._analytics_cache
        mod._analytics_cache = None
        try:
            cache = get_analytics_cache()
            assert isinstance(cache, AnalyticsCache)
        finally:
            mod._analytics_cache = old

    def test_get_analytics_cache_returns_same_instance(self):
        import src.services.analytics_cache as mod
        old = mod._analytics_cache
        mod._analytics_cache = None
        try:
            c1 = get_analytics_cache()
            c2 = get_analytics_cache()
            assert c1 is c2
        finally:
            mod._analytics_cache = old
