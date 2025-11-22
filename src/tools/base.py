"""
Base classes for the Tool System

This module provides the foundation for all tools in the Tool-Using Agent.
Follows patterns established in ColumnMapper and MappingCache.

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import time
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """
    Tool categories for organization and filtering.
    Similar to mapping_type in TableMapper.
    """
    SCHEMA = "schema"      # Schema exploration tools
    DATA = "data"          # Data sampling tools
    QUERY = "query"        # Query validation tools
    VALIDATION = "validation"  # SQL validation tools


@dataclass
class ToolResult:
    """
    Result from tool execution.

    Similar to ValidationResult in ResultPatternLearner.
    Tracks execution metadata for observability.
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tool_name: str = ""
    cache_hit: bool = False  # Whether result came from cache

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "tool_name": self.tool_name,
            "cache_hit": self.cache_hit,
        }

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAILED"
        cache = " (cached)" if self.cache_hit else ""
        return f"<ToolResult {self.tool_name}: {status} in {self.execution_time_ms:.1f}ms{cache}>"


@dataclass
class ToolDefinition:
    """
    Definition of a tool for LLM consumption and API documentation.

    Similar to how ColumnMapping stores mapping metadata.
    Can be cached with MappingCache for performance.
    """
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]  # JSON Schema format
    required_params: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    # Metrics (following ColumnMapper pattern)
    times_executed: int = 0
    success_rate: float = 1.0
    avg_execution_time_ms: float = 0.0

    def to_prompt_format(self) -> str:
        """
        Format tool definition for inclusion in LLM prompt.

        Example output:
        - search_schema(keyword: string, fuzzy: boolean): Search for tables and columns matching a keyword.
        """
        params_str = ", ".join(
            f"{k}: {v.get('type', 'any')}"
            for k, v in self.parameters.items()
        )
        return f"- {self.name}({params_str}): {self.description}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "examples": self.examples,
            "times_executed": self.times_executed,
            "success_rate": self.success_rate,
            "avg_execution_time_ms": self.avg_execution_time_ms,
        }

    def get_cache_key(self) -> str:
        """Cache key for tool definition (long TTL: 1 hour)"""
        return f"tool_def:{self.name}"


class BaseTool:
    """
    Base class for all tools.

    Subclasses should:
    1. Set class attributes: name, description, category
    2. Override execute() method
    3. Override get_definition() method

    Example:
        @register_tool
        class SearchSchemaTool(BaseTool):
            name = "search_schema"
            description = "Search for tables and columns"
            category = ToolCategory.SCHEMA

            async def execute(self, keyword: str) -> ToolResult:
                # Implementation
                pass
    """

    # Class attributes - override in subclasses
    name: str = "base_tool"
    description: str = "Base tool - override in subclass"
    category: ToolCategory = ToolCategory.SCHEMA

    # Caching configuration
    cacheable: bool = True      # Whether results can be cached
    cache_ttl: int = 300        # Default 5 minute TTL for results

    def __init__(
        self,
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
    ):
        """
        Initialize tool with database access.

        Args:
            session: Database session (async or sync)
            schema_inspector: SchemaInspector instance for schema access
            schema_cache: SchemaCache instance (from feedback-system-update)
            connection_id: Database connection ID for cache keys
        """
        self.session = session
        self.schema_inspector = schema_inspector
        self.schema_cache = schema_cache
        self.connection_id = connection_id

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given arguments.

        Override in subclasses to implement tool logic.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with execution outcome
        """
        raise NotImplementedError(f"Tool {self.name} must implement execute()")

    def get_definition(self) -> ToolDefinition:
        """
        Get tool definition for LLM prompt and API documentation.

        Override in subclasses to provide proper schema.
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={},
            required_params=[],
        )

    def get_cache_key(self, **kwargs) -> str:
        """
        Generate cache key for tool execution with given arguments.

        Uses MD5 hash of sorted arguments for consistent keys.
        Format: tool_result:{tool_name}:{args_hash}
        """
        # Sort and serialize arguments for consistent hashing
        args_str = json.dumps(kwargs, sort_keys=True, default=str)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]

        # Include connection_id if available for isolation
        if self.connection_id:
            return f"tool_result:{self.name}:{self.connection_id}:{args_hash}"
        return f"tool_result:{self.name}:{args_hash}"

    async def _get_schema(self) -> Dict[str, Any]:
        """
        Get database schema using SchemaCache if available.

        This leverages the SchemaCache from feedback-system-update
        for 99% reduction in schema introspection time.
        """
        if self.schema_cache and self.connection_id:
            # Use cached schema (< 1ms vs 50-500ms)
            return await self.schema_cache.get_schema(
                connection_id=self.connection_id,
                session=self.session,
                schema_inspector=self.schema_inspector,
            )
        elif self.schema_inspector and self.session:
            # Fall back to direct introspection
            return await self.schema_inspector.get_full_schema(self.session)
        else:
            raise ValueError("No schema_cache or schema_inspector available")

    def _measure_execution(self, start_time: float) -> float:
        """Calculate execution time in milliseconds"""
        return (time.time() - start_time) * 1000

    def set_context(
        self,
        session=None,
        schema_inspector=None,
        schema_cache=None,
        connection_id: Optional[int] = None,
    ):
        """
        Set execution context for the tool.

        This allows tools to be instantiated without context,
        then have context set before execution.
        Useful for testing and registry usage.

        Args:
            session: Database session (async or sync)
            schema_inspector: SchemaInspector instance
            schema_cache: SchemaCache instance
            connection_id: Database connection ID
        """
        if session is not None:
            self.session = session
        if schema_inspector is not None:
            self.schema_inspector = schema_inspector
        if schema_cache is not None:
            self.schema_cache = schema_cache
        if connection_id is not None:
            self.connection_id = connection_id

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
