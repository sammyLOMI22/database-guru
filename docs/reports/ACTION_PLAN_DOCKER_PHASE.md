# Action Plan: Critical Fixes & Suggestions

**Target Branch:** `docker_containerization`
**Scope:** Immediate architectural improvements and bug fixes.

---

## 🛠️ Section 1: Immediate Critical Fixes

### A. Fix `DATABASE_URL` Defaulting Issue
In `docker-compose.yml`, the `backend` service currently hardcodes `DATABASE_URL=sqlite...`. This prevents users from easily switching to Postgres using the `full` profile without editing the YAML.

**Suggestion:**
```yaml
# docker-compose.yml
backend:
  environment:
    - DATABASE_URL=${DATABASE_URL:-sqlite+aiosqlite:///./data/database_guru.db}
```

### B. Consolidate `OllamaClient` Logic (DRY Violation)
Refactor `src/llm/ollama_client.py` to use a shared internal helper for tracking, reducing duplication in `generate` and `chat`.

**Suggested Snippet:**
```python
async def _execute_with_tracking(self, db, method_name, prompt, tracking_args, call_fn):
    if not db:
        return await call_fn()

    async with llm_usage_tracker.track_call(
        db=db,
        llm_method=method_name,
        prompt=prompt,
        provider="ollama",
        **tracking_args
    ) as tracking:
        result_dict = await call_fn()
        # Handle different response structures for chat vs generate
        response_text = self._extract_response_text(result_dict, method_name)
        tracking.set_response(response_text, result_dict)
        return result_dict
```

---

## 🏗️ Section 2: Architectural Improvements

### A. Unified UTC Handling
Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` across the codebase to ensure compatibility with Python 3.12+ and prevent issues with naive timestamps.

**Affected Files:**
- `src/api/endpoints/query.py`
- `src/main.py`
- `src/database/models.py` (if any default values)

### B. Health Check Orchestration
The `backend` container should ideally wait for `ollama-pull` to finish downloading the model before it becomes "Healthy".

**Suggestion:**
Modify the `backend` healthcheck or use an `init_container` pattern to verify model availability:
```bash
# In entrypoint.sh or healthcheck
curl -s http://ollama:11434/api/tags | grep -q "${OLLAMA_MODEL}"
```

### C. SQLLineageParser: Recursive CTE Support
Enhance `_extract_ctes` to detect the `RECURSIVE` keyword and set a flag to handle potential circularities in lineage tracing.

**Suggested Snippet:**
```python
def _extract_ctes(self, stmt: sqlparse.sql.Statement) -> None:
    for token in stmt.tokens:
        if token.ttype is Keyword and token.value.upper() == 'WITH':
            # Check next non-whitespace token for RECURSIVE
            # ... logic to handle recursion ...
            pass
```

---

## 🚀 Section 3: Next Iteration Refactors

1.  **Observability:** Implement a Prometheus exporter for `LLMUsageTracker` metrics.
2.  **UI Feedback:** Add a "Database Connectivity" indicator in the frontend to show if the backend is successfully talking to the Target DB and the Ollama instance.
3.  **Schema Cache:** Implement an automatic cache invalidation for schema introspection if the connection parameters change.
4.  **Security:** Add a `SQL_INJECTION_CHECK` layer using a specialized library like `sql-metadata` to supplement the current regex/system prompt approach.
