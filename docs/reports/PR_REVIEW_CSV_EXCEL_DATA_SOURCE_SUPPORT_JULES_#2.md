# Multi-Dimensional Technical Audit Report: Phase 13 & Lineage Intelligence

**Date:** January 24, 2026
**Project:** Database Guru (Antigravity Framework)
**Status:** Pre-Production Audit

---

## 1. Persona Critiques

### 🛠 Senior Software Engineer
**Focus:** *Code Quality, DRY, Resilience, and Maintainability*

*   **DRY Violations (High Priority):**
    *   **LLM Call Patterns:** `ResultNarrator`, `LineageNarrator`, `LineageConversationAgent`, and others all independently implement `asyncio.wait_for` wrappers around LLM calls. This logic should be centralized into `src/llm/llm_utils.py` or a base agent class.
    *   **File Utilities:** `excel_to_temp_csv` is defined in `file_source_handler.py` but used in `file_source_session.py`. It should reside in `src/core/file_utils.py`.
    *   **Validation Logic:** `_validate_file_path` and `_sanitize_sheet_name` are appropriately moved to `file_utils.py`, but ensure all components (Handlers and Sessions) import from there consistently.
*   **Resilience:**
    *   Hardcoded 15s timeouts in lineage agents may cause failures on slower local LLMs (e.g., Llama 3 8B on consumer hardware). These should always pull from the `ModelRouter` and `SystemSettings`.
*   **Logic Bugs:**
    *   `SQLExecutor.validate_query_safety` relies on basic keyword matching which can be bypassed by comments or clever formatting.

### 📅 Project Manager
**Focus:** *Definition of Done, Technical Debt, and ROI*

*   **Definition of Done:** Phase 13 (CSV/Excel) is functionally complete but lacks a centralized **Audit Log** despite being referenced in `SystemSettings`. This is a gap in the "production-ready" criteria.
*   **Technical Debt:**
    *   **In-Memory Context:** `LineageConversationAgent` uses an in-memory dictionary for chat history. This will fail in a load-balanced environment and data is lost on restart. Move to Redis or the main Postgres DB.
*   **Innovations:**
    *   **Home Server Optimization:** For Mac Mini deployments, implement a **Token-aware Request Queue**. Currently, parallel executions (`MultiDatabaseHandler`) could easily OOM a small server if multiple users trigger large LLM tasks.

### 🏛 Data Architect
**Focus:** *Lineage, Traceability, and Schema Integrity*

*   **Lineage Logic Bug:** `SQLLineageParser` currently identifies Common Table Expressions (CTEs) as source tables. This breaks traceability as it suggests the data comes from a non-existent table `cte_name` rather than the underlying base table.
*   **Parsing Redundancy:** `ImpactAnalyzer` duplicates SQL parsing logic using crude regex instead of utilizing the `SQLLineageParser`. This leads to inconsistent impact reports.
*   **State Predictability:** The "Antigravity" pods require predictable state transitions. The transition from `processing` to `ready` in `FileSource` is well-handled, but the lazy-loading in `FileSourceDuckDBSession` needs a clear "eviction policy" to prevent memory leaks over time.

### 📈 Data Analyst
**Focus:** *Data Utility, Telemetry, and AI Integrity*

*   **Telemetry Utility:** `QueryHistory` is excellent. It captures the "how" (SQL) and the "why" (Question).
*   **Telemetry Gap:** We lack telemetry on **Lineage usage**. We should track which tables are most frequently explained by the `LineageNarrator` to identify "confusing" schema areas.
*   **AI Integrity:** `ResultNarrator`'s anomaly detection (Z-scores) is a "Win" for data integrity. It alerts analysts to potential outliers that might bias their interpretation of the AI's summary.

---

## 2. The Review Matrix

| Category | Feedback |
| :--- | :--- |
| **The Wins** | **Parallel Execution:** `MultiDatabaseHandler` and `SelfCorrectingAgent` show sophisticated concurrent logic. **Robust Parsing:** `extract_json_object` with balanced brace matching is highly reliable. |
| **Issues & Bugs** | **CTE Shadowing:** Lineage parser fails to resolve CTEs to base tables. **Volatile Chat:** Lineage Q&A history is lost on server restart. |
| **Security Concerns** | **Local API Exposure:** Ensure DuckDB memory limits are strictly enforced (currently set to 1GB) to prevent DoS via large file uploads. **Prompt Injection:** `PromptSanitizer` is robust, but ensure it's applied to the new `LineageConversationAgent` inputs. |
| **Cohesion** | The integration of local files via DuckDB feels seamless. It treats files as first-class database citizens, which is architecturally elegant. |
| **Future Direction** | **Mac Mini Server:** Implement `Ollama` request batching. **Refactor:** Move all LLM "wait-for-and-parse" logic to a unified `BaseAgent` class to reduce boilerplate. |

---

## 3. Visual Flow (Data & Lineage)

```text
[ USER UPLOAD ]
      |
      v
[ FileSourceHandler ] ---> [ Physical Disk Storage ]
      |                      (Hash-deduplicated)
      v
[ FileSource (SQL DB) ] <--- Metadata & Inferred Schema
      |
      +--- [ FileSourceDuckDBSession ]
                  |
                  v
            [ In-Memory DuckDB ] <--- Lazy Loading (on query)
                  |
                  +--- [ MultiDatabaseHandler ]
                              |
                              v
                        [ Result Set ] ---> [ ResultNarrator ] ---> [ Business Insights ]

[ SQL QUERY ]
      |
      v
[ SQLLineageParser ] ---> [ LineageGraph (Nodes/Edges) ]
      |                         |
      |                         v
      +-----------------> [ LineageNarrator ] ---> [ "Data flows from Users to Sales..." ]
```

---

## 4. Action Plan (Critical Fixes)

1.  **[High] Fix CTE Parsing:** Update `SQLLineageParser` to ignore CTE names (found in `WITH` clauses) and trace through them to physical source tables.
2.  **[High] Unified LLM Utility:** Create `src/llm/llm_utils.py:call_llm_with_timeout()` to centralize the `wait_for` + `extract_json` + `retry` logic used by all narrators and agents.
3.  **[Medium] Persistent Lineage Chat:** Refactor `LineageConversationAgent` to store session history in the `chat_messages` table instead of an in-memory dict.
4.  **[Medium] Refactor File Utilities:** Move `excel_to_temp_csv` from `file_source_handler.py` to `file_utils.py` to clean up the import dependency loop.
5.  **[Low] Performance Monitoring:** Add a "Memory Pressure" check to `FileSourceDuckDBSession` that unloads the least recently used (LRU) tables when approaching the 1GB limit.
 PR Review Triage Summary                                                                                                                                             
                                                                                                                                                                       
  Already Resolved (No Action Needed)                                                                                                                                  
  ┌───────────────────────────────────────────┬──────────────────┬─────────────────────────────────────────────────────┐                                               
  │                   Issue                   │      Source      │                       Status                        │                                               
  ├───────────────────────────────────────────┼──────────────────┼─────────────────────────────────────────────────────┤                                               
  │ Unified LLM utility (extract_json_object) │ Jules #2         │ src/lineage/llm_utils.py exists, all agents use it  │                                               
  ├───────────────────────────────────────────┼──────────────────┼─────────────────────────────────────────────────────┤
  │ excel_to_temp_csv location                │ Jules #2         │ Shared via import, file_utils.py handles validation │
  ├───────────────────────────────────────────┼──────────────────┼─────────────────────────────────────────────────────┤
  │ pytest missing from requirements          │ File Integration │ requirements-dev.txt includes pytest                │
  ├───────────────────────────────────────────┼──────────────────┼─────────────────────────────────────────────────────┤
  │ DuckDB thread safety                      │ File Integration │ Async locks + threading locks + per-op cursors      │
  ├───────────────────────────────────────────┼──────────────────┼─────────────────────────────────────────────────────┤
  │ ImpactAdvisor SQL parsing duplication     │ Jules #2         │ No regex-based parsing found; delegates properly    │
  ├───────────────────────────────────────────┼──────────────────┼─────────────────────────────────────────────────────┤
  │ CTE parsing bug                           │ Jules #2         │ CTEs are ignored (not misidentified) — low priority │
  └───────────────────────────────────────────┴──────────────────┴─────────────────────────────────────────────────────┘
  Still Outstanding — Worth Addressing

  High Priority:

  1. File expiration cleanup not implemented (File Integration review)
    - FileSource has an expires_at field but no background task ever runs to delete expired files. Files accumulate indefinitely on disk.
  2. PromptSanitizer not applied to LineageConversationAgent (Jules #2)
    - src/lineage/lineage_conversation_agent.py processes user questions directly with no prompt injection protection. The sanitizer exists but isn't wired in.

  Medium Priority:

  3. In-memory lineage chat history (Jules #2)
    - LineageConversationAgent stores contexts in a plain dict. Has TTL cleanup (1hr) and LRU eviction (100 sessions), so it won't leak memory — but history is lost on
   restart. Moving to the chat_messages table would add persistence.
  4. DuckDB table eviction (Jules #2 / File Integration)
    - Tables are lazily loaded into the in-memory DuckDB instance but never evicted. No memory pressure monitoring. The 1GB limit is set, but there's no graceful LRU
  unloading before hitting it.
  5. Generic error exposure in file upload endpoint (File Integration)
    - The catch-all except Exception in the upload endpoint returns str(e) to the client, which could leak internal details in edge cases.

  Low Priority:

  6. ResultNarrator size (File Integration) — 1,221 lines but well-organized with clear method separation. Not urgent.
  7. Hardcoded timeouts (Jules #2) — Agents have hardcoded defaults (15-30s) but do attempt to load from ModelRouter. Reasonable as-is.

  ---
  Recommendation

  The two items I'd prioritize are:

  - File expiration cleanup — this is a real resource leak. Uploaded files never get cleaned up.
  - PromptSanitizer on LineageConversationAgent — this is a security gap where user input goes directly to LLM prompts without injection detection.
