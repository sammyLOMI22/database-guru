# SQL Generation Pipeline: Semantic Understanding Improvements

## Overview

This document outlines the implementation plan for improving SQL generation quality through semantic understanding. The improvements target pre-generation validation to reduce CANNOT_ANSWER failures and improve first-attempt SQL accuracy.

**Priority**: High
**Scope**: Universal (PostgreSQL, MySQL, SQLite, DuckDB)
**Approach**: New components with integration into existing flow

---

## Phase 1: Query Intent Classification & Required Data Detection

### Goal
Understand what the user is asking BEFORE generating SQL to:
1. Detect impossible queries early (no wasted LLM calls)
2. Extract entities for better SQL generation context
3. Provide helpful suggestions when queries cannot be answered

### New Components

#### 1.1 QueryIntentClassifier (`src/llm/query_intent_classifier.py`)

Classifies query intent using fast regex patterns (no LLM):

**Query Intents**:
| Intent | Example | SQL Pattern |
|--------|---------|-------------|
| `LOOKUP` | "Show all products" | Simple SELECT |
| `AGGREGATION` | "How many orders?" | COUNT/SUM/AVG |
| `COMPARISON` | "Products under $50" | WHERE with operators |
| `RELATIONSHIP` | "Orders with products" | JOIN required |
| `TEMPORAL` | "Orders from last week" | Date filtering |
| `RANKING` | "Top 10 customers" | ORDER BY + LIMIT |
| `IMPOSSIBLE` | "Customer locations" (no table) | CANNOT_ANSWER |

**Key Dataclasses**:
```python
@dataclass
class ExtractedEntity:
    original_text: str        # "California"
    entity_type: str          # "location", "table", "column"
    normalized_value: str     # "CA"
    mapped_to_schema: bool    # True if matches schema
    schema_match: str         # Actual table/column name

@dataclass
class QueryIntentResult:
    intent: QueryIntent
    confidence: float
    extracted_entities: List[ExtractedEntity]
    required_tables: Set[str]
    required_columns: Dict[str, Set[str]]
    aggregations: List[str]
    filters: List[Dict]
    impossible_reason: Optional[str]
    suggestions: List[str]
```

**Pattern Examples**:
```python
LOOKUP_PATTERNS = [
    r'^show\s+(me\s+)?(all\s+)?',
    r'^list\s+(all\s+)?',
    r'^get\s+(all\s+)?',
]

AGGREGATION_PATTERNS = [
    r'\b(count|total|sum|average|avg)\b',
    r'\bhow\s+many\b',
    r'\bnumber\s+of\b',
]

RELATIONSHIP_PATTERNS = [
    r'\bwith\s+(their|its|the)\b',
    r'\balongside\b',
    r'\brelated\s+to\b',
]
```

#### 1.2 RequiredDataDetector (`src/llm/required_data_detector.py`)

Validates extracted entities against schema:

```python
class RequiredDataDetector:
    def detect_required_data(self, question: str) -> RequiredDataResult:
        # 1. Extract table references using regex
        tables = self._extract_table_references(question)

        # 2. Extract column references
        columns = self._extract_column_references(question)

        # 3. Detect locations (reuse LocationMapper)
        locations = LocationMapper.detect_location_in_query(question)

        # 4. Validate against schema with fuzzy matching
        return self._validate_against_schema(tables, columns, locations)
```

**Key Features**:
- Fuzzy matching using `SequenceMatcher` (threshold: 0.7)
- Singular/plural handling ("customer" matches "customers")
- Location integration via existing `LocationMapper`
- Helpful suggestions for missing entities

### Integration Points

#### Primary: `src/llm/self_correcting_agent.py` (line ~846)

```python
# BEFORE tool exploration and first generation attempt
if schema_dict and self.quality_profile.enable_intent_classification:
    classifier = QueryIntentClassifier(schema_dict)
    intent_result = classifier.classify(question)

    trace.add_step("analysis",
        f"Query intent: {intent_result.intent.value}",
        metadata=intent_result.to_dict()
    )

    # Early exit for IMPOSSIBLE queries
    if not intent_result.can_answer():
        return {
            "success": False,
            "cannot_answer": True,
            "cannot_answer_reason": intent_result.impossible_reason,
            "suggestions": intent_result.suggestions,
            "intent_classification": intent_result.to_dict()
        }

    # Enhance question with entity hints
    if intent_result.extracted_entities:
        entity_hints = self._format_entity_hints(intent_result)
        enhanced_question = f"{question}\n\n{entity_hints}"
```

#### Quality Profile: `src/llm/quality_profile.py`

Add new fields to `QualityProfile`:
```python
@dataclass
class QualityProfile:
    # ... existing fields ...

    # NEW: Pre-generation validation
    enable_intent_classification: bool
    enable_pre_validation: bool
```

Update factory settings:
| Tier | Classification | Validation |
|------|---------------|------------|
| FAST (0-30%) | Disabled | Disabled |
| BALANCED (31-70%) | Enabled | Enabled |
| THOROUGH (71-100%) | Enabled | Enabled |

### Performance Requirements

- Intent classification: <50ms (regex only, no LLM)
- Schema validation: <20ms (pre-built indices)
- Total overhead: <100ms before first SQL generation

---

## Phase 2: Dynamic Few-Shot Examples

### Goal
Generate schema-specific examples instead of hardcoded examples that may confuse the LLM into using non-existent tables.

### Problem Statement

Current few-shot examples in `src/llm/prompts.py` (lines 218-279) use hardcoded table names:
```python
# Current problematic examples:
"Question: Show me users registered in the last month"
"SQL: SELECT * FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"

# LLM may copy "users" even if schema has "customers" instead
```

### New Component

#### 2.1 DynamicExampleGenerator (`src/llm/dynamic_example_generator.py`)

Generates examples from the ACTUAL schema:

```python
class DynamicExampleGenerator:
    """Generates schema-specific SQL examples for few-shot learning"""

    def __init__(self, schema_dict: Dict[str, Any]):
        self.schema = schema_dict
        self.tables = list(schema_dict.get('tables', {}).keys())

    def generate_examples(self, intent: QueryIntent = None) -> str:
        """Generate examples tailored to actual schema and query intent"""
        examples = []

        # Generate per-table examples
        for table in self.tables[:3]:  # Limit to 3 tables
            examples.append(self._generate_table_example(table))

        # Generate relationship examples if FKs exist
        if self._has_relationships():
            examples.append(self._generate_join_example())

        # Generate aggregation examples
        examples.append(self._generate_aggregation_example())

        return self._format_examples(examples)

    def _generate_table_example(self, table_name: str) -> Dict:
        """Generate a simple lookup example for a table"""
        columns = self._get_table_columns(table_name)
        return {
            "question": f"Show all {table_name}",
            "sql": f"SELECT * FROM {table_name} LIMIT 10"
        }

    def _generate_join_example(self) -> Dict:
        """Generate a JOIN example using actual FK relationships"""
        relationships = self.schema.get('relationships', [])
        if not relationships:
            return None

        rel = relationships[0]
        from_table = rel.get('from_table')
        to_table = rel.get('to_table')
        from_col = rel.get('from_column')
        to_col = rel.get('to_column')

        return {
            "question": f"Show {from_table} with their {to_table}",
            "sql": f"SELECT * FROM {from_table} JOIN {to_table} ON {from_table}.{from_col} = {to_table}.{to_col} LIMIT 10"
        }

    def _generate_aggregation_example(self) -> Dict:
        """Generate a COUNT example using first table"""
        table = self.tables[0] if self.tables else "items"
        return {
            "question": f"How many {table} are there?",
            "sql": f"SELECT COUNT(*) FROM {table}"
        }
```

#### 2.2 Example Templates by Intent

Different intents get relevant examples:

```python
INTENT_EXAMPLE_TEMPLATES = {
    QueryIntent.LOOKUP: [
        ("Show all {table}", "SELECT * FROM {table} LIMIT {limit}"),
        ("List {table} names", "SELECT name FROM {table} LIMIT {limit}"),
    ],
    QueryIntent.AGGREGATION: [
        ("Count {table}", "SELECT COUNT(*) FROM {table}"),
        ("Total {numeric_col} by {group_col}",
         "SELECT {group_col}, SUM({numeric_col}) FROM {table} GROUP BY {group_col}"),
    ],
    QueryIntent.COMPARISON: [
        ("{table} with {col} over {value}",
         "SELECT * FROM {table} WHERE {col} > {value}"),
    ],
    QueryIntent.RELATIONSHIP: [
        ("{table1} with their {table2}",
         "SELECT * FROM {table1} JOIN {table2} ON {join_condition}"),
    ],
}
```

### Integration

#### Modify: `src/llm/prompts.py`

```python
def build_few_shot_examples(
    schema_dict: Dict[str, Any] = None,
    intent: QueryIntent = None
) -> str:
    """Build few-shot examples - dynamic if schema provided, else static"""

    if schema_dict:
        # NEW: Generate schema-specific examples
        generator = DynamicExampleGenerator(schema_dict)
        return generator.generate_examples(intent)
    else:
        # FALLBACK: Use existing static examples with disclaimer
        return FEW_SHOT_EXAMPLES
```

#### Modify: `src/llm/sql_generator.py`

```python
def generate_sql(self, question, schema, ..., schema_dict=None, intent_result=None):
    # ...

    # Generate dynamic examples if schema available
    if schema_dict and self.quality_profile.use_dynamic_examples:
        few_shot = build_few_shot_examples(
            schema_dict=schema_dict,
            intent=intent_result.intent if intent_result else None
        )
    else:
        few_shot = FEW_SHOT_EXAMPLES

    # Build prompt with dynamic examples
    prompt = build_sql_prompt(schema, question, few_shot=few_shot)
```

### Column Value Awareness

#### 2.3 Enhance Examples with Sample Values

When schema includes sample values, use them in examples:

```python
def _generate_filter_example(self, table: str, column: str) -> Dict:
    """Generate filter example using actual column values"""
    col_info = self._get_column_info(table, column)
    samples = col_info.get('sample_values', [])

    if samples and column.lower() in ['state', 'status', 'type', 'category']:
        # Use actual value from schema
        value = samples[0]
        return {
            "question": f"{table} where {column} is '{value}'",
            "sql": f"SELECT * FROM {table} WHERE {column} = '{value}' LIMIT 10",
            "note": f"Note: {column} values include: {', '.join(samples[:5])}"
        }
```

Example output:
```
Question: products where state is 'CA'
SQL: SELECT * FROM products WHERE state = 'CA' LIMIT 10
Note: state values include: 'CA', 'NY', 'TX', 'FL', 'WA'
```

### Quality Profile Integration

Add to `QualityProfile`:
```python
@dataclass
class QualityProfile:
    # ... existing fields ...

    # NEW: Dynamic examples
    use_dynamic_examples: bool  # Generate schema-specific examples
```

Settings:
| Tier | Dynamic Examples |
|------|-----------------|
| FAST | Disabled (use static for speed) |
| BALANCED | Enabled |
| THOROUGH | Enabled |

---

## Files Summary

### Phase 1: To Create
| File | Purpose | Lines (est) |
|------|---------|-------------|
| `src/llm/query_intent_classifier.py` | Intent classification + entity extraction | ~350 |
| `src/llm/required_data_detector.py` | Schema validation + fuzzy matching | ~280 |
| `tests/test_query_intent_classifier.py` | Unit tests | ~200 |
| `tests/test_required_data_detector.py` | Unit tests | ~150 |

### Phase 2: To Create
| File | Purpose | Lines (est) |
|------|---------|-------------|
| `src/llm/dynamic_example_generator.py` | Schema-specific example generation | ~250 |
| `tests/test_dynamic_example_generator.py` | Unit tests | ~150 |

### Files to Modify
| File | Changes |
|------|---------|
| `src/llm/self_correcting_agent.py` | Add classification before generation (lines 845-880) |
| `src/llm/quality_profile.py` | Add 3 new fields to QualityProfile |
| `src/llm/prompts.py` | Add `build_few_shot_examples()` function |
| `src/llm/sql_generator.py` | Use dynamic examples when available |

---

## Implementation Order

### Week 1: Phase 1 Core
1. Create `query_intent_classifier.py` with patterns
2. Create `required_data_detector.py` with schema validation
3. Add unit tests for both
4. Update `quality_profile.py` with new flags

### Week 2: Phase 1 Integration
1. Integrate into `self_correcting_agent.py`
2. Add trace steps for observability
3. Test with real queries
4. Performance validation (<100ms)

### Week 3: Phase 2 Implementation
1. Create `dynamic_example_generator.py`
2. Add intent-based example templates
3. Integrate column value awareness
4. Update prompts.py and sql_generator.py

### Week 4: Testing & Polish
1. End-to-end testing with both phases
2. Performance optimization
3. Documentation updates

---

## Expected Outcomes

| Metric | Current | After Phase 1 | After Phase 2 |
|--------|---------|---------------|---------------|
| CANNOT_ANSWER accuracy | ~60% | 95% | 95% |
| First-attempt success | ~60% | 75% | 85% |
| LLM uses wrong tables | ~20% | ~10% | ~2% |
| Pre-validation catch rate | 0% | 90% | 90% |

---

## Design Patterns to Follow

1. **Dataclasses** - Match `QueryPlan`, `ConfidenceScore` patterns
2. **Fuzzy matching** - Reuse `SequenceMatcher` from `SchemaValidator`
3. **Location integration** - Reuse `LocationMapper.detect_location_in_query()`
4. **Trace integration** - Add steps to `AgentTrace` for UI visibility
5. **Quality profile control** - Features gated by quality settings
6. **Graceful fallback** - If new features fail, continue with existing behavior

---

## Phase 3: SQL Semantic Validation + Improvements

### Overview

Phase 3 implementation covers:
1. **SQL Semantic Validation** - Post-generation intent matching
2. **User Settings** - Make Phase 1/2/3 components toggleable
3. **Bug Fix** - "New York" classified as category instead of location
4. **Column Semantics** - Distinguish categorical vs location columns

---

### 3.1 SQL Semantic Validator

Validates generated SQL matches detected intent BEFORE execution.

**New File**: `src/llm/sql_semantic_validator.py` (~350 lines)

```python
class SemanticMismatchType(Enum):
    NO_MISMATCH = "no_mismatch"
    MISSING_AGGREGATION = "missing_aggregation"
    MISSING_JOIN = "missing_join"
    MISSING_WHERE = "missing_where"
    MISSING_ORDER_BY = "missing_order_by"
    MISSING_DATE_FILTER = "missing_date_filter"
    TABLE_NOT_COVERED = "table_not_covered"
    LOCATION_NOT_MAPPED = "location_not_mapped"

@dataclass
class SemanticValidationResult:
    is_valid: bool
    confidence: float  # 0.0-1.0
    mismatch_type: SemanticMismatchType
    mismatch_details: List[str]
    suggestions: List[str]

    def get_regeneration_hints(self) -> str: ...

class SQLSemanticValidator:
    def validate(self, sql: str, intent_result: QueryIntentResult) -> SemanticValidationResult
    def _validate_aggregation_intent(self, sql, intent) -> Tuple[bool, List[str], float]
    def _validate_comparison_intent(self, sql, intent) -> Tuple[bool, List[str], float]
    def _validate_relationship_intent(self, sql, intent) -> Tuple[bool, List[str], float]
    def _validate_ranking_intent(self, sql, intent) -> Tuple[bool, List[str], float]
    def _validate_temporal_intent(self, sql, intent) -> Tuple[bool, List[str], float]
```

**Validation Rules by Intent**:
| Intent | Required SQL Elements | Mismatch Confidence |
|--------|----------------------|---------------------|
| AGGREGATION | COUNT/SUM/AVG/MIN/MAX | 0.85 |
| COMPARISON | WHERE with operators | 0.75 |
| RELATIONSHIP | JOIN keyword | 0.80 |
| TEMPORAL | Date column in WHERE | 0.70 |
| RANKING | ORDER BY + LIMIT | 0.75 |

**Integration**: `self_correcting_agent.py` after SQL generation, before execution.

---

### 3.2 User Settings for Semantic Understanding

**Goal**: Let users toggle Phase 1/2/3 independently in settings UI.

**Database Model** (`src/database/models.py`):
```python
# Add to SystemSettings:
enable_intent_classification: bool = True    # Phase 1
enable_dynamic_examples: bool = True         # Phase 2
enable_semantic_validation: bool = True      # Phase 3
```

**Frontend** (`frontend/src/components/SettingsPanel.tsx`):
```tsx
{/* SQL Generation Intelligence Section */}
<Toggle label="Intent Classification" description="Detect impossible queries" />
<Toggle label="Dynamic Examples" description="Schema-specific few-shot examples" />
<Toggle label="Semantic Validation" description="Validate SQL matches question" />
```

---

### 3.3 Bug Fix: "New York" as Category

**Root Cause**: `STOP_WORDS` in `query_intent_classifier.py:259` includes "new" and "york", filtering them before location detection.

**Fix** (`src/llm/query_intent_classifier.py`):

1. Remove location words from STOP_WORDS
2. Extract locations FIRST in `_extract_entities()`
3. Exclude detected location words from table matching

```python
def _extract_entities(self, question: str) -> List[ExtractedEntity]:
    entities = []

    # Step 1: Extract locations FIRST
    location_entities = self._extract_locations(question)
    entities.extend(location_entities)

    # Build set of words that are part of locations
    location_words = set()
    for loc in location_entities:
        location_words.update(loc.original_text.lower().split())

    # Step 2: Extract tables, excluding location words
    entities.extend(self._extract_table_entities(question, exclude_words=location_words))
    # ...
```

Same fix needed in `src/llm/required_data_detector.py`.

---

### 3.4 Column Semantic Metadata

**Goal**: Distinguish categorical columns (status, type) from location columns (state, city).

**New File**: `src/core/column_semantics.py` (~200 lines)

```python
class ColumnSemanticType(Enum):
    CATEGORICAL = "categorical"   # status, type, category
    LOCATION = "location"         # state, city, country
    TEMPORAL = "temporal"         # date, timestamp
    NUMERIC = "numeric"           # price, count
    IDENTIFIER = "identifier"     # id, code
    TEXT = "text"                 # name, description

@dataclass
class ColumnSemantics:
    semantic_type: ColumnSemanticType
    location_subtype: Optional[str] = None  # "us_state", "city", "country"
    value_format: Optional[str] = None      # "code" (CA), "full_name" (California)
    cardinality: Optional[int] = None
    confidence: float = 0.0

class ColumnSemanticsDetector:
    def detect(self, column_name: str, sql_type: str,
               sample_values: List[Any] = None) -> ColumnSemantics:
        # 1. Check name patterns (state, status, created_at)
        # 2. Check value patterns (2-letter codes, dates)
        # 3. Check against known location codes
        # 4. Return semantic type with confidence
```

**Integration**:
- `schema_inspector.py`: Add semantic detection to column introspection
- `dynamic_example_generator.py`: Use semantics for better examples
- `prompts.py`: Enhance prompts with semantic hints

---

### 3.5 Files Summary

**New Files (4)**:
| File | Lines | Purpose |
|------|-------|---------|
| `src/llm/sql_semantic_validator.py` | ~350 | Phase 3 validation |
| `src/core/column_semantics.py` | ~200 | Column type detection |
| `tests/test_sql_semantic_validator.py` | ~250 | Validator tests |
| `tests/test_column_semantics.py` | ~150 | Semantics tests |

**Modified Files (9)**:
| File | Changes |
|------|---------|
| `src/database/models.py` | Add 3 settings fields |
| `src/models/schemas.py` | Add Pydantic schemas |
| `src/llm/quality_profile.py` | Merge user settings |
| `src/llm/query_intent_classifier.py` | Fix STOP_WORDS bug |
| `src/llm/required_data_detector.py` | Fix STOP_WORDS bug |
| `src/llm/self_correcting_agent.py` | Integrate Phase 3 |
| `src/core/schema_inspector.py` | Add semantic detection |
| `src/llm/dynamic_example_generator.py` | Use semantic types |
| `frontend/src/components/SettingsPanel.tsx` | Add toggles |

---

### 3.6 Expected Outcomes

| Metric | Before | After |
|--------|--------|-------|
| "New York" classified correctly | No | Yes |
| Location vs category accuracy | ~60% | ~95% |
| First-attempt SQL success | ~60% | ~80% |
| User control over features | None | Full |

---

## Future Phases (Out of Scope)

- **Phase 4**: Query Pattern Learning per database
- **Phase 5**: User Feedback Integration with inline corrections
