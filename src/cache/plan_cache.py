"""
EXPLAIN Plan Caching for Query Compilation

Caches database execution plans to avoid expensive re-planning for repeated queries.
Uses schema fingerprinting to detect cache invalidation.

Architecture:
- Cache Keys: plan:{connection_id}:{normalized_hash}
- Schema Fingerprinting: Detects when schema changes invalidate plans
- Query-Type-Based TTL: Aggregations 1hr, Joins 6hr, Lookups 24hr
- Table-Based Index: plan:index:{connection_id}:{table} for surgical invalidation
- EXPLAIN Parsing: Extract cost, scan type, indexes for different databases
"""

import logging
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CachedPlan:
    """Result of EXPLAIN plan caching"""
    normalized_hash: str           # From normalized query
    schema_fingerprint: str        # Schema state hash
    database_type: str             # postgresql, mysql, sqlite, duckdb
    connection_id: int             # Which database connection
    explain_plan: List[str]        # Raw EXPLAIN output lines
    estimated_cost: Optional[float] # Extracted cost estimate
    uses_indexes: List[str]        # Detected index usage
    scan_type: str                 # Sequential, Index, Bitmap, etc.
    query_type: str               # SELECT, INSERT, UPDATE, DELETE
    has_aggregation: bool         # Has COUNT/SUM/etc
    has_join: bool                # Uses JOIN
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    hits: int = 0                 # Cache hit counter
    tables: List[str] = field(default_factory=list)  # Tables in query


class PlanCache:
    """
    EXPLAIN plan caching with schema-aware invalidation.

    Strategy:
    1. Cache plans by (connection_id, normalized_hash)
    2. Validate schema fingerprint on each lookup
    3. Use query-type-based TTL for expiration
    4. Maintain table index for surgical invalidation
    """

    # TTL by query type (seconds)
    TTL_BY_QUERY_TYPE = {
        'aggregation': 3600,      # 1 hour - data changes affect cardinality
        'join': 21600,            # 6 hours - joins are stable unless schema changes
        'lookup': 86400,          # 24 hours - simple lookups are very stable
        'write': 0,               # 0 - never cache writes
    }

    # In-memory cache (for now - can be backed by Redis)
    _cache: Dict[str, CachedPlan] = {}
    _table_index: Dict[str, List[str]] = {}  # plan:index:{connection}:{table} -> [hashes]

    def __init__(self):
        """Initialize plan cache"""
        self._cache = {}
        self._table_index = {}

    async def get_cached_plan(
        self,
        connection_id: int,
        normalized_hash: str,
        current_schema_fingerprint: str,
    ) -> Optional[CachedPlan]:
        """
        Get cached plan if it exists and schema hasn't changed.

        Args:
            connection_id: Connection ID
            normalized_hash: Hash of normalized query template
            current_schema_fingerprint: Current schema fingerprint

        Returns:
            CachedPlan if valid, None if missing or invalid
        """
        cache_key = f"plan:{connection_id}:{normalized_hash}"

        # Check if plan exists
        if cache_key not in self._cache:
            logger.debug(f"Plan cache miss: {cache_key}")
            return None

        plan = self._cache[cache_key]

        # Validate schema fingerprint
        if plan.schema_fingerprint != current_schema_fingerprint:
            logger.warning(
                f"Plan invalidated (schema changed): {cache_key} "
                f"(old: {plan.schema_fingerprint[:8]}, new: {current_schema_fingerprint[:8]})"
            )
            # Remove invalid plan
            self._invalidate_plan(cache_key, plan)
            return None

        # Update hit counter
        plan.hits += 1
        logger.debug(
            f"Plan cache hit: {cache_key} (hits: {plan.hits}, "
            f"cost: {plan.estimated_cost}, scan: {plan.scan_type})"
        )

        return plan

    async def cache_plan(
        self,
        connection_id: int,
        normalized_hash: str,
        schema_fingerprint: str,
        explain_output: List[str],
        query_type: str,
        has_aggregation: bool,
        has_join: bool,
        tables: List[str],
        database_type: str,
    ) -> CachedPlan:
        """
        Cache EXPLAIN plan result.

        Args:
            connection_id: Connection ID
            normalized_hash: Hash of normalized query
            schema_fingerprint: Current schema fingerprint
            explain_output: Raw EXPLAIN output lines
            query_type: SELECT, INSERT, UPDATE, DELETE
            has_aggregation: Has aggregation functions
            has_join: Uses JOIN
            tables: Tables in query
            database_type: postgresql, mysql, sqlite, duckdb

        Returns:
            CachedPlan with parsed information
        """
        # Parse EXPLAIN output
        estimated_cost, scan_type, indexes = self._parse_explain(
            explain_output,
            database_type,
        )

        # Create plan object
        plan = CachedPlan(
            normalized_hash=normalized_hash,
            schema_fingerprint=schema_fingerprint,
            database_type=database_type,
            connection_id=connection_id,
            explain_plan=explain_output,
            estimated_cost=estimated_cost,
            uses_indexes=indexes,
            scan_type=scan_type,
            query_type=query_type,
            has_aggregation=has_aggregation,
            has_join=has_join,
            tables=tables,
        )

        # Store in cache
        cache_key = f"plan:{connection_id}:{normalized_hash}"
        self._cache[cache_key] = plan

        # Update table index for surgical invalidation
        for table in tables:
            index_key = f"plan:index:{connection_id}:{table}"
            if index_key not in self._table_index:
                self._table_index[index_key] = []
            self._table_index[index_key].append(cache_key)

        logger.info(
            f"Cached plan: {cache_key} "
            f"(cost: {estimated_cost}, scan: {scan_type}, indexes: {len(indexes)})"
        )

        return plan

    async def invalidate_connection(self, connection_id: int) -> int:
        """
        Invalidate all plans for a connection.

        Args:
            connection_id: Connection to invalidate

        Returns:
            Number of plans invalidated
        """
        prefix = f"plan:{connection_id}:"
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]

        # Also remove table indexes
        index_prefix = f"plan:index:{connection_id}:"
        for key in list(self._table_index.keys()):
            if key.startswith(index_prefix):
                del self._table_index[key]

        # Remove plans
        for key in keys_to_remove:
            del self._cache[key]

        logger.info(f"Invalidated {len(keys_to_remove)} plans for connection {connection_id}")
        return len(keys_to_remove)

    async def invalidate_table(self, connection_id: int, table_name: str) -> int:
        """
        Invalidate plans that use a specific table (surgical invalidation).

        Args:
            connection_id: Connection ID
            table_name: Table that changed

        Returns:
            Number of plans invalidated
        """
        index_key = f"plan:index:{connection_id}:{table_name}"

        if index_key not in self._table_index:
            logger.debug(f"No plans found for table {table_name} in connection {connection_id}")
            return 0

        # Get all plans that use this table
        plan_keys = self._table_index[index_key]

        # Remove plans
        count = 0
        for key in plan_keys:
            if key in self._cache:
                plan = self._cache[key]
                self._invalidate_plan(key, plan)
                count += 1

        # Remove index entry
        del self._table_index[index_key]

        logger.info(
            f"Invalidated {count} plans using table {table_name} "
            f"for connection {connection_id}"
        )

        return count

    def _invalidate_plan(self, cache_key: str, plan: CachedPlan) -> None:
        """
        Remove a plan from cache and clean up indexes.

        Args:
            cache_key: Cache key
            plan: Plan to remove
        """
        if cache_key in self._cache:
            del self._cache[cache_key]

        # Clean up table index
        for table in plan.tables:
            index_key = f"plan:index:{plan.connection_id}:{table}"
            if index_key in self._table_index:
                try:
                    self._table_index[index_key].remove(cache_key)
                    if not self._table_index[index_key]:
                        del self._table_index[index_key]
                except ValueError:
                    pass

    def _parse_explain(
        self,
        explain_output: List[str],
        database_type: str,
    ) -> tuple:
        """
        Parse EXPLAIN output to extract cost, scan type, and indexes.

        Args:
            explain_output: Raw EXPLAIN lines
            database_type: postgresql, mysql, sqlite, duckdb

        Returns:
            Tuple of (estimated_cost, scan_type, indexes)
        """
        estimated_cost = None
        scan_type = "Unknown"
        indexes = []

        try:
            explain_text = "\n".join(explain_output)

            if database_type == "postgresql":
                # PostgreSQL: "cost=0.00..5.04"
                cost_match = re.search(r'cost=[\d.]+\.\.([\d.]+)', explain_text)
                if cost_match:
                    estimated_cost = float(cost_match.group(1))

                # Scan types: Index Scan, Seq Scan, Bitmap Index Scan (check Bitmap before Index)
                if "Bitmap Index Scan" in explain_text or "Bitmap Heap Scan" in explain_text:
                    scan_type = "Bitmap"
                elif "Index Scan" in explain_text:
                    scan_type = "Index"
                elif "Seq Scan" in explain_text:
                    scan_type = "Sequential"

                # Extract index names (match "using idx_name" specifically)
                index_matches = re.findall(r'using\s+(\w+)', explain_text, re.IGNORECASE)
                indexes = list(set(index_matches))

            elif database_type == "mysql":
                # MySQL: "type: ALL, index, range, ref, index_merge"
                type_match = re.search(r'type:\s*(\w+)', explain_text, re.IGNORECASE)
                if type_match:
                    scan_type = type_match.group(1)

                # Extract key name (index used)
                key_matches = re.findall(r'key:\s*(\w+)', explain_text, re.IGNORECASE)
                indexes = list(set(key_matches))

                # Try to extract rows statistic as cost proxy
                rows_match = re.search(r'rows:\s*(\d+)', explain_text, re.IGNORECASE)
                if rows_match:
                    estimated_cost = float(rows_match.group(1))

            elif database_type == "sqlite":
                # SQLite: "EXPLAIN QUERY PLAN" output
                # Format: "0|0|0|SCAN TABLE products" or "SEARCH TABLE products USING INDEX idx"
                if "SEARCH TABLE" in explain_text and "USING INDEX" in explain_text:
                    scan_type = "Index"
                elif "SCAN TABLE" in explain_text or "SCAN INDEX" in explain_text:
                    scan_type = "Sequential" if "SCAN TABLE" in explain_text else "Index"

                # Extract index names (from "USING INDEX idx_name")
                index_matches = re.findall(r'USING\s+INDEX\s+(\w+)', explain_text)
                indexes = list(set(index_matches))

            elif database_type == "duckdb":
                # DuckDB: "Estimated Cardinality: 100"
                card_match = re.search(r'Estimated Cardinality:\s*([\d.]+)', explain_text)
                if card_match:
                    estimated_cost = float(card_match.group(1))

                # Scan types: Table Scan, Index Scan
                if "Index Scan" in explain_text:
                    scan_type = "Index"
                elif "Table Scan" in explain_text:
                    scan_type = "Sequential"

                # Extract index names
                index_matches = re.findall(r'(\w+_idx)', explain_text)
                indexes = list(set(index_matches))

            logger.debug(
                f"Parsed EXPLAIN ({database_type}): cost={estimated_cost}, "
                f"scan={scan_type}, indexes={indexes}"
            )

        except Exception as e:
            logger.debug(f"Error parsing EXPLAIN output: {e}")

        return estimated_cost, scan_type, indexes

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of statistics
        """
        total_hits = sum(plan.hits for plan in self._cache.values())
        total_plans = len(self._cache)

        return {
            "total_plans_cached": total_plans,
            "total_cache_hits": total_hits,
            "avg_hits_per_plan": total_hits / max(total_plans, 1),
            "table_index_entries": len(self._table_index),
            "cache_size_mb": sum(
                len(plan.explain_plan) * 100 / (1024 * 1024)
                for plan in self._cache.values()
            ),
        }

    def clear_cache(self) -> None:
        """Clear entire cache"""
        self._cache.clear()
        self._table_index.clear()
        logger.info("Cleared plan cache")


# Global singleton
_plan_cache: Optional[PlanCache] = None


def get_plan_cache() -> PlanCache:
    """
    Get global plan cache instance.

    Returns:
        Singleton PlanCache instance
    """
    global _plan_cache
    if _plan_cache is None:
        _plan_cache = PlanCache()
    return _plan_cache
