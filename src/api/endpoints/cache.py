"""
Cache API Endpoints

Provides REST API for cache management:
- GET /cache/stats - Get cache statistics
- GET /cache/semantic/recent - Get recent cached queries
- DELETE /cache/semantic - Clear semantic cache
- DELETE /cache/llm - Clear LLM cache
- DELETE /cache/all - Clear all caches

Part of Phase 3.3: Semantic Caching UI Components
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.cache.semantic_cache import get_semantic_cache, SemanticCacheEntry
from src.cache.llm_cache import get_llm_cache
from src.cache.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SemanticCacheStats(BaseModel):
    """Semantic cache statistics"""
    total_lookups: int = 0
    total_hits: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0
    hit_rate_percent: float = 0.0
    semantic_hit_rate_percent: float = 0.0
    total_stores: int = 0
    similarity_threshold: float = 0.85
    ttl_seconds: int = 86400
    memory_entries: int = 0


class LLMCacheStats(BaseModel):
    """LLM cache statistics"""
    total_lookups: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate_percent: float = 0.0
    total_stores: int = 0
    similarity_threshold: float = 0.88
    ttl_seconds: int = 43200


class EmbeddingServiceStats(BaseModel):
    """Embedding service statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_hit_rate_percent: float = 0.0
    ollama_calls: int = 0
    tfidf_fallbacks: int = 0
    ollama_available: bool = False


class CacheStatsResponse(BaseModel):
    """Combined cache statistics response"""
    semantic_cache: SemanticCacheStats
    llm_cache: LLMCacheStats
    embedding_service: EmbeddingServiceStats


class CachedQueryResponse(BaseModel):
    """A cached query entry"""
    question: str
    sql: str
    connection_id: int
    database_type: str
    created_at: str
    hits: int = 0
    last_hit_at: Optional[str] = None
    # Don't include embedding or full result in API response


class RecentQueriesResponse(BaseModel):
    """Response for recent cached queries"""
    queries: List[CachedQueryResponse]
    total: int


class ClearCacheResponse(BaseModel):
    """Response for cache clear operations"""
    message: str
    entries_cleared: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get statistics for all cache layers.

    Returns combined stats for:
    - Semantic cache (query results)
    - LLM cache (SQL generation)
    - Embedding service (text embeddings)
    """
    try:
        # Get semantic cache stats
        semantic_cache = get_semantic_cache()
        semantic_stats = semantic_cache.get_stats()

        # Get LLM cache stats
        llm_cache = get_llm_cache()
        llm_stats = llm_cache.get_stats()

        # Get embedding service stats
        embedding_service = get_embedding_service()
        embedding_stats = embedding_service.get_stats()

        return CacheStatsResponse(
            semantic_cache=SemanticCacheStats(
                total_lookups=semantic_stats.get("total_lookups", 0),
                total_hits=semantic_stats.get("total_hits", 0),
                exact_hits=semantic_stats.get("exact_hits", 0),
                semantic_hits=semantic_stats.get("semantic_hits", 0),
                misses=semantic_stats.get("misses", 0),
                hit_rate_percent=semantic_stats.get("hit_rate_percent", 0.0),
                semantic_hit_rate_percent=semantic_stats.get("semantic_hit_rate_percent", 0.0),
                total_stores=semantic_stats.get("total_stores", 0),
                similarity_threshold=semantic_stats.get("similarity_threshold", 0.85),
                ttl_seconds=semantic_stats.get("ttl_seconds", 86400),
                memory_entries=semantic_stats.get("memory_entries", 0),
            ),
            llm_cache=LLMCacheStats(
                total_lookups=llm_stats.get("total_lookups", 0),
                hits=llm_stats.get("hits", 0),
                misses=llm_stats.get("misses", 0),
                hit_rate_percent=llm_stats.get("hit_rate_percent", 0.0),
                total_stores=llm_stats.get("total_stores", 0),
                similarity_threshold=llm_stats.get("similarity_threshold", 0.88),
                ttl_seconds=llm_stats.get("ttl_seconds", 43200),
            ),
            embedding_service=EmbeddingServiceStats(
                total_requests=embedding_stats.get("total_requests", 0),
                cache_hits=embedding_stats.get("cache_hits", 0),
                cache_hit_rate_percent=embedding_stats.get("cache_hit_rate_percent", 0.0),
                ollama_calls=embedding_stats.get("ollama_calls", 0),
                tfidf_fallbacks=embedding_stats.get("tfidf_fallbacks", 0),
                ollama_available=embedding_stats.get("ollama_available", False),
            ),
        )

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic/recent", response_model=RecentQueriesResponse)
async def get_recent_cached_queries(
    limit: int = Query(10, ge=1, le=100, description="Max queries to return"),
    connection_id: Optional[int] = Query(None, description="Filter by connection ID"),
    database_type: Optional[str] = Query(None, description="Filter by database type"),
):
    """
    Get recent cached queries from the semantic cache.

    Returns a list of cached queries with metadata (excluding embeddings and full results).
    Retrieves from both Redis (via sorted set) and in-memory fallback.
    """
    try:
        semantic_cache = get_semantic_cache()

        # Get entries from cache (Redis + memory fallback)
        cache_entries, total = await semantic_cache.get_recent_entries(
            limit=limit,
            connection_id=connection_id,
            database_type=database_type,
        )

        # Convert to response format
        entries = [
            CachedQueryResponse(
                question=entry.question,
                sql=entry.sql,
                connection_id=entry.connection_id,
                database_type=entry.database_type,
                created_at=entry.created_at,
                hits=entry.hits,
                last_hit_at=entry.last_hit_at,
            )
            for entry in cache_entries
        ]

        return RecentQueriesResponse(
            queries=entries,
            total=total,
        )

    except Exception as e:
        logger.error(f"Failed to get recent cached queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/semantic", response_model=ClearCacheResponse)
async def clear_semantic_cache():
    """
    Clear all semantic cache entries.

    Use when you want to invalidate cached query results.
    """
    try:
        semantic_cache = get_semantic_cache()
        count = await semantic_cache.clear()

        logger.info(f"Cleared semantic cache: {count} entries")

        return ClearCacheResponse(
            message="Semantic cache cleared successfully",
            entries_cleared=count,
        )

    except Exception as e:
        logger.error(f"Failed to clear semantic cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/llm", response_model=ClearCacheResponse)
async def clear_llm_cache():
    """
    Clear all LLM response cache entries.

    Use when you want to force fresh LLM SQL generation.
    """
    try:
        llm_cache = get_llm_cache()
        count = await llm_cache.clear()

        logger.info(f"Cleared LLM cache: {count} entries")

        return ClearCacheResponse(
            message="LLM cache cleared successfully",
            entries_cleared=count,
        )

    except Exception as e:
        logger.error(f"Failed to clear LLM cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/all", response_model=ClearCacheResponse)
async def clear_all_caches():
    """
    Clear all caches (semantic + LLM).

    Use sparingly - this will cause all queries to be regenerated.
    """
    try:
        semantic_cache = get_semantic_cache()
        llm_cache = get_llm_cache()

        semantic_count = await semantic_cache.clear()
        llm_count = await llm_cache.clear()

        total_count = semantic_count + llm_count

        logger.info(f"Cleared all caches: {total_count} entries (semantic={semantic_count}, llm={llm_count})")

        return ClearCacheResponse(
            message="All caches cleared successfully",
            entries_cleared=total_count,
        )

    except Exception as e:
        logger.error(f"Failed to clear all caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/semantic/connection/{connection_id}", response_model=ClearCacheResponse)
async def clear_connection_cache(connection_id: int):
    """
    Clear semantic cache entries for a specific connection.

    Use when a database schema changes or connection is updated.
    """
    try:
        semantic_cache = get_semantic_cache()
        count = await semantic_cache.invalidate_connection(connection_id)

        logger.info(f"Cleared cache for connection {connection_id}: {count} entries")

        return ClearCacheResponse(
            message=f"Cache cleared for connection {connection_id}",
            entries_cleared=count,
        )

    except Exception as e:
        logger.error(f"Failed to clear cache for connection {connection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
