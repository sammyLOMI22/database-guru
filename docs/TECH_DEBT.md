# Technical Debt Register

This document tracks known technical debt items for future resolution.

---

## Lineage Intelligence Module

### 1. DRY Violation - LLM Call Handling (Critical)

**Source:** PR Review (Jules - Oct 2023)

**Issue:** `LineageConversationAgent`, `LineageNarrator`, `ImpactAdvisor`, `PatternIntelligence`, and `SchemaHealthAnalyzer` all implement near-identical logic for:
- Calling LLM client with `asyncio.wait_for`
- Handling `TimeoutError`
- Catching exceptions and returning fallbacks

**Files Affected:**
- `src/lineage/lineage_narrator.py` (3 call sites)
- `src/lineage/lineage_conversation_agent.py` (1 call site)
- `src/lineage/impact_advisor.py` (3 call sites)
- `src/lineage/pattern_intelligence.py` (1 call site)
- `src/lineage/schema_health_analyzer.py` (1 call site)

**Proposed Fix:** Create `safe_llm_call()` utility in `src/lineage/llm_utils.py`:
```python
async def safe_llm_call(
    llm_func: Callable,
    fallback_value: str,
    timeout_seconds: float = 15.0,
    error_context: str = "LLM generation",
) -> str:
    """Executes LLM call with standardized timeout and error handling."""
    try:
        response = await asyncio.wait_for(llm_func, timeout=timeout_seconds)
        return response.strip() if response else fallback_value
    except asyncio.TimeoutError:
        logger.warning(f"{error_context} timed out after {timeout_seconds}s")
        return fallback_value
    except Exception as e:
        logger.error(f"{error_context} failed: {e}")
        return fallback_value
```

**Priority:** High
**Effort:** Medium (10+ call sites to refactor)

---

### 2. In-Memory Session Storage (High)

**Source:** PR Review (Jules - Oct 2023)

**Issue:** `LineageConversationAgent` uses `_conversation_contexts` (in-memory dict) to store session history. Server restarts will wipe all active conversations.

**File:** `src/lineage/lineage_conversation_agent.py:200`

**Inconsistency:** Project already has `ChatSession` table in `src/database/models.py` that is not used by this feature.

**Proposed Fix:**
1. Persist `ConversationContext` to `ChatSession` table
2. Use `connection_id` and `user_id` to resume sessions across restarts
3. Add session expiry/cleanup job

**Priority:** High (blocks production deployment)
**Effort:** Medium

---

### 3. Fuzzy SQL Matching Creates Phantom Lineage (Medium)

**Source:** PR Review (Jules - Oct 2023)

**Issue:** `LineageConversationAgent` and `ImpactAnalyzer` find tables using:
```python
QueryHistory.generated_sql.ilike(f"%{table}%")
```

Searching for table `user` incorrectly matches `user_sessions`, `payment_user_ref`, etc.

**Files:**
- `src/lineage/lineage_conversation_agent.py:554`
- `src/lineage/impact_analyzer.py:245`

**Proposed Fix:**
1. Pre-process `QueryHistory` entries using `SQLLineageParser`
2. Store parsed lineage as JSON in new `lineage_metadata` column
3. Query structured data instead of fuzzy text matching

**Priority:** Medium
**Effort:** High

---

## Phase 16: LLM Usage Monitoring

### 4. Multi-DB Parallel Queries Lose Tracking Context (Medium)

**Source:** PR Review (Phase 16, Feb 2026) — Issue #7

**Issue:** `_execute_single_query_task` in `multi_db_query.py` does not receive `db`, `query_history_id`, or `chat_session_id`. Per-database SQL generation LLM calls (the most expensive ones) are untracked in the multi-db path.

**File:** `src/api/endpoints/multi_db_query.py`

**Proposed Fix:** Pass tracking context (db session, query_history_id, chat_session_id) into `_execute_single_query_task` so the LLM usage tracker can record per-database calls.

**Priority:** Medium (data completeness gap)
**Effort:** Medium

---

### 5. Orphaned QueryHistory Records on Error (Medium)

**Source:** PR Review (Phase 16, Feb 2026) — Issue #8

**Issue:** A `QueryHistory` record is created with `status="processing"` before SQL generation. If the request fails, the record is never updated to `status="failed"`, leaving orphaned processing records.

**File:** `src/api/endpoints/query.py:221-231`

**Proposed Fix:** Add a try/finally or error handler to update the QueryHistory status to `"failed"` on exceptions.

**Priority:** Medium (data integrity)
**Effort:** Low

---

### 6. SQLite-Specific SQL in Aggregator and API (Medium)

**Source:** PR Review (Phase 16, Feb 2026) — Issue #9 / Technical Audit

**Issue:** `func.strftime()` and `func.date()` in `LLMUsageAggregator` and `llm_usage.py` are SQLite-only. Will break if metadata DB is migrated to PostgreSQL.

**Files:**
- `src/services/llm_usage_aggregator.py`
- `src/api/endpoints/llm_usage.py`

**Proposed Fix:** Use SQLAlchemy's `extract()` or a cross-platform date helper.

**Priority:** Medium (only matters if migrating off SQLite)
**Effort:** Low

---

### 7. N+1 Upsert in Aggregator (Medium)

**Source:** PR Review (Phase 16, Feb 2026) — Issue #10

**Issue:** Individual SELECT + INSERT/UPDATE per aggregation bucket in `LLMUsageAggregator`. Could result in dozens of queries.

**File:** `src/services/llm_usage_aggregator.py:57-93`

**Proposed Fix:** Use `INSERT ... ON CONFLICT UPDATE` (upsert) to batch operations.

**Priority:** Medium (performance at scale)
**Effort:** Medium

---

### 8. Uncached Cost Service DB Queries (Medium)

**Source:** PR Review (Phase 16, Feb 2026) — Issue #11

**Issue:** `LLMCostService.calculate_cost` runs 1-2 DB queries per tracked LLM call to look up model config. With 5+ agents per request, that's 5-10 extra DB queries.

**File:** `src/services/llm_usage_tracker.py:175`

**Proposed Fix:** Cache model configs in memory with a TTL or load them once at startup.

**Priority:** Medium (performance)
**Effort:** Low

---

### 9. Two Competing Token-Tracking Patterns (Low)

**Source:** PR Review (Phase 16, Feb 2026) — Issue #12

**Issue:** Some agents use Pattern A (tracker handles everything) while others use Pattern B (also request `return_full_response=True` and manually extract tokens for AgentTrace). Token extraction logic is duplicated.

**Files:** `src/llm/sql_generator.py`, `src/llm/query_planning_agent.py`, `src/llm/result_narrator.py`

**Proposed Fix:** Standardize on one pattern. Prefer Pattern A (tracker-only) and have the tracker populate AgentTrace data.

**Priority:** Low (maintainability)
**Effort:** Medium

---

### 10. Frontend Dashboard Polish (Low)

**Source:** PR Review (Phase 16, Feb 2026) — Issues #13-15, #28-30

**Issues:**
- Remaining `any` types in `LLMUsageDashboard.tsx` (`byModel`, `byProvider` state, API return types)
- No error state in dashboard — fetch failures show blank/zeros instead of an error message
- `response_model=List[dict]` on two API endpoints — no Pydantic validation or OpenAPI docs
- No `AbortController` for request cancellation on rapid time-range switches
- `SessionUsageBadge` usage state typed as `any`
- Missing `aria-pressed` on time range buttons, missing `aria-label` on loading spinner

**Files:**
- `frontend/src/components/dashboard/LLMUsageDashboard.tsx`
- `frontend/src/components/dashboard/SessionUsageBadge.tsx`
- `frontend/src/services/llmUsageApi.ts`
- `src/api/endpoints/llm_usage.py:94,127`

**Priority:** Low
**Effort:** Medium

---

### 11. Low-Severity Cleanup Items (Low)

**Source:** PR Review (Phase 16, Feb 2026) — Issues #16-27

| # | File | Issue |
|---|------|-------|
| 16 | `llm_usage_tracker.py:21-28` | Encoder retry on every call after failure — no sentinel to prevent retries + log spam |
| 17 | `llm_usage_tracker.py:195` | Redundant `request_timestamp` column — `created_at` does the same thing |
| 18 | `llm_cost_service.py:24-28` | LIKE pattern doesn't escape `%`/`_` wildcards in model names |
| 19 | `llm_cost_service.py:57-86` | Missing `qwen2.5-coder` (primary project model) from default configs |
| 20 | `llm_usage_aggregator.py:58` | `int(row.hour)` crashes on NULL hours |
| 21 | `models.py:92` | Nullable hour in unique constraint allows duplicate daily aggregates |
| 22 | `schemas.py` | `InlineUsageStats` defined but never used |
| 23 | `ollama_client.py` | `generate()` return type weakened from `str` to `Any` |
| 24 | `pattern_intelligence.py` | `_generate_optimizations` accepts tracking params but never makes LLM calls — dead params |
| 25 | `lineage_conversation_agent.py` | Missing `chat_session_id`/`chat_message_id` — calls tracked without session context |
| 26 | `multi_db_query.py:938` | `query_record_id` captured but never used (dead code) |
| 27 | `query.py:368` | Same dead `query_record_id` variable |

**Priority:** Low
**Effort:** Low-Medium

---

### 12. Test Coverage Gaps (Medium)

**Source:** PR Review (Phase 16, Feb 2026)

**Missing tests:**
- No tests for `track_call` failure/error path (silent data loss undetected)
- No test for aggregation idempotency (could double-count)
- No tests for any of the 7 API endpoints in `llm_usage.py`
- No test for session usage endpoint (`/session/{session_id}`)
- `extract_tokens` not tested for None/empty response, unknown provider, partial Ollama response
- Fuzzy model name matching (`llama3:latest` → `llama3`) untested
- Token estimation test only asserts `> 0`, not a reasonable range

**Priority:** Medium
**Effort:** Medium

---

## Resolved Items

### Schema Cache Fingerprint Performance (Fixed 2026-02-01)
`get_quick_fingerprint()` was calling `get_full_schema()` defeating cache optimization. Fixed to use lightweight SQLAlchemy inspection.

### Impact Advisor SQL List Format (Fixed 2026-02-01)
LLM returning `sql` as list instead of string caused Pydantic validation error. Added list-to-string conversion.

### Schema Health Analyzer Import (Fixed 2026-02-01)
Changed from non-existent `ConnectionManager` to `UserDatabaseConnector`.

### Schema Health Recommendations Format (Fixed 2026-02-01)
Added parsing for LLM returning recommendations as dicts instead of strings.

### Graph Recursion Depth (Fixed 2026-02-01)
Added `max_depth=50` parameter to `_trace_sources` to prevent stack overflow.
