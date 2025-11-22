"""
Tool Registry - Manages tool registration, execution, and metrics.

Follows patterns established by ColumnMapper and TableMapper:
- Uses MappingCache for caching (no new cache implementation)
- Tracks metrics: times_executed, success_rate, avg_execution_time_ms
- Provides stats and filtering similar to mappings API

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import asyncio
import logging
from typing import Dict, List, Optional, Type, Any
from datetime import datetime

from src.tools.base import BaseTool, ToolDefinition, ToolResult, ToolCategory
from src.llm.mapping_cache import get_mapping_cache

logger = logging.getLogger(__name__)

# Global tool registry (singleton pattern like mapping cache)
_TOOL_REGISTRY: Dict[str, Type[BaseTool]] = {}


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """
    Decorator to register a tool class.

    Usage:
        @register_tool
        class SearchSchemaTool(BaseTool):
            name = "search_schema"
            ...

    Similar to how ColumnMapper registers mappings.
    """
    if not hasattr(tool_class, 'name') or not tool_class.name:
        raise ValueError(f"Tool class {tool_class.__name__} must have a 'name' attribute")

    _TOOL_REGISTRY[tool_class.name] = tool_class
    logger.info(f"Registered tool: {tool_class.name} ({tool_class.category.value})")
    return tool_class


def get_tool(name: str) -> Optional[Type[BaseTool]]:
    """Get a tool class by name"""
    return _TOOL_REGISTRY.get(name)


def get_all_tools() -> Dict[str, Type[BaseTool]]:
    """Get all registered tools"""
    return _TOOL_REGISTRY.copy()


def get_tools_by_category(category: ToolCategory) -> List[Type[BaseTool]]:
    """Get tools filtered by category"""
    return [
        tool_class for tool_class in _TOOL_REGISTRY.values()
        if tool_class.category == category
    ]


class ToolRegistry:
    """
    Manages tool execution with caching and metrics tracking.

    Design patterns from existing infrastructure:
    - MappingCache: For caching tool results (no new cache!)
    - ColumnMapper: For metrics tracking (times_executed, success_rate)
    - ResultPatternLearner: For effectiveness tracking

    Usage:
        registry = ToolRegistry()
        result = await registry.execute_tool(
            "search_schema",
            session=db_session,
            schema_inspector=inspector,
            keyword="customer"
        )
    """

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize the tool registry.

        Args:
            max_concurrent: Maximum concurrent tool executions
        """
        self._cache = get_mapping_cache()  # Reuse existing cache!
        self._tool_instances: Dict[str, BaseTool] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

        logger.info(f"ToolRegistry initialized with max_concurrent={max_concurrent}")

    def _get_tool_instance(
        self,
        tool_name: str,
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
    ) -> Optional[BaseTool]:
        """
        Get or create a tool instance.

        Tool instances are cached per session to avoid recreation.
        """
        # Create unique key for this tool + session combination
        cache_key = f"{tool_name}:{id(session)}:{connection_id or 0}"

        if cache_key not in self._tool_instances:
            tool_class = get_tool(tool_name)
            if tool_class:
                self._tool_instances[cache_key] = tool_class(
                    session=session,
                    schema_inspector=schema_inspector,
                    schema_cache=schema_cache,
                    connection_id=connection_id,
                )
            else:
                return None

        return self._tool_instances.get(cache_key)

    async def execute_tool(
        self,
        tool_name: str,
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
        use_cache: bool = True,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool with caching and metrics tracking.

        Follows ColumnMapper.apply_mappings() pattern:
        1. Check cache first
        2. Execute if cache miss
        3. Cache successful results
        4. Record metrics

        Args:
            tool_name: Name of the tool to execute
            session: Database session
            schema_inspector: SchemaInspector instance
            schema_cache: SchemaCache instance (from feedback-system-update)
            connection_id: Database connection ID
            use_cache: Whether to use caching
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with execution outcome
        """
        import time
        start_time = time.time()

        # Get tool instance
        tool = self._get_tool_instance(
            tool_name,
            session=session,
            schema_inspector=schema_inspector,
            schema_cache=schema_cache,
            connection_id=connection_id,
        )

        if not tool:
            logger.warning(f"Unknown tool: {tool_name}")
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}. Available: {list(_TOOL_REGISTRY.keys())}",
                tool_name=tool_name,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Check cache first (like _get_applicable_mappings in ColumnMapper)
        if use_cache and tool.cacheable:
            cache_key = tool.get_cache_key(**kwargs)
            cached_result = self._cache.get(cache_key)

            if cached_result is not None:
                logger.debug(f"Cache hit for tool: {tool_name}")
                # Return cached result with cache_hit flag
                cached_result.cache_hit = True
                cached_result.execution_time_ms = (time.time() - start_time) * 1000
                return cached_result

        # Execute tool with semaphore for concurrency control
        async with self._semaphore:
            try:
                logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
                result = await tool.execute(**kwargs)
                result.execution_time_ms = (time.time() - start_time) * 1000
                result.tool_name = tool_name

                # Cache successful results
                if use_cache and tool.cacheable and result.success:
                    cache_key = tool.get_cache_key(**kwargs)
                    self._cache.set(cache_key, result, ttl=tool.cache_ttl)
                    logger.debug(f"Cached result for {tool_name} (TTL: {tool.cache_ttl}s)")

                # Record metrics (like _record_mapping_usage in ColumnMapper)
                await self._record_execution(tool_name, result, kwargs)

                logger.info(
                    f"Tool {tool_name} completed in {result.execution_time_ms:.1f}ms "
                    f"({'success' if result.success else 'failed'})"
                )
                return result

            except Exception as e:
                logger.error(f"Tool {tool_name} failed with exception: {e}")
                error_result = ToolResult(
                    success=False,
                    error=str(e),
                    tool_name=tool_name,
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
                await self._record_execution(tool_name, error_result, kwargs)
                return error_result

    async def execute_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_calls: List of {"tool_name": str, "kwargs": dict}
            session: Database session
            schema_inspector: SchemaInspector instance
            schema_cache: SchemaCache instance
            connection_id: Database connection ID

        Returns:
            List of ToolResults in same order as tool_calls
        """
        tasks = [
            self.execute_tool(
                tool_name=call["tool_name"],
                session=session,
                schema_inspector=schema_inspector,
                schema_cache=schema_cache,
                connection_id=connection_id,
                **call.get("kwargs", {})
            )
            for call in tool_calls
        ]

        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _record_execution(
        self,
        tool_name: str,
        result: ToolResult,
        args: Dict[str, Any]
    ):
        """
        Record tool execution for metrics tracking.

        Follows ColumnMapper._record_mapping_usage() pattern:
        - Update in-memory stats (cached)
        - Track success rate, execution time
        """
        stats_key = f"tool_stats:{tool_name}"
        stats = self._cache.get(stats_key) or {
            "tool_name": tool_name,
            "times_executed": 0,
            "successes": 0,
            "failures": 0,
            "total_time_ms": 0.0,
            "cache_hits": 0,
            "last_executed": None,
        }

        # Update stats
        stats["times_executed"] += 1
        if result.success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        if result.cache_hit:
            stats["cache_hits"] += 1
        stats["total_time_ms"] += result.execution_time_ms
        stats["success_rate"] = stats["successes"] / stats["times_executed"]
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["times_executed"]
        stats["cache_hit_rate"] = stats["cache_hits"] / stats["times_executed"]
        stats["last_executed"] = datetime.utcnow().isoformat()

        # Cache stats with longer TTL (1 hour)
        self._cache.set(stats_key, stats, ttl=3600)

    async def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get tool execution statistics.

        Follows ColumnMapper.get_mapping_stats() pattern.

        Args:
            tool_name: Optional specific tool name

        Returns:
            Statistics dictionary
        """
        if tool_name:
            stats_key = f"tool_stats:{tool_name}"
            return self._cache.get(stats_key) or {
                "tool_name": tool_name,
                "times_executed": 0,
                "success_rate": 1.0,
            }

        # Get stats for all tools
        all_stats = {}
        for name in _TOOL_REGISTRY.keys():
            stats_key = f"tool_stats:{name}"
            stats = self._cache.get(stats_key)
            if stats:
                all_stats[name] = stats
            else:
                all_stats[name] = {
                    "tool_name": name,
                    "times_executed": 0,
                    "success_rate": 1.0,
                }

        return all_stats

    def get_available_tools(
        self,
        category: Optional[ToolCategory] = None
    ) -> List[ToolDefinition]:
        """
        Get definitions of all available tools.

        Args:
            category: Optional category filter

        Returns:
            List of ToolDefinitions
        """
        definitions = []
        for name, tool_class in _TOOL_REGISTRY.items():
            if category and tool_class.category != category:
                continue

            tool = tool_class()
            definitions.append(tool.get_definition())

        return definitions

    def format_tools_for_prompt(
        self,
        category: Optional[ToolCategory] = None
    ) -> str:
        """
        Format available tools for inclusion in LLM prompt.

        Args:
            category: Optional category filter

        Returns:
            Formatted string for prompt
        """
        tools = self.get_available_tools(category=category)

        if not tools:
            return "No tools available."

        lines = ["Available tools:"]
        for tool in tools:
            lines.append(tool.to_prompt_format())

        return "\n".join(lines)

    def invalidate_tool_cache(self, tool_name: Optional[str] = None):
        """
        Invalidate tool result caches.

        Uses MappingCache.invalidate_pattern() for efficient bulk invalidation.

        Args:
            tool_name: Optional specific tool, or None for all tools
        """
        if tool_name:
            pattern = f"tool_result:{tool_name}:*"
        else:
            pattern = "tool_result:*"

        self._cache.invalidate_pattern(pattern)
        logger.info(f"Invalidated cache pattern: {pattern}")

    def clear_tool_instances(self):
        """Clear cached tool instances (useful for testing)"""
        self._tool_instances.clear()
        logger.info("Cleared all tool instances")


# Convenience function for getting a global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global ToolRegistry instance.

    Follows singleton pattern like get_mapping_cache().
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry():
    """Reset the global registry (for testing)"""
    global _global_registry
    if _global_registry:
        _global_registry.clear_tool_instances()
    _global_registry = None
