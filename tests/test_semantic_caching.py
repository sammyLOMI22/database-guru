"""
Tests for Semantic Caching System

Tests cover:
- Embedding Service (TF-IDF fallback, similarity calculation)
- Semantic Cache (storage, retrieval, similarity matching)
- LLM Cache (schema fingerprinting, caching LLM responses)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.cache.embedding_service import (
    EmbeddingService,
    EmbeddingResult,
    get_embedding_service,
    reset_embedding_service,
)
from src.cache.semantic_cache import (
    SemanticCache,
    SemanticCacheEntry,
    SemanticCacheHit,
    get_semantic_cache,
    reset_semantic_cache,
)
from src.cache.llm_cache import (
    LLMCache,
    LLMCacheEntry,
    LLMCacheHit,
    get_llm_cache,
    reset_llm_cache,
)


# ==================== Embedding Service Tests ====================


class TestEmbeddingService:
    """Tests for the EmbeddingService"""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global singletons before each test"""
        reset_embedding_service()
        yield
        reset_embedding_service()

    def test_embedding_service_init(self):
        """Test embedding service initialization"""
        service = EmbeddingService()
        assert service.model == EmbeddingService.DEFAULT_MODEL
        assert service.cache_embeddings is True
        assert service._ollama_available is False  # Before initialization

    @pytest.mark.asyncio
    async def test_embedding_service_tfidf_fallback(self):
        """Test TF-IDF fallback when Ollama unavailable"""
        service = EmbeddingService()
        service._init_tfidf_fallback()
        service._ollama_available = False

        result = await service.get_embedding("Show me all customers from California")

        assert isinstance(result, EmbeddingResult)
        assert result.source == "tfidf"
        assert len(result.embedding) == service._tfidf_dimension
        assert result.dimension == service._tfidf_dimension

    @pytest.mark.asyncio
    async def test_embedding_service_caching(self):
        """Test embedding cache functionality"""
        service = EmbeddingService()
        service._init_tfidf_fallback()
        service._ollama_available = False

        # First call - should be a miss
        result1 = await service.get_embedding("test query")
        assert result1.source == "tfidf"

        # Second call - should be a cache hit
        result2 = await service.get_embedding("test query")
        assert result2.source == "cache"
        assert result1.embedding == result2.embedding

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        service = EmbeddingService()

        # Identical vectors should have similarity 1.0
        vec1 = [1.0, 0.0, 0.0]
        similarity = service.cosine_similarity(vec1, vec1)
        assert similarity == pytest.approx(1.0)

        # Orthogonal vectors should have similarity 0.0
        vec2 = [0.0, 1.0, 0.0]
        similarity = service.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)

        # Opposite vectors should have similarity -1.0
        vec3 = [-1.0, 0.0, 0.0]
        similarity = service.cosine_similarity(vec1, vec3)
        assert similarity == pytest.approx(-1.0)

    def test_is_similar(self):
        """Test similarity threshold checking"""
        service = EmbeddingService()

        vec1 = [1.0, 0.1, 0.0]
        vec2 = [1.0, 0.15, 0.0]

        # High similarity vectors
        is_similar, score = service.is_similar(vec1, vec2, threshold=0.9)
        assert is_similar is True
        assert score > 0.9

        # With higher threshold
        is_similar, score = service.is_similar(vec1, vec2, threshold=0.999)
        assert is_similar is False

    @pytest.mark.asyncio
    async def test_tfidf_semantic_similarity(self):
        """Test that similar queries get similar TF-IDF embeddings"""
        service = EmbeddingService()
        service._init_tfidf_fallback()
        service._ollama_available = False

        # Very similar queries
        q1 = "show me customers from california"
        q2 = "list customers in california"

        result1 = await service.get_embedding(q1, use_cache=False)
        result2 = await service.get_embedding(q2, use_cache=False)

        similarity = service.cosine_similarity(result1.embedding, result2.embedding)

        # Similar queries should have moderate similarity (TF-IDF is limited)
        # Note: TF-IDF gives lower similarity than neural embeddings
        assert similarity > 0.4  # Adjusted for TF-IDF limitations

    def test_get_stats(self):
        """Test statistics retrieval"""
        service = EmbeddingService()
        stats = service.get_stats()

        assert "total_requests" in stats
        assert "cache_hits" in stats
        assert "cache_hit_rate_percent" in stats
        assert stats["ollama_available"] is False


# ==================== Semantic Cache Tests ====================


class TestSemanticCache:
    """Tests for the SemanticCache"""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global singletons before each test"""
        reset_semantic_cache()
        reset_embedding_service()
        yield
        reset_semantic_cache()
        reset_embedding_service()

    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache"""
        mock_cache = MagicMock()
        mock_cache.redis = None  # Simulate no Redis connection
        mock_cache.connect = AsyncMock()
        mock_cache.health_check = AsyncMock(return_value=False)
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.delete = AsyncMock(return_value=True)
        mock_cache.clear_pattern = AsyncMock(return_value=0)
        return mock_cache

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service"""
        mock_service = MagicMock()
        mock_service.initialize = AsyncMock(return_value=True)
        mock_service.get_embedding = AsyncMock(
            return_value=EmbeddingResult(
                embedding=[0.1] * 512,
                model="mock",
                dimension=512,
                source="mock",
                generation_time_ms=1.0,
            )
        )
        mock_service.cosine_similarity = MagicMock(return_value=0.9)
        return mock_service

    def test_semantic_cache_init(self):
        """Test semantic cache initialization"""
        cache = SemanticCache(
            similarity_threshold=0.85,
            ttl=3600,
        )
        assert cache.similarity_threshold == 0.85
        assert cache.ttl == 3600

    @pytest.mark.asyncio
    async def test_semantic_cache_set_and_get(
        self, mock_redis_cache, mock_embedding_service
    ):
        """Test storing and retrieving from semantic cache"""
        cache = SemanticCache(
            redis_cache=mock_redis_cache,
            embedding_service=mock_embedding_service,
        )

        # Store a query
        success = await cache.set(
            question="Show me customers from California",
            sql="SELECT * FROM customers WHERE state = 'CA'",
            result={"data": [], "row_count": 10},
            connection_id=1,
            database_type="postgresql",
        )
        assert success is True

        # Verify it's stored in memory (since Redis is mocked to fail)
        assert len(cache._memory_entries) == 1

    @pytest.mark.asyncio
    async def test_semantic_cache_miss(self, mock_redis_cache, mock_embedding_service):
        """Test cache miss when no similar entry exists"""
        cache = SemanticCache(
            redis_cache=mock_redis_cache,
            embedding_service=mock_embedding_service,
        )

        result = await cache.get_similar(
            question="Show me customers",
            connection_id=1,
            database_type="postgresql",
        )

        assert result is None
        assert cache._misses == 1

    @pytest.mark.asyncio
    async def test_semantic_cache_hit(self, mock_redis_cache, mock_embedding_service):
        """Test cache hit when similar entry exists"""
        cache = SemanticCache(
            redis_cache=mock_redis_cache,
            embedding_service=mock_embedding_service,
            similarity_threshold=0.85,
        )

        # Store a query
        await cache.set(
            question="Show me customers from California",
            sql="SELECT * FROM customers WHERE state = 'CA'",
            result={"data": [], "row_count": 10},
            connection_id=1,
            database_type="postgresql",
        )

        # Look up similar query (mock returns 0.9 similarity)
        result = await cache.get_similar(
            question="List customers in California",
            connection_id=1,
            database_type="postgresql",
        )

        assert result is not None
        assert isinstance(result, SemanticCacheHit)
        assert result.similarity == 0.9
        assert result.cached_sql == "SELECT * FROM customers WHERE state = 'CA'"

    def test_get_stats(self):
        """Test statistics retrieval"""
        cache = SemanticCache()
        cache._total_lookups = 100
        cache._semantic_hits = 30
        cache._exact_hits = 20
        cache._misses = 50

        stats = cache.get_stats()

        assert stats["total_lookups"] == 100
        assert stats["total_hits"] == 50
        assert stats["hit_rate_percent"] == 50.0


# ==================== LLM Cache Tests ====================


class TestLLMCache:
    """Tests for the LLMCache"""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """Reset global singletons before each test"""
        reset_llm_cache()
        reset_embedding_service()
        yield
        reset_llm_cache()
        reset_embedding_service()

    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache"""
        mock_cache = MagicMock()
        mock_cache.redis = None
        mock_cache.connect = AsyncMock()
        mock_cache.health_check = AsyncMock(return_value=False)
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.clear_pattern = AsyncMock(return_value=0)
        return mock_cache

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service"""
        mock_service = MagicMock()
        mock_service.initialize = AsyncMock(return_value=True)
        mock_service.get_embedding = AsyncMock(
            return_value=EmbeddingResult(
                embedding=[0.1] * 512,
                model="mock",
                dimension=512,
                source="mock",
                generation_time_ms=1.0,
            )
        )
        mock_service.cosine_similarity = MagicMock(return_value=0.92)
        return mock_service

    def test_llm_cache_init(self):
        """Test LLM cache initialization"""
        cache = LLMCache(
            similarity_threshold=0.88,
            ttl=43200,
        )
        assert cache.similarity_threshold == 0.88
        assert cache.ttl == 43200

    def test_schema_fingerprint(self):
        """Test schema fingerprint generation"""
        cache = LLMCache()

        schema1 = """
        Table: customers (id, name, email)
        Table: orders (id, customer_id, total)
        """

        schema2 = """
        Table: customers (id, name, email, phone)
        Table: orders (id, customer_id, total)
        """

        fp1 = cache.create_schema_fingerprint(schema1)
        fp2 = cache.create_schema_fingerprint(schema2)

        # Same tables should produce same fingerprint
        # (fingerprint is based on table names, not columns)
        assert fp1 == fp2

    @pytest.mark.asyncio
    async def test_llm_cache_set_and_get(
        self, mock_redis_cache, mock_embedding_service
    ):
        """Test storing and retrieving LLM responses"""
        cache = LLMCache(
            redis_cache=mock_redis_cache,
            embedding_service=mock_embedding_service,
        )

        schema = "Table: customers (id, name)"

        # Cache a response
        success = await cache.cache_sql(
            question="Show me all customers",
            schema=schema,
            database_type="postgresql",
            sql="SELECT * FROM customers",
            raw_output="SELECT * FROM customers",
            model_used="test-model",
        )
        assert success is True

        # Verify it's stored
        assert len(cache._memory_entries) == 1

    @pytest.mark.asyncio
    async def test_llm_cache_hit(self, mock_redis_cache, mock_embedding_service):
        """Test LLM cache hit when similar query exists"""
        cache = LLMCache(
            redis_cache=mock_redis_cache,
            embedding_service=mock_embedding_service,
            similarity_threshold=0.88,
        )

        schema = "Table: customers (id, name)"

        # Cache a response
        await cache.cache_sql(
            question="Show me all customers",
            schema=schema,
            database_type="postgresql",
            sql="SELECT * FROM customers",
            raw_output="SELECT * FROM customers",
            model_used="test-model",
        )

        # Look up similar query (mock returns 0.92 similarity)
        result = await cache.get_cached_sql(
            question="List all customers",
            schema=schema,
            database_type="postgresql",
        )

        assert result is not None
        assert isinstance(result, LLMCacheHit)
        assert result.sql == "SELECT * FROM customers"
        assert result.similarity == 0.92

    @pytest.mark.asyncio
    async def test_llm_cache_miss_different_schema(
        self, mock_redis_cache, mock_embedding_service
    ):
        """Test cache miss when schema fingerprint differs"""
        cache = LLMCache(
            redis_cache=mock_redis_cache,
            embedding_service=mock_embedding_service,
        )

        schema1 = "Table: customers (id, name)"
        schema2 = "Table: products (id, name)"  # Different table

        # Cache with schema1
        await cache.cache_sql(
            question="Show me all items",
            schema=schema1,
            database_type="postgresql",
            sql="SELECT * FROM customers",
            raw_output="SELECT * FROM customers",
            model_used="test-model",
        )

        # Look up with schema2 (different fingerprint)
        result = await cache.get_cached_sql(
            question="Show me all items",
            schema=schema2,
            database_type="postgresql",
        )

        # Should miss because fingerprint is different
        assert result is None

    def test_get_stats(self):
        """Test statistics retrieval"""
        cache = LLMCache()
        cache._total_lookups = 50
        cache._hits = 25
        cache._misses = 25

        stats = cache.get_stats()

        assert stats["total_lookups"] == 50
        assert stats["hits"] == 25
        assert stats["hit_rate_percent"] == 50.0


# ==================== Integration Tests ====================


class TestSemanticCachingIntegration:
    """Integration tests for the full caching system"""

    @pytest.fixture(autouse=True)
    def reset_all(self):
        """Reset all global singletons"""
        reset_embedding_service()
        reset_semantic_cache()
        reset_llm_cache()
        yield
        reset_embedding_service()
        reset_semantic_cache()
        reset_llm_cache()

    @pytest.mark.asyncio
    async def test_end_to_end_tfidf_semantic_matching(self):
        """Test full flow with TF-IDF embeddings"""
        # Create service with TF-IDF fallback
        embedding_service = EmbeddingService()
        embedding_service._init_tfidf_fallback()
        embedding_service._ollama_available = False

        # Create semantic cache
        cache = SemanticCache(
            embedding_service=embedding_service,
            similarity_threshold=0.5,  # Lower threshold for TF-IDF
        )

        # Store a query
        await cache.set(
            question="show customers from california",
            sql="SELECT * FROM customers WHERE state = 'CA'",
            result={"data": [], "row_count": 5},
            connection_id=1,
            database_type="postgresql",
        )

        # Look up with similar query
        result = await cache.get_similar(
            question="list customers in california",
            connection_id=1,
            database_type="postgresql",
            threshold=0.3,  # Low threshold for TF-IDF
        )

        # Should find the match
        assert result is not None
        assert result.cached_sql == "SELECT * FROM customers WHERE state = 'CA'"

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that singletons work correctly"""
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        assert service1 is service2

        cache1 = get_semantic_cache()
        cache2 = get_semantic_cache()
        assert cache1 is cache2

        llm1 = get_llm_cache()
        llm2 = get_llm_cache()
        assert llm1 is llm2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
