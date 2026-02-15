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
    "citadel": lambda r: (r.get("usage", {}).get("citadel_input_tokens"), r.get("usage", {}).get("citadel_output_tokens")),
}

def extract_tokens(self, response: dict, provider: str):
    extractor = self.token_extractors.get(provider)
    if extractor:
         return extractor(response)
    # Default/Error handling
    return None, None
```

### 2. Cross-Platform Aggregator (Senior Engineer)
**Issue**: SQLite-specific `strftime` in `LLMUsageAggregator`.
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
**Issue**: `schema_health_analyzer.py` is too large (1000+ lines).
**Suggestion**: Decouple the structural checks from the LLM logic.

- `src/lineage/analyzers/structural.py`: Moves `StructuralAnalyzer` class.
- `src/lineage/analyzers/indexing.py`: Moves `IndexAnalyzer` class.
- `src/lineage/analyzers/llm_advisor.py`: Keeps the LLM-specific logic.

### 4. Direct Connection Tracking (Data Architect)
**Issue**: Hard to query cost per database without joining through `QueryHistory`.
**Suggestion**: Add `connection_id` to `LLMUsage` model.

```python
class LLMUsage(Base):
    # ...
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True, index=True)
```

### 5. Schema Input Sanitization (Security)
**Issue**: `QueryPlanningAgent` accepts raw schema text which could be used for prompt injection.
**Suggestion**: Sanitize or strictly type-check the schema input.

```python
def validate_schema_input(schema_str: str) -> str:
    # Ensure it's valid JSON or restricted format
    try:
         json.loads(schema_str)
    except:
         # Log warning, maybe fallback or escape special characters
         pass
    return schema_str
```

---

## 🗺 Visual Flow: LLM Data Lineage

This diagram represents how a user query flows through the system, capturing telemetry at each step.

```mermaid
graph TD
    A[User Request] --> B[API: /query]
    B --> C{Cache Check}
    C -- Hit --> D[Return Cached]
    C -- Miss --> E[SQLGenerator]
    
    subgraph "Telemetry Capture (LLMUsageTracker)"
        E -- track_call --> F[Generate SQL (Ollama)]
        F -- "tokens/time" --> G[(LLMUsage Table)]
    end
    
    E --> H[Verify & Execute]
    H --> I[ResultNarrator]
    
    subgraph "Narrative Telemetry"
        I -- track_call --> J[Generate Summary (Ollama)]
        J -- "tokens/time" --> G
    end

    H --> K[(QueryHistory Table)]
    G -. fk -> K
    
    subgraph "Aggregation Worker"
        L[LLMUsageAggregator]
        G --> L
        L --> M[(LLMUsageAggregate Table)]
    end
    
    M --> N[Usage Dashboard]
```

### Data Flow Breakdown:
1.  **Request Phase**: User initiates a query via `/query`.
2.  **Execution Phase**: `SQLGenerator` calls Ollama. The `OllamaClient` wraps this in `track_call`.
3.  **Capture Phase**: `track_call` records `input_tokens`, `output_tokens`, `model`, `provider` in `LLMUsage`.
4.  **Lineage linking**: The usages are linked to `QueryHistory` via `query_history_id`.
5.  **Aggregation**: Background job aggregates `LLMUsage` into `LLMUsageAggregate` for fast dashboarding.
