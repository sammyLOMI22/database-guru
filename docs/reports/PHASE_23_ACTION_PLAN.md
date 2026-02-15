# Phase 23: Action Plan
**Branch:** `docker-containerization`

This action plan outlines critical fixes and recommended next steps based on the technical audit. These are suggestions for immediate implementation to ensure production readiness.

## 1. 🛡️ Security Hardening (High Priority)
**Issue:** Application connects as `postgres` superuser (or whatever `POSTGRES_USER` is set to, which defaults to `dbguru`).
**Fix:** Create a dedicated application user with limited privileges.

**Proposed Changes:**
- **File:** `docker/init-db.sh` (New file)
- **Action:** Add an initialization script to Postgres docker entrypoint.

```bash
#!/bin/bash
set -e

# Create a restricted user for the application
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER app_runtime_user WITH PASSWORD '$APP_DB_PASSWORD';
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO app_runtime_user;
    GRANT USAGE ON SCHEMA public TO app_runtime_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime_user;
EOSQL
```

## 2. 🔄 Reliability Improvements (Medium Priority)
**Issue:** `OllamaClient` lacks retry logic for transient failures.
**Fix:** Add `tenacity` retry decorator to generation methods.

**Proposed Changes:**
- **File:** `src/llm/ollama_client.py`
- **Action:** Decorate `generate` and `embeddings` methods.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout))
)
async def generate(self, ...):
    # ... existing code ...
```

## 3. 🏗️ Architectural Refactoring (Low Priority / Tech Debt)
**Issue:** `src/llm/prompts.py` is a large monolithic file.
**Fix:** Split into a module structure.

**Proposed Structure:**
```text
src/llm/prompts/
├── __init__.py
├── sql_generation.py    # SYSTEM_PROMPT, SQL_GENERATION_TEMPLATE
├── analysis.py          # NARRATIVE_GENERATION_PROMPT, SCHEMA_ANALYSIS
└── dialects.py          # DIALECT_RULES
```
**Action:** Move constants to respective files and update imports in `ollama_client.py` and agents.

## 4. 🧬 Data Lineage Depth (Medium Priority)
**Issue:** `sql_lineage_parser.py` may miss Common Table Expressions (CTEs).
**Fix:** Add CTE extraction logic using `sqlparse`.

**Proposed Snippet:**
```python
# In SQLLineageParser class

def _extract_ctes(self, stmt):
    """Extract CTE definitions explicitly"""
    ctes = {}
    # Iterate through tokens to find WITH clause
    # Logic to parse CTE name and its definition
    # This involves finding the 'AS' keyword and the parenthesized query
    return ctes
```

## 5. 🚀 Next Steps (Future Roadmap)
1.  **Observability:** Implement OpenTelemetry in the Docker stack (Jaeger/Prometheus).
2.  **Smart Insights:** Use the Lineage Graph to suggest query optimizations to the user automatically (e.g., "You are filtering on a non-indexed column").
3.  **Visual Lineage:** Add a React Flow component to the frontend to visualize the `LineageGraph` JSON returned by the backend.
