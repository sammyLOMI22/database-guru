# SQL Query Quality Improvement Plan

**Status**: COMPLETE (Implemented December 26, 2025)
**Date**: December 26, 2025
**Scope**: System-wide quality slider (0-100%) + bug fixes + overall query improvement
**Verified**: All root causes confirmed via codebase exploration
**Tests**: 45 unit tests passing

---

## Design Decisions (Verified Dec 26, 2025)

### Decision 1: Quality Level Storage
**Choice**: Load from SystemSettings in endpoint, NOT per-request in QueryRequest

**Rationale**:
- Quality is a system-wide preference, not a per-query decision
- Follows existing pattern (auto_learning_enabled, confidence_threshold)
- Simpler implementation - no frontend changes to query submission

### Decision 2: Quality Profile Location
**Choice**: Create new file `src/llm/quality_profile.py`

**Rationale**:
- Cohesive, self-contained module (~100 lines)
- Follows existing pattern (confidence_scorer.py, correction_learner.py)
- Single-responsibility: profile definition + generation

### Decision 3: Profile Threading
**Choice**: Pass as constructor parameter to SelfCorrectingSQLAgent, then selectively to sub-agents

**Flow**:
```
query.py → SelfCorrectingSQLAgent.__init__(quality_profile=...)
         → Sets self.max_retries, self.enable_result_verification
         → Passes to sql_generator.generate_sql(quality_profile=...)
         → Passes to planning_agent.should_use_planning(quality_profile=...)
```

---

## Summary

Add a user-configurable quality slider (0-100%) to the Settings panel that controls the trade-off between query speed and accuracy. Additionally, fix underlying bugs that cause queries like "products shipped to New York" to fail.

### Quality Levels
- **0-30% (Fast)**: Minimal planning, basic prompts, skip verification
- **31-70% (Balanced)**: Current behavior with bug fixes enabled
- **71-100% (Thorough)**: Full planning, rich context, strict verification

---

## Root Cause Analysis

### Why "Products Shipped to New York" Fails

#### Issue 1: Dead Code - LocationMapper Never Called (CRITICAL) ✅ VERIFIED
**File**: `src/core/location_mapper.py` (lines 199-234)

```python
# This method EXISTS but is NEVER called anywhere in the codebase!
def enhance_query_with_location_hints(cls, query: str, schema: Dict) -> str:
    # Detects locations like "New York", "California"
    # Checks schema for state column formats
    # Returns enhanced query with hints
```

**Evidence**: Grep search confirmed **zero callers** - only the definition itself appears. Not imported anywhere.
**Method Details**: Lines 199-234, fully implemented with location detection logic.

**Impact**: The LLM never receives hints like "New York should use code 'NY'" so it generates `WHERE state = 'New York'` instead of `WHERE state = 'NY'`.

---

#### Issue 2: Missing Few-Shot Examples ✅ VERIFIED
**File**: `src/llm/prompts.py` (lines 206-240)

Current examples (7 total):
1. Simple recent users
2. Simple product list
3. Product revenue with JOIN (only 1 JOIN example)
4. Count active customers
5. Show all orders
6. Group orders by status
7. Group products by category

**Missing**:
- Zero location query examples (no state = 'CA', state = 'NY')
- Only 1 JOIN example (no location filtering with JOINs)
- No state code normalization patterns

**Impact**: The LLM has no patterns to learn from for location-based queries.

---

#### Issue 3: SQL Generator Has No Location Context Parameter ✅ VERIFIED
**File**: `src/llm/sql_generator.py` (lines 167-312)

```python
async def generate_sql(
    self,
    question: str,
    schema: str,
    database_type: str = "postgresql",
    allow_write: bool = False,
    use_few_shot: bool = True,
    model: Optional[str] = None,
    skip_cache: bool = False,
    # NO quality_profile parameter!
    # NO location_hints parameter!
) -> Dict[str, Any]:
```

**Callers Found**:
- `src/api/endpoints/query.py:610`
- `src/api/endpoints/multi_db_query.py:1017`
- `src/llm/tool_using_agent.py:210`

**Impact**: Even if LocationMapper hints were generated somewhere, there's no way to pass them to SQL generation.

---

#### Issue 4: Schema Samples Not Emphasized ✅ VERIFIED
**File**: `src/core/schema_inspector.py` (lines 530-537)

```python
# Current format (lines 531-535):
sample_hint = ""
if "sample_values" in col and col["sample_values"]:
    samples = col["sample_values"]
    sample_str = ", ".join(repr(s) for s in samples[:5])
    sample_hint = f"  // Examples: {sample_str}"
# Renders as: - state: VARCHAR(2)  // Examples: 'NY', 'CA', 'TX'
```

**Sampling Logic** (lines 114-148): Smart keyword matching for 'state', 'country', 'city', 'status', etc.

**Impact**: The LLM may ignore inline comments rather than treating them as critical hints.

---

#### Issue 5: Planning Agent Generates Hints But Doesn't Enforce Them ✅ VERIFIED
**File**: `src/llm/query_planning_agent.py`

**Method `_generate_location_hints()`** (lines 1074-1141):
- Detects locations in question ✅
- Checks schema for state column format ✅
- Returns formatted hints ✅
- **BUT**: Hints only used in QueryPlanningAgent's own prompts ❌
- **NOT passed to SQLGenerator** for general queries ❌

**Hardcoded Threshold** (line 350):
```python
if complexity_score >= 0.5:  # HARDCODED - should be configurable
```

---

### The Flow Breakdown

```
User: "Products shipped to New York"
    ↓
Query Planning Agent
    ├── Complexity score: 0.5 (triggers planning) ✓
    ├── Location hints: "New York → NY" ✓
    └── Creates plan ✓
    ↓
SQL Generator
    ├── Receives: question, schema (NO hints!)
    ├── Few-shot examples: (no location patterns!)
    └── Generates: WHERE state = 'New York' ✗
    ↓
Execution: 0 rows (because state column contains 'NY', not 'New York')
```

---

### Components Causing the Issue

| Component | File | Problem | Fix |
|-----------|------|---------|-----|
| LocationMapper | `src/core/location_mapper.py` | `enhance_query_with_location_hints()` is dead code | Wire it up in SQLGenerator |
| FewShotExamples | `src/llm/prompts.py` | No location/JOIN examples | Add 4 new examples |
| SQLGenerator | `src/llm/sql_generator.py` | No parameter for hints/quality | Add `quality_profile` parameter |
| SchemaInspector | `src/core/schema_inspector.py` | Samples are inline comments | Add emphasis mode |
| QueryPlanningAgent | `src/llm/query_planning_agent.py` | Hints generated but not passed forward | Pass to SQLGenerator |

---

### How the Quality Slider Fixes This

| Quality Level | LocationMapper | Enhanced Few-Shot | Sample Emphasis |
|--------------|----------------|-------------------|-----------------|
| 0-30% (Fast) | Disabled | Disabled | No |
| 31-70% (Balanced) | **Enabled** | **Enabled** | No |
| 71-100% (Thorough) | **Enabled** | **Enabled** | **Yes** |

At **Balanced (50%)** or higher, the system will:
1. Call `LocationMapper.enhance_query_with_location_hints()`
2. Include location-aware few-shot examples
3. Properly route hints to SQL generation

---

## Implementation Plan

### Phase 1: Database & API Changes

#### 1.1 Add to SystemSettings Model
**File**: `src/database/models.py` (after line 258, after `max_audit_log_days`)

```python
# Query Quality Settings (add after line 258)
query_quality_level = Column(Integer, default=50, nullable=False)  # 0-100 scale
```

**Pattern Reference**: Line 258 (`max_audit_log_days = Column(Integer, default=90, nullable=False)`)

#### 1.2 Update Pydantic Schemas
**File**: `src/models/schemas.py`

In `SystemSettingsResponse` (after line 444):
```python
query_quality_level: int
```

In `SystemSettingsUpdateRequest` (after line 461):
```python
query_quality_level: Optional[int] = Field(None, ge=0, le=100)
```

**Pattern Reference**: Lines 455 (`confidence_threshold`), 461 (`max_audit_log_days`)

#### 1.3 Update Settings Endpoint Defaults
**File**: `src/api/endpoints/settings.py`

In `get_or_create_settings()` (around line 33):
```python
query_quality_level=50,  # Balanced default
```

In `reset_settings()` (around line 133):
```python
settings.query_quality_level = 50
```

---

### Phase 2: Create Quality Profile System

#### 2.1 New File: `src/llm/quality_profile.py`

```python
from dataclasses import dataclass
from enum import Enum

class QualityLevel(Enum):
    FAST = "fast"           # 0-30%
    BALANCED = "balanced"   # 31-70%
    THOROUGH = "thorough"   # 71-100%

@dataclass
class QualityProfile:
    level: QualityLevel
    raw_value: int

    # Planning
    force_planning: bool
    complexity_threshold: float

    # LLM Generation
    temperature: float
    use_enhanced_few_shot: bool
    include_location_hints: bool
    include_join_examples: bool

    # Schema Context
    schema_sample_limit: int
    emphasize_samples: bool

    # Corrections
    use_parallel_corrections: bool
    correction_timeout: int
    enable_result_verification: bool
    max_retries: int

    # Tools
    enable_tool_exploration: bool

def get_quality_profile(quality_level: int) -> QualityProfile:
    """Generate profile from slider value (0-100)"""
    if quality_level <= 30:
        return QualityProfile(
            level=QualityLevel.FAST,
            raw_value=quality_level,
            force_planning=False,
            complexity_threshold=0.8,
            temperature=0.1,
            use_enhanced_few_shot=False,
            include_location_hints=False,
            include_join_examples=False,
            schema_sample_limit=0,
            emphasize_samples=False,
            use_parallel_corrections=True,
            correction_timeout=5,
            enable_result_verification=False,
            max_retries=1,
            enable_tool_exploration=False,
        )
    elif quality_level <= 70:
        return QualityProfile(
            level=QualityLevel.BALANCED,
            raw_value=quality_level,
            force_planning=False,
            complexity_threshold=0.5,
            temperature=0.1,
            use_enhanced_few_shot=True,
            include_location_hints=True,  # BUG FIX
            include_join_examples=True,   # BUG FIX
            schema_sample_limit=5,
            emphasize_samples=False,
            use_parallel_corrections=True,
            correction_timeout=10,
            enable_result_verification=True,
            max_retries=3,
            enable_tool_exploration=False,
        )
    else:
        return QualityProfile(
            level=QualityLevel.THOROUGH,
            raw_value=quality_level,
            force_planning=True,
            complexity_threshold=0.2,
            temperature=0.05,
            use_enhanced_few_shot=True,
            include_location_hints=True,
            include_join_examples=True,
            schema_sample_limit=10,
            emphasize_samples=True,
            use_parallel_corrections=True,
            correction_timeout=15,
            enable_result_verification=True,
            max_retries=5,
            enable_tool_exploration=True,
        )
```

---

### Phase 3: Bug Fixes

#### 3.1 Wire Up LocationMapper (CRITICAL)
**File**: `src/llm/sql_generator.py` (line ~250)

```python
async def generate_sql(self, question: str, schema: str, ..., quality_profile=None):
    # NEW: Apply location hints when enabled
    if quality_profile and quality_profile.include_location_hints:
        from src.core.location_mapper import LocationMapper
        question = LocationMapper.enhance_query_with_location_hints(question, schema_dict)
```

#### 3.2 Add Location & JOIN Few-Shot Examples
**File**: `src/llm/prompts.py` (after line 240)

```python
# Add to FEW_SHOT_EXAMPLES:

Example 8: Show me customers from California
SQL: SELECT * FROM customers WHERE state = 'CA' LIMIT 100

Example 9: Find orders shipped to New York
SQL: SELECT o.* FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE c.state = 'NY' LIMIT 100

Example 10: Show products with their categories
SQL: SELECT p.name, c.name as category_name
FROM products p
JOIN categories c ON p.category_id = c.id
LIMIT 100

Example 11: Get order totals by customer
SQL: SELECT c.name, SUM(o.total) as total_spent
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY total_spent DESC LIMIT 10
```

#### 3.3 Emphasize Schema Samples
**File**: `src/core/schema_inspector.py` (in format_schema_for_llm)

When `emphasize_samples=True` (Thorough mode), format samples as:
```
** IMPORTANT: Use these exact values: 'NY', 'CA', 'TX' **
```

---

### Phase 4: Backend Integration

#### 4.1 Update Query Endpoint
**File**: `src/api/endpoints/query.py` (line ~60)

```python
@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest, db: AsyncSession = Depends(get_db), ...):
    # Load system settings
    settings_record = await get_or_create_settings(db)

    # Generate quality profile
    from src.llm.quality_profile import get_quality_profile
    quality_profile = get_quality_profile(settings_record.query_quality_level)

    # Pass to agent
    self_correcting_agent = SelfCorrectingSQLAgent(
        sql_generator=sql_generator,
        quality_profile=quality_profile,
        ...
    )
```

#### 4.2 Update SelfCorrectingSQLAgent
**File**: `src/llm/self_correcting_agent.py`

- Accept `quality_profile` parameter in `__init__`
- Use profile settings for `max_retries`, `enable_result_verification`, etc.
- Pass profile to `sql_generator.generate_sql()`

#### 4.3 Update QueryPlanningAgent
**File**: `src/llm/query_planning_agent.py`

- Accept profile in `should_use_planning()`
- If `profile.force_planning`, always return True
- Use `profile.complexity_threshold` instead of hardcoded 0.5

---

### Phase 5: Frontend UI

#### 5.1 Update SettingsPanel
**File**: `frontend/src/components/SettingsPanel.tsx`

Add before Auto-Learning Section:

```tsx
{/* Query Quality Section */}
<div className="space-y-4">
  <h3 className="text-lg font-semibold">Query Quality</h3>

  <div className="p-4 bg-gradient-to-r from-green-50 via-blue-50 to-purple-50 rounded-lg">
    <label className="block font-semibold mb-2">
      Quality Level: {settings.query_quality_level}%
    </label>
    <p className="text-sm text-gray-600 mb-4">
      Balance between speed and query accuracy
    </p>

    <div className="flex items-center space-x-4">
      <span className="text-xs text-green-600">Fast</span>
      <input
        type="range"
        min="0"
        max="100"
        step="5"
        value={settings.query_quality_level}
        onChange={(e) => setSettings({
          ...settings,
          query_quality_level: parseInt(e.target.value)
        })}
        className="flex-1 h-2 bg-gray-200 rounded-lg cursor-pointer"
      />
      <span className="text-xs text-purple-600">Thorough</span>
    </div>

    {/* Mode Description */}
    <div className="mt-3 p-3 bg-white rounded text-sm">
      {settings.query_quality_level <= 30 && (
        <p className="text-green-700">
          <strong>Fast:</strong> Quick responses, minimal planning. Best for simple queries.
        </p>
      )}
      {settings.query_quality_level > 30 && settings.query_quality_level <= 70 && (
        <p className="text-blue-700">
          <strong>Balanced:</strong> Standard planning and verification. Recommended.
        </p>
      )}
      {settings.query_quality_level > 70 && (
        <p className="text-purple-700">
          <strong>Thorough:</strong> Full analysis, rich context. Best for complex queries.
        </p>
      )}
    </div>
  </div>
</div>
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/database/models.py` | Add `query_quality_level` column |
| `src/models/schemas.py` | Add field to request/response schemas |
| `src/api/endpoints/settings.py` | Update defaults |
| `src/llm/quality_profile.py` | **NEW FILE** - Quality profile system |
| `src/llm/prompts.py` | Add location + JOIN few-shot examples |
| `src/llm/sql_generator.py` | Accept profile, wire up LocationMapper |
| `src/llm/self_correcting_agent.py` | Accept and use quality profile |
| `src/llm/query_planning_agent.py` | Use profile for planning decisions |
| `src/core/schema_inspector.py` | Emphasize samples in Thorough mode |
| `src/api/endpoints/query.py` | Load settings, create profile |
| `frontend/src/components/SettingsPanel.tsx` | Add quality slider UI |

---

## Testing Strategy

### Unit Tests (`tests/test_quality_profile.py`)
- Profile generation at 0, 30, 50, 70, 100
- Correct level assignment (FAST/BALANCED/THOROUGH)
- Parameter values at each level

### Integration Tests (`tests/test_quality_integration.py`)
- Location query "customers from California" → uses 'CA'
- "Products shipped to New York" → correct JOIN with 'NY'
- Fast mode skips verification (check trace)
- Thorough mode uses tools (check trace)

### Frontend Tests
- Slider renders with default 50
- Mode descriptions update correctly
- Settings save includes quality_level

---

## Implementation Sequence

1. **Day 1**: Database model + API changes + migrations
2. **Day 2**: Create quality_profile.py + unit tests
3. **Day 2-3**: Bug fixes (LocationMapper, few-shot examples)
4. **Day 3-4**: Backend integration (agents, endpoints)
5. **Day 4**: Frontend slider UI
6. **Day 5**: Integration tests + documentation

---

## Success Criteria

1. "Products shipped to New York" returns correct results at quality >= 31%
2. Settings slider persists across sessions
3. Fast mode (0-30%) is measurably faster than Thorough (71-100%)
4. All existing tests continue to pass
5. New tests cover quality profile system

---

## Related Documentation

- [Advanced Visualization Phase 2 Plan](ADVANCED_VISUALIZATION_PHASE2_PLAN.md)
- [PR Review: Phase 8 & 10](PR_REVIEW_PHASE_8_10.md)
- [CLAUDE.md](../CLAUDE.md) - Architecture overview
