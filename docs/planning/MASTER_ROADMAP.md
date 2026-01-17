# Database Guru - Master Development Roadmap

**Last Updated**: January 17, 2026
**Purpose**: Unified view of all planned features and their dependencies

---

## Visual Roadmap

```
                              DATABASE GURU - MASTER DEVELOPMENT ROADMAP
                              ==========================================

    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    COMPLETED FEATURES                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Parallel Multi-DB  │  │  Parallel Corrections │  │   Semantic Caching   │
    │   Execution (3x)     │  │   (1.6x speedup)     │  │   (50% hit rate)     │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Tool-Using Agent   │  │  Connection Pooling  │  │   Result Narrator    │
    │   (10 tools)         │  │   (30x faster)       │  │   (Advanced Analysis)│
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Chart Intelligence │  │   Advanced Charts    │  │   Query Compilation  │
    │   (Phase 8)          │  │   (Phase 10)         │  │   & Prepared Stmts   │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ IN REVIEW       │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Model Router       │  │   Query Templates    │  │   Prompt Optimizer   │
    │   (Per-task models)  │  │   (20% LLM bypass)   │  │   (40% token save)   │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐
    │   Dialect Registry   │  │  Multi-DB Validator  │
    │   (DB-specific SQL)  │  │   (Pre-flight check) │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    READY TO IMPLEMENT                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │         ER DIAGRAM GENERATOR (Phase 7)      │
                    │  =========================================  │
                    │  • Interactive schema visualization         │
                    │  • React Flow + Dagre auto-layout          │
                    │  • FK relationship inference               │
                    │  • Multi-database color coding             │
                    │  • Export PNG/SVG                          │
                    │                                             │
                    │  Est: ~1,600 lines | Priority: HIGH        │
                    │  Dependencies: None                         │
                    └─────────────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Query Path Overlay │  │   Table Statistics   │  │   Schema Health      │
    │   (Highlight tables) │  │   (Row counts, size) │  │   (Missing PKs, etc) │
    │   Est: ~150 lines    │  │   Est: ~280 lines    │  │   Est: ~270 lines    │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                              INSIGHT QUALITY IMPROVEMENTS                                │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │  Advanced Preprocess │──────▶│   Pattern Learning   │──────▶│   Model Performance  │
    │  (Phase 2.3)         │       │   (Phase 2.6)        │       │   Tracker            │
    │                      │       │                      │       │                      │
    │  • Date normalization│       │  • Learn from success│       │  • Track accuracy    │
    │  • Boolean handling  │       │  • Auto-templates    │       │  • Auto model select │
    │  • Status values     │       │  • Pattern matching  │       │  • Performance stats │
    │                      │       │                      │       │                      │
    │  Est: 2-3 days       │       │  Est: 4-5 days       │       │  (Included in 2.6)   │
    │  NOT STARTED         │       │  NOT STARTED         │       │  NOT STARTED         │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    TABLE IMPROVEMENTS                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │   Table Sorting      │       │   Column Resizing    │       │   Export Options     │
    │   (Quick Win)        │       │   (Enhancement)      │       │   (CSV, Excel, JSON) │
    │                      │       │                      │       │                      │
    │  • Click column head │       │  • Drag to resize    │       │  • Multiple formats  │
    │  • Multi-column sort │       │  • Persist widths    │       │  • Filtered export   │
    │  • Asc/Desc toggle   │       │  • Auto-fit option   │       │  • Streaming export  │
    │                      │       │                      │       │                      │
    │  Est: 1-2 days       │       │  Est: 1-2 days       │       │  Est: 2-3 days       │
    │  NOT STARTED         │       │  NOT STARTED         │       │  NOT STARTED         │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                      FUTURE PHASES                                       │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │      DATA LINEAGE & IMPACT (Phase 11)       │
                    │  =========================================  │
                    │  • Query lineage graph                      │
                    │  • Column-level tracking                    │
                    │  • "What breaks if..." analysis            │
                    │  • Query pattern analytics                  │
                    │                                             │
                    │  Est: ~2,400 lines | Priority: MEDIUM      │
                    │  Depends on: Phase 7 ER Diagrams           │
                    └─────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │   Streaming Results  │       │   Query Suggestions  │       │   Collaborative      │
    │   (SSE)              │       │   (AI-powered)       │       │   Features           │
    │                      │       │                      │       │                      │
    │  • Real-time stream  │       │  • Schema-aware      │       │  • Share sessions    │
    │  • Progressive render│       │  • History-based     │       │  • Team queries      │
    │  • Large dataset UX  │       │  • Autocomplete      │       │  • Templates library │
    │                      │       │                      │       │                      │
    │  Est: 1-2 weeks      │       │  Est: 2 weeks        │       │  Est: 3-4 weeks      │
    │  Priority: MEDIUM    │       │  Priority: LOW       │       │  Priority: LOW       │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                               DEFERRED CHART COMPONENTS                                  │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Sankey Diagram     │  │   Violin Plot        │  │   Sparklines         │
    │   (Flow data)        │  │   (Distribution)     │  │   (Inline mini)      │
    │   Needs: d3-sankey   │  │   Complex: KDE calc  │  │   Lower priority     │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                              SECURITY & INFRASTRUCTURE                                   │
    │                                  (Lower Priority)                                        │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Authorization      │  │   Session Expiration │  │   Rate Limiting      │
    │   System             │  │   (TTL, cleanup)     │  │   (Per-user)         │
    │   CRITICAL but       │  │   Est: 2 days        │  │   Est: 2-3 days      │
    │   user deferred      │  │   MEDIUM priority    │  │   LOW priority       │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## Dependency Graph

```
                                    FEATURE DEPENDENCIES
                                    ====================

    Query Compilation (Current PR)
            │
            ├───────────────────────────────────────────────────────────────┐
            ▼                                                               │
    ┌───────────────────┐                                                   │
    │  ER Diagrams      │◀───────────────────────────────────────────┐      │
    │  (Phase 7)        │                                            │      │
    └───────────────────┘                                            │      │
            │                                                        │      │
            ├──────────────────┬──────────────────┐                  │      │
            ▼                  ▼                  ▼                  │      │
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐         │      │
    │ Query Path    │  │ Table Stats   │  │ Schema Health │         │      │
    │ Overlay       │  │ Overlay       │  │ Indicators    │         │      │
    └───────────────┘  └───────────────┘  └───────────────┘         │      │
            │                  │                  │                  │      │
            └──────────────────┴──────────────────┘                  │      │
                               │                                     │      │
                               ▼                                     │      │
                    ┌───────────────────┐                            │      │
                    │  Data Lineage     │◀───────────────────────────┘      │
                    │  (Phase 11)       │                                   │
                    └───────────────────┘                                   │
                                                                            │
    ┌───────────────────┐                                                   │
    │  Advanced         │◀──────────────────────────────────────────────────┘
    │  Preprocessing    │
    │  (Phase 2.3)      │
    └───────────────────┘
            │
            ▼
    ┌───────────────────┐
    │  Pattern Learning │
    │  (Phase 2.6)      │
    └───────────────────┘
            │
            ▼
    ┌───────────────────┐
    │  Model Performance│
    │  Tracker          │
    └───────────────────┘


    INDEPENDENT FEATURES (Can Start Anytime):
    =========================================

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Table Sorting    │  │  Column Resizing  │  │  Export Options   │
    └───────────────────┘  └───────────────────┘  └───────────────────┘

    ┌───────────────────┐  ┌───────────────────┐
    │  Streaming Results│  │  Error Boundaries │
    └───────────────────┘  └───────────────────┘
```

---

## Recommended Next Steps

Based on your interests (no auth, ER diagrams, data visualization, insight quality, table sorting):

### Priority 1: ER Diagram Generator (Phase 7)
**Why**: Foundation for schema understanding and Data Lineage (Phase 11)
- Interactive schema visualization with React Flow
- Auto-layout with Dagre algorithm
- FK relationship inference from naming conventions
- Multi-database color coding
- Export PNG/SVG

**Effort**: ~1,600 lines | 3-5 days

### Priority 2: Table Sorting (Quick Win)
**Why**: User explicitly mentioned, immediate UX improvement
- Click column header to sort
- Asc/Desc toggle indicator
- Multi-column sort support
- Persist sort preferences

**Effort**: ~200 lines | 1-2 days

### Priority 3: Advanced Preprocessing (Phase 2.3)
**Why**: Improves insight quality for all queries
- Date normalization ("last 7 days" → SQL)
- Boolean handling ("active" → `status = 'active'`)
- Status value normalization (detect actual DB values)

**Effort**: ~400 lines | 2-3 days

### Priority 4: Pattern Learning (Phase 2.6)
**Why**: Continuous improvement of SQL generation
- Learn successful patterns from queries
- Auto-generate templates from usage
- Track model performance per task

**Effort**: ~800 lines | 4-5 days

---

## Summary by Category

| Category | Features | Status | Total Effort |
|----------|----------|--------|--------------|
| **Visualization** | ER Diagrams, Data Lineage | Ready + Future | ~4,000 lines |
| **Insight Quality** | Preprocessing, Pattern Learning | Ready | ~1,200 lines |
| **Table UX** | Sorting, Resizing, Export | Ready | ~600 lines |
| **Performance** | Streaming Results | Future | ~1,500 lines |
| **Security** | Auth, Rate Limiting | Deferred | ~2,000 lines |

---

## Quick Reference: What's Complete

| Feature | Impact | Tests |
|---------|--------|-------|
| Parallel Multi-DB | 3x speedup | 6 tests |
| Parallel Corrections | 1.6x speedup | 7 tests |
| Semantic Caching | 50% hit rate | 20 tests |
| Tool-Using Agent | Better first-attempt | 26 tests |
| Connection Pooling | 30x faster | 29 tests |
| Result Narrator | Advanced analysis | 75 tests |
| Chart Intelligence | Smart recommendations | 71 tests |
| Advanced Charts | 6 new chart types | 61 tests |
| Query Compilation | Cache + prepared stmts | 21 tests |
| Model Router | Per-task models | 220 lines tests |
| Prompt Optimizer | 40% token reduction | 52 tests |
| Dialect Registry | DB-specific SQL | 72 lines tests |
| Multi-DB Validator | Pre-flight validation | 27 tests |

**Total Tests**: 600+ passing

---

## Source Documents

- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Core roadmap
- [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md) - Visualization features
- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - LLM optimization features

---

**Created**: January 17, 2026
