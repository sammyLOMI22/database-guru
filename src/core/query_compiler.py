"""
Query Compiler Module
Handles normalization, compilation, and caching of SQL queries for performance optimization.

Uses sqlparse for robust SQL tokenization instead of regex patterns.
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import logging
import threading
from collections import OrderedDict

import sqlparse
from sqlparse import tokens as T

logger = logging.getLogger(__name__)

@dataclass
class CompiledQuery:
    """Represents a compiled and cached query execution plan"""
    sql_template: str              # Parameterized SQL
    query_hash: str                # Unique hash of the template
    compiled_at: datetime          # When this was compiled
    execution_count: int = 0       # How many times used
    last_used_at: datetime = field(default_factory=datetime.utcnow)
    avg_execution_ms: float = 0.0  # Performance tracking
    parameter_count: int = 0       # Number of parameters in template

class QueryCompiler:
    """
    Compiles and caches SQL execution plans.

    This class is responsible for:
    1. Normalizing raw SQL into parameterized templates
    2. Caching these templates to avoid re-parsing/re-planning
    3. Tracking performance metrics for compiled queries

    Supported SQL Features:
    - String literals: 'value' → :p0 (including escaped quotes like 'O''Reilly')
    - Numeric literals: 123, -99.99, 1e10 → :p0
    - Double-quoted identifiers: "Order 1" preserved as-is
    - SQL comments: -- and /* */ stripped before processing
    - Column/table names with numbers: col1, table2 preserved

    Known Limitations:
    - Array literals: PostgreSQL/DuckDB array syntax like ['a', 'b'] is preserved
      as-is and NOT parameterized. This is intentional because array parameter
      binding varies by database driver and converting to :p0 would produce
      invalid SQL. Queries with array literals will have lower cache hit rates
      since the array values remain in the template.
    - Hex literals: 0xFF is not parameterized (uncommon in typical queries)
    - Complex expressions: Nested parentheses with arithmetic may not be
      fully captured in all cases.

    Thread Safety:
    - Singleton pattern with thread-safe initialization
    - Cache operations protected by _cache_lock

    Future Enhancement:
    - Consider Redis persistence for cross-process cache sharing
      (see docs/planning/FUTURE_PLANS.md)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_cache_size: int = 1000):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(QueryCompiler, cls).__new__(cls)
                # Use OrderedDict for O(1) LRU
                cls._instance.compiled_queries = OrderedDict()
                cls._instance.max_cache_size = max_cache_size
                cls._instance._stats = {
                    "hits": 0,
                    "misses": 0,
                    "evictions": 0
                }
                cls._instance._cache_lock = threading.Lock()
        return cls._instance

    def __init__(self, max_cache_size: int = 1000):
        # Init logic moved to __new__ for Singleton pattern
        # This prevents re-initialization if called multiple times
        pass

    def normalize_query(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """
        Convert raw SQL to a parameterized template with named parameters.

        Uses sqlparse for robust tokenization. Replaces literals (strings, numbers)
        with ':pX' placeholders while preserving all other SQL structure.

        Example:
            Input: "SELECT * FROM users WHERE id = 123 AND name = 'Alice'"
            Output: ("SELECT * FROM users WHERE id = :p0 AND name = :p1", {'p0': 123, 'p1': 'Alice'})

        Handles:
            - Negative numbers: -100 → :p0 with value -100
            - Escaped quotes: 'O''Reilly' → :p0 with value "O'Reilly"
            - Double-quoted identifiers: "Order 1" preserved as-is
            - Array literals: ['a', 'b'] preserved as-is (dialect-specific)
            - SQL comments: automatically skipped by sqlparse
            - Scientific notation: 1e10 → :p0 with value 10000000000.0
        """
        params = {}
        counter = 0
        result_tokens = []

        # Parse SQL into tokens
        parsed = sqlparse.parse(sql)
        if not parsed:
            return sql, {}

        statement = parsed[0]

        def process_token(token):
            """Process a single token, replacing literals with parameters."""
            nonlocal counter

            # Skip comments entirely
            if token.ttype in (T.Comment.Single, T.Comment.Multiline):
                result_tokens.append(' ')  # Preserve whitespace
                return

            # Handle number literals (includes negative numbers like -100)
            if token.ttype in (T.Literal.Number.Integer, T.Literal.Number.Float):
                param_name = f"p{counter}"
                counter += 1
                val = token.value
                try:
                    if '.' in val or 'e' in val.lower():
                        params[param_name] = float(val)
                    else:
                        params[param_name] = int(val)
                except ValueError:
                    params[param_name] = val
                result_tokens.append(f":{param_name}")
                return

            # Handle single-quoted string literals only
            # Double-quoted strings (T.Literal.String.Symbol) are identifiers, not values
            if token.ttype == T.Literal.String.Single:
                param_name = f"p{counter}"
                counter += 1
                # Remove quotes and unescape doubled quotes
                val = token.value[1:-1].replace("''", "'")
                params[param_name] = val
                result_tokens.append(f":{param_name}")
                return

            # Preserve everything else as-is
            result_tokens.append(token.value)

        # Flatten and process all tokens
        for token in statement.flatten():
            process_token(token)

        template = ''.join(result_tokens)
        return template, params

    def get_compiled_query(self, sql: str) -> Tuple[Optional[CompiledQuery], Dict[str, Any]]:
        """
        Attempt to retrieve a compiled query for the given SQL.

        Returns:
            (CompiledQuery, params) if found, else (None, {})
        """
        template, params = self.normalize_query(sql)
        query_hash = self._generate_hash(template)

        with self._cache_lock:
            if query_hash in self.compiled_queries:
                self._stats["hits"] += 1
                # LRU: Move to end (most recently used)
                self.compiled_queries.move_to_end(query_hash)
                compiled = self.compiled_queries[query_hash]
                compiled.last_used_at = datetime.utcnow()
                compiled.execution_count += 1
                return compiled, params

            self._stats["misses"] += 1
            return None, params

    def compile_query(self, sql: str) -> Tuple[CompiledQuery, Dict[str, Any]]:
        """
        Create a new compiled query entry.

        This assumes the caller has already checked get_compiled_query
        and received None.
        """
        template, params = self.normalize_query(sql)
        query_hash = self._generate_hash(template)

        with self._cache_lock:
            # Enforce cache size limit (Simple LRU)
            if len(self.compiled_queries) >= self.max_cache_size:
                # OrderedDict pops FIFO if last=False (oldest item)
                self.compiled_queries.popitem(last=False)
                self._stats["evictions"] += 1

            compiled = CompiledQuery(
                sql_template=template,
                query_hash=query_hash,
                compiled_at=datetime.utcnow(),
                parameter_count=len(params)
            )

            self.compiled_queries[query_hash] = compiled
            return compiled, params

    def update_stats(self, compiled: CompiledQuery, execution_time_ms: float):
        """Update performance stats for a compiled query after execution"""
        # Moving average
        if compiled.execution_count <= 1:
            compiled.avg_execution_ms = execution_time_ms
        else:
            # Weight recent executions slightly more? standard avg for now
            total = (compiled.avg_execution_ms * (compiled.execution_count - 1)) + execution_time_ms
            compiled.avg_execution_ms = total / compiled.execution_count

    def get_stats(self) -> Dict[str, Any]:
        """Return compiler statistics"""
        with self._cache_lock:
            return {
                "cache_size": len(self.compiled_queries),
                "max_cache_size": self.max_cache_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": self._calculate_hit_rate()
            }

    def _generate_hash(self, template: str) -> str:
        """Generate MD5 hash of the template"""
        return hashlib.md5(template.encode('utf-8')).hexdigest()

    def _evict_lru(self):
        """Evict the least recently used item (Managed by OrderedDict now)"""
        pass # Deprecated by OrderedDict

    def _calculate_hit_rate(self) -> float:
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return self._stats["hits"] / total
