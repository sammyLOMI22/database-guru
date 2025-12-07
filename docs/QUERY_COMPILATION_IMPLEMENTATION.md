# Query Compilation Implementation Plan

**Status**: Phase 4.2 - P0 Priority (In Progress)
**Timeline**: 3-4 days (4 working days)
**Last Updated**: December 7, 2025

## Executive Summary

Implement a three-layered query compilation system to achieve **50-70% speedup** for repeated query patterns through:

1. **SQL Normalization & Parameterization** - Extract literals to parameters for cache reuse
2. **EXPLAIN Plan Caching** - Cache database execution plans with schema fingerprinting
3. **Prepared Statement Management** - Reuse database-native prepared statements

**Design Philosophy**: **Accuracy over speed** - Conservative caching with strict invalidation on schema changes.

### Strategic Context

**Position in Roadmap**: Phase 4.2 (P0 - Next Immediate)

**Immediate Follow-On Features**:
- **Phase 4.3**: Visualizations & Export (4-5 days)
- **Phase 4.4**: Data Narratives (2-3 days)
- **Phase 5.1**: Business Glossary (1 week)

**Why Compilation First?**:
- ✅ **Foundation for all future features** - Faster queries = better UX everywhere
- ✅ **Performance baseline** - Visualizations and narratives benefit from faster data retrieval
- ✅ **Enables metadata extraction** - EXPLAIN plans provide hints for chart type selection
- ✅ **Backend optimization** - Complete before shifting to frontend UX features

## Architecture Overview

### Layered Services Design

```
┌─────────────────────────────────────────────────────────────┐
│               Query Compilation System                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: SQL Normalizer                                    │
│  - Parse SQL AST (sqlparse library)                         │
│  - Extract literals → parameters (:p1, :p2, ...)            │
│  - Generate normalized template + hash                      │
│  - Extract metadata (tables, query type, aggregations)      │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: EXPLAIN Plan Cache                                │
│  - Check Redis for cached plan                              │
│  - Validate schema fingerprint                              │
│  - Fetch EXPLAIN on cache miss                              │
│  - Store with query-type-based TTL                          │
│  - Table-based invalidation index                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Prepared Statement Manager                        │
│  - Lazy preparation (only after 2+ executions)              │
│  - LRU eviction (max 100 statements per pool)               │
│  - Per-connection isolation                                 │
│  - Background cleanup task (30-minute TTL)                  │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Timeline

| Day | Focus | Hours | Status |
|-----|-------|-------|--------|
| **Day 1** | SQL Normalization | 8h | 🟡 In Progress |
| **Day 2** | EXPLAIN Plan Caching | 8h | ⏳ Pending |
| **Day 3** | Prepared Statements | 8h | ⏳ Pending |
| **Day 4 AM** | Database & API | 4h | ⏳ Pending |
| **Day 4 PM** | Frontend & Validation | 3h | ⏳ Pending |
| **Day 4 Final** | Documentation & Deploy | 1h | ⏳ Pending |

**Total**: 32 hours = 4 working days

## Phase 1: SQL Normalization (Day 1)

**File**: `src/core/sql_normalizer.py` (~400 lines)

### Key Design
- Uses `sqlparse` library (already in codebase)
- Named parameters: `WHERE id = 123` → `WHERE id = :p1`
- Preserves structural literals: `LIMIT 10` stays unchanged
- Tracks parameter types for cache stability
- Extracts metadata: tables, query type, aggregations

### Dataclasses
```python
@dataclass
class NormalizedQuery:
    template: str
    parameters: Dict[str, Any]
    parameter_types: Dict[str, str]
    normalization_hash: str
    original_sql: str
    metadata: Dict[str, Any]
```

### Testing
- ☐ 20 unit tests (edge cases, IN clauses, LIKE patterns, NULL handling)
- ☐ 1 integration test (normalization in executor)

### Status
- ⏳ Implementation
- ⏳ Testing

---

## Phase 2: EXPLAIN Plan Caching (Day 2)

**File**: `src/cache/plan_cache.py` (~500 lines)

### Key Design
- Cache keys: `plan:{connection_id}:{normalized_hash}`
- Schema fingerprinting for invalidation detection
- Query-type-based TTL:
  - Aggregations: 1 hour
  - Joins: 6 hours
  - Lookups: 24 hours
- Table-based invalidation index

### Dataclasses
```python
@dataclass
class CachedPlan:
    normalized_hash: str
    schema_fingerprint: str
    database_type: str
    connection_id: int
    explain_plan: List[str]
    estimated_cost: Optional[float]
    uses_indexes: List[str]
    scan_type: str
```

### Testing
- ☐ 15 unit tests (hit/miss, schema validation, TTL, table invalidation)
- ☐ 1 integration test (EXPLAIN fetching and caching)

### Status
- ⏳ Implementation

---

## Phase 3: Prepared Statement Management (Day 3)

**File**: `src/core/prepared_statement_manager.py` (~450 lines)

### Key Design
- Lazy preparation (only after 2+ executions)
- LRU eviction (max 100 statements)
- Per-connection isolation
- Background cleanup (30-minute TTL)

### Modified File
- `src/core/executor.py` - Add `enable_compilation` parameter and compilation flow

### Testing
- ☐ 12 unit tests (lazy preparation, LRU eviction, cleanup, isolation)
- ☐ 1 integration test (end-to-end compilation flow)

### Status
- ⏳ Implementation

---

## Phase 4: Database & API (Day 4 AM)

### New API Endpoints
- `GET /api/compilation/stats`
- `GET /api/compilation/metrics/{connection_id}`
- `DELETE /api/compilation/cache/connection/{id}`
- `DELETE /api/compilation/cache/table/{id}/{table}`

### Database Tables
- `CompiledQueryMetrics`
- `CompilationInvalidationLog`
- Extend `QueryHistory`

### Status
- ⏳ Implementation

---

## Phase 5: Frontend (Day 4 PM)

### New Components
- `CompilationStats.tsx` - Real-time metrics dashboard

### New Services
- `compilationApi.ts` - API integration

### Modified Components
- `App.tsx` - Add Compilation tab
- `QueryResults.tsx` - Show compilation badge

### Status
- ⏳ Implementation

---

## Performance Expectations

### Conservative Estimates

| Scenario | First Run | Subsequent | Speedup |
|----------|-----------|-----------|---------|
| Simple Lookup | 100ms | 52ms | **48%** |
| Filtered Query | 120ms | 60ms | **50%** |
| Join (2 tables) | 200ms | 100ms | **50%** |
| Aggregation | 180ms | 90ms | **50%** |
| Complex Query | 350ms | 175ms | **50%** |

### Breakdown
- Normalization overhead: +2-5ms
- Plan cache lookup: 1-3ms (Redis)
- Prepared statement reuse: -40 to -50ms
- **Net speedup: 48-52%**

### Cache Hit Rates
- **Plan Cache**: 60-70%
- **Prepared Statements**: 40-50%
- **Overall Benefit**: ~30% of queries

---

## Critical Files

### New Files
1. `src/core/sql_normalizer.py` (~400 lines)
2. `src/cache/plan_cache.py` (~500 lines)
3. `src/core/prepared_statement_manager.py` (~450 lines)
4. `src/api/endpoints/compilation.py` (~200 lines)
5. `frontend/src/components/CompilationStats.tsx` (~200 lines)
6. `frontend/src/services/compilationApi.ts` (~100 lines)

### Modified Files
1. `src/core/executor.py` (lines 24-100)
2. `src/core/schema_inspector.py` (add method)
3. `src/api/endpoints/query.py` (lines 200-260)
4. `src/database/models.py` (add tables + extend QueryHistory)
5. `src/config/settings.py` (add 7 settings)
6. `CLAUDE.md` (update overview)
7. `frontend/src/App.tsx` (add tab)

---

## Success Criteria

✅ **Functionality**:
- [ ] Queries normalize correctly
- [ ] EXPLAIN plans cache and invalidate properly
- [ ] Prepared statements reuse across executions
- [ ] Schema changes trigger invalidation

✅ **Performance**:
- [ ] 50-70% speedup measured
- [ ] Normalization overhead <5ms
- [ ] Plan cache lookup <10ms
- [ ] Cache hit rate 60-70%

✅ **Quality**:
- [ ] 90%+ unit test coverage
- [ ] All integration tests passing
- [ ] Performance benchmarks validated
- [ ] Documentation complete

✅ **Production**:
- [ ] Feature flag implemented
- [ ] Metrics monitoring configured
- [ ] Logging configured
- [ ] Rollback plan documented

---

## See Also

- **Plan File**: `/Users/sam/.claude/plans/lexical-herding-sparkle.md` (detailed reference)
- **Roadmap**: `docs/ROADMAP_ANALYSIS_2025-12-07.md` (strategic context)
- **Original Design**: `NEXT_FEATURES_ROADMAP.md` (lines 1300-1407)
