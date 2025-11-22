# Phase 3 Implementation Plan: Tool-Using Agent + LangGraph Integration

> **Created**: 2025-11-21
> **Updated**: 2025-11-21 (Phase 3.1 COMPLETE!)
> **Branch**: `feedback-system-update` (merged to main)
> **Status**: Phase 3.1 COMPLETE, Phase 3.2 PENDING

## Overview

This document provides a detailed implementation plan for Phase 3 features:
1. **Phase 3.1: Tool-Using Agent** (Week 1) - Schema exploration and query validation tools **COMPLETE!**
2. **Phase 3.2: LangGraph Integration** (Week 2-3) - Multi-agent orchestration with state management

The key insight: **Build tools first**, so both the current architecture and future LangGraph integration benefit.

---

## Phase 3.1 Status: COMPLETE (November 21, 2025)

All Phase 3.1 deliverables have been implemented and tested:

| Deliverable | Status | Details |
|-------------|--------|---------|
| Tool base classes | COMPLETE | `src/tools/base.py` - BaseTool, ToolResult, ToolDefinition, ToolCategory |
| Tool Registry | COMPLETE | `src/tools/tool_registry.py` - Follows ColumnMapper pattern, uses MappingCache |
| Schema Tools (4) | COMPLETE | search_schema, get_table_info, find_columns, get_relationships |
| Data Tools (3) | COMPLETE | get_sample_data, get_column_values, count_rows |
| Query Tools (3) | COMPLETE | test_query, validate_sql, explain_query |
| Tool-Using Agent | COMPLETE | `src/llm/tool_using_agent.py` - Question analysis, tool execution, context building |
| REST API | COMPLETE | `src/api/endpoints/tools.py` - 6 endpoints for tool management |
| Integration | COMPLETE | 4th parallel fix strategy in self_correcting_agent.py |
| Tests | COMPLETE | 26 tests passing (100% coverage) |
| Documentation | COMPLETE | TOOL_USING_AGENT.md, CLAUDE.md updated, README updated |

---

## IMPORTANT: Infrastructure from `feedback-system-update`

The recently merged `feedback-system-update` branch provides infrastructure we **MUST leverage**:

### Available Infrastructure to Reuse

| Component | Location | Reuse For |
|-----------|----------|-----------|
| **MappingCache** | `src/llm/mapping_cache.py` | Tool definition & result caching |
| **SchemaCache** | `src/core/schema_cache.py` | Fast schema access for tools |
| **ColumnMapper** | `src/llm/column_mapper.py` | Pattern for ToolRegistry design |
| **ResultPatternLearner** | `src/llm/result_pattern_learner.py` | Tool effectiveness tracking |
| **Mappings API** | `src/api/endpoints/mappings.py` | API endpoint patterns |

### Key Patterns to Follow

```python
# 1. Singleton Cache Pattern (from mapping_cache.py)
from src.llm.mapping_cache import get_mapping_cache
cache = get_mapping_cache()

# 2. TTL-based caching with metrics
cached = cache.get("tool_result:search_schema:customer")
if cached is None:
    result = await execute_tool(...)
    cache.set("tool_result:search_schema:customer", result, ttl=300)

# 3. Pattern-based invalidation
cache.invalidate_pattern("tool_result:*")  # Invalidate all tool results

# 4. Thread-safe with RLock (already handled by MappingCache)
```

### Cache Key Strategy for Tools

```
tool_def:{tool_name}                    # Tool definitions (long TTL: 3600s)
tool_result:{tool_name}:{args_hash}     # Execution results (short TTL: 300s)
tool_stats:{tool_name}                  # Usage statistics (medium TTL: 600s)
```

### Database Tables Available

- `column_mappings` - Pattern for tool execution tracking
- `table_mappings` - Pattern for tool registry
- `result_validation_patterns` - Pattern for tool effectiveness

---

## Phase 3.1: Tool-Using Agent (Week 1)

### Goal
Enable agents to dynamically explore schemas, test queries, and gather information before generating SQL.

### Architecture (Updated to Use Existing Infrastructure)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Tool-Using Agent                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Schema Tools │  │  Data Tools  │  │ Query Tools  │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │search_schema │  │get_sample    │  │test_query    │          │
│  │get_table_info│  │get_col_values│  │explain_query │          │
│  │find_columns  │  │count_rows    │  │validate_sql  │          │
│  │get_relations │  │preview_table │  │suggest_fixes │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        ToolRegistry (follows ColumnMapper pattern)       │   │
│  │  - Registers tools with @register_tool decorator         │   │
│  │  - Tracks metrics: times_executed, success_rate          │   │
│  │  - Uses MappingCache for caching (no new cache!)        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        Uses Existing Infrastructure:                     │   │
│  │  - MappingCache (from mapping_cache.py)                 │   │
│  │  - SchemaCache (from schema_cache.py)                   │   │
│  │  - API patterns (from mappings.py)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure (Updated)

```
src/
├── tools/                          # NEW: Tool implementations
│   ├── __init__.py                 # Registry + exports
│   ├── base.py                     # BaseTool, ToolResult (like ColumnMapping)
│   ├── schema_tools.py             # 4 schema tools (uses SchemaCache!)
│   ├── data_tools.py               # 3 data tools
│   ├── query_tools.py              # 3 query tools
│   └── tool_registry.py            # NEW: Follows ColumnMapper pattern
├── llm/
│   ├── mapping_cache.py            # EXISTING: Reuse for tool caching
│   ├── column_mapper.py            # EXISTING: Pattern to follow
│   └── tool_using_agent.py         # NEW: Main tool-using agent
├── core/
│   └── schema_cache.py             # EXISTING: Reuse for schema access
└── api/
    └── endpoints/
        ├── mappings.py             # EXISTING: Pattern to follow
        └── tools.py                # NEW: Tool API (follows mappings.py)
```

### What We DON'T Need to Build (Already Exists)

| Component | Status | Location |
|-----------|--------|----------|
| Thread-safe cache | DONE | `src/llm/mapping_cache.py` |
| Schema caching | DONE | `src/core/schema_cache.py` |
| API patterns | DONE | `src/api/endpoints/mappings.py` |
| Metrics tracking | DONE | `times_applied`, `success_rate` pattern |
| Pattern invalidation | DONE | `cache.invalidate_pattern()` |

### Day 1: Core Tool Infrastructure

#### 1.1 Base Tool Classes (`src/tools/base.py`)

```python
"""Base classes for tool system"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Tool categories for organization"""
    SCHEMA = "schema"
    DATA = "data"
    QUERY = "query"
    VALIDATION = "validation"


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tool_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "tool_name": self.tool_name,
        }


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM consumption"""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]  # JSON Schema format
    required_params: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_prompt_format(self) -> str:
        """Format tool for inclusion in LLM prompt"""
        params_str = ", ".join(
            f"{k}: {v.get('type', 'any')}"
            for k, v in self.parameters.items()
        )
        return f"- {self.name}({params_str}): {self.description}"


class BaseTool:
    """Base class for all tools"""

    name: str = "base_tool"
    description: str = "Base tool"
    category: ToolCategory = ToolCategory.SCHEMA

    def __init__(self, session=None, schema_inspector=None):
        self.session = session
        self.schema_inspector = schema_inspector

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool - override in subclasses"""
        raise NotImplementedError

    def get_definition(self) -> ToolDefinition:
        """Get tool definition for LLM"""
        raise NotImplementedError
```

#### 1.2 Tool Registry (`src/tools/__init__.py`)

```python
"""Tool registry and exports"""
from typing import Dict, List, Type
from .base import BaseTool, ToolDefinition, ToolResult, ToolCategory

# Registry of all available tools
_TOOL_REGISTRY: Dict[str, Type[BaseTool]] = {}


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """Decorator to register a tool"""
    _TOOL_REGISTRY[tool_class.name] = tool_class
    return tool_class


def get_tool(name: str) -> Type[BaseTool]:
    """Get a tool class by name"""
    return _TOOL_REGISTRY.get(name)


def get_all_tools() -> Dict[str, Type[BaseTool]]:
    """Get all registered tools"""
    return _TOOL_REGISTRY.copy()


def get_tools_by_category(category: ToolCategory) -> List[Type[BaseTool]]:
    """Get tools filtered by category"""
    return [
        tool for tool in _TOOL_REGISTRY.values()
        if tool.category == category
    ]


# Import tools to register them
from .schema_tools import *
from .data_tools import *
from .query_tools import *
```

### Day 2: Schema Tools (`src/tools/schema_tools.py`)

```python
"""Schema exploration tools"""
import asyncio
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher
from .base import BaseTool, ToolResult, ToolDefinition, ToolCategory
from . import register_tool


@register_tool
class SearchSchemaTool(BaseTool):
    """Search for tables/columns matching a keyword"""

    name = "search_schema"
    description = "Search for tables and columns matching a keyword. Returns matching table names and column names with their tables."
    category = ToolCategory.SCHEMA

    async def execute(self, keyword: str, fuzzy: bool = True, threshold: float = 0.6) -> ToolResult:
        """
        Search schema for matching tables/columns

        Args:
            keyword: Search term
            fuzzy: Enable fuzzy matching
            threshold: Minimum similarity for fuzzy matches (0.0-1.0)
        """
        import time
        start = time.time()

        try:
            if not self.schema_inspector or not self.session:
                return ToolResult(
                    success=False,
                    error="Schema inspector or session not available",
                    tool_name=self.name
                )

            # Get full schema
            schema = await self.schema_inspector.get_full_schema(self.session)

            matches = {
                "tables": [],
                "columns": [],
                "keyword": keyword,
            }

            keyword_lower = keyword.lower()

            for table_name, table_info in schema.get("tables", {}).items():
                # Check table name
                table_lower = table_name.lower()
                if keyword_lower in table_lower:
                    matches["tables"].append({
                        "name": table_name,
                        "match_type": "exact" if keyword_lower == table_lower else "contains",
                    })
                elif fuzzy:
                    ratio = SequenceMatcher(None, keyword_lower, table_lower).ratio()
                    if ratio >= threshold:
                        matches["tables"].append({
                            "name": table_name,
                            "match_type": "fuzzy",
                            "similarity": round(ratio, 2),
                        })

                # Check columns
                for column in table_info.get("columns", []):
                    col_name = column.get("name", "")
                    col_lower = col_name.lower()

                    if keyword_lower in col_lower:
                        matches["columns"].append({
                            "table": table_name,
                            "column": col_name,
                            "type": column.get("type", "unknown"),
                            "match_type": "exact" if keyword_lower == col_lower else "contains",
                        })
                    elif fuzzy:
                        ratio = SequenceMatcher(None, keyword_lower, col_lower).ratio()
                        if ratio >= threshold:
                            matches["columns"].append({
                                "table": table_name,
                                "column": col_name,
                                "type": column.get("type", "unknown"),
                                "match_type": "fuzzy",
                                "similarity": round(ratio, 2),
                            })

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data=matches,
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "keyword": {"type": "string", "description": "Search term"},
                "fuzzy": {"type": "boolean", "description": "Enable fuzzy matching", "default": True},
                "threshold": {"type": "number", "description": "Fuzzy match threshold (0.0-1.0)", "default": 0.6},
            },
            required_params=["keyword"],
            examples=[
                {"keyword": "customer", "result": "Tables: customers, customer_orders; Columns: customer_id, customer_name"},
                {"keyword": "prodct", "fuzzy": True, "result": "Tables: products (fuzzy match 0.86)"},
            ]
        )


@register_tool
class GetTableInfoTool(BaseTool):
    """Get detailed information about a specific table"""

    name = "get_table_info"
    description = "Get detailed schema information for a specific table including columns, types, constraints, and foreign keys."
    category = ToolCategory.SCHEMA

    async def execute(self, table_name: str) -> ToolResult:
        """Get detailed table information"""
        import time
        start = time.time()

        try:
            schema = await self.schema_inspector.get_full_schema(self.session)
            tables = schema.get("tables", {})

            if table_name not in tables:
                # Try case-insensitive match
                for name in tables:
                    if name.lower() == table_name.lower():
                        table_name = name
                        break
                else:
                    return ToolResult(
                        success=False,
                        error=f"Table '{table_name}' not found. Available tables: {list(tables.keys())}",
                        tool_name=self.name
                    )

            table_info = tables[table_name]

            # Get relationships
            relationships = []
            for fk in schema.get("foreign_keys", []):
                if fk.get("source_table") == table_name:
                    relationships.append({
                        "type": "outgoing",
                        "column": fk.get("source_column"),
                        "references": f"{fk.get('target_table')}.{fk.get('target_column')}",
                    })
                elif fk.get("target_table") == table_name:
                    relationships.append({
                        "type": "incoming",
                        "from": f"{fk.get('source_table')}.{fk.get('source_column')}",
                        "column": fk.get("target_column"),
                    })

            result = {
                "table_name": table_name,
                "columns": table_info.get("columns", []),
                "primary_key": table_info.get("primary_key"),
                "relationships": relationships,
                "indexes": table_info.get("indexes", []),
            }

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data=result,
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {"type": "string", "description": "Name of the table to inspect"},
            },
            required_params=["table_name"],
        )


@register_tool
class FindColumnsTool(BaseTool):
    """Find which tables contain a specific column"""

    name = "find_columns"
    description = "Find all tables that contain a column with the given name. Useful for finding where data lives."
    category = ToolCategory.SCHEMA

    async def execute(self, column_name: str, exact: bool = False) -> ToolResult:
        """Find tables containing the specified column"""
        import time
        start = time.time()

        try:
            schema = await self.schema_inspector.get_full_schema(self.session)

            results = []
            column_lower = column_name.lower()

            for table_name, table_info in schema.get("tables", {}).items():
                for column in table_info.get("columns", []):
                    col_name = column.get("name", "")

                    if exact:
                        match = col_name.lower() == column_lower
                    else:
                        match = column_lower in col_name.lower()

                    if match:
                        results.append({
                            "table": table_name,
                            "column": col_name,
                            "type": column.get("type", "unknown"),
                            "nullable": column.get("nullable", True),
                        })

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data={"column_name": column_name, "found_in": results},
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "column_name": {"type": "string", "description": "Column name to search for"},
                "exact": {"type": "boolean", "description": "Require exact match", "default": False},
            },
            required_params=["column_name"],
        )


@register_tool
class GetRelationshipsTool(BaseTool):
    """Get foreign key relationships between tables"""

    name = "get_relationships"
    description = "Get all foreign key relationships for a table or between two tables. Shows how tables can be joined."
    category = ToolCategory.SCHEMA

    async def execute(self, table_name: Optional[str] = None, target_table: Optional[str] = None) -> ToolResult:
        """Get table relationships"""
        import time
        start = time.time()

        try:
            schema = await self.schema_inspector.get_full_schema(self.session)
            all_fks = schema.get("foreign_keys", [])

            if table_name is None and target_table is None:
                # Return all relationships
                return ToolResult(
                    success=True,
                    data={"all_relationships": all_fks},
                    execution_time_ms=(time.time() - start) * 1000,
                    tool_name=self.name
                )

            results = []

            for fk in all_fks:
                source = fk.get("source_table", "")
                target = fk.get("target_table", "")

                if table_name:
                    if source.lower() == table_name.lower() or target.lower() == table_name.lower():
                        if target_table:
                            if source.lower() == target_table.lower() or target.lower() == target_table.lower():
                                results.append(fk)
                        else:
                            results.append(fk)

            # Also suggest join paths
            join_suggestions = []
            if table_name and target_table:
                # Simple direct join check
                for fk in results:
                    join_suggestions.append({
                        "type": "direct",
                        "sql_hint": f"{fk['source_table']}.{fk['source_column']} = {fk['target_table']}.{fk['target_column']}",
                    })

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data={
                    "table": table_name,
                    "target": target_table,
                    "relationships": results,
                    "join_suggestions": join_suggestions,
                },
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {"type": "string", "description": "Table to get relationships for"},
                "target_table": {"type": "string", "description": "Optional: specific target table"},
            },
            required_params=[],
        )
```

### Day 3: Data Tools (`src/tools/data_tools.py`)

```python
"""Data sampling and exploration tools"""
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from .base import BaseTool, ToolResult, ToolDefinition, ToolCategory
from . import register_tool


@register_tool
class GetSampleDataTool(BaseTool):
    """Get sample rows from a table"""

    name = "get_sample_data"
    description = "Get sample rows from a table to understand data format and content. Useful for understanding what data looks like."
    category = ToolCategory.DATA

    async def execute(self, table_name: str, limit: int = 5, columns: Optional[List[str]] = None) -> ToolResult:
        """Get sample data from table"""
        import time
        start = time.time()

        try:
            # Build query
            if columns:
                cols = ", ".join(f'"{c}"' for c in columns)
            else:
                cols = "*"

            query = text(f'SELECT {cols} FROM "{table_name}" LIMIT :limit')
            result = await self.schema_inspector._execute_query(self.session, query, {"limit": limit})

            rows = result.fetchall()
            column_names = list(result.keys()) if hasattr(result, 'keys') else []

            data = {
                "table": table_name,
                "row_count": len(rows),
                "columns": column_names,
                "rows": [dict(zip(column_names, row)) for row in rows],
            }

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {"type": "string", "description": "Table to sample from"},
                "limit": {"type": "integer", "description": "Number of rows", "default": 5},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Specific columns to include"},
            },
            required_params=["table_name"],
        )


@register_tool
class GetColumnValuesTool(BaseTool):
    """Get distinct values from a column"""

    name = "get_column_values"
    description = "Get distinct values from a column. Essential for understanding data format (e.g., 'CA' vs 'California', 'pending' vs 'PENDING')."
    category = ToolCategory.DATA

    async def execute(self, table_name: str, column_name: str, limit: int = 20) -> ToolResult:
        """Get distinct column values"""
        import time
        start = time.time()

        try:
            values = await self.schema_inspector.sample_column_values(
                self.session, table_name, column_name, limit
            )

            data = {
                "table": table_name,
                "column": column_name,
                "distinct_values": values,
                "count": len(values),
            }

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {"type": "string", "description": "Table name"},
                "column_name": {"type": "string", "description": "Column to get values from"},
                "limit": {"type": "integer", "description": "Max distinct values", "default": 20},
            },
            required_params=["table_name", "column_name"],
        )


@register_tool
class CountRowsTool(BaseTool):
    """Count rows in a table with optional filter"""

    name = "count_rows"
    description = "Count rows in a table, optionally with a WHERE condition. Helps validate query expectations."
    category = ToolCategory.DATA

    async def execute(self, table_name: str, where_clause: Optional[str] = None) -> ToolResult:
        """Count rows in table"""
        import time
        start = time.time()

        try:
            if where_clause:
                # Basic safety check
                dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
                if any(d in where_clause.upper() for d in dangerous):
                    return ToolResult(
                        success=False,
                        error="WHERE clause contains potentially dangerous keywords",
                        tool_name=self.name
                    )
                query = text(f'SELECT COUNT(*) as count FROM "{table_name}" WHERE {where_clause}')
            else:
                query = text(f'SELECT COUNT(*) as count FROM "{table_name}"')

            result = await self.schema_inspector._execute_query(self.session, query)
            row = result.fetchone()
            count = row[0] if row else 0

            data = {
                "table": table_name,
                "where": where_clause,
                "count": count,
            }

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "table_name": {"type": "string", "description": "Table to count"},
                "where_clause": {"type": "string", "description": "Optional WHERE condition (without WHERE keyword)"},
            },
            required_params=["table_name"],
        )
```

### Day 4: Query Tools (`src/tools/query_tools.py`)

```python
"""Query validation and testing tools"""
from typing import Any, Dict, Optional
from sqlalchemy import text
from .base import BaseTool, ToolResult, ToolDefinition, ToolCategory
from . import register_tool


@register_tool
class TestQueryTool(BaseTool):
    """Test if a SQL query is valid without fully executing it"""

    name = "test_query"
    description = "Test if SQL syntax is valid without executing. Uses EXPLAIN or LIMIT 0 to validate."
    category = ToolCategory.QUERY

    async def execute(self, sql: str, database_type: str = "postgresql") -> ToolResult:
        """Test query validity"""
        import time
        start = time.time()

        try:
            # Determine test method based on database type
            if database_type in ["postgresql", "mysql"]:
                test_sql = f"EXPLAIN {sql}"
            elif database_type == "sqlite":
                # SQLite doesn't have EXPLAIN ANALYZE, use LIMIT 0
                test_sql = f"SELECT * FROM ({sql}) AS test LIMIT 0"
            else:
                # DuckDB and others
                test_sql = f"EXPLAIN {sql}"

            query = text(test_sql)
            await self.schema_inspector._execute_query(self.session, query)

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "valid": True,
                    "message": "Query syntax is valid",
                },
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,  # Tool succeeded, query is invalid
                data={
                    "sql": sql,
                    "valid": False,
                    "error": str(e),
                    "message": f"Query has syntax error: {str(e)[:200]}",
                },
                execution_time_ms=elapsed,
                tool_name=self.name
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "sql": {"type": "string", "description": "SQL query to test"},
                "database_type": {"type": "string", "description": "Database type", "default": "postgresql"},
            },
            required_params=["sql"],
        )


@register_tool
class ExplainQueryTool(BaseTool):
    """Get query execution plan"""

    name = "explain_query"
    description = "Get the execution plan for a query. Shows how the database will execute it (joins, scans, etc.)."
    category = ToolCategory.QUERY

    async def execute(self, sql: str, analyze: bool = False) -> ToolResult:
        """Get query plan"""
        import time
        start = time.time()

        try:
            if analyze:
                explain_sql = f"EXPLAIN ANALYZE {sql}"
            else:
                explain_sql = f"EXPLAIN {sql}"

            query = text(explain_sql)
            result = await self.schema_inspector._execute_query(self.session, query)

            plan_rows = [str(row[0]) for row in result.fetchall()]

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "plan": plan_rows,
                    "analyzed": analyze,
                },
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "sql": {"type": "string", "description": "SQL query to explain"},
                "analyze": {"type": "boolean", "description": "Also analyze (actually run)", "default": False},
            },
            required_params=["sql"],
        )


@register_tool
class ValidateSQLTool(BaseTool):
    """Validate SQL against schema"""

    name = "validate_sql"
    description = "Validate SQL references against actual schema. Checks if tables and columns exist."
    category = ToolCategory.VALIDATION

    async def execute(self, sql: str) -> ToolResult:
        """Validate SQL against schema"""
        import time
        import re
        start = time.time()

        try:
            schema = await self.schema_inspector.get_full_schema(self.session)
            tables = set(schema.get("tables", {}).keys())

            # Simple extraction of table names from SQL
            # This is basic - a real implementation would use sqlparse
            sql_upper = sql.upper()
            from_match = re.findall(r'FROM\s+["\']?(\w+)["\']?', sql_upper, re.IGNORECASE)
            join_match = re.findall(r'JOIN\s+["\']?(\w+)["\']?', sql_upper, re.IGNORECASE)

            referenced_tables = set(t.lower() for t in from_match + join_match)
            actual_tables_lower = {t.lower(): t for t in tables}

            issues = []
            suggestions = []

            for ref_table in referenced_tables:
                if ref_table not in actual_tables_lower:
                    issues.append(f"Table '{ref_table}' not found in schema")
                    # Find similar tables
                    from difflib import get_close_matches
                    matches = get_close_matches(ref_table, list(actual_tables_lower.keys()), n=3, cutoff=0.6)
                    if matches:
                        suggestions.append(f"Did you mean: {', '.join(matches)}?")

            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "valid": len(issues) == 0,
                    "referenced_tables": list(referenced_tables),
                    "issues": issues,
                    "suggestions": suggestions,
                },
                execution_time_ms=elapsed,
                tool_name=self.name
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters={
                "sql": {"type": "string", "description": "SQL to validate"},
            },
            required_params=["sql"],
        )
```

### Day 5: Tool Executor and Agent (`src/tools/tool_executor.py`)

```python
"""Tool executor - routes and executes tools"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field

from .base import BaseTool, ToolResult, ToolDefinition
from . import get_tool, get_all_tools

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """A request to execute a tool"""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ToolExecutionTrace:
    """Trace of tool executions for observability"""
    calls: List[Dict[str, Any]] = field(default_factory=list)
    total_time_ms: float = 0.0

    def add_call(self, tool_name: str, args: Dict, result: ToolResult):
        self.calls.append({
            "tool": tool_name,
            "arguments": args,
            "success": result.success,
            "result": result.data if result.success else result.error,
            "time_ms": result.execution_time_ms,
        })
        self.total_time_ms += result.execution_time_ms


class ToolExecutor:
    """
    Executes tools and manages tool state

    Usage:
        executor = ToolExecutor(session=db_session, schema_inspector=inspector)
        result = await executor.execute("search_schema", keyword="customer")
    """

    def __init__(self, session=None, schema_inspector=None, max_concurrent: int = 5):
        self.session = session
        self.schema_inspector = schema_inspector
        self.max_concurrent = max_concurrent
        self._tool_instances: Dict[str, BaseTool] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def _get_tool_instance(self, tool_name: str) -> Optional[BaseTool]:
        """Get or create a tool instance"""
        if tool_name not in self._tool_instances:
            tool_class = get_tool(tool_name)
            if tool_class:
                self._tool_instances[tool_name] = tool_class(
                    session=self.session,
                    schema_inspector=self.schema_inspector
                )
        return self._tool_instances.get(tool_name)

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a single tool"""
        async with self._semaphore:
            tool = self._get_tool_instance(tool_name)
            if not tool:
                return ToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                    tool_name=tool_name
                )

            try:
                logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
                result = await tool.execute(**kwargs)
                logger.info(f"Tool {tool_name} completed in {result.execution_time_ms:.2f}ms")
                return result
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return ToolResult(
                    success=False,
                    error=str(e),
                    tool_name=tool_name
                )

    async def execute_batch(self, calls: List[ToolCall], parallel: bool = True) -> List[ToolResult]:
        """Execute multiple tool calls"""
        if parallel:
            tasks = [
                self.execute(call.tool_name, **call.arguments)
                for call in calls
            ]
            return await asyncio.gather(*tasks, return_exceptions=False)
        else:
            results = []
            for call in calls:
                result = await self.execute(call.tool_name, **call.arguments)
                results.append(result)
            return results

    def get_available_tools(self) -> List[ToolDefinition]:
        """Get definitions of all available tools"""
        definitions = []
        for name, tool_class in get_all_tools().items():
            tool = self._get_tool_instance(name)
            if tool:
                definitions.append(tool.get_definition())
        return definitions

    def format_tools_for_prompt(self) -> str:
        """Format available tools for inclusion in LLM prompt"""
        tools = self.get_available_tools()
        lines = ["Available tools:"]
        for tool in tools:
            lines.append(tool.to_prompt_format())
        return "\n".join(lines)
```

### Day 5 (continued): Tool-Using Agent (`src/llm/tool_using_agent.py`)

```python
"""Tool-Using Agent - Uses tools to gather information before generating SQL"""
import asyncio
import logging
import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.tools.tool_executor import ToolExecutor, ToolCall, ToolExecutionTrace
from src.tools.base import ToolResult
from src.llm.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


@dataclass
class ToolUsingResult:
    """Result from tool-using agent"""
    success: bool
    sql: Optional[str] = None
    explanation: str = ""
    tools_used: List[str] = field(default_factory=list)
    tool_trace: Optional[ToolExecutionTrace] = None
    confidence: float = 0.0
    error: Optional[str] = None


class ToolUsingAgent:
    """
    Agent that uses tools to gather schema information before generating SQL

    Flow:
    1. Analyze question to determine what information is needed
    2. Use tools to gather that information
    3. Generate SQL with enriched context

    Example:
        agent = ToolUsingAgent(executor, generator)
        result = await agent.process("Show orders from California")
        # Agent will:
        # 1. search_schema("order") - find orders table
        # 2. search_schema("state") or search_schema("california") - find state column
        # 3. get_column_values("customers", "state") - see format (CA vs California)
        # 4. Generate SQL with correct format
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        sql_generator: SQLGenerator,
        max_tool_calls: int = 5,
        enable_auto_explore: bool = True,
    ):
        self.executor = tool_executor
        self.generator = sql_generator
        self.max_tool_calls = max_tool_calls
        self.enable_auto_explore = enable_auto_explore

    async def process(
        self,
        question: str,
        schema: str,
        database_type: str = "postgresql",
        use_tools: bool = True,
    ) -> ToolUsingResult:
        """
        Process a question using tools to gather context

        Args:
            question: Natural language question
            schema: Database schema (for fallback)
            database_type: Type of database
            use_tools: Whether to use tools (can be disabled for simple queries)

        Returns:
            ToolUsingResult with SQL and tool trace
        """
        trace = ToolExecutionTrace()
        tools_used = []

        try:
            if use_tools and self.enable_auto_explore:
                # Step 1: Analyze question and determine tool calls
                tool_calls = await self._plan_tool_calls(question, schema)

                # Step 2: Execute tool calls
                enriched_context = {}
                for call in tool_calls[:self.max_tool_calls]:
                    result = await self.executor.execute(call.tool_name, **call.arguments)
                    trace.add_call(call.tool_name, call.arguments, result)
                    tools_used.append(call.tool_name)

                    if result.success:
                        enriched_context[call.tool_name] = result.data

                # Step 3: Generate SQL with enriched context
                context_prompt = self._format_tool_context(enriched_context)
                enhanced_schema = f"{schema}\n\n{context_prompt}" if context_prompt else schema
            else:
                enhanced_schema = schema

            # Step 4: Generate SQL
            sql_result = await self.generator.generate_sql(
                question=question,
                schema=enhanced_schema,
                database_type=database_type,
            )

            return ToolUsingResult(
                success=True,
                sql=sql_result.get("sql"),
                explanation=sql_result.get("explanation", ""),
                tools_used=tools_used,
                tool_trace=trace,
                confidence=0.8 if tools_used else 0.6,
            )

        except Exception as e:
            logger.error(f"Tool-using agent failed: {e}")
            return ToolUsingResult(
                success=False,
                error=str(e),
                tools_used=tools_used,
                tool_trace=trace,
            )

    async def _plan_tool_calls(self, question: str, schema: str) -> List[ToolCall]:
        """
        Analyze question and plan which tools to use

        This uses simple heuristics - can be enhanced with LLM planning
        """
        calls = []
        question_lower = question.lower()

        # Extract key entities from question
        # Pattern 1: Look for table-like words
        table_keywords = ["orders", "customers", "products", "users", "sales", "employees"]
        for keyword in table_keywords:
            if keyword in question_lower or keyword[:-1] in question_lower:
                calls.append(ToolCall(
                    tool_name="search_schema",
                    arguments={"keyword": keyword}
                ))
                break

        # Pattern 2: Look for location-based queries
        location_keywords = ["california", "new york", "texas", "state", "city", "country"]
        for loc in location_keywords:
            if loc in question_lower:
                calls.append(ToolCall(
                    tool_name="search_schema",
                    arguments={"keyword": "state"}
                ))
                # Also get sample values to understand format
                calls.append(ToolCall(
                    tool_name="find_columns",
                    arguments={"column_name": "state"}
                ))
                break

        # Pattern 3: Look for filter/category queries
        filter_keywords = ["category", "type", "status", "by"]
        for kw in filter_keywords:
            if kw in question_lower:
                # Try to extract what they're filtering by
                words = question_lower.split()
                for i, word in enumerate(words):
                    if word == "by" and i + 1 < len(words):
                        filter_col = words[i + 1]
                        calls.append(ToolCall(
                            tool_name="find_columns",
                            arguments={"column_name": filter_col}
                        ))
                        break
                break

        # Pattern 4: If mentions specific table, get its info
        # This is simplified - real implementation would use NER or LLM

        return calls

    def _format_tool_context(self, context: Dict[str, Any]) -> str:
        """Format tool results for inclusion in prompt"""
        if not context:
            return ""

        lines = ["Additional context from schema exploration:"]

        for tool_name, data in context.items():
            if tool_name == "search_schema":
                if data.get("tables"):
                    lines.append(f"- Found tables matching query: {[t['name'] for t in data['tables']]}")
                if data.get("columns"):
                    cols = data["columns"][:5]  # Limit
                    lines.append(f"- Found columns: {[(c['table'], c['column']) for c in cols]}")

            elif tool_name == "get_column_values":
                vals = data.get("distinct_values", [])[:10]
                lines.append(f"- Values in {data.get('table')}.{data.get('column')}: {vals}")

            elif tool_name == "find_columns":
                found = data.get("found_in", [])[:5]
                if found:
                    lines.append(f"- Column '{data.get('column_name')}' found in: {[(f['table'], f['column']) for f in found]}")

            elif tool_name == "get_table_info":
                cols = [c.get("name") for c in data.get("columns", [])][:10]
                lines.append(f"- Table {data.get('table_name')} has columns: {cols}")

        return "\n".join(lines)

    async def explore_for_question(
        self,
        question: str,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Deep exploration for a question - gathers comprehensive context

        This can be called before generate_and_execute for complex queries
        """
        exploration = {
            "question": question,
            "discovered_tables": [],
            "discovered_columns": [],
            "value_samples": {},
            "relationships": [],
        }

        # First pass: find relevant tables/columns
        keywords = self._extract_keywords(question)

        for keyword in keywords[:3]:  # Limit to top 3
            result = await self.executor.execute("search_schema", keyword=keyword)
            if result.success:
                for table in result.data.get("tables", []):
                    if table["name"] not in exploration["discovered_tables"]:
                        exploration["discovered_tables"].append(table["name"])
                for col in result.data.get("columns", []):
                    exploration["discovered_columns"].append(col)

        # Second pass: get details on discovered tables
        for table in exploration["discovered_tables"][:3]:
            info_result = await self.executor.execute("get_table_info", table_name=table)
            if info_result.success:
                exploration["relationships"].extend(info_result.data.get("relationships", []))

        # Third pass: sample values for key columns
        value_columns = ["state", "status", "type", "category"]
        for col_info in exploration["discovered_columns"]:
            if any(vc in col_info["column"].lower() for vc in value_columns):
                values_result = await self.executor.execute(
                    "get_column_values",
                    table_name=col_info["table"],
                    column_name=col_info["column"],
                    limit=10
                )
                if values_result.success:
                    key = f"{col_info['table']}.{col_info['column']}"
                    exploration["value_samples"][key] = values_result.data.get("distinct_values", [])

        return exploration

    def _extract_keywords(self, question: str) -> List[str]:
        """Extract searchable keywords from question"""
        # Remove common words
        stop_words = {
            "show", "me", "get", "find", "list", "all", "the", "a", "an",
            "from", "where", "with", "by", "in", "on", "and", "or", "to",
            "how", "many", "much", "what", "which", "who", "that", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had",
        }

        words = re.findall(r'\b\w+\b', question.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords
```

### Integration with Self-Correcting Agent

Add tool-using as a 4th parallel strategy in `_try_parallel_fixes()`:

```python
# In src/llm/self_correcting_agent.py, add to _try_parallel_fixes():

async def try_tool_fix():
    """Try tool-based exploration and fix"""
    if not self.tool_agent:
        return None

    try:
        # Use tools to explore and understand the error
        exploration = await self.tool_agent.explore_for_question(
            question=self.current_question,  # Need to store this
            max_depth=1,  # Quick exploration
        )

        # If we found relevant info, regenerate with enriched context
        if exploration["discovered_tables"] or exploration["value_samples"]:
            enhanced_schema = self._enhance_schema_with_exploration(schema, exploration)

            result = await self.generator.fix_sql_error(
                sql=sql,
                error=f"{last_error}\n\nContext from exploration:\n{json.dumps(exploration, indent=2)}",
                schema=enhanced_schema,
                database_type=database_type,
            )

            return {
                "sql": result["sql"],
                "fix_method": "tool_exploration",
                "confidence": 0.75,
                "explanation": f"Used tools to explore schema: found {len(exploration['discovered_tables'])} relevant tables",
                "exploration": exploration,
            }
        return None
    except Exception as e:
        logger.warning(f"Tool-based fix failed: {e}")
        return None
```

---

## Phase 3.2: LangGraph Integration (Week 2-3)

### Goal
Refactor the agent system to use LangGraph for multi-agent orchestration with explicit state management.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     LangGraph SQL Agent System                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│   │   Analyze   │───>│   Explore   │───>│    Plan     │                │
│   │   Question  │    │   Schema    │    │    Query    │                │
│   └─────────────┘    └─────────────┘    └─────────────┘                │
│          │                  │                  │                         │
│          │          Uses Tools:                │                         │
│          │          - search_schema            │                         │
│          │          - get_table_info           │                         │
│          │          - get_column_values        │                         │
│          ▼                  ▼                  ▼                         │
│   ┌─────────────────────────────────────────────────────┐              │
│   │                    State Graph                       │              │
│   │  {question, schema, tools_used, plan, sql, result}  │              │
│   └─────────────────────────────────────────────────────┘              │
│          │                  │                  │                         │
│          ▼                  ▼                  ▼                         │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│   │  Generate   │───>│   Execute   │───>│   Verify    │                │
│   │    SQL      │    │   Query     │    │   Result    │                │
│   └─────────────┘    └─────────────┘    └─────────────┘                │
│          │                  │                  │                         │
│          │         ┌───────┴───────┐          │                         │
│          │         ▼               ▼          │                         │
│          │    [Success]       [Error]         │                         │
│          │         │               │          │                         │
│          │         │        ┌──────┴──────┐   │                         │
│          │         │        │  Fix Error  │   │                         │
│          │         │        │  (4 strats) │   │                         │
│          │         │        └─────────────┘   │                         │
│          │         │               │          │                         │
│          │         └───────┬───────┘          │                         │
│          │                 ▼                  │                         │
│          │           [Return]                 │                         │
│          │                                    │                         │
│          └────────────────────────────────────┘                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
src/
├── langgraph/                      # NEW: LangGraph implementation
│   ├── __init__.py
│   ├── state.py                    # State definitions
│   ├── nodes/                      # Graph nodes (agents)
│   │   ├── __init__.py
│   │   ├── analyzer.py             # Question analysis node
│   │   ├── explorer.py             # Schema exploration node (uses tools!)
│   │   ├── planner.py              # Query planning node
│   │   ├── generator.py            # SQL generation node
│   │   ├── executor.py             # Query execution node
│   │   ├── verifier.py             # Result verification node
│   │   └── fixer.py                # Error correction node
│   ├── edges.py                    # Conditional edge logic
│   ├── graph.py                    # Graph assembly
│   └── workflow.py                 # High-level workflow API
└── api/
    └── endpoints/
        └── langgraph_query.py      # NEW: LangGraph-based query endpoint
```

### Day 1-2: State Definitions (`src/langgraph/state.py`)

```python
"""LangGraph state definitions for SQL agent system"""
from typing import TypedDict, Optional, List, Dict, Any, Annotated
from dataclasses import dataclass, field
from enum import Enum
import operator


class WorkflowStatus(Enum):
    """Overall workflow status"""
    ANALYZING = "analyzing"
    EXPLORING = "exploring"
    PLANNING = "planning"
    GENERATING = "generating"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    FIXING = "fixing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ToolUsage:
    """Record of a tool call"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    execution_time_ms: float


@dataclass
class AttemptRecord:
    """Record of a SQL attempt"""
    sql: str
    success: bool
    error: Optional[str] = None
    fix_method: Optional[str] = None
    confidence: float = 0.0


class SQLAgentState(TypedDict):
    """
    State that flows through the LangGraph workflow

    This state is updated by each node and passed to the next.
    Using TypedDict for LangGraph compatibility.
    """
    # Input
    question: str
    database_type: str
    session_id: Optional[str]
    connection_id: Optional[int]

    # Schema context
    schema: str
    enhanced_schema: Optional[str]  # After tool exploration

    # Tool usage (list because multiple tools can be called)
    tools_used: Annotated[List[ToolUsage], operator.add]

    # Analysis results
    complexity: str  # "simple", "moderate", "complex"
    intent: Dict[str, Any]  # Parsed intent
    entities: List[str]  # Extracted entities

    # Planning
    query_plan: Optional[Dict[str, Any]]
    plan_confidence: float

    # SQL generation
    sql: Optional[str]
    sql_explanation: Optional[str]

    # Execution
    result: Optional[Dict[str, Any]]
    row_count: int
    execution_time_ms: float

    # Verification
    verification_passed: bool
    verification_issues: List[str]

    # Error handling
    attempts: Annotated[List[AttemptRecord], operator.add]
    current_attempt: int
    max_attempts: int
    last_error: Optional[str]

    # Workflow control
    status: WorkflowStatus
    should_retry: bool

    # Metrics
    total_time_ms: float
    llm_calls: int

    # Conversation context (from ConversationalMemoryAgent)
    conversation_context: Optional[str]


def create_initial_state(
    question: str,
    schema: str,
    database_type: str = "postgresql",
    session_id: Optional[str] = None,
    connection_id: Optional[int] = None,
    max_attempts: int = 3,
) -> SQLAgentState:
    """Create initial state for workflow"""
    return SQLAgentState(
        question=question,
        database_type=database_type,
        session_id=session_id,
        connection_id=connection_id,
        schema=schema,
        enhanced_schema=None,
        tools_used=[],
        complexity="unknown",
        intent={},
        entities=[],
        query_plan=None,
        plan_confidence=0.0,
        sql=None,
        sql_explanation=None,
        result=None,
        row_count=0,
        execution_time_ms=0.0,
        verification_passed=False,
        verification_issues=[],
        attempts=[],
        current_attempt=0,
        max_attempts=max_attempts,
        last_error=None,
        status=WorkflowStatus.ANALYZING,
        should_retry=False,
        total_time_ms=0.0,
        llm_calls=0,
        conversation_context=None,
    )
```

### Day 3-4: Graph Nodes (`src/langgraph/nodes/`)

#### Analyzer Node (`analyzer.py`)

```python
"""Question analysis node"""
from typing import Dict, Any
from src.langgraph.state import SQLAgentState, WorkflowStatus
import logging

logger = logging.getLogger(__name__)


async def analyze_question(state: SQLAgentState) -> Dict[str, Any]:
    """
    Analyze the input question to determine:
    - Complexity level
    - Intent (SELECT, aggregation, join, etc.)
    - Key entities mentioned

    Returns partial state update.
    """
    question = state["question"]

    # Simple heuristic-based analysis (can be enhanced with LLM)
    complexity = _assess_complexity(question)
    intent = _parse_intent(question)
    entities = _extract_entities(question)

    logger.info(f"Analyzed question: complexity={complexity}, intent={intent.get('type')}")

    return {
        "complexity": complexity,
        "intent": intent,
        "entities": entities,
        "status": WorkflowStatus.EXPLORING,
    }


def _assess_complexity(question: str) -> str:
    """Assess query complexity"""
    question_lower = question.lower()

    # Complex indicators
    complex_keywords = ["compare", "trend", "growth", "percentage", "ratio", "vs", "versus"]
    join_keywords = ["with", "along with", "including", "and their", "related"]

    # Count indicators
    complex_count = sum(1 for kw in complex_keywords if kw in question_lower)
    join_count = sum(1 for kw in join_keywords if kw in question_lower)

    if complex_count >= 2 or join_count >= 2:
        return "complex"
    elif complex_count >= 1 or join_count >= 1:
        return "moderate"
    else:
        return "simple"


def _parse_intent(question: str) -> Dict[str, Any]:
    """Parse query intent"""
    question_lower = question.lower()

    intent = {"type": "select", "operations": []}

    if any(w in question_lower for w in ["count", "how many", "number of"]):
        intent["operations"].append("count")
    if any(w in question_lower for w in ["sum", "total"]):
        intent["operations"].append("sum")
    if any(w in question_lower for w in ["average", "avg", "mean"]):
        intent["operations"].append("average")
    if any(w in question_lower for w in ["group", "by each", "per"]):
        intent["operations"].append("group_by")
    if any(w in question_lower for w in ["order", "sort", "top", "bottom"]):
        intent["operations"].append("order_by")
    if any(w in question_lower for w in ["join", "with", "related"]):
        intent["operations"].append("join")

    intent["type"] = "aggregate" if intent["operations"] else "select"

    return intent


def _extract_entities(question: str) -> list:
    """Extract potential table/column names"""
    import re

    # Simple extraction - can be enhanced with NER
    words = re.findall(r'\b[a-z_]+\b', question.lower())

    # Filter common words
    stop_words = {"show", "me", "get", "all", "the", "from", "where", "how", "many"}
    entities = [w for w in words if w not in stop_words and len(w) > 2]

    return list(set(entities))
```

#### Explorer Node (`explorer.py`) - Uses Tools!

```python
"""Schema exploration node - uses tools from Phase 3.1"""
from typing import Dict, Any, List
from src.langgraph.state import SQLAgentState, WorkflowStatus, ToolUsage
from src.tools.tool_executor import ToolExecutor
import logging

logger = logging.getLogger(__name__)


class ExplorerNode:
    """
    Schema exploration node that uses tools to gather context

    This is where Phase 3.1 tools are integrated into LangGraph!
    """

    def __init__(self, tool_executor: ToolExecutor):
        self.executor = tool_executor

    async def explore_schema(self, state: SQLAgentState) -> Dict[str, Any]:
        """
        Use tools to explore schema based on question analysis

        Uses tools:
        - search_schema: Find relevant tables/columns
        - get_table_info: Get table details
        - get_column_values: Sample values for understanding data format
        - get_relationships: Find join paths
        """
        tools_used: List[ToolUsage] = []
        enhanced_info = []

        complexity = state["complexity"]
        entities = state["entities"]
        intent = state["intent"]

        # Skip exploration for simple queries
        if complexity == "simple" and len(entities) <= 1:
            logger.info("Simple query - skipping schema exploration")
            return {
                "status": WorkflowStatus.PLANNING,
                "tools_used": [],
            }

        # Step 1: Search for relevant tables/columns
        for entity in entities[:3]:  # Limit to top 3 entities
            result = await self.executor.execute("search_schema", keyword=entity)
            tools_used.append(ToolUsage(
                tool_name="search_schema",
                arguments={"keyword": entity},
                result=result.data if result.success else None,
                success=result.success,
                execution_time_ms=result.execution_time_ms,
            ))

            if result.success and result.data:
                tables = result.data.get("tables", [])
                if tables:
                    enhanced_info.append(f"Found tables for '{entity}': {[t['name'] for t in tables]}")

        # Step 2: Get details on discovered tables (for complex queries)
        if complexity in ["moderate", "complex"]:
            discovered_tables = set()
            for usage in tools_used:
                if usage.success and usage.result:
                    for t in usage.result.get("tables", []):
                        discovered_tables.add(t["name"])

            for table in list(discovered_tables)[:2]:  # Limit
                info_result = await self.executor.execute("get_table_info", table_name=table)
                tools_used.append(ToolUsage(
                    tool_name="get_table_info",
                    arguments={"table_name": table},
                    result=info_result.data if info_result.success else None,
                    success=info_result.success,
                    execution_time_ms=info_result.execution_time_ms,
                ))

        # Step 3: Sample values for filter columns (if needed)
        if "group_by" in intent.get("operations", []) or complexity == "complex":
            # Find columns that might need value sampling
            value_columns = ["state", "status", "type", "category"]
            for usage in tools_used:
                if usage.tool_name == "get_table_info" and usage.success:
                    for col in usage.result.get("columns", []):
                        if any(vc in col["name"].lower() for vc in value_columns):
                            val_result = await self.executor.execute(
                                "get_column_values",
                                table_name=usage.result["table_name"],
                                column_name=col["name"],
                                limit=10,
                            )
                            if val_result.success:
                                enhanced_info.append(
                                    f"Values in {usage.result['table_name']}.{col['name']}: "
                                    f"{val_result.data.get('distinct_values', [])[:5]}"
                                )
                            tools_used.append(ToolUsage(
                                tool_name="get_column_values",
                                arguments={
                                    "table_name": usage.result["table_name"],
                                    "column_name": col["name"],
                                },
                                result=val_result.data if val_result.success else None,
                                success=val_result.success,
                                execution_time_ms=val_result.execution_time_ms,
                            ))

        # Build enhanced schema
        enhanced_schema = state["schema"]
        if enhanced_info:
            enhanced_schema += "\n\n--- Tool Exploration Results ---\n"
            enhanced_schema += "\n".join(enhanced_info)

        logger.info(f"Schema exploration complete: {len(tools_used)} tool calls")

        return {
            "enhanced_schema": enhanced_schema,
            "tools_used": tools_used,
            "status": WorkflowStatus.PLANNING,
        }
```

### Day 5-6: Graph Assembly (`src/langgraph/graph.py`)

```python
"""LangGraph workflow assembly"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.langgraph.state import SQLAgentState, WorkflowStatus, create_initial_state
from src.langgraph.nodes.analyzer import analyze_question
from src.langgraph.nodes.explorer import ExplorerNode
from src.langgraph.nodes.planner import PlannerNode
from src.langgraph.nodes.generator import GeneratorNode
from src.langgraph.nodes.executor import ExecutorNode
from src.langgraph.nodes.verifier import VerifierNode
from src.langgraph.nodes.fixer import FixerNode

from src.tools.tool_executor import ToolExecutor
from src.llm.sql_generator import SQLGenerator
from src.llm.query_planning_agent import QueryPlanningAgent
from src.llm.result_verification_agent import ResultVerificationAgent
from src.core.executor import SQLExecutor

import logging

logger = logging.getLogger(__name__)


def create_sql_agent_graph(
    tool_executor: ToolExecutor,
    sql_generator: SQLGenerator,
    query_planner: QueryPlanningAgent,
    sql_executor: SQLExecutor,
    result_verifier: ResultVerificationAgent,
    schema_fixer=None,
    correction_learner=None,
) -> StateGraph:
    """
    Create the LangGraph workflow for SQL generation

    Flow:
    analyze → explore → plan → generate → execute → verify
                                    ↑            ↓
                                    └── fix ←── [error]
    """
    # Initialize nodes with dependencies
    explorer = ExplorerNode(tool_executor)
    planner = PlannerNode(query_planner)
    generator = GeneratorNode(sql_generator)
    executor = ExecutorNode(sql_executor)
    verifier = VerifierNode(result_verifier)
    fixer = FixerNode(schema_fixer, correction_learner, sql_generator)

    # Create graph
    workflow = StateGraph(SQLAgentState)

    # Add nodes
    workflow.add_node("analyze", analyze_question)
    workflow.add_node("explore", explorer.explore_schema)
    workflow.add_node("plan", planner.create_plan)
    workflow.add_node("generate", generator.generate_sql)
    workflow.add_node("execute", executor.execute_sql)
    workflow.add_node("verify", verifier.verify_result)
    workflow.add_node("fix", fixer.fix_error)

    # Define edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "explore")
    workflow.add_edge("explore", "plan")
    workflow.add_edge("plan", "generate")
    workflow.add_edge("generate", "execute")

    # Conditional edge after execution
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "verify": "verify",
            "fix": "fix",
            "end": END,
        }
    )

    # Conditional edge after verification
    workflow.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "end": END,
            "fix": "fix",
        }
    )

    # Edge from fix back to execute (retry loop)
    workflow.add_conditional_edges(
        "fix",
        route_after_fix,
        {
            "execute": "execute",
            "end": END,
        }
    )

    return workflow


def route_after_execute(state: SQLAgentState) -> Literal["verify", "fix", "end"]:
    """Route after SQL execution"""
    if state.get("last_error"):
        if state["current_attempt"] < state["max_attempts"]:
            return "fix"
        else:
            return "end"
    return "verify"


def route_after_verify(state: SQLAgentState) -> Literal["end", "fix"]:
    """Route after result verification"""
    if state.get("verification_passed", True):
        return "end"
    # Only retry if we haven't exhausted attempts
    if state["current_attempt"] < state["max_attempts"]:
        return "fix"
    return "end"


def route_after_fix(state: SQLAgentState) -> Literal["execute", "end"]:
    """Route after error fix"""
    if state.get("sql") and state["current_attempt"] < state["max_attempts"]:
        return "execute"
    return "end"


class SQLAgentWorkflow:
    """
    High-level workflow API for the SQL agent

    Usage:
        workflow = SQLAgentWorkflow(...)
        result = await workflow.run("Show me all orders from California")
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        sql_generator: SQLGenerator,
        query_planner: QueryPlanningAgent,
        sql_executor: SQLExecutor,
        result_verifier: ResultVerificationAgent,
        schema_fixer=None,
        correction_learner=None,
        enable_checkpointing: bool = True,
    ):
        self.graph = create_sql_agent_graph(
            tool_executor=tool_executor,
            sql_generator=sql_generator,
            query_planner=query_planner,
            sql_executor=sql_executor,
            result_verifier=result_verifier,
            schema_fixer=schema_fixer,
            correction_learner=correction_learner,
        )

        # Compile with optional checkpointing
        if enable_checkpointing:
            self.memory = MemorySaver()
            self.app = self.graph.compile(checkpointer=self.memory)
        else:
            self.app = self.graph.compile()

    async def run(
        self,
        question: str,
        schema: str,
        database_type: str = "postgresql",
        session_id: str = None,
        connection_id: int = None,
        config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Run the workflow for a question

        Returns the final state with results.
        """
        initial_state = create_initial_state(
            question=question,
            schema=schema,
            database_type=database_type,
            session_id=session_id,
            connection_id=connection_id,
        )

        # Use thread_id for checkpointing if session_id provided
        run_config = config or {}
        if session_id:
            run_config["configurable"] = {"thread_id": session_id}

        # Run the workflow
        final_state = await self.app.ainvoke(initial_state, run_config)

        return self._format_result(final_state)

    def _format_result(self, state: SQLAgentState) -> Dict[str, Any]:
        """Format final state as result"""
        return {
            "success": state.get("result") is not None and not state.get("last_error"),
            "sql": state.get("sql"),
            "result": state.get("result"),
            "row_count": state.get("row_count", 0),
            "explanation": state.get("sql_explanation"),
            "attempts": len(state.get("attempts", [])),
            "tools_used": [
                {"name": t.tool_name, "success": t.success}
                for t in state.get("tools_used", [])
            ],
            "verification": {
                "passed": state.get("verification_passed", False),
                "issues": state.get("verification_issues", []),
            },
            "metrics": {
                "total_time_ms": state.get("total_time_ms", 0),
                "llm_calls": state.get("llm_calls", 0),
                "tool_calls": len(state.get("tools_used", [])),
            },
            "plan": state.get("query_plan"),
            "error": state.get("last_error"),
        }
```

---

## Testing Strategy

### Phase 3.1 Tests (`tests/test_tools.py`)

```python
"""Tests for tool system"""
import pytest
from src.tools import get_all_tools, get_tool
from src.tools.tool_executor import ToolExecutor
from src.tools.schema_tools import SearchSchemaTool


@pytest.mark.asyncio
async def test_search_schema_tool(mock_session, mock_schema_inspector):
    """Test schema search tool"""
    tool = SearchSchemaTool(session=mock_session, schema_inspector=mock_schema_inspector)
    result = await tool.execute(keyword="customer")

    assert result.success
    assert "tables" in result.data
    assert "columns" in result.data


@pytest.mark.asyncio
async def test_tool_executor_parallel(mock_session, mock_schema_inspector):
    """Test parallel tool execution"""
    executor = ToolExecutor(session=mock_session, schema_inspector=mock_schema_inspector)

    from src.tools.tool_executor import ToolCall
    calls = [
        ToolCall(tool_name="search_schema", arguments={"keyword": "order"}),
        ToolCall(tool_name="search_schema", arguments={"keyword": "customer"}),
    ]

    results = await executor.execute_batch(calls, parallel=True)

    assert len(results) == 2
    assert all(r.success for r in results)
```

### Phase 3.2 Tests (`tests/test_langgraph.py`)

```python
"""Tests for LangGraph workflow"""
import pytest
from src.langgraph.state import create_initial_state, WorkflowStatus
from src.langgraph.nodes.analyzer import analyze_question


@pytest.mark.asyncio
async def test_analyze_simple_question():
    """Test question analysis for simple query"""
    state = create_initial_state(
        question="Show me all products",
        schema="CREATE TABLE products (id INT, name VARCHAR)",
    )

    result = await analyze_question(state)

    assert result["complexity"] == "simple"
    assert result["status"] == WorkflowStatus.EXPLORING


@pytest.mark.asyncio
async def test_full_workflow(mock_dependencies):
    """Test complete workflow execution"""
    from src.langgraph.graph import SQLAgentWorkflow

    workflow = SQLAgentWorkflow(**mock_dependencies)

    result = await workflow.run(
        question="How many orders from California?",
        schema="CREATE TABLE orders (id INT, state VARCHAR)",
    )

    assert result["success"]
    assert result["sql"] is not None
    assert len(result["tools_used"]) > 0
```

---

## Implementation Timeline

### Week 1: Tool-Using Agent (Phase 3.1)
| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Core tool infrastructure | `src/tools/base.py`, `__init__.py` |
| 2 | Schema tools | `src/tools/schema_tools.py` (4 tools) |
| 3 | Data tools | `src/tools/data_tools.py` (3 tools) |
| 4 | Query tools | `src/tools/query_tools.py` (3 tools) |
| 5 | Tool executor + Agent | `tool_executor.py`, `tool_using_agent.py` |
| 5 | Integration | Add to `_try_parallel_fixes()` |
| 6 | Testing + Docs | Tests, documentation |

### Week 2-3: LangGraph Integration (Phase 3.2)
| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | State definitions | `src/langgraph/state.py` |
| 3-4 | Core nodes | `analyzer.py`, `explorer.py`, `generator.py` |
| 5-6 | Execution nodes | `executor.py`, `verifier.py`, `fixer.py` |
| 7-8 | Graph assembly | `graph.py`, `workflow.py` |
| 9-10 | API integration | `langgraph_query.py` endpoint |
| 11-12 | Testing + Docs | Comprehensive tests, documentation |

---

## Migration Path

### Gradual Rollout

```python
# In query endpoint, use feature flag
if settings.USE_LANGGRAPH:
    result = await langgraph_workflow.run(question, schema)
else:
    result = await self_correcting_agent.process_query(question, schema)
```

### Backward Compatibility

- Keep existing `SelfCorrectingAgent` working
- LangGraph workflow calls same underlying components
- Tools work independently of LangGraph

---

## Success Metrics

### Phase 3.1 (Tool-Using Agent)
- [ ] 10 tools implemented and tested
- [ ] < 100ms average tool execution time
- [ ] 15% improvement in first-attempt accuracy (tools provide better context)
- [ ] Integration with parallel fixes working

### Phase 3.2 (LangGraph)
- [ ] Full workflow operational
- [ ] Checkpointing enabled for conversation continuity
- [ ] < 5% regression in latency vs current system
- [ ] Observable state at each node
- [ ] 100% test coverage for state transitions

---

## Summary

**Phase 3.1** (Tool-Using Agent) provides immediate value by enabling schema exploration before SQL generation. The tools work in the current architecture and become even more powerful when integrated into LangGraph.

**Phase 3.2** (LangGraph) brings formal multi-agent orchestration with explicit state management, making the system more maintainable, observable, and extensible.

Both phases share the tool infrastructure, maximizing code reuse and minimizing risk.

**Recommendation**: Start Phase 3.1 immediately. Tools can ship incrementally and provide value within days.
