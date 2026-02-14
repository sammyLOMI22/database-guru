# Technical Audit Report: Phase 16 (LLM Usage Monitoring)

**Branch**: `phase-16-llm-usage-monitoring`  
**Focus**: Integration of LLM usage tracking, cost monitoring, and statistics.

---

## 🛠 Senior Engineer Review
*Audit for code quality, logic bugs, and resilience.*

### The Wins
- **Clean Context Management**: The use of `@asynccontextmanager` in `LLMUsageTracker.track_call` (src/services/llm_usage_tracker.py) ensures a consistent pattern for tracking calls without boilerplate.
- **Resilient Token Estimation**: Excellent fallback strategy from `tiktoken` to character-based estimation, ensuring the system doesn't crash if a specific library or model isn't available.
- **Instrumented Client**: The `OllamaClient` is correctly instrumented to track both `generate` and `chat` calls automatically when a database session is provided.

### Issues & Potential Bugs
- **Hardcoded Provider Logic**: `extract_tokens` in `LLMUsageTracker` uses an `if-elif` chain (Ollama, OpenAI, Anthropic, Azure). This violates the Open/Closed principle and will become hard to maintain. **Critical Refactor**.
- **Silent Save Failures**: The `save` method in `_TrackingContext` swallows exceptions (`except Exception as e: logger.error(...)`). While good for UX, it hides telemetry failures. Suggest adding a metric or a dedicated error log channel.
- **SQLite Dependency**: `LLMUsageAggregator` uses `func.strftime('%H', ...)` which is SQLite-specific. This will break if migrated to PostgreSQL (which uses `extract(hour from ...)` or `to_char`).

### Security Concerns
- **Prompt Injection (Schema)**: The `QueryPlanningAgent` (src/llm/query_planning_agent.py) accepts a raw `schema` string in step `create_query_plan`. If a user manually calls the API with a malicious schema string (e.g., in a chat context or API call), it could influence the planner's behavior.
- **Result Truncation**: `LLMUsage` truncates `response_summary` to 500 characters. While this saves space, it makes it impossible to fully audit model hallucinations or large-scale data leaks in the logs.

---

## 📊 Project Manager Review
*Evaluate 'Definition of Done' and technical debt.*

### The Wins
- **Feature Completeness**: The core requirements (usage tracking, cost estimation, aggregation) are implemented.
- **Production Readiness**: The inclusion of `LLMUsageAggregate` table shows foresight for dashboard performance, avoiding expensive raw data scans.

### Concerns
- **Technical Debt**: The `SchemaHealthAnalyzer` (`src/lineage/schema_health_analyzer.py`) is a "God Class" with over 1000 lines. It mixes structural analysis, index suggestions, and LLM logic. It should be refactored into smaller, single-purpose classes immediately.
- **Chat vs Query Confusion**: The `chat.py` endpoints primarily handle message storage, while `query.py` handles the actual LLM generation. This separation is logical for history management but potentially confusing for new developers tracing the "chat" flow.

---

## 🏗 Data Architect Review
*Review data lineage and schema optimization.*

### The Wins
- **Schema Optimization**: `LLMUsageAggregate` effectively pre-aggregates data by `date`, `hour`, `agent_type`, and `model`, which is ideal for time-series visualization.
- **Nullable Relations**: Correct use of `ondelete="SET NULL"` for foreign keys (`query_history_id`, `chat_session_id`) ensures usage data survives session deletion.

### Issues
- **Missing Connection Link**: `LLMUsage` links to `QueryHistory`, which links to `DatabaseConnection`. However, `LLMUsage` does not have a direct `connection_id`. This requires a JOIN to answer "How much did we spend on the Production DB?".
- **Metadata JSON**: Good use of `metadata_json` for extensibility, but valid JSON schemas should be enforced to prevent it becoming a data swamp (e.g., what keys are allowed in metadata?).

---

## 📈 Data Analyst Review
*Audit data utility and query-friendliness.*

### The Wins
- **Query-Friendly Telemetry**: The `token_estimation_method` field is crucial for distinguishing between "exact" (API returned) and "estimated" (character count) costs.
- **Cost Analysis**: breakdown by `agent_type` allows us to see if the "Planner" or the "Narrator" is driving costs.

### Issues
- **Truncated Summaries**: As noted by Engineering, the 500-char limit on prompts/responses restricts deep quality analysis.
    - *Recommendation*: Implement a "Sampling Strategy" where 1% of calls (or flagged calls) store the FULL response in a separate `LLMUsageDetails` table or blob storage.

---

## 🏁 Final Verdict
**Status**: 🟢 **Production-Ready with caveats.** (Proceed after addressing Security & SQLite dependency).

### Action Items
1.  **Refactor Provider Logic**: Implement Registry pattern.
2.  **Fix SQL Portability**: Use SQLAlchemy generic functions for date extraction.
3.  **Sanitize Schema Input**: Ensure `schema` string in planning agent is treated as data, not instruction.
4.  **Split Health Analyzer**: Break down the 1k line file.

---

## 🚀 Future Direction
1.  **Smart Routing**: Use `avg_response_time_ms` from `LLMUsageAggregate` to dynamically timeout or switch models.
2.  **Anomaly Detection**: Alert when `input_tokens` for a specific query pattern exceeds 2 std deviations.
