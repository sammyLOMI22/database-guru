"""Abstract base classes for NoSQL database support.

Each NoSQL database implements these interfaces to provide:
- Schema introspection (document sampling, key analysis, mapping inspection)
- Query generation (NL -> native query language via LLM)
- Query execution (run generated queries safely)
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Shared client pool lifecycle management ──────────────────────────────

MAX_POOL_SIZE = 20
IDLE_TTL_SECONDS = 1800  # 30 minutes


class NoSQLClientPoolMixin:
    """Mixin providing TTL eviction and max-size enforcement for NoSQL client pools.

    Each pool stores entries as tuples where the **last element** is a
    ``datetime`` (last-accessed timestamp).  Subclasses must set
    ``_pool_dict`` to point at their internal dict and implement
    ``_close_entry(key, entry)`` to perform database-specific cleanup.

    Usage in subclass ``get_client()`` / ``get_session()``:
        self._cleanup_stale()          # prune idle entries
        ...
        self._enforce_max_size()       # after inserting a new entry
    """

    # Subclasses must assign this in __init__
    _pool_dict: Dict[int, Tuple] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _last_used(self, entry: Tuple) -> datetime:
        """Extract the last-used timestamp (always the last tuple element)."""
        return entry[-1]

    def _cleanup_stale(self) -> List[int]:
        """Remove entries that have been idle longer than IDLE_TTL_SECONDS.

        Returns list of evicted connection IDs.
        """
        now = self._now()
        stale_keys = []
        for key, entry in list(self._pool_dict.items()):
            idle = (now - self._last_used(entry)).total_seconds()
            if idle > IDLE_TTL_SECONDS:
                stale_keys.append(key)

        for key in stale_keys:
            entry = self._pool_dict.pop(key)
            self._close_entry_sync(key, entry)
            logger.info(f"Evicted idle NoSQL client for connection {key}")

        return stale_keys

    def _enforce_max_size(self) -> None:
        """If pool exceeds MAX_POOL_SIZE, evict the least-recently-used entry."""
        while len(self._pool_dict) > MAX_POOL_SIZE:
            lru_key = min(self._pool_dict, key=lambda k: self._last_used(self._pool_dict[k]))
            entry = self._pool_dict.pop(lru_key)
            self._close_entry_sync(lru_key, entry)
            logger.info(f"Evicted LRU NoSQL client for connection {lru_key} (pool full)")

    def _close_entry_sync(self, key: int, entry: Tuple) -> None:
        """Close a pool entry. Override for database-specific cleanup.

        This is called synchronously — for async cleanup (e.g. Redis aclose),
        schedule via fire-and-forget or override in the subclass.
        """
        pass


class NoSQLSchemaInspector(ABC):
    """Base class for NoSQL schema introspection.

    Implementations produce dicts compatible with DatabaseConnection.schema_cache JSON.
    """

    @abstractmethod
    async def get_schema(self, connection: Any) -> Dict[str, Any]:
        """Inspect the NoSQL database and return schema information.

        Returns:
            Dict with structure compatible with SchemaCache format:
            {
                "tables": {
                    "collection_or_index_name": {
                        "columns": [{"name": str, "type": str, "nullable": bool}],
                        "row_count": int (estimated),
                    }
                },
                "database_type": str,
            }
        """
        ...

    @abstractmethod
    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Convert schema dict to a string suitable for LLM prompts.

        Returns:
            Human-readable schema description for the query generation prompt.
        """
        ...


class NoSQLQueryGenerator(ABC):
    """Base class for NoSQL query generation via LLM."""

    @abstractmethod
    async def generate(
        self,
        question: str,
        schema: str,
        model: Optional[str] = None,
    ) -> Any:
        """Generate a native query from natural language.

        Args:
            question: Natural language question
            schema: Schema string from format_schema_for_llm()
            model: Optional LLM model override

        Returns:
            Type-specific query object (MQLQuery, RedisCommand, etc.)
        """
        ...

    @abstractmethod
    async def generate_with_error_context(
        self,
        question: str,
        schema: str,
        previous_query: str,
        error_message: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Re-generate a query with error context for self-correction.

        Args:
            question: Original natural language question
            schema: Schema string from format_schema_for_llm()
            previous_query: Display string of the failed query
            error_message: Error from the previous attempt
            model: Optional LLM model override

        Returns:
            Type-specific query object (same as generate())
        """
        ...

    @abstractmethod
    def query_to_display_string(self, query: Any) -> str:
        """Convert the generated query to a human-readable string.

        This string is stored in QueryHistory.generated_sql and shown in the UI.
        """
        ...


# ── Shared schema caching constants ──────────────────────────────────────

MAX_RETRIES = 3
SCHEMA_TTL_SECONDS = 1800  # 30 minutes


class NoSQLHandler(ABC):
    """Base handler that orchestrates schema → generation → execution → retry.

    Each NoSQL database implements this to provide the full query flow.
    Subclasses implement handle() to set up DB-specific pool/inspector/generator/
    executor, then delegate to the shared _get_schema(),
    _generate_and_execute_with_retry(), and _build_error_result() methods.
    """

    @abstractmethod
    async def handle(
        self,
        question: str,
        connection: Any,
        model: Optional[str] = None,
        allow_write: bool = False,
        row_limit: int = 1000,
        db: Optional[Any] = None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a natural language query against a NoSQL database.

        Returns:
            Dict matching generate_and_execute_with_retry() contract:
            {
                "success": bool,
                "sql": str,  # display string of the native query
                "result": {
                    "success": bool,
                    "data": List[Dict],
                    "columns": List[str],
                    "row_count": int,
                    "execution_time_ms": float,
                    "truncated": bool,
                    "error": Optional[str],
                },
                "attempts": List,
                "self_corrected": bool,
                "total_attempts": int,
                "error": Optional[str],
                "agent_trace": Dict,
                "model_used": str,
            }
        """
        ...

    async def _get_schema(
        self,
        connection: Any,
        inspector: "NoSQLSchemaInspector",
        db: Optional[Any],
        trace: Any,
    ) -> Dict[str, Any]:
        """Get schema from cache or inspect fresh (shared across all handlers)."""
        cached = connection.schema_cache
        if cached and isinstance(cached, dict) and cached.get("tables"):
            updated_at = connection.schema_updated_at
            if updated_at:
                age_seconds = (datetime.utcnow() - updated_at).total_seconds()
                if age_seconds < SCHEMA_TTL_SECONDS:
                    tables = cached.get("tables", {})
                    trace.add_step(
                        "analysis",
                        f"Using cached schema ({len(tables)} collections/tables, {int(age_seconds)}s old)",
                    )
                    return cached

        trace.add_step("analysis", "Inspecting database schema...")
        schema_dict = await inspector.get_schema()
        tables = schema_dict.get("tables", {})
        trace.add_step(
            "analysis",
            f"Found {len(tables)} collections/tables: {', '.join(list(tables.keys())[:10])}",
        )

        # Persist to DatabaseConnection.schema_cache
        if db:
            try:
                connection.schema_cache = schema_dict
                connection.schema_updated_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to cache schema: {e}")

        return schema_dict

    async def _generate_and_execute_with_retry(
        self,
        question: str,
        schema_str: str,
        generator: "NoSQLQueryGenerator",
        executor: Any,
        trace: Any,
        error_classifier: Callable[[str], Tuple[Any, str]],
        model: Optional[str] = None,
        db: Optional[Any] = None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a native query and execute with up to MAX_RETRIES attempts.

        Works with any NoSQL generator/executor pair. The error_classifier
        is a callable(error_msg) -> (ErrorType, hint) specific to each DB.
        """
        last_query_str = ""
        last_error = ""
        attempts: List[Dict[str, Any]] = []

        for attempt_num in range(1, MAX_RETRIES + 1):
            trace.add_step(
                "attempt_start",
                f"Attempt {attempt_num}/{MAX_RETRIES}",
                metadata={"attempt": attempt_num},
            )

            # Generate query
            try:
                if attempt_num == 1:
                    query = await generator.generate(
                        question=question,
                        schema=schema_str,
                        model=model,
                        db=db,
                        query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
                else:
                    query = await generator.generate_with_error_context(
                        question=question,
                        schema=schema_str,
                        previous_query=last_query_str,
                        error_message=last_error,
                        model=model,
                        db=db,
                        query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                    )
            except Exception as e:
                logger.warning(f"Query generation failed (attempt {attempt_num}): {e}")
                trace.add_step("error", f"Generation failed: {e}")
                last_error = str(e)
                attempts.append({
                    "attempt": attempt_num,
                    "query": "",
                    "error": str(e),
                    "success": False,
                })
                continue

            query_str = generator.query_to_display_string(query)
            last_query_str = query_str
            trace.add_step("generation", f"Generated: {query_str[:120]}")

            # Execute
            result = await executor.execute(query)

            if result["success"]:
                trace.add_step(
                    "success",
                    f"Returned {result['row_count']} results in {result['execution_time_ms']:.0f}ms",
                )
                attempts.append({
                    "attempt": attempt_num,
                    "query": query_str,
                    "success": True,
                    "row_count": result["row_count"],
                })

                return {
                    "success": True,
                    "sql": query_str,
                    "result": result,
                    "attempts": attempts,
                    "self_corrected": attempt_num > 1,
                    "total_attempts": attempt_num,
                    "error": None,
                    "agent_trace": trace.to_dict(),
                    "model_used": model or "default",
                    "query_plan": None,
                    "verification_warnings": [],
                    "used_planning": False,
                }

            # Query failed — classify error for retry
            error_msg = result.get("error", "Unknown error")
            error_type, hint = error_classifier(error_msg)
            last_error = f"{error_msg}\nHint: {hint}"

            error_type_value = error_type.value if hasattr(error_type, "value") else str(error_type)
            trace.add_step(
                "error",
                f"Query failed: {error_msg[:100]}",
                metadata={"error_type": error_type_value, "hint": hint},
            )
            attempts.append({
                "attempt": attempt_num,
                "query": query_str,
                "error": error_msg,
                "error_type": error_type_value,
                "success": False,
            })

        # All attempts exhausted
        trace.add_step("error", f"All {MAX_RETRIES} attempts failed")
        return self._build_error_result(
            f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
            trace,
            sql=last_query_str,
            attempts=attempts,
        )

    def _build_error_result(
        self,
        error: str,
        trace: Any,
        sql: str = "",
        attempts: Optional[List] = None,
    ) -> Dict[str, Any]:
        """Build a standardized error result dict."""
        return {
            "success": False,
            "sql": sql,
            "result": None,
            "attempts": attempts or [],
            "self_corrected": False,
            "total_attempts": len(attempts) if attempts else 0,
            "error": error,
            "agent_trace": trace.to_dict(),
            "model_used": "default",
            "query_plan": None,
            "verification_warnings": [],
            "used_planning": False,
        }
