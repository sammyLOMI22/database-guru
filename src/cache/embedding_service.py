"""
Embedding Service for Semantic Caching

This module provides text embedding generation for semantic similarity matching.
Uses Ollama embeddings by default (local, no API keys needed), with fallback
to simple TF-IDF vectorization.

Performance:
- Ollama embedding generation: 50-200ms per query
- TF-IDF fallback: <5ms per query (lower quality)
- Embedding dimension: 768-4096 (model dependent)

Usage:
    from src.cache.embedding_service import get_embedding_service

    embedding_service = get_embedding_service()
    await embedding_service.initialize()

    # Generate embedding for a query
    embedding = await embedding_service.get_embedding("Show me all customers from CA")

    # Calculate similarity between queries
    similarity = embedding_service.cosine_similarity(embedding1, embedding2)
"""

import logging
import hashlib
import math
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from collections import Counter
import re

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    embedding: List[float]
    model: str
    dimension: int
    source: str  # 'ollama', 'tfidf', 'cache'
    generation_time_ms: float


class EmbeddingService:
    """
    Text embedding service for semantic similarity.

    Supports:
    - Ollama embeddings (primary, high quality)
    - TF-IDF fallback (when Ollama unavailable)
    - Embedding caching for performance

    Similarity Thresholds:
    - >= 0.92: Nearly identical queries
    - >= 0.85: Very similar (safe for cache hit)
    - >= 0.75: Related queries (might need adaptation)
    - < 0.75: Different queries
    """

    # Default embedding model (nomic-embed-text is small and fast)
    DEFAULT_MODEL = "nomic-embed-text"

    # Similarity thresholds
    THRESHOLD_IDENTICAL = 0.95
    THRESHOLD_SIMILAR = 0.85
    THRESHOLD_RELATED = 0.75

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        cache_embeddings: bool = True,
        max_cache_size: int = 10000,
    ):
        """
        Initialize embedding service.

        Args:
            model: Ollama embedding model name
            cache_embeddings: Whether to cache embeddings in memory
            max_cache_size: Maximum number of embeddings to cache
        """
        self.model = model
        self.cache_embeddings = cache_embeddings
        self.max_cache_size = max_cache_size

        # Ollama client
        self._ollama_client = None
        self._ollama_available = False

        # Embedding cache: hash(text) -> embedding
        self._embedding_cache: Dict[str, List[float]] = {}

        # TF-IDF vocabulary for fallback
        self._tfidf_vocab: Dict[str, int] = {}
        self._tfidf_idf: Dict[str, float] = {}
        self._tfidf_dimension = 512  # Fixed dimension for TF-IDF

        # Metrics
        self._total_requests = 0
        self._cache_hits = 0
        self._ollama_calls = 0
        self._tfidf_fallbacks = 0

        logger.info(f"Initialized EmbeddingService with model: {model}")

    async def initialize(self) -> bool:
        """
        Initialize Ollama client and verify embedding model availability.

        Returns:
            True if Ollama is available, False if falling back to TF-IDF
        """
        try:
            import ollama
            self._ollama_client = ollama.AsyncClient()

            # Test embedding generation
            test_response = await self._ollama_client.embeddings(
                model=self.model,
                prompt="test"
            )

            if test_response and "embedding" in test_response:
                self._ollama_available = True
                dimension = len(test_response["embedding"])
                logger.info(
                    f"Ollama embedding service initialized. "
                    f"Model: {self.model}, Dimension: {dimension}"
                )
                return True

        except ImportError:
            logger.warning("Ollama package not installed. Using TF-IDF fallback.")
        except Exception as e:
            logger.warning(
                f"Ollama embeddings unavailable ({e}). Using TF-IDF fallback."
            )

        self._ollama_available = False
        self._init_tfidf_fallback()
        return False

    def _init_tfidf_fallback(self):
        """Initialize TF-IDF vocabulary with common SQL/database terms"""
        # Pre-populate vocabulary with common terms
        common_terms = [
            # SQL keywords
            "select", "from", "where", "and", "or", "join", "left", "right",
            "inner", "outer", "on", "group", "by", "order", "having", "limit",
            "count", "sum", "avg", "max", "min", "distinct", "as", "in", "not",
            "null", "is", "like", "between", "case", "when", "then", "else",
            # Common query words
            "show", "list", "find", "get", "all", "total", "number", "how",
            "many", "what", "which", "who", "where", "when", "top", "first",
            "last", "recent", "latest", "oldest", "highest", "lowest", "most",
            "least", "average", "per", "each", "every", "any", "some",
            # Data concepts
            "customer", "customers", "order", "orders", "product", "products",
            "user", "users", "sale", "sales", "employee", "employees",
            "revenue", "profit", "price", "amount", "quantity", "date",
            "year", "month", "day", "week", "time", "name", "id", "status",
            # Locations
            "state", "city", "country", "region", "location", "address",
            "california", "ca", "new", "york", "ny", "texas", "tx",
        ]

        for i, term in enumerate(common_terms):
            self._tfidf_vocab[term] = i

        # Default IDF values (will be updated with actual corpus)
        for term in self._tfidf_vocab:
            self._tfidf_idf[term] = 1.0

        logger.info(f"TF-IDF fallback initialized with {len(self._tfidf_vocab)} terms")

    async def get_embedding(
        self,
        text: str,
        use_cache: bool = True,
    ) -> EmbeddingResult:
        """
        Generate embedding for text.

        Args:
            text: Text to embed
            use_cache: Whether to check/use embedding cache

        Returns:
            EmbeddingResult with embedding and metadata
        """
        import time
        start_time = time.time()

        self._total_requests += 1

        # Normalize text
        normalized_text = self._normalize_text(text)
        text_hash = self._hash_text(normalized_text)

        # Check cache
        if use_cache and self.cache_embeddings and text_hash in self._embedding_cache:
            self._cache_hits += 1
            embedding = self._embedding_cache[text_hash]
            elapsed_ms = (time.time() - start_time) * 1000

            return EmbeddingResult(
                embedding=embedding,
                model=self.model if self._ollama_available else "tfidf",
                dimension=len(embedding),
                source="cache",
                generation_time_ms=elapsed_ms,
            )

        # Generate embedding
        if self._ollama_available:
            embedding = await self._get_ollama_embedding(normalized_text)
            source = "ollama"
            self._ollama_calls += 1
        else:
            embedding = self._get_tfidf_embedding(normalized_text)
            source = "tfidf"
            self._tfidf_fallbacks += 1

        # Cache result
        if self.cache_embeddings:
            self._cache_embedding(text_hash, embedding)

        elapsed_ms = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embedding=embedding,
            model=self.model if self._ollama_available else "tfidf",
            dimension=len(embedding),
            source=source,
            generation_time_ms=elapsed_ms,
        )

    async def _get_ollama_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama"""
        try:
            response = await self._ollama_client.embeddings(
                model=self.model,
                prompt=text
            )
            return response["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            # Fall back to TF-IDF
            return self._get_tfidf_embedding(text)

    def _get_tfidf_embedding(self, text: str) -> List[float]:
        """Generate TF-IDF based embedding (fallback)"""
        # Tokenize
        tokens = self._tokenize(text)
        token_counts = Counter(tokens)
        total_tokens = len(tokens)

        # Create sparse TF-IDF vector
        embedding = [0.0] * self._tfidf_dimension

        for token, count in token_counts.items():
            if token in self._tfidf_vocab:
                idx = self._tfidf_vocab[token]
                if idx < self._tfidf_dimension:
                    # TF-IDF: term frequency * inverse document frequency
                    tf = count / total_tokens if total_tokens > 0 else 0
                    idf = self._tfidf_idf.get(token, 1.0)
                    embedding[idx] = tf * idf

        # Add hash-based features for out-of-vocabulary terms
        for token in tokens:
            if token not in self._tfidf_vocab:
                # Hash to a position in the vector
                hash_idx = hash(token) % self._tfidf_dimension
                embedding[hash_idx] += 0.1

        # Normalize to unit vector
        return self._normalize_vector(embedding)

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Similarity score between -1 and 1 (higher = more similar)
        """
        if len(vec1) != len(vec2):
            logger.warning(
                f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}. "
                "Truncating to shorter length."
            )
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def is_similar(
        self,
        vec1: List[float],
        vec2: List[float],
        threshold: float = None,
    ) -> Tuple[bool, float]:
        """
        Check if two embeddings are similar enough for cache hit.

        Args:
            vec1: First embedding
            vec2: Second embedding
            threshold: Similarity threshold (default: THRESHOLD_SIMILAR)

        Returns:
            Tuple of (is_similar, similarity_score)
        """
        if threshold is None:
            threshold = self.THRESHOLD_SIMILAR

        similarity = self.cosine_similarity(vec1, vec2)
        return similarity >= threshold, similarity

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent embedding"""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove punctuation except SQL-relevant chars
        text = re.sub(r'[^\w\s\*\.\,\(\)]', ' ', text)
        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Simple whitespace tokenization
        return text.lower().split()

    def _hash_text(self, text: str) -> str:
        """Generate hash for text caching"""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _normalize_vector(self, vec: List[float]) -> List[float]:
        """Normalize vector to unit length"""
        magnitude = math.sqrt(sum(x * x for x in vec))
        if magnitude == 0:
            return vec
        return [x / magnitude for x in vec]

    def _cache_embedding(self, text_hash: str, embedding: List[float]):
        """Cache embedding with LRU-style eviction"""
        if len(self._embedding_cache) >= self.max_cache_size:
            # Simple eviction: remove oldest 10%
            keys_to_remove = list(self._embedding_cache.keys())[
                : self.max_cache_size // 10
            ]
            for key in keys_to_remove:
                del self._embedding_cache[key]

        self._embedding_cache[text_hash] = embedding

    def get_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics"""
        hit_rate = (
            self._cache_hits / self._total_requests * 100
            if self._total_requests > 0
            else 0
        )

        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "cache_hit_rate_percent": round(hit_rate, 2),
            "ollama_calls": self._ollama_calls,
            "tfidf_fallbacks": self._tfidf_fallbacks,
            "cached_embeddings": len(self._embedding_cache),
            "max_cache_size": self.max_cache_size,
            "ollama_available": self._ollama_available,
            "model": self.model,
        }

    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(
    model: str = EmbeddingService.DEFAULT_MODEL,
) -> EmbeddingService:
    """
    Get the global embedding service instance (singleton pattern).

    Args:
        model: Ollama embedding model (only used on first call)

    Returns:
        Global EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService(model=model)

    return _embedding_service


def reset_embedding_service():
    """Reset the global embedding service (useful for testing)"""
    global _embedding_service
    _embedding_service = None
    logger.info("Embedding service reset")
