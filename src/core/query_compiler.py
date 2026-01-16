"""
Query Compiler Module
Handles normalization, compilation, and caching of SQL queries for performance optimization.
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import logging
import threading
from collections import OrderedDict

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

        Replaces literals (strings, numbers) with ':pX' placeholders.
        Returns tuple of (template_sql, params_dict).

        Example:
            Input: "SELECT * FROM users WHERE id = 123 AND name = 'Alice'"
            Output: ("SELECT * FROM users WHERE id = :p0 AND name = :p1", {'p0': 123, 'p1': 'Alice'})
        """
        params = {}
        counter = 0

        def replace_token(match):
            nonlocal counter

            # Check which group matched
            # Group 1: Double quoted identifier (e.g. "Order 1") - IGNORE
            if match.group(1) is not None:
                return match.group(1)

            param_name = f"p{counter}"
            counter += 1

            # Group 2: Single quoted string (e.g. 'Alice' or 'O''Reilly')
            if match.group(2) is not None:
                # String match - extract content (group 3) and unescape quotes
                val = match.group(3).replace("''", "'")
                params[param_name] = val
                return f":{param_name}"

            # Group 4: Number (e.g. 123 or 99.99)
            if match.group(4) is not None:
                # Number match
                val = match.group(4)
                try:
                    if '.' in val:
                        params[param_name] = float(val)
                    else:
                        params[param_name] = int(val)
                except ValueError:
                    params[param_name] = val
                return f":{param_name}"

            return match.group(0)

        # Improved Regex:
        # ("[^"]*")             -> Group 1: Double-quoted identifiers (ignore)
        # |                     -> OR
        # ('((?:''|[^'])*)')    -> Group 2: Single-quoted strings (parameterize). Group 3 is content.
        #                          Handles escaped quotes like 'O''Reilly'.
        # |                     -> OR
        # (\b\d+(?:\.\d+)?\b)   -> Group 4: Numbers (parameterize).
        pattern = r'("[^"]*")|(\'((?:\'\'|[^\'])*)\')|(\b\d+(?:\.\d+)?\b)'

        template = re.sub(pattern, replace_token, sql)

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
