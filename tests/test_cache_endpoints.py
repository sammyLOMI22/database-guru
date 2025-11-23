"""
Tests for Cache API Endpoints

Tests cover:
- GET /api/cache/stats - Cache statistics
- GET /api/cache/semantic/recent - Recent cached queries
- DELETE /api/cache/semantic - Clear semantic cache
- DELETE /api/cache/llm - Clear LLM cache
- DELETE /api/cache/all - Clear all caches
- DELETE /api/cache/semantic/connection/{id} - Clear connection cache

Part of Phase 3.3: Semantic Caching UI Components
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestCacheEndpoints:
    """Tests for cache API endpoints"""

    @pytest.fixture
    def mock_semantic_cache(self):
        """Create a mock semantic cache"""
        mock_cache = MagicMock()
        mock_cache.get_stats = MagicMock(return_value={
            "total_lookups": 100,
            "total_hits": 50,
            "exact_hits": 20,
            "semantic_hits": 30,
            "misses": 50,
            "hit_rate_percent": 50.0,
            "semantic_hit_rate_percent": 30.0,
            "total_stores": 60,
            "similarity_threshold": 0.85,
            "ttl_seconds": 86400,
            "memory_entries": 25,
        })
        mock_cache.clear = AsyncMock(return_value=25)
        mock_cache.invalidate_connection = AsyncMock(return_value=10)
        mock_cache._memory_entries = {}
        return mock_cache

    @pytest.fixture
    def mock_llm_cache(self):
        """Create a mock LLM cache"""
        mock_cache = MagicMock()
        mock_cache.get_stats = MagicMock(return_value={
            "total_lookups": 80,
            "hits": 45,
            "misses": 35,
            "hit_rate_percent": 56.25,
            "total_stores": 50,
            "similarity_threshold": 0.88,
            "ttl_seconds": 43200,
        })
        mock_cache.clear = AsyncMock(return_value=15)
        return mock_cache

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service"""
        mock_service = MagicMock()
        mock_service.get_stats = MagicMock(return_value={
            "total_requests": 200,
            "cache_hits": 150,
            "cache_hit_rate_percent": 75.0,
            "ollama_calls": 40,
            "tfidf_fallbacks": 10,
            "ollama_available": True,
        })
        return mock_service

    def test_get_cache_stats(self, mock_semantic_cache, mock_llm_cache, mock_embedding_service):
        """Test GET /api/cache/stats returns combined statistics"""
        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache), \
             patch('src.api.endpoints.cache.get_llm_cache', return_value=mock_llm_cache), \
             patch('src.api.endpoints.cache.get_embedding_service', return_value=mock_embedding_service):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/cache/stats")
            assert response.status_code == 200

            data = response.json()
            assert "semantic_cache" in data
            assert "llm_cache" in data
            assert "embedding_service" in data

            # Verify semantic cache stats
            assert data["semantic_cache"]["total_lookups"] == 100
            assert data["semantic_cache"]["hit_rate_percent"] == 50.0
            assert data["semantic_cache"]["semantic_hits"] == 30

            # Verify LLM cache stats
            assert data["llm_cache"]["total_lookups"] == 80
            assert data["llm_cache"]["hit_rate_percent"] == 56.25

            # Verify embedding service stats
            assert data["embedding_service"]["ollama_available"] is True
            assert data["embedding_service"]["cache_hit_rate_percent"] == 75.0

    def test_get_recent_queries_empty(self, mock_semantic_cache):
        """Test GET /api/cache/semantic/recent with empty cache"""
        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/cache/semantic/recent")
            assert response.status_code == 200

            data = response.json()
            assert data["queries"] == []
            assert data["total"] == 0

    def test_get_recent_queries_with_data(self, mock_semantic_cache):
        """Test GET /api/cache/semantic/recent with cached entries"""
        from src.cache.semantic_cache import SemanticCacheEntry

        # Add mock entries
        mock_semantic_cache._memory_entries = {
            "hash1": SemanticCacheEntry(
                question="Show me customers",
                sql="SELECT * FROM customers",
                result={"data": []},
                connection_id=1,
                database_type="postgresql",
                embedding=[0.1] * 512,
                created_at="2025-11-22T10:00:00",
                hits=5,
                last_hit_at="2025-11-22T11:00:00",
            ),
            "hash2": SemanticCacheEntry(
                question="List all orders",
                sql="SELECT * FROM orders",
                result={"data": []},
                connection_id=1,
                database_type="mysql",
                embedding=[0.2] * 512,
                created_at="2025-11-22T09:00:00",
                hits=2,
                last_hit_at=None,
            ),
        }

        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/cache/semantic/recent?limit=10")
            assert response.status_code == 200

            data = response.json()
            assert len(data["queries"]) == 2
            assert data["total"] == 2

            # Should be sorted by created_at (newest first)
            assert data["queries"][0]["question"] == "Show me customers"
            assert data["queries"][0]["hits"] == 5

    def test_get_recent_queries_with_filters(self, mock_semantic_cache):
        """Test GET /api/cache/semantic/recent with connection_id filter"""
        from src.cache.semantic_cache import SemanticCacheEntry

        mock_semantic_cache._memory_entries = {
            "hash1": SemanticCacheEntry(
                question="Query 1",
                sql="SELECT 1",
                result={},
                connection_id=1,
                database_type="postgresql",
                embedding=[],
                created_at="2025-11-22T10:00:00",
                hits=0,
            ),
            "hash2": SemanticCacheEntry(
                question="Query 2",
                sql="SELECT 2",
                result={},
                connection_id=2,
                database_type="mysql",
                embedding=[],
                created_at="2025-11-22T09:00:00",
                hits=0,
            ),
        }

        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            # Filter by connection_id
            response = client.get("/cache/semantic/recent?connection_id=1")
            assert response.status_code == 200
            data = response.json()
            assert len(data["queries"]) == 1
            assert data["queries"][0]["connection_id"] == 1

    @pytest.mark.asyncio
    async def test_clear_semantic_cache(self, mock_semantic_cache):
        """Test DELETE /api/cache/semantic clears semantic cache"""
        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.delete("/cache/semantic")
            assert response.status_code == 200

            data = response.json()
            assert data["message"] == "Semantic cache cleared successfully"
            assert data["entries_cleared"] == 25

            mock_semantic_cache.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_llm_cache(self, mock_llm_cache):
        """Test DELETE /api/cache/llm clears LLM cache"""
        with patch('src.api.endpoints.cache.get_llm_cache', return_value=mock_llm_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.delete("/cache/llm")
            assert response.status_code == 200

            data = response.json()
            assert data["message"] == "LLM cache cleared successfully"
            assert data["entries_cleared"] == 15

            mock_llm_cache.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all_caches(self, mock_semantic_cache, mock_llm_cache):
        """Test DELETE /api/cache/all clears both caches"""
        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache), \
             patch('src.api.endpoints.cache.get_llm_cache', return_value=mock_llm_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.delete("/cache/all")
            assert response.status_code == 200

            data = response.json()
            assert data["message"] == "All caches cleared successfully"
            assert data["entries_cleared"] == 40  # 25 + 15

            mock_semantic_cache.clear.assert_called_once()
            mock_llm_cache.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_connection_cache(self, mock_semantic_cache):
        """Test DELETE /api/cache/semantic/connection/{id}"""
        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_semantic_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.delete("/cache/semantic/connection/1")
            assert response.status_code == 200

            data = response.json()
            assert "connection 1" in data["message"]
            assert data["entries_cleared"] == 10

            mock_semantic_cache.invalidate_connection.assert_called_once_with(1)


class TestCacheEndpointValidation:
    """Tests for validation and edge cases"""

    def test_recent_queries_limit_validation(self):
        """Test limit parameter validation"""
        mock_cache = MagicMock()
        mock_cache._memory_entries = {}

        with patch('src.api.endpoints.cache.get_semantic_cache', return_value=mock_cache):

            from src.api.endpoints.cache import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            # Valid limit
            response = client.get("/cache/semantic/recent?limit=50")
            assert response.status_code == 200

            # Limit too high (over 100)
            response = client.get("/cache/semantic/recent?limit=200")
            assert response.status_code == 422  # Validation error

            # Limit too low (under 1)
            response = client.get("/cache/semantic/recent?limit=0")
            assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
