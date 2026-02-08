# Multi-Dimensional Technical Audit: File Data Source Integration

## 1. Executive Summary
The "File Data Source Integration" feature introduces the ability to upload CSV and Excel files, infer their schemas using DuckDB, and query them using the existing natural language interface. 

**Status**: ⚠️ **Near Production-Ready, but blocked by CI/Environment issues.**
The core logic is sound and architecturally cohesive with Antigravity+Gemini. However, the testing environment is currently broken (missing `pytest`), and there are potential concurrency bottlenecks in the DuckDB session management.

---

## 2. Persona-Based Audit

### 👷‍♂️ Senior Software Engineer
**Focus**: Code Quality, Patterns, Integrations, Tests.

*   **The Wins**:
    *   **DuckDB Integration**: Using `duckdb` for both schema inference and querying is an excellent choice for performance and flexibility without needing a heavy database setup.
    *   **Async I/O**: Proper use of `aiofiles` and `run_in_executor` to keep the main event loop non-blocking during file operations.
    *   **Fallback Logic**: The `ResultNarrator` (lines 650-668) has robust fallback logic if the LLM fails, ensuring the user always gets *some* insight.
    *   **Security**: `_sanitize_filename` and path validation prevent directory traversal attacks.

*   **Issues & Bugs**:
    *   **CRITICAL: Missing Test Dependencies**: The project uses `pytest` imports in `tests/`, but `pytest` is not listed in `requirements.txt` (only `fastapi`, `sqlalchemy`, etc.). This causes CI/CD reliability issues.
    *   **Concurrency Risk**: `FileSourceDuckDBSession` uses a lock for *loading* tables, but `execute_query` relies on `duckdb`'s internal handling inside a thread pool. While DuckDB `cursor()` is generally thread-safe for read-only, high-load parallel queries might contend or crash if not managed carefully in in-memory mode.
    *   **Error Handling**: Exception handling in `process_upload` is good, but `upload_file` endpoint could expose raw internal error strings to the user in some `HTTP 500` cases.

*   **Recommendations**:
    *   Add `pytest` and `httpx` to a `requirements-dev.txt`.
    *   Verify thread safety of concurrent DuckDB queries under load.

### 👩‍💼 Project Manager
**Focus**: UX, Scope, "Definition of Done".

*   **The Wins**:
    *   **Feature Completeness**: Upload, auto-schema detection, and querying are all implemented. Frontend supports drag-and-drop and progress/status.
    *   **User Value**: Significantly expands the tool's utility beyond connected DBs to ad-hoc analysis.

*   **Issues**:
    *   **UX Gaps**: The "Processing" state might hang if the backend restarts. There is no websocket/polling mechanism visible in `FileUploadModal` to update status from 'processing' to 'ready' without a refresh or manual action (though `handleFileUploadSuccess` does wait for the request to finish, which is synchronous-ish).
    *   **Technical Debt**: `ResultNarrator.py` is becoming a "God Class" (1200+ lines). It handles stats, prompts, anomalies, and formatting.

*   **Definition of Done**:
    *   [x] Feature Implemented
    *   [ ] Tests Passing (Failed)
    *   [ ] CI Configured (Missing deps)

### 🏗️ Data Architect
**Focus**: Data Lineage, Schema, State.

*   **The Wins**:
    *   **Schema & Lineage**: `FileSource` model correctly links `user_id`, `chat_session_id`, and `original_filename`. We can trace exactly where data came from.
    *   **Lazy Loading**: `FileSourceDuckDBSession` lazily loads tables into memory only when requested. This is crucial for memory management.

*   **Issues**:
    *   **State Management**: In-memory DuckDB tables are lost on server restart. The system handles this by reloading from disk on next query (`ensure_table_loaded`), which is good, but large files will cause a "cold start" delay after every restart.
    *   **Data Types**: DuckDB inference is powerful but might misclassify columns with mixed types (e.g., ID columns that look like integers but are strings).

### 🔍 Data Analyst
**Focus**: Data Utility, Bias, Interpretability.

*   **The Wins**:
    *   **Smart Narratives**: The `ResultNarrator` ignores "ID" columns to focus on meaningful statistics (min/max/avg for numbers, distribution for strings).
    *   **Anomaly Detection**: The Z-score implementation for outlier detection adds real analytical value beyond just "summarizing rows".

*   **Issues**:
    *   **LLM Hallucination Risk**: If `ResultNarrator` feeds too much raw data to Gemini Flash 3, it might truncate or hallucinate trends. The hard limit of `max_sample_rows=20` is safe but might miss broader context.

---

## 3. Data Lineage & Flow (Visual)

```mermaid
graph TD
    User[User] -->|Uploads File| API[API /upload]
    API -->|Validate & Sanitize| Handler[FileSourceHandler]
    Handler -->|Write Stream| Disk[(Local Disk Storage)]
    Handler -->|Connect| Duck[DuckDB (In-Memory)]
    Duck -->|Read_CSV_Auto| Schema[Inferred Schema]
    Handler -->|Save Metadata| DB[(PostgreSQL Metadata)]
    
    subgraph Query Execution
    User -->|Ask Question| Chat[Chat Interface]
    Chat -->|Natural Language| Planner[Query Planner]
    Planner -->|Select Source| Router[Multi-DB Router]
    Router -->|SQL Generation| Gen[LLM (Gemini)]
    Gen -->|Execute SQL| Session[FileSourceDuckDBSession]
    Session -->|Lazy Load| Duck
    Duck -->|Query| Disk
    Session -->|Result Set| Narrator[ResultNarrator]
    Narrator -->|Stats & Insights| User
    end
```

## 4. Action Plan (Immediate Fixes)

1.  **Fix Test Environment**:
    *   Create `requirements-dev.txt` including `pytest`, `pytest-asyncio`, `httpx`.
    *   Update `requirements.txt` if these are needed in production (unlikely for pytest).
2.  **Hardening DuckDB Session**:
    *   Add a test case that attempts concurrent queries to `FileSourceDuckDBSession` to verify thread safety.
3.  **Refactor ResultNarrator**:
    *   Extract `_extract_statistics`, `_detect_anomalies`, `_detect_trends` into a separate `DataProfiler` service class to reduce the size of `ResultNarrator`.
4.  **UX Polish**:
    *   Ensure `FileSource` cleanup (expiration) is actually scheduled (e.g., via a background task or cron), as `expires_at` exists in the model but no background job was seen in the diff.
