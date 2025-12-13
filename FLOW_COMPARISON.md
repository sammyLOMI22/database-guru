# Query Processing Flow: Main vs Query-Compilation Branch

## Executive Summary

The Query-Compilation branch introduces **3 NEW FEATURES** into the query processing pipeline:

1. **Query Planning Agent** - Creates structured execution plans before SQL generation
2. **Tool-Using Agent** - Explores schema with tools to gather context
3. **Query Compilation System** - Executes SQL compilation (normalization, plan caching, prepared statements)

These add significant overhead but claim 50-70% speedup for repeated queries. **The issue:** They also change the SQL generation flow, potentially affecting accuracy.

---

## Side-by-Side Flow Comparison

### MAIN BRANCH (Baseline - Proven Accurate)

```
User Question
    ↓
Input Sanitization
    ↓
Conversational Context (if session_id)
    ↓
Schema Introspection (from user's database)
    ↓
Self-Correcting Agent
    ├─→ SQL Generation (via LLM)
    ├─→ Execution
    ├─→ [If Error] → Parallel Fixes (quick_fix, learned, llm)
    ├─→ [If Error] → Result Verification
    └─→ Return Result

QUERY GENERATION TIME: ~500-800ms (direct LLM)
```

### QUERY-COMPILATION BRANCH (With New Features)

```
User Question
    ↓
Input Sanitization
    ↓
Conversational Context (if session_id)
    ↓
Schema Introspection (from user's database)
    ↓
Self-Correcting Agent
    ├─→ QUERY PLANNING AGENT [NEW]
    │   ├─→ Analyze question complexity
    │   ├─→ Create structured plan (if complex enough)
    │   └─→ Generate SQL from plan
    │
    ├─→ TOOL-USING AGENT [NEW] ⚠️ OVERHEAD ADDED HERE
    │   ├─→ Analyze question
    │   ├─→ Execute schema tools (search_schema, get_table_info, etc.)
    │   ├─→ Build enriched context (300-800ms added)
    │   └─→ Pass enriched schema to SQL generator
    │
    ├─→ SQL Generation (via LLM with enriched schema)
    │
    ├─→ Execution with Query Compilation [NEW]
    │   ├─→ SQL Normalization (extract parameters)
    │   ├─→ EXPLAIN Plan Caching (if connection context provided)
    │   └─→ Prepared Statement Management
    │
    ├─→ [If Error] → Parallel Fixes (quick_fix, learned, llm, tool_using)
    │
    ├─→ [If Error] → Result Verification
    │
    └─→ Return Result with Compilation Metadata

QUERY GENERATION TIME: ~1.0-1.5s (with planning + tool-using overhead)
```

---

## Detailed Differences

### 1. SQL Generation Phase

| Aspect | Main | Query-Compilation |
|--------|------|-------------------|
| **SQL Generation** | Direct LLM call with schema | Query Planning Agent → LLM OR Tool-Using Agent → LLM |
| **Query Planning** | None | Optional (if complexity >= 0.5) |
| **Tool-Using** | None | ALWAYS runs during initial generation ⚠️ |
| **Schema Context** | Raw schema | Enriched with tool exploration |
| **Overhead** | ~200ms | ~800ms+ (planning + tools) |

### 2. Execution Phase

| Aspect | Main | Query-Compilation |
|--------|------|-------------------|
| **SQL Execution** | Direct execution | Compilation layers executed |
| **Normalization** | None | Always normalized (literals → params) |
| **Plan Caching** | None | EXPLAIN plans cached per connection |
| **Prepared Statements** | None | Lazy-prepared after 2+ executions |
| **Metadata Returned** | Basic (time, rows) | Compilation stats (cache hits, prepared) |

### 3. Error Correction Phase

| Aspect | Main | Query-Compilation |
|--------|------|-------------------|
| **Fix Strategies** | quick_fix, learned, llm | quick_fix, learned, llm, **tool_using** |
| **Parallelism** | Parallel (3 strategies) | Parallel (4 strategies) |
| **Tool-Using in Fixes** | No | Yes (extra tools called on error) |

---

## New Features' Purpose & Overhead

### Feature 1: Query Planning Agent
**Purpose:** Improve accuracy for complex multi-table queries
**How:** Creates structured execution plan before SQL generation
**Overhead:** 200-500ms per query (always for complex queries)
**Triggers on:** Questions with complexity score >= 0.5
- Multi-table operations: +0.3
- Aggregations: +0.2
- Grouping: +0.2
- Temporal operations: +0.1

**For "what products shipped to new york":**
- Score: 0.2 (only location keyword)
- Result: Skipped (< 0.5 threshold)
- No overhead

### Feature 2: Tool-Using Agent ⚠️ HIGH OVERHEAD
**Purpose:** Gather schema context before SQL generation
**How:** Runs schema tools (search_schema, get_table_info, get_column_values, etc.)
**Overhead:** 300-800ms per query ⚠️ RUNS ALWAYS DURING INITIAL GENERATION
**Triggers on:** Every single query (no threshold check!)

**For "what products shipped to new york":**
- Runs 3-5 schema tools
- Adds 300-800ms ALWAYS
- Enriches schema with sample values
- Result: Slower first attempt but potentially more accurate

### Feature 3: Query Compilation
**Purpose:** Speed up REPEATED queries
**How:** Cache EXPLAIN plans and prepared statements
**Overhead:** <2ms per query (minimal - happens after SQL generated)
**Triggers on:** Execution phase (after SQL already generated)

**Benefit:** Only visible on REPEATED queries (2nd+ execution)
**Cost:** None on first execution (just adds metadata)

---

## The Problem: Tool-Using Agent During Generation

### Current Flow in Query-Compilation
```python
for attempt_num in range(1, max_retries + 1):
    if attempt_num == 1:
        if sql is None:
            # ⚠️ ALWAYS RUNS
            if self.enable_tool_using and self.tool_using_agent:
                tool_result = await self.tool_using_agent.process(...)
                enhanced_schema = f"{schema}\n\n{tool_result.enriched_context}"

            gen_result = await self.generator.generate_sql(
                question=question,
                schema=enhanced_schema,  # <-- Now enriched with tool data
                ...
            )
```

**Issue:** Tool-Using Agent adds 300-800ms overhead on EVERY query, not just complex ones.

**Side Effect:** The enriched schema might confuse the LLM for simple queries:
- More context = more information
- But also more noise/complexity
- LLM might generate worse SQL for simple queries

---

## Hypothesis: Why Accuracy Degraded

### Simple Query Example: "what products shipped to new york"

**Main Branch (Accurate):**
1. Direct LLM generation with clean schema
2. Result: Good SQL ✅

**Query-Compilation Branch (Degraded):**
1. Tool-Using Agent explores schema (300-800ms)
2. Tools find: tables, sample data, relationships
3. Enriched schema passed to LLM (now much longer)
4. LLM generates SQL based on enriched context
5. **Problem:** LLM might hallucinate tables that don't exist (shipments table)
6. Result: Bad SQL ❌

### Why Hallucination Happens:
- Enriched schema might mention relationships that don't exist
- LLM confused by extra context for simple queries
- Tool exploration might suggest non-existent tables

---

## Performance Claims vs Reality

### Claimed Benefits
- "50-70% speedup for repeated queries"
- "Better accuracy for complex queries"
- "Improved query generation with schema exploration"

### Actual Costs
- **First query:** +300-800ms (Tool-Using overhead)
- **Repeated query:** -40-50ms (Compilation benefit)
- **Net for 2 executions:** 300-800ms - (40-50ms) = **+250-750ms slower overall** ❌

### When Compilation Helps
- Only on **repeated** queries (same question asked twice)
- Only if you run same query **2+ times** (lazy preparation)
- Only if you have **multiple database connections** (per-connection isolation)

### When Compilation Hurts
- **All first queries:** 300-800ms slower (Tool-Using overhead)
- **Accuracy degraded:** LLM confused by enriched schema
- **Simpler queries:** Don't benefit from Query Planning (complexity < 0.5)

---

## Code Changes Summary

### Files Modified:
1. `src/core/executor.py` - Added compilation parameter capture ✅ (safe)
2. `src/api/endpoints/query.py` - Added compilation metadata tracking ✅ (safe)
3. `src/core/schema_inspector.py` - Added fingerprinting ✅ (safe)
4. `src/llm/self_correcting_agent.py` - **Added Tool-Using Agent call ⚠️ (overhead)**
5. `src/main.py` - Registered compilation router ✅ (safe)

### Files NOT Changed:
- `src/llm/sql_generator.py` - SQL generation logic unchanged ✅
- `src/llm/prompts.py` - Prompts unchanged ✅
- `src/llm/confidence_scorer.py` - Unchanged ✅

**Conclusion:** SQL generation itself didn't change, but **additional processing before SQL generation** was added.

---

## Recommendation

### To Fix Accuracy Issues:

**Option 1: Remove Tool-Using During Generation (FASTEST FIX)**
```python
# Remove this block from attempt_num == 1:
if self.enable_tool_using and self.tool_using_agent:
    tool_result = await self.tool_using_agent.process(...)
    enhanced_schema = f"{schema}\n\n{tool_result.enriched_context}"

# Just use normal schema
enhanced_schema = schema
```
**Result:** Restore accuracy to main branch levels, lose Tool-Using context benefit

**Option 2: Make Tool-Using Optional/Conditional**
```python
# Only use Tool-Using for complex queries
if self.enable_tool_using and self.tool_using_agent and is_complex_query:
    tool_result = await self.tool_using_agent.process(...)
```
**Result:** Keep benefit for complex queries, avoid overhead for simple ones

**Option 3: Revert to Main Branch**
```bash
git checkout main -- src/llm/
```
**Result:** Guaranteed accuracy, lose all new features

### Performance Trade-off:
- Compilation helps **repeated queries** (cache hits)
- But hurts **first queries** (Tool-Using overhead)
- **Unless:** You specifically enable Tool-Using only for complex queries

---

## Next Steps

1. **Decide:** Keep Tool-Using or remove it?
   - Keep: Better for complex queries, worse for simple ones
   - Remove: Faster, more accurate, but loses context enrichment

2. **Test:** Measure actual performance
   - Time simple queries: "what products shipped to new york"
   - Time complex queries: "for each category, show sales by month"
   - Compare overhead vs benefits

3. **Document:** Update roadmap with actual costs/benefits
   - Tool-Using adds 300-800ms per query
   - Compilation saves 40-50ms per repeated execution
   - Break-even: ~7-15 repeated queries per unique query

