"""
Tools API Endpoints

Provides REST API for tool management:
- GET /tools - List available tools
- GET /tools/stats - Get tool execution statistics
- POST /tools/{tool_name}/execute - Execute a tool
- POST /tools/{tool_name}/invalidate-cache - Invalidate tool cache

Follows patterns from mappings.py endpoint.

Part of Phase 3.1: Tool-Using Agent Implementation
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.database.connection import get_db
from src.tools import (
    get_tool_registry,
    get_all_tools,
    get_tools_by_category,
    ToolCategory,
)
from src.tools.base import ToolDefinition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ToolParameter(BaseModel):
    """Tool parameter definition"""
    type: str
    description: str
    default: Optional[Any] = None


class ToolResponse(BaseModel):
    """Tool definition response"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    required_params: List[str] = []
    cacheable: bool = True
    cache_ttl: int = 300


class ToolStatsResponse(BaseModel):
    """Tool execution statistics"""
    tool_name: str
    times_executed: int = 0
    successes: int = 0
    failures: int = 0
    success_rate: float = 1.0
    avg_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    last_executed: Optional[str] = None


class AllToolStatsResponse(BaseModel):
    """All tools statistics"""
    total_tools: int
    total_executions: int
    overall_success_rate: float
    by_tool: Dict[str, ToolStatsResponse]


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool"""
    connection_id: Optional[int] = Field(None, description="Database connection ID")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    use_cache: bool = Field(True, description="Whether to use caching")


class ToolExecuteResponse(BaseModel):
    """Tool execution response"""
    success: bool
    tool_name: str
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    cache_hit: bool = False


class ToolsPromptResponse(BaseModel):
    """Tools formatted for LLM prompt"""
    prompt: str
    tool_count: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=List[ToolResponse])
async def get_available_tools(
    category: Optional[str] = Query(None, description="Filter by category (schema, data, query, validation)")
):
    """
    Get all available tools, optionally filtered by category.

    Categories:
    - schema: Schema exploration tools (search_schema, get_table_info, etc.)
    - data: Data sampling tools (get_sample_data, get_column_values, count_rows)
    - query: Query validation tools (test_query, validate_sql, explain_query)
    - validation: SQL validation tools
    """
    try:
        # Get tools
        if category:
            try:
                cat = ToolCategory(category)
                tool_classes = get_tools_by_category(cat)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}. Valid: schema, data, query, validation"
                )
        else:
            tool_classes = list(get_all_tools().values())

        # Convert to response format
        tools = []
        for tool_class in tool_classes:
            tool = tool_class()
            definition = tool.get_definition()
            tools.append(ToolResponse(
                name=definition.name,
                description=definition.description,
                category=definition.category.value,
                parameters=definition.parameters,
                required_params=definition.required_params,
                cacheable=tool.cacheable,
                cache_ttl=tool.cache_ttl,
            ))

        return tools

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=AllToolStatsResponse)
async def get_tool_stats():
    """
    Get execution statistics for all tools.

    Returns aggregate stats and per-tool breakdown.
    """
    try:
        registry = get_tool_registry()
        stats = await registry.get_tool_stats()

        # Calculate aggregates
        total_executions = sum(s.get("times_executed", 0) for s in stats.values())
        total_successes = sum(s.get("successes", 0) for s in stats.values())

        overall_success_rate = (
            total_successes / total_executions if total_executions > 0 else 1.0
        )

        # Format per-tool stats
        by_tool = {}
        for name, tool_stats in stats.items():
            by_tool[name] = ToolStatsResponse(
                tool_name=name,
                times_executed=tool_stats.get("times_executed", 0),
                successes=tool_stats.get("successes", 0),
                failures=tool_stats.get("failures", 0),
                success_rate=tool_stats.get("success_rate", 1.0),
                avg_time_ms=tool_stats.get("avg_time_ms", 0.0),
                cache_hit_rate=tool_stats.get("cache_hit_rate", 0.0),
                last_executed=tool_stats.get("last_executed"),
            )

        return AllToolStatsResponse(
            total_tools=len(get_all_tools()),
            total_executions=total_executions,
            overall_success_rate=overall_success_rate,
            by_tool=by_tool,
        )

    except Exception as e:
        logger.error(f"Failed to get tool stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{tool_name}", response_model=ToolStatsResponse)
async def get_single_tool_stats(tool_name: str):
    """Get execution statistics for a specific tool."""
    try:
        # Verify tool exists
        all_tools = get_all_tools()
        if tool_name not in all_tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found. Available: {list(all_tools.keys())}"
            )

        registry = get_tool_registry()
        stats = await registry.get_tool_stats(tool_name)

        return ToolStatsResponse(
            tool_name=tool_name,
            times_executed=stats.get("times_executed", 0),
            successes=stats.get("successes", 0),
            failures=stats.get("failures", 0),
            success_rate=stats.get("success_rate", 1.0),
            avg_time_ms=stats.get("avg_time_ms", 0.0),
            cache_hit_rate=stats.get("cache_hit_rate", 0.0),
            last_executed=stats.get("last_executed"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt", response_model=ToolsPromptResponse)
async def get_tools_prompt(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get tools formatted for inclusion in LLM prompt.

    Returns a formatted string listing all available tools and their parameters.
    """
    try:
        registry = get_tool_registry()

        cat = None
        if category:
            try:
                cat = ToolCategory(category)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}"
                )

        prompt = registry.format_tools_for_prompt(category=cat)
        tool_count = len(get_tools_by_category(cat) if cat else get_all_tools())

        return ToolsPromptResponse(
            prompt=prompt,
            tool_count=tool_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tools prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tool_name}/invalidate-cache")
async def invalidate_tool_cache(tool_name: str):
    """
    Invalidate the cache for a specific tool.

    Useful when schema or data changes and cached results are stale.
    """
    try:
        # Verify tool exists
        all_tools = get_all_tools()
        if tool_name not in all_tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found. Available: {list(all_tools.keys())}"
            )

        registry = get_tool_registry()
        registry.invalidate_tool_cache(tool_name)

        return {
            "message": f"Cache invalidated for tool: {tool_name}",
            "tool_name": tool_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invalidate cache for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate-all-cache")
async def invalidate_all_tool_cache():
    """
    Invalidate cache for all tools.

    Use sparingly - invalidates all cached tool results.
    """
    try:
        registry = get_tool_registry()
        registry.invalidate_tool_cache()  # None = all tools

        return {
            "message": "Cache invalidated for all tools",
        }

    except Exception as e:
        logger.error(f"Failed to invalidate all tool cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Note: Tool execution endpoint is intentionally NOT included here
# because tools require database session and schema_inspector which
# should come from the query context, not a standalone API call.
# Use the ToolUsingAgent within the query endpoint instead.
