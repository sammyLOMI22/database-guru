# Database Guru: Deep Dive & Improvement Recommendations

This document provides a technical deep dive into four core features of Database Guru, analyzing their architecture, strengths, and areas for improvement.

## 1. Self-Correcting SQL Agent

**File:** `src/llm/self_correcting_agent.py`

### Architecture
The `SelfCorrectingSQLAgent` is designed to be resilient against SQL generation errors. It operates on a retry loop (default 3 attempts) and employs a "race-to-fix" strategy where multiple correction methods run in parallel.

*   **Parallel Correction Strategy**: The `_try_parallel_fixes` method launches four concurrent tasks:
    1.  **Quick Fix**: Rule-based regex/schema fixes (fastest, no LLM).
    2.  **Learned Fix**: Retrieves historical corrections for similar errors (fast, no LLM).
    3.  **Tool-Using Fix**: Allows an agent to explore the schema using tools (slowest, most thorough).
    4.  **LLM Fix**: Standard prompt-based regeneration (baseline).
    *   *Winner Takes All*: The first successful result is returned, cancelling the others.
*   **Observability**: Integrated `AgentTrace` records every step, decision, and metric for UI visualization.
*   **Result Verification**: Post-execution, the `ResultVerificationAgent` checks for logical anomalies (e.g., empty results, suspicious zeros) even if the SQL validly executes.

### Recommendations
1.  **Adaptive Model Routing for Fallbacks**: currently, if the parallel race times out, it falls back to a standard LLM fix.
    *   *Improvement*: Configure the fallback to use a specific "Coder" model (e.g., DeepSeek-Coder or CodeLlama) which might have higher accuracy for syntax repairs than the general chat model.
2.  **"Safe Mode" Toggle**: The Tool-Using agent is powerful but can be unpredictable or resource-intensive.
    *   *Improvement*: Add a strict "Safe Mode" configuration that disables the Tool-Using path for high-throughput production environments, relying only on deterministic Quick/Learned fixes.
3.  **Structured Error Classification**: The `ErrorDiagnostics` class uses string matching.
    *   *Improvement*: Map database-specific error codes (e.g., Postgres SQLSTATE) to `ErrorType` enums for 100% accurate classification, rather than relying on regex parsing of error messages.

## 2. Conversational Memory

**File:** `src/llm/conversational_memory_agent.py`

### Architecture
The Conversational Memory system enables natural, multi-turn dialogue (e.g., "Show products", "Filter by price").

*   **Context Window**: Retains a sliding window of the last $N$ (default 3) queries.
*   **Context Detection**: Uses a heuristic `should_use_context` method to decide if the user's current query is a follow-up. It looks for pronouns ("it", "them") or modification keywords ("filter", "sort") at the start of the sentence.
*   **Prompt Construction**: Merges previous Q&A pairs into the system prompt using `create_safe_context_prompt`, ensuring separation between user input and context to prevent injection.

### Recommendations
1.  **Semantic Context Detection**: The current heuristic (`startswith("filter")`) is brittle.
    *   *Improvement*: Implement a lightweight BERT-based classifier or a small LLM call to determine "Is this a follow-up?" with higher accuracy, handling edge cases like "Show me orders *that* are late" (which contains "that" but might be standalone).
2.  **Context Summarization**: As the conversation grows, dropping the 4th oldest message loses history.
    *   *Improvement*: Instead of a hard window, implement a "Summary Memory" where older turns are compressed into a single natural language summary (e.g., "User is analyzing sales in California") and appended to the active window.
3.  **Entity Resolution**: "Filter *them* by price" relies on the LLM to resolve "them".
    *   *Improvement*: Explicitly track active entities (e.g., "Current Table: Products") in the session state and inject this metadata into the prompt.

## 3. Semantic Caching

**File:** `src/cache/semantic_cache.py`

### Architecture
This feature reduces LLM costs and latency by serving cached results for semantically similar questions.

*   **Dual-Layer Storage**:
    *   **Exact Match**: Hash of the question string (O(1) lookup).
    *   **Semantic Match**: Vector embeddings (Cosine Similarity).
*   **Embedding Service**: Generates embeddings for queries.
*   **Thresholding**:
    *   `> 0.95`: Treated as exact match.
    *   `> 0.85`: Treated as similar; SQL is reused.
*   **Invalidation**: Support for invalidating caches by Connection ID when schema changes are detected.

### Recommendations
1.  **Hybrid Search (Keyword + Vector)**: Pure vector search sometimes misses specific entity differences (e.g., "Sales for *May*" vs "Sales for *June*" might be 0.95 similar).
    *   *Improvement*: Combine vector similarity with a keyword overlap check. If specific named entities (Dates, IDs) differ, force a cache miss or require SQL adaptation.
2.  **SQL Adaptation Layer**: Currently, it largely reuses the cached SQL.
    *   *Improvement*: If similarity is high (0.85-0.95), ask a small LLM to "Adapt this SQL [Cached SQL] for this new question [New Question]" rather than generating from scratch. This is much faster and safer.
3.  **Cache Warming**:
    *   *Improvement*: Allow administrators to define a "Golden Set" of common questions that are pre-calculated and cached on system startup.

## 4. Parallel Execution & Connection Pooling

**Files:** `src/core/multi_db_handler.py`, `src/core/connection_pool_manager.py`

### Architecture
*   **Parallel Execution**:
    *   Uses `asyncio.gather` to concurrently execute queries against multiple databases.
    *   **Throttling**: Controlled by `MAX_PARALLEL_DATABASES` semaphore to prevent resource exhaustion.
    *   **Fault Tolerance**: `return_exceptions=True` ensures that one failing database doesn't crash the entire batch.
*   **Connection Pooling**:
    *   **Singleton Manager**: `ConnectionPoolManager` ensures one pool registry per app instance.
    *   **Isolation**: Pools are keyed by `(connection_id, db_type)`.
    *   **Sync/Async Support**: Handles both `AsyncEngine` (Postgres/MySQL) and `SyncEngine` (DuckDB) transparently.
    *   **Eviction**: Background task cleans up idle pools after configurable timeout.

### Recommendations
1.  **Circuit Breaker Pattern**:
    *   *Improvement*: If a specific database connection fails $N$ times consecutively, "open" the circuit and fail fast for subsequent queries for a cooldown period. This prevents the entire multi-db query from hanging on one bad connection timeout.
2.  **Adaptive Throttling**:
    *   *Improvement*: Instead of a static `MAX_PARALLEL_DATABASES`, dynamically adjust concurrency based on system CPU/Memory usage or average query latency.
3.  **Query Cost Estimation**:
    *   *Improvement*: Before execution, run an `EXPLAIN` (where supported) to estimate query cost. Reject or deprioritize queries that are predicted to scan millions of rows without an index, protecting the connection pool from saturation.
