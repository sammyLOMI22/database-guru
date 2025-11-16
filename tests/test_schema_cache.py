"""
Tests for schema caching functionality

Verifies that schema introspection results are properly cached
and invalidated when needed.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.core.schema_cache import SchemaCache
from src.llm.mapping_cache import reset_mapping_cache, get_mapping_cache


class TestSchemaCache:
    """Test the SchemaCache class"""

    def setup_method(self):
        """Reset cache before each test"""
        reset_mapping_cache()

    @pytest.mark.asyncio
    async def test_get_schema_cache_miss(self):
        """Test getting schema when not in cache (cache miss)"""
        # Mock SchemaInspector
        mock_schema_data = {
            "tables": {"users": {"columns": [{"name": "id"}]}},
            "summary": {"table_count": 1, "total_columns": 1}
        }

        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value
            mock_inspector.get_full_schema = AsyncMock(return_value=mock_schema_data)

            # Mock user_db_session
            mock_session = Mock()

            schema_data = await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session,
                force_refresh=False
            )

            # Should call introspection (cache miss)
            assert mock_inspector.get_full_schema.called
            assert schema_data == mock_schema_data

    @pytest.mark.asyncio
    async def test_get_schema_cache_hit(self):
        """Test getting schema from cache (cache hit)"""
        mock_schema_data = {
            "tables": {"users": {"columns": [{"name": "id"}]}},
            "summary": {"table_count": 1, "total_columns": 1}
        }

        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value
            mock_inspector.get_full_schema = AsyncMock(return_value=mock_schema_data)

            mock_session = Mock()

            # First call - cache miss
            schema_data1 = await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session
            )

            # Second call - should hit cache
            schema_data2 = await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session
            )

            # Should only call introspection once
            assert mock_inspector.get_full_schema.call_count == 1
            assert schema_data1 == schema_data2

    @pytest.mark.asyncio
    async def test_get_schema_force_refresh(self):
        """Test force refresh bypasses cache"""
        mock_schema_data = {
            "tables": {"users": {"columns": [{"name": "id"}]}},
            "summary": {"table_count": 1, "total_columns": 1}
        }

        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value
            mock_inspector.get_full_schema = AsyncMock(return_value=mock_schema_data)

            mock_session = Mock()

            # First call - cache miss
            await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session
            )

            # Second call with force_refresh - should bypass cache
            await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session,
                force_refresh=True
            )

            # Should call introspection twice (no cache hit on second call)
            assert mock_inspector.get_full_schema.call_count == 2

    def test_invalidate_schema(self):
        """Test invalidating schema cache for specific connection"""
        cache = get_mapping_cache()

        # Add some cached schemas
        cache.set("schema:1:test_db", {"tables": {}}, ttl=300)
        cache.set("schema:2:other_db", {"tables": {}}, ttl=300)

        # Invalidate connection 1
        result = SchemaCache.invalidate_schema(connection_id=1, connection_name="test_db")

        assert result is True
        assert cache.get("schema:1:test_db") is None
        assert cache.get("schema:2:other_db") is not None

    def test_invalidate_schema_not_cached(self):
        """Test invalidating schema that isn't cached"""
        result = SchemaCache.invalidate_schema(connection_id=999)

        # Should return False (nothing was invalidated)
        assert result is False

    def test_invalidate_all_schemas(self):
        """Test invalidating all schema caches"""
        cache = get_mapping_cache()

        # Add multiple cached schemas
        cache.set("schema:1:db1", {"tables": {}}, ttl=300)
        cache.set("schema:2:db2", {"tables": {}}, ttl=300)
        cache.set("schema:3:db3", {"tables": {}}, ttl=300)
        cache.set("other_cache_key", "value", ttl=300)

        # Invalidate all schemas
        count = SchemaCache.invalidate_all_schemas()

        # Should invalidate all 3 schema keys
        assert count == 3
        assert cache.get("schema:1:db1") is None
        assert cache.get("schema:2:db2") is None
        assert cache.get("schema:3:db3") is None
        assert cache.get("other_cache_key") == "value"

    @pytest.mark.asyncio
    async def test_schema_cache_with_custom_ttl(self):
        """Test caching schema with custom TTL"""
        mock_schema_data = {
            "tables": {},
            "summary": {"table_count": 0, "total_columns": 0}
        }

        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value
            mock_inspector.get_full_schema = AsyncMock(return_value=mock_schema_data)

            mock_session = Mock()

            # Cache with custom TTL
            await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session,
                ttl=600  # 10 minutes
            )

            # Verify it was cached (by getting it again without calling inspector)
            cache = get_mapping_cache()
            cached_data = cache.get("schema:1:test_db")

            assert cached_data is not None
            assert cached_data == mock_schema_data

    @pytest.mark.asyncio
    async def test_schema_cache_with_different_connections(self):
        """Test that different connections have separate cache entries"""
        mock_schema_data_1 = {
            "tables": {"users": {}},
            "summary": {"table_count": 1, "total_columns": 0}
        }
        mock_schema_data_2 = {
            "tables": {"products": {}},
            "summary": {"table_count": 1, "total_columns": 0}
        }

        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value

            # Different return values for different calls
            mock_inspector.get_full_schema = AsyncMock(
                side_effect=[mock_schema_data_1, mock_schema_data_2]
            )

            mock_session = Mock()

            # Cache schema for connection 1
            schema_1 = await SchemaCache.get_schema(
                connection_id=1,
                connection_name="db1",
                user_db_session=mock_session
            )

            # Cache schema for connection 2
            schema_2 = await SchemaCache.get_schema(
                connection_id=2,
                connection_name="db2",
                user_db_session=mock_session
            )

            # Should be different schemas
            assert schema_1 != schema_2
            assert "users" in schema_1["tables"]
            assert "products" in schema_2["tables"]

    @pytest.mark.asyncio
    async def test_schema_cache_preserves_samples_flag(self):
        """Test that include_samples parameter is passed through"""
        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value
            mock_inspector.get_full_schema = AsyncMock(
                return_value={"tables": {}, "summary": {"table_count": 0, "total_columns": 0}}
            )

            mock_session = Mock()

            # Call with include_samples=False
            await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session,
                include_samples=False
            )

            # Verify get_full_schema was called with include_samples=False
            call_args = mock_inspector.get_full_schema.call_args
            assert call_args.kwargs['include_samples'] is False

    @pytest.mark.asyncio
    async def test_cache_key_format(self):
        """Test that cache keys follow expected format"""
        cache = get_mapping_cache()

        # Manually create a cache entry
        cache.set("schema:42:my_database", {"tables": {}}, ttl=300)

        # Verify pattern matching works for invalidation
        count = SchemaCache.invalidate_schema(connection_id=42)

        assert count == 1

    def test_invalidate_schema_pattern_matching(self):
        """Test that pattern invalidation works correctly"""
        cache = get_mapping_cache()

        # Create multiple entries for same connection but different names
        cache.set("schema:1:db_v1", {"tables": {}}, ttl=300)
        cache.set("schema:1:db_v2", {"tables": {}}, ttl=300)
        cache.set("schema:2:other_db", {"tables": {}}, ttl=300)

        # Invalidate all schemas for connection 1
        result = SchemaCache.invalidate_schema(connection_id=1)

        # Should return True (at least one entry was invalidated)
        assert result is True
        assert cache.get("schema:1:db_v1") is None
        assert cache.get("schema:1:db_v2") is None
        assert cache.get("schema:2:other_db") is not None


class TestSchemaCacheIntegration:
    """Integration tests for schema cache with actual components"""

    def setup_method(self):
        """Reset cache before each test"""
        reset_mapping_cache()

    @pytest.mark.asyncio
    async def test_cache_statistics_tracking(self):
        """Test that cache statistics are properly tracked"""
        mock_schema_data = {
            "tables": {},
            "summary": {"table_count": 0, "total_columns": 0}
        }

        with patch('src.core.schema_cache.SchemaInspector') as MockInspector:
            mock_inspector = MockInspector.return_value
            mock_inspector.get_full_schema = AsyncMock(return_value=mock_schema_data)

            mock_session = Mock()

            # First call - cache miss
            await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session
            )

            # Second call - cache hit
            await SchemaCache.get_schema(
                connection_id=1,
                connection_name="test_db",
                user_db_session=mock_session
            )

            # Check cache stats
            cache = get_mapping_cache()
            stats = cache.get_stats()

            assert stats["total_hits"] >= 1
            assert stats["total_misses"] >= 1
            assert stats["total_sets"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
