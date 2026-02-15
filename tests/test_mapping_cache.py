"""
Tests for mapping cache functionality

Verifies that the in-memory cache correctly stores and retrieves
mapping data, handles TTL expiration, and properly invalidates entries.
"""
import pytest
import time
import asyncio
from src.llm.mapping_cache import MappingCache, get_mapping_cache, reset_mapping_cache


class TestMappingCache:
    """Test the MappingCache class"""

    def setup_method(self):
        """Reset cache before each test"""
        reset_mapping_cache()

    def test_cache_set_and_get(self):
        """Test basic set and get operations"""
        cache = MappingCache()

        # Set a value
        test_data = [{"id": 1, "name": "test"}]
        cache.set("test_key", test_data, ttl=60)

        # Get the value
        result = cache.get("test_key")

        assert result == test_data
        assert cache.get_stats()["total_hits"] == 1
        assert cache.get_stats()["total_misses"] == 0

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = MappingCache()

        result = cache.get("nonexistent_key")

        assert result is None
        assert cache.get_stats()["total_hits"] == 0
        assert cache.get_stats()["total_misses"] == 1

    def test_cache_ttl_expiration(self):
        """Test that entries expire after TTL"""
        cache = MappingCache()

        # Set with 1 second TTL
        cache.set("expiring_key", "test_value", ttl=1)

        # Should be available immediately
        assert cache.get("expiring_key") == "test_value"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("expiring_key") is None

    def test_cache_invalidate_single_key(self):
        """Test invalidating a single cache entry"""
        cache = MappingCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Invalidate key1
        result = cache.invalidate("key1")

        assert result is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cache_invalidate_pattern(self):
        """Test pattern-based invalidation with wildcards"""
        cache = MappingCache()

        # Set multiple related keys
        cache.set("col_mappings:db1:postgres:users", [{"id": 1}])
        cache.set("col_mappings:db1:postgres:orders", [{"id": 2}])
        cache.set("col_mappings:db1:mysql:products", [{"id": 3}])
        cache.set("tbl_mappings:db1:postgres", [{"id": 4}])

        # Invalidate all postgres column mappings for db1
        count = cache.invalidate_pattern("col_mappings:db1:postgres:*")

        assert count == 2
        assert cache.get("col_mappings:db1:postgres:users") is None
        assert cache.get("col_mappings:db1:postgres:orders") is None
        assert cache.get("col_mappings:db1:mysql:products") == [{"id": 3}]
        assert cache.get("tbl_mappings:db1:postgres") == [{"id": 4}]

    def test_cache_invalidate_all_mappings(self):
        """Test invalidating all mapping types"""
        cache = MappingCache()

        cache.set("col_mappings:db1:postgres:users", [1])
        cache.set("tbl_mappings:db1:postgres", [2])
        cache.set("result_patterns:all:0.6", [3])
        cache.set("pattern_count", 10)
        cache.set("other_cache_key", "should remain")

        count = cache.invalidate_all_mappings()

        # All mapping-related keys should be invalidated
        assert cache.get("col_mappings:db1:postgres:users") is None
        assert cache.get("tbl_mappings:db1:postgres") is None
        assert cache.get("result_patterns:all:0.6") is None
        assert cache.get("pattern_count") is None

        # Other keys should remain
        assert cache.get("other_cache_key") == "should remain"

    def test_cache_clear(self):
        """Test clearing entire cache"""
        cache = MappingCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
        assert cache.get_stats()["total_entries"] == 0

    def test_cache_cleanup_expired(self):
        """Test manual cleanup of expired entries"""
        cache = MappingCache()

        # Set some entries with different TTLs
        cache.set("short_ttl", "value1", ttl=1)
        cache.set("long_ttl", "value2", ttl=60)

        # Wait for short TTL to expire
        time.sleep(1.1)

        # Cleanup
        removed_count = cache.cleanup_expired()

        assert removed_count == 1
        assert cache.get("short_ttl") is None
        assert cache.get("long_ttl") == "value2"

    def test_cache_statistics(self):
        """Test cache statistics tracking"""
        cache = MappingCache(default_ttl=300)

        # Perform various operations
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss
        cache.invalidate("key2")

        stats = cache.get_stats()

        assert stats["total_entries"] == 1  # key1 remains
        assert stats["total_hits"] == 2
        assert stats["total_misses"] == 1
        assert stats["total_sets"] == 2
        assert stats["total_invalidations"] == 1
        assert stats["hit_rate_percent"] == 66.67  # 2 hits / 3 total requests
        assert stats["default_ttl"] == 300

    def test_cache_entry_info(self):
        """Test getting detailed entry information"""
        cache = MappingCache()

        test_data = [{"id": 1}, {"id": 2}]
        cache.set("test_key", test_data, ttl=120)

        # Immediately get info
        info = cache.get_entry_info("test_key")

        assert info is not None
        assert info["key"] == "test_key"
        assert info["ttl"] == 120
        assert info["age_seconds"] < 1.0
        assert info["remaining_ttl_seconds"] > 119.0
        assert info["hits"] == 0
        assert info["is_expired"] is False
        assert info["data_type"] == "list"
        assert info["data_size"] == 2

    def test_cache_hit_counting(self):
        """Test that cache hits are properly counted per entry"""
        cache = MappingCache()

        cache.set("key1", "value1")

        # Access key1 multiple times
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")

        info = cache.get_entry_info("key1")

        assert info["hits"] == 3

    def test_cache_thread_safety_simulation(self):
        """Test that cache operations don't raise exceptions with concurrent access"""
        cache = MappingCache()

        # Simulate concurrent operations (not truly parallel in CPython due to GIL)
        for i in range(100):
            cache.set(f"key_{i % 10}", f"value_{i}")
            cache.get(f"key_{i % 5}")
            if i % 3 == 0:
                cache.invalidate(f"key_{i % 10}")

        # Should complete without exceptions
        stats = cache.get_stats()
        assert stats["total_sets"] == 100

    def test_singleton_get_mapping_cache(self):
        """Test that get_mapping_cache returns singleton instance"""
        cache1 = get_mapping_cache()
        cache2 = get_mapping_cache()

        assert cache1 is cache2

        # Set on one, get on other
        cache1.set("test_key", "test_value")
        assert cache2.get("test_key") == "test_value"

    def test_reset_mapping_cache(self):
        """Test resetting the global cache instance"""
        cache1 = get_mapping_cache()
        cache1.set("key", "value")

        reset_mapping_cache()

        cache2 = get_mapping_cache()

        # Should be a new instance
        assert cache2.get("key") is None

    def test_cache_with_different_data_types(self):
        """Test caching different data types"""
        cache = MappingCache()

        # List
        cache.set("list_key", [1, 2, 3])
        assert cache.get("list_key") == [1, 2, 3]

        # Dict
        cache.set("dict_key", {"a": 1, "b": 2})
        assert cache.get("dict_key") == {"a": 1, "b": 2}

        # String
        cache.set("string_key", "test string")
        assert cache.get("string_key") == "test string"

        # None
        cache.set("none_key", None)
        assert cache.get("none_key") is None  # Ambiguous with cache miss!

        # Integer
        cache.set("int_key", 42)
        assert cache.get("int_key") == 42

    def test_cache_key_format_consistency(self):
        """Test that cache keys follow expected format"""
        cache = MappingCache()

        # Column mappings
        col_key = "col_mappings:my_db:postgres:users"
        cache.set(col_key, [{"id": 1}])
        assert cache.get(col_key) == [{"id": 1}]

        # Table mappings
        tbl_key = "tbl_mappings:my_db:postgres"
        cache.set(tbl_key, [{"id": 2}])
        assert cache.get(tbl_key) == [{"id": 2}]

        # Result patterns
        pattern_key = "result_patterns:all:0.6"
        cache.set(pattern_key, [{"id": 3}])
        assert cache.get(pattern_key) == [{"id": 3}]

    def test_cache_default_ttl(self):
        """Test that default TTL is used when not specified"""
        cache = MappingCache(default_ttl=120)

        cache.set("test_key", "test_value")  # No TTL specified

        info = cache.get_entry_info("test_key")
        assert info["ttl"] == 120

    def test_cache_override_default_ttl(self):
        """Test overriding default TTL on specific entries"""
        cache = MappingCache(default_ttl=300)

        cache.set("default_ttl_key", "value1")  # Uses default 300
        cache.set("custom_ttl_key", "value2", ttl=60)  # Override to 60

        info1 = cache.get_entry_info("default_ttl_key")
        info2 = cache.get_entry_info("custom_ttl_key")

        assert info1["ttl"] == 300
        assert info2["ttl"] == 60


class TestMappingCacheIntegration:
    """Integration tests for cache with mapper classes"""

    def setup_method(self):
        """Reset cache before each test"""
        reset_mapping_cache()

    @pytest.mark.asyncio
    async def test_cache_reduces_database_queries(self):
        """
        Test that cache actually reduces database queries
        (This would require mocking the mapper classes and counting DB calls)
        """
        # This is a placeholder for a more comprehensive integration test
        # In a real scenario, we would:
        # 1. Mock the database session to count execute() calls
        # 2. Call mapper methods multiple times with same parameters
        # 3. Verify that DB is only hit once (first time)
        # 4. Verify cache is hit on subsequent calls
        pass

    def test_cache_logging(self):
        """Test that cache operations are logged appropriately"""
        import logging

        target_logger = logging.getLogger("src.llm.mapping_cache")
        old_level = target_logger.level
        old_disabled = target_logger.disabled
        target_logger.disabled = False
        target_logger.setLevel(logging.DEBUG)

        # Use a dedicated handler to capture log records reliably
        records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = CaptureHandler()
        handler.setLevel(logging.DEBUG)
        target_logger.addHandler(handler)

        cache = MappingCache()

        try:
            cache.set("test_key", "test_value")
            cache.get("test_key")  # Hit
            cache.get("missing_key")  # Miss
            cache.invalidate_pattern("test_*")

            messages = [r.getMessage() for r in records]
            assert any("Cache HIT" in m for m in messages), f"Expected 'Cache HIT' in {messages}"
            assert any("Cache MISS" in m for m in messages), f"Expected 'Cache MISS' in {messages}"
            assert any("Cache SET" in m for m in messages), f"Expected 'Cache SET' in {messages}"
            assert any("INVALIDATE PATTERN" in m for m in messages), f"Expected 'INVALIDATE PATTERN' in {messages}"
        finally:
            target_logger.removeHandler(handler)
            target_logger.setLevel(old_level)
            target_logger.disabled = old_disabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
