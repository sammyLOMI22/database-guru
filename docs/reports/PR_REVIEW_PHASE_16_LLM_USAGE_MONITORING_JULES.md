# Multi-Dimensional Technical Audit: Phase 16 - LLM Usage Monitoring

**Audit Status**: Production-Ready with Minor Critical Fixes
**Branch**: `phase-16-llm-usage-monitoring`
**Base Branch**: `origin/main`

---

## 1. Senior Software Engineer Perspective

### Code Quality & Logic
- **Win**: The use of an asynchronous context manager (`track_call`) in `LLMUsageTracker` is an excellent pattern. It ensures that tracking starts before the call and saves afterward, even if the call fails, while remaining non-intrusive to the core logic.
- **Win**: Native token extraction for multiple providers (Ollama, OpenAI, Anthropic, Azure) is well-implemented with a sensible fallback chain.
- **Issue (Logic)**: In `LLMCostService.get_model_config`, the fuzzy matching logic uses `scalar_one_or_none()`. This will raise a `MultipleResultsFound` exception if, for example, both `llama3` and `llama3.1` exist in the `llm_model_config` table and the requested model is `llama3:latest`.
- **Issue (DRY)**: The frontend components (`LLMUsageDashboard`, `SessionUsageBadge`, `UsageSummary`) define their own formatting helpers (e.g., `formatCurrency`, `formatNumber`). These should be centralized in a shared utility file.
- **Issue (Error Handling)**: `LLMUsageTracker.save()` uses `begin_nested()` to create a savepoint. While this protects the parent transaction, if the session is in a failed state (which can happen after an LLM timeout/exception depending on the driver), `begin_nested()` might still fail.

### Best Practices
- **Issue (Deprecation)**: Multiple files still use `datetime.utcnow()`, which is deprecated in Python 3.12. Use `datetime.now(timezone.utc)` instead.
- **Issue (Consistency)**: Mixing naïve (`datetime.utcnow`) and aware (`datetime.now(timezone.utc)`) datetimes can lead to subtle comparison bugs in SQLite and hard failures in more strict databases like PostgreSQL.

---

## 2. Project Manager Perspective

### Definition of Done Evaluation
- **Cohesion**: The feature is highly cohesive. Tracking is threaded through almost all agents (SQL Generator, Narrators, Lineage Agents).
- **Technical Debt**:
    - **Pagination**: The `/recent` endpoint lacks pagination (limit only), which will become a problem as usage history grows.
    - **Background Polling**: `SessionUsageBadge` polls every 30 seconds even if the tab is in the background.
    - **Dead Code**: `UsageSummary.tsx` appears to be unused in the main UI flow.

### Future Innovation & Next Steps
- **Data Retention**: Implement a cleanup job to prune raw `llm_usage` records after N days, relying on `llm_usage_aggregate` for historical trends.
- **Streaming Support**: Enhance the tracker to handle streaming responses accurately (Ollama provides final stats at the end of the stream).
- **Budget Alerts**: Add threshold-based notifications when cost or token usage exceeds a daily/monthly limit.

---

## 3. Data Architect Perspective

### Data Lineage & Schema
- **Optimized Schema**: The `llm_usage` table has appropriate indexes on high-cardinality columns (`agent_type`, `model_name`, `provider`, `chat_session_id`).
- **Traceability**: Excellent linkage between LLM calls and `QueryHistory` / `ChatSession`. This allows for a "reasoning-to-cost" audit trail.
- **Aggregation Strategy**: The hourly/daily aggregation in `LLMUsageAggregate` is well-designed for dashboard performance.
- **Issue (Portability)**: The `LLMUsageAggregator` uses SQLite-specific `strftime`. If the metadata database is migrated to PostgreSQL, these queries will break.

---

## 4. Data Analyst Perspective

### Data Utility & Telemetry
- **Provenance**: The `token_estimation_method` column is crucial for analysts to understand the accuracy of cost reports.
- **Metadata**: The `metadata_json` column allows for capturing agent-specific context (like winning strategy in parallel correction) without schema changes.
- **Issue (Serialization)**: The `LLMUsageResponse` schema defines `total_tokens` as a field, but in the model, it is a `@property`. This can lead to serialization issues where the field returns a default value (0) instead of the computed sum unless using Pydantic's `from_attributes` correctly with a computed field.

### Bias & Integrity
- **Auditing**: Storing `prompt_summary` and `response_summary` (500 chars) provides a good balance between auditability and storage efficiency.
- **Note**: Ensure that the `prompt_summary` is sanitized when displayed in the frontend to prevent accidental rendering of malicious inputs (though React's default escaping covers this).

---

## The Review Matrix

| Feature | Feedback |
| :--- | :--- |
| **The Wins** | Context-manager based tracking, native token extraction, comprehensive dashboard, non-intrusive integration. |
| **Issues & Bugs** | `MultipleResultsFound` in fuzzy cost lookup, `datetime.utcnow` deprecations, `strftime` portability, background polling. |
| **Security** | Minimal concern. Usage endpoints are open but don't expose sensitive data beyond query summaries. |
| **Cohesion** | Very high. Feels like a native part of the agent ecosystem. |
| **Future Direction** | Retention policies, streaming support, budget alerts, and smart usage insights (e.g., "This agent is 3x more expensive but only 5% more accurate"). |

---

## Visual Flow (Data & Meta-Lineage)

This diagram shows how LLM usage data flows through the system and connects to the existing data lineage/history.

```text
      [ USER INTERFACE ]
              │
      (1) Natural Language Query
              │
              ▼
      [ QUERY ENDPOINT ] ───▶ (2) Create QueryHistory (status="processing")
              │
              ├───────────────────────────────────┐
              ▼                                   ▼
      [ AGENT PIPELINE ]                  [ USAGE TRACKING ]
      (SQL Gen, Planning, etc.)           (Async Context Manager)
              │                                   │
              ├───────────┐                       │
              │           ▼                       │
              │   [ OLLAMA CLIENT ]               │
              │           │                       │
              │           ▼                       │
              │   (3) Physical LLM Call ◄─────────┤
              │           │                       │
              │           ▼                       │
              │   (4) Return Response ──────────▶ │
              │                                   │
              │                                   ▼
              │                       [ LLM USAGE TRACKER ]
              │                       │ - Extract Tokens  │
              │                       │ - Calculate Cost  │
              │                       ▼                   │
              │               (5) Save LLMUsage Record    │
              │                   (Linked to QueryHistory)│
              ▼                                           │
      [ RESULTS & LINEAGE ]                               │
      │ - Parse SQL Lineage                               │
      │ - Generate Narrative (Triggers another LLM Call) ─┘
      │ - Update QueryHistory (status="completed")
      ▼
[ ANALYTICS DASHBOARD ] ◄── [ AGGREGATOR ] ◄── [ LLM_USAGE TABLE ]
```

---

## Critical Fixes Action Plan (Immediate)

### 1. Fix Cost Service Fuzzy Match
Replace `scalar_one_or_none()` with `.first()` and order by length to prefer exact-ish matches.
```python
# src/services/llm_cost_service.py
stmt = select(LLMModelConfig).where(LLMModelConfig.model_name.like(f"{base_name}%")).order_by(func.length(LLMModelConfig.model_name))
result = await db.execute(stmt)
config = result.scalars().first()
```

### 2. Standardize Datetimes
Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` in all models and services.

### 3. Fix Dashbord Max Range
The API `/timeseries` endpoint limits `days` to 30, but the frontend allows selecting 90. Update the FastAPI `Query` param to allow 90.
```python
# src/api/endpoints/llm_usage.py
async def get_usage_timeseries(days: int = Query(default=7, ge=1, le=90), ...)
```

### 4. Optimize Frontend Polling
In `SessionUsageBadge.tsx`, use `document.visibilityState` to pause polling when the tab is inactive.