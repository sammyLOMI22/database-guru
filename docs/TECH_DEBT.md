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
