"""Cache package for Database Guru"""
from src.cache.redis_client import RedisCache, get_redis_cache
from src.cache.decorators import cached, cache_query_result, invalidate_cache, CacheNamespace
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

__all__ = [
    # Redis cache
    "RedisCache",
    "get_redis_cache",
    # Decorators
    "cached",
    "cache_query_result",
    "invalidate_cache",
    "CacheNamespace",
    # Embedding service
    "EmbeddingService",
    "EmbeddingResult",
    "get_embedding_service",
    "reset_embedding_service",
    # Semantic cache
    "SemanticCache",
    "SemanticCacheEntry",
    "SemanticCacheHit",
    "get_semantic_cache",
    "reset_semantic_cache",
    # LLM cache
    "LLMCache",
    "LLMCacheEntry",
    "LLMCacheHit",
    "get_llm_cache",
    "reset_llm_cache",
]
