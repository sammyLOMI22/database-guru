# Phase 16: Action Plan & Visual Flow

## ⚡️ Action Plan (Critical Fixes & Suggestions)

### 1. Multi-Provider Registry (Senior Engineer)
**Issue**: Hardcoded provider logic in `LLMUsageTracker`.
**Suggestion**: Use a registry pattern for token extraction.

```python
# Create a mapping/registry for provider-specific extraction
token_extractors = {
    "ollama": lambda r: (r.get("prompt_eval_count"), r.get("eval_count")),
    "openai": lambda r: (r.get("usage", {}).get("prompt_tokens"), r.get("usage", {}).get("completion_tokens")),
}

def extract_tokens(self, response: dict, provider: str):
    extractor = self.token_extractors.get(provider)
    return extractor(response) if extractor else (None, None)
```

### 2. Cross-Platform Aggregator (Senior Engineer)
**Issue**: SQLite-specific `strftime`.
**Suggestion**: Use SQLAlchemy's `extract` or a more generic helper.

```python
from sqlalchemy import extract
# Instead of strftime:
stmt = select(
    extract('hour', LLMUsage.created_at).label('hour'),
    # ...
)
```

### 3. Split Schema Health Analyzer (Project Manager)
**Issue**: `schema_health_analyzer.py` is too large.
**Suggestion**: Decouple the structural checks from the LLM logic.

- `src/lineage/analyzers/structural.py`
- `src/lineage/analyzers/indexing.py`
- `src/lineage/analyzers/llm_advisor.py`

### 4. Direct Connection Tracking (Data Architect)
**Issue**: Hard to query cost per database.
**Suggestion**: Add `connection_id` to `LLMUsage` model.

```python
class LLMUsage(Base):
    # ...
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True, index=True)
```

---

## 🗺 Visual Flow: LLM Data Lineage

This diagram represents how a user query flows through the system, capturing telemetry at each step.

```mermaid
graph TD
    A[User Request] --> B[ChatSession / API]
    B --> C{Query Planner Agent}
    
    subgraph "Telemetry Capture (LLMUsageTracker)"
        C -- track_call --> D[SQL Generator Agent]
        D -- track_call --> E[Self-Correcting Agent]
        E -- track_call --> F[Result Narrator]
    end
    
    D --> G[(Database)]
    G --> F
    
    subgraph "Data Lineage Storage"
        D1[(LLMUsage Table)]
        D2[(QueryHistory Table)]
        D3[(LLMUsageAggregate)]
    end
    
    D -. captures ID .-> D1
    E -. captures ID .-> D1
    F -. captures ID .-> D1
    
    D1 -- fk points to -- D2
    D2 -- fk points to -- B
    
    D1 -- background worker -- D3
    D3 -- powers -- H[Usage Dashboard]
```

### Data Flow Breakdown:
1. **Request Phase**: User initiates a query. A `ChatSession` is active.
2. **Execution Phase**: Each LLM interaction (Planner -> Generator -> Fixer -> Narrator) is wrapped in an `async with track_call(...)`.
3. **Capture Phase**: `track_call` records timing, tokens, cost, and links the entry to `query_history_id` and `chat_session_id`.
4. **Lineage linking**: If a generated SQL fails and is corrected, the `LLMUsage` table records both calls under the same `query_history_id`, enabling ROI/Quality analysis.
5. **Aggregation**: `LLMUsageAggregator` scans `LLMUsage` and updates `LLMUsageAggregate` for high-performance frontend charts.
