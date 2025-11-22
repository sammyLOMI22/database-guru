"""
Tool System for Database Guru

This module provides the Tool-Using Agent infrastructure:
- Base classes for tools (BaseTool, ToolResult, ToolDefinition)
- Tool registry with caching and metrics
- Schema exploration tools
- Data sampling tools
- Query validation tools

Part of Phase 3.1: Tool-Using Agent Implementation

Usage:
    from src.tools import get_tool_registry, ToolCategory

    # Get registry
    registry = get_tool_registry()

    # Execute a tool
    result = await registry.execute_tool(
        "search_schema",
        session=db_session,
        schema_inspector=inspector,
        keyword="customer"
    )

    # Get all available tools
    tools = registry.get_available_tools()

    # Format for LLM prompt
    prompt_text = registry.format_tools_for_prompt()
"""

# Base classes
from src.tools.base import (
    BaseTool,
    ToolResult,
    ToolDefinition,
    ToolCategory,
)

# Registry
from src.tools.tool_registry import (
    register_tool,
    get_tool,
    get_all_tools,
    get_tools_by_category,
    ToolRegistry,
    get_tool_registry,
    reset_tool_registry,
)

__all__ = [
    # Base classes
    "BaseTool",
    "ToolResult",
    "ToolDefinition",
    "ToolCategory",
    # Registry
    "register_tool",
    "get_tool",
    "get_all_tools",
    "get_tools_by_category",
    "ToolRegistry",
    "get_tool_registry",
    "reset_tool_registry",
]

# Import tool modules to trigger registration
# These are imported at the end to avoid circular imports
def _register_all_tools():
    """Import all tool modules to register them"""
    from src.tools import schema_tools  # noqa: F401
    from src.tools import data_tools    # noqa: F401
    from src.tools import query_tools   # noqa: F401


# Auto-register tools on module import
_register_all_tools()
