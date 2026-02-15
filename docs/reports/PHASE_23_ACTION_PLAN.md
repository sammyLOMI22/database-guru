# Phase 23: Action Plan

**Date:** 2026-02-15
**Status:** Post-Audit
**Prepared By:** Antigravity Agent

## 1. Critical Immediate Fixes (Conf/Code)

### A. Docker Compose `DATABASE_URL` Mismatch
**Issue:** The `backend` service defaults to SQLite even if the `postgres` profile is active.
**Fix:** Use an environment variable override or a `docker-compose.override.yml` pattern. For the main file, we can use a conditional approach or document the env var requirement clearly.

**Snippet (`docker-compose.yml` suggestion):**
```yaml
  backend:
    environment:
      # Allow override, but default to SQLite if not specified. 
      # Users running profile:full MUST set DATABASE_URL in .env
      - DATABASE_URL=${DATABASE_URL:-sqlite+aiosqlite:///./data/database_guru.db} 
```

### B. LLM Model Availability Check
**Issue:** `docker-compose.yml` defaults to `llama3.2:latest`. If the user hasn't pulled this specific tag, the `ollama` container starts empty, and the app might timeout waiting for the *first* generation or pull.
**Fix:** Add a dedicated `init-ollama` service or detailed check in the `ollama-pull` service to ensure readiness before backend starts.

**Snippet (`docker-compose.yml` suggestion):**
```yaml
  ollama-pull:
    # ... existing config ...
    entrypoint: ["/bin/sh", "-c", "ollama pull ${OLLAMA_MODEL:-llama3.2:latest} && echo 'Model ready'"]
```

## 2. Recommended Refactors (Next Iteration)

### A. Lineage Parser - Recursive Common Table Expressions (CTE)
**Observation:** The current CTE parser handles basic `WITH` clauses but might struggle with recursive CTEs (`WITH RECURSIVE`) which are common in hierarchical data (like org charts).
**Suggestion:** Add a specific recursion depth check or `RECURSIVE` keyword handler in `_extract_ctes`.

### B. Frontend "Connection Status" Indicator
**Observation:** The UI doesn't clearly show *which* backend DB is currently active (SQLite vs Postgres) or the status of the Ollama connection.
**Suggestion:** Add a status pill in the `SettingsPanel` or `Sidebar`.

## 3. Future Innovation (Phase 24+)

### A. "Smart Caching" based on Lineage
**Concept:** Use the extracted lineage to invalidate cache intelligently. If the lineage shows a query depends on `sales_table`, and we detect a write to `sales_table`, we invalidate only related queries.

### B. "Explain Plan" Visualization
**Concept:** Since we parse the SQL, we can run `EXPLAIN (FORMAT JSON)` on Postgres and visualize the query cost alongside the lineage graph.
