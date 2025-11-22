# Tool-Using Agent

**Status**: Production-Ready with Full UI (November 21-22, 2025)
**Phase**: 3.1
**Tests**: 26 backend tests + 30 frontend tests (56 total)

The Tool-Using Agent enhances SQL generation by using specialized tools to explore schema and gather context before query generation, resulting in better first-attempt accuracy.

---

## Overview

The Tool-Using Agent addresses a common problem: generating correct SQL often requires understanding the actual data format in the database. For example, are US states stored as "California" or "CA"? Is the column named "customer_id" or "cust_id"?

By using tools to explore the schema and sample data before generating SQL, the agent can:
- Discover correct table and column names
- Understand data formats and value representations
- Find foreign key relationships for joins
- Validate SQL references before execution

---

## 10 Specialized Tools

### Schema Tools (`src/tools/schema_tools.py`)

| Tool | Description | Example Use |
|------|-------------|-------------|
| `search_schema` | Search tables/columns by keyword with fuzzy matching | Find "customer" → customers table, customer_id column |
| `get_table_info` | Get detailed table info: columns, PKs, relationships | Understand orders table structure |
| `find_columns` | Find columns across all tables | Where is "state" stored? |
| `get_relationships` | Get FK relationships and join suggestions | How to join orders → customers |

### Data Tools (`src/tools/data_tools.py`)

| Tool | Description | Example Use |
|------|-------------|-------------|
| `get_sample_data` | Sample rows from tables (max 20) | See what data looks like |
| `get_column_values` | Get distinct values (essential!) | "CA" vs "California" |
| `count_rows` | Row count with optional WHERE | Validate query expectations |

### Query Tools (`src/tools/query_tools.py`)

| Tool | Description | Example Use |
|------|-------------|-------------|
| `test_query` | Test SQL syntax using EXPLAIN | Catch syntax errors early |
| `validate_sql` | Validate references with suggestions | "customerz" → "customers" |
| `explain_query` | Get query execution plan | Understand query performance |

---

## How It Works

### Example Flow

**User Question**: "Show me orders from California"

```
1. Tool-Using Agent analyzes question
   → Identifies: need to find California in data

2. Agent plans tool calls:
   → search_schema("order") - find orders table
   → find_columns("state") - find state column location
   → get_column_values("customers", "state") - see actual values

3. Tool Results:
   → search_schema: Found 'orders' table
   → find_columns: 'state' found in customers.state
   → get_column_values: ['CA', 'NY', 'TX', 'FL', ...]

4. Agent builds enriched context:
   "Note: States are stored as 2-letter codes.
    California = 'CA', not 'California'"

5. SQL Generator receives enriched context
   → Generates correct SQL:
   SELECT * FROM orders o
   JOIN customers c ON o.customer_id = c.id
   WHERE c.state = 'CA'

6. First attempt succeeds!
```

---

## Integration with Self-Correcting Agent

The Tool-Using Agent is integrated as the **4th parallel fix strategy** in the self-correcting agent:

```python
# src/llm/self_correcting_agent.py

async def _try_parallel_fixes(self, ...):
    # 4 strategies run in parallel:
    tasks = [
        try_quick_fix(),      # Schema-aware typo correction
        try_learned_fix(),    # Previously learned corrections
        try_llm_fix(),        # LLM-generated fix
        try_tool_fix(),       # NEW: Tool-assisted fix
    ]

    # First successful fix wins
    results = await asyncio.gather(*tasks)
```

When a query fails, the tool-using strategy:
1. Uses tools to explore schema and understand the error
2. Builds enriched context with discovered information
3. Regenerates SQL with better understanding

---

## API Endpoints

### GET /api/tools
List all available tools, optionally filtered by category.

```bash
# Get all tools
curl http://localhost:8000/api/tools

# Filter by category
curl http://localhost:8000/api/tools?category=schema
```

**Categories**: `schema`, `data`, `query`, `validation`

### GET /api/tools/stats
Get execution statistics for all tools.

```json
{
  "total_tools": 10,
  "total_executions": 150,
  "overall_success_rate": 0.95,
  "by_tool": {
    "search_schema": {
      "times_executed": 45,
      "successes": 43,
      "success_rate": 0.96,
      "cache_hit_rate": 0.6
    }
  }
}
```

### GET /api/tools/stats/{tool_name}
Get stats for a specific tool.

### GET /api/tools/prompt
Get tools formatted for LLM prompt inclusion.

### POST /api/tools/{tool_name}/invalidate-cache
Invalidate cache for a specific tool (useful after schema changes).

### POST /api/tools/invalidate-all-cache
Invalidate cache for all tools.

---

## Architecture

### File Structure

```
src/tools/
├── __init__.py           # Module exports
├── base.py               # BaseTool, ToolResult, ToolDefinition, ToolCategory
├── tool_registry.py      # ToolRegistry with caching (follows ColumnMapper pattern)
├── schema_tools.py       # 4 schema exploration tools
├── data_tools.py         # 3 data sampling tools
└── query_tools.py        # 3 query validation tools

src/llm/
└── tool_using_agent.py   # Main agent for tool orchestration

src/api/endpoints/
└── tools.py              # REST API endpoints

tests/
└── test_tools.py         # 26 comprehensive tests
```

### Key Classes

**BaseTool** (`src/tools/base.py`):
```python
class BaseTool:
    name: str = "base_tool"
    category: ToolCategory = ToolCategory.SCHEMA
    cacheable: bool = True
    cache_ttl: int = 300  # 5 minutes

    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def get_definition(self) -> ToolDefinition:
        # Returns tool definition for LLM prompt
```

**ToolRegistry** (`src/tools/tool_registry.py`):
```python
class ToolRegistry:
    # Follows ColumnMapper pattern
    # Uses MappingCache for caching

    async def execute_tool(self, tool_name, session, **kwargs) -> ToolResult:
        # Check cache, execute, cache result, track metrics
```

**ToolUsingAgent** (`src/llm/tool_using_agent.py`):
```python
class ToolUsingAgent:
    async def process(self, question, schema, ...) -> ToolUsingResult:
        # 1. Plan tool calls based on question analysis
        # 2. Execute tools to gather context
        # 3. Build enriched context
        # 4. Generate SQL with enhanced understanding
```

---

## Performance

### Caching

All tools support caching via MappingCache (from feedback-system-update branch):
- Default TTL: 5 minutes for most tools
- Schema tools: 10 minutes (schema changes infrequently)
- Data tools: 5 minutes (data can change more frequently)
- Query tools: 1-5 minutes

### Security

**SQL Injection Protection** in `count_rows` tool:
```python
# Blocks dangerous keywords in WHERE clause
dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
             "TRUNCATE", "CREATE", "GRANT", "REVOKE", ";", "--"]
```

---

## Testing

26 comprehensive tests covering:

```bash
# Run tool tests
python -m pytest tests/test_tools.py -v

# Test categories:
- TestToolRegistry (6 tests) - Registry, singleton, categories
- TestSchemaTools (8 tests) - Schema exploration
- TestDataTools (1 test) - Security checks
- TestQueryTools (2 tests) - SQL validation
- TestToolDefinitions (2 tests) - Definitions, cache keys
- TestToolUsingAgent (4 tests) - Agent functionality
- TestToolRegistryMetrics (1 test) - Stats tracking
- TestSelfCorrectingAgentIntegration (2 tests) - Integration
```

---

## Configuration

No additional configuration required. Tools use existing settings:

```python
# Cache TTL (per-tool, in seconds)
SearchSchemaTool.cache_ttl = 600   # 10 minutes
GetColumnValuesTool.cache_ttl = 300  # 5 minutes
CountRowsTool.cache_ttl = 60        # 1 minute

# Max tool calls per request
ToolUsingAgent.max_tool_calls = 5
```

---

## Future Enhancements

Potential improvements for future phases:

1. **LLM-Based Tool Planning**: Use LLM to plan tool calls instead of heuristics
2. **Tool Chaining**: Allow tools to call other tools
3. **Custom Tools**: User-defined tools for domain-specific operations
4. **Tool Results in UI**: Display tool exploration results to users

---

## Frontend UI Components (NEW - November 22, 2025)

The Tool-Using Agent includes a comprehensive management UI accessible via the **Tools** tab in the main navigation.

### Tab Structure

The Tools panel is added as the **4th main tab** in `App.tsx`, alongside Query Interface, Feedback Dashboard, and Settings. It uses an **orange color scheme** to visually distinguish it.

### Components

| Component | File | Description |
|-----------|------|-------------|
| **ToolsPanel** | `frontend/src/components/ToolsPanel.tsx` | Main tabbed container with 3 views |
| **ToolsOverview** | `frontend/src/components/ToolsOverview.tsx` | Summary dashboard with stats cards |
| **ToolDirectory** | `frontend/src/components/ToolDirectory.tsx` | Browsable tool list with filtering |
| **ToolUsageStats** | `frontend/src/components/ToolUsageStats.tsx` | Per-tool execution metrics |
| **toolsApi** | `frontend/src/services/toolsApi.ts` | API service for tools endpoints |

### ToolsPanel (Main Container)

The main container provides navigation between three views:

- **Overview Tab**: Summary stats and quick actions
- **Tool Directory Tab**: Browse all 10 tools with descriptions
- **Usage Stats Tab**: Per-tool execution metrics and charts

### ToolsOverview (Summary Dashboard)

Displays:
- **Total Tools**: Count of available tools (10)
- **Total Executions**: Cumulative tool execution count
- **Success Rate**: Overall tool success percentage
- **Categories**: Number of tool categories (4)
- **Tools by Category**: Visual breakdown by SCHEMA/DATA/QUERY/VALIDATION
- **How It Works**: 3-step explanation of tool-using flow
- **Quick Actions**: Clear All Tool Cache button, Refresh Stats button

### ToolDirectory (Tool Browser)

Features:
- **Category Filter**: Filter by schema/data/query/validation or show all
- **Expandable Tool Cards**: Click to expand and see parameters
- **Color-Coded Categories**: Blue (schema), Green (data), Purple (query), Orange (validation)
- **Parameter Details**: Shows type, required status, description, default values
- **Cache Info**: Displays cache TTL and whether caching is enabled

### ToolUsageStats (Metrics Dashboard)

Shows for each tool:
- **Executions**: Total execution count with progress bar
- **Success Rate**: Percentage with color-coded indicator (green >= 80%, yellow >= 50%, red < 50%)
- **Avg Time**: Average execution time in milliseconds
- **Cache Hits**: Cache hit rate percentage
- **Last Executed**: Timestamp of most recent execution

Sorting options: By Executions, Success Rate, or Avg Time

### TypeScript Types

New types added to `frontend/src/types/api.ts`:

```typescript
type ToolCategory = 'schema' | 'data' | 'query' | 'validation';

interface ToolParameter {
  type: string;
  description: string;
  default?: any;
}

interface ToolResponse {
  name: string;
  description: string;
  category: ToolCategory;
  parameters: Record<string, ToolParameter>;
  required_params: string[];
  cacheable: boolean;
  cache_ttl: number;
}

interface ToolStatsResponse {
  times_executed: number;
  successes: number;
  failures: number;
  success_rate: number;
  avg_time_ms: number;
  cache_hit_rate: number;
  last_executed?: string;
}

interface AllToolStatsResponse {
  total_tools: number;
  total_executions: number;
  overall_success_rate: number;
  by_tool: Record<string, ToolStatsResponse>;
}

interface ToolsPromptResponse {
  prompt_text: string;
  tool_count: number;
}
```

### API Service (toolsApi.ts)

Provides 6 methods:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `listTools(filters?)` | `GET /api/tools` | List tools, optionally filtered by category |
| `getAllStats()` | `GET /api/tools/stats` | Get execution stats for all tools |
| `getToolStats(name)` | `GET /api/tools/stats/{name}` | Get stats for specific tool |
| `getToolsPrompt(category?)` | `GET /api/tools/prompt` | Get tools formatted for LLM prompt |
| `invalidateToolCache(name)` | `POST /api/tools/{name}/invalidate-cache` | Invalidate cache for one tool |
| `invalidateAllCache()` | `POST /api/tools/invalidate-all-cache` | Invalidate all tool caches |

### Testing

30 comprehensive tests in `frontend/tests/ToolsPanel.test.tsx` covering:
- Tab navigation and switching
- Overview stats rendering
- Tool directory filtering
- Usage stats sorting
- Error handling and loading states
- Cache invalidation actions
- Responsive layout behavior

---

## Related Documentation

- [Phase 3 Implementation Plan](PHASE_3_IMPLEMENTATION_PLAN.md)
- [Schema-Aware Fixes](SCHEMA_AWARE_FIXES.md)
- [Query Planning Agent](QUERY_PLANNING_AGENT.md)
- [Parallel Execution](PARALLEL_EXECUTION.md)
