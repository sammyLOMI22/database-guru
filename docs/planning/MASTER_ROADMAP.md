# Database Guru - Master Development Roadmap

**Last Updated**: January 28, 2026
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

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Dialect Registry   │  │  Multi-DB Validator  │  │   ER Diagrams        │
    │   (DB-specific SQL)  │  │   (Pre-flight check) │  │   (Phase 7)          │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐
    │   Data Lineage       │
    │   (Phase 11)         │
    │   185 tests passing  │
    │   ✅ COMPLETE        │
    └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    READY TO IMPLEMENT                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                      LINEAGE INTELLIGENCE (Phase 12) - LLM-Powered                        │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
    │  │ 12.1 Lineage│   │ 12.2 Impact │   │ 12.3 Schema │   │ 12.4 Pattern│   │ 12.5 Lineage│ │
    │  │ Narrator    │──▶│ Advisor     │──▶│ Health      │──▶│ Intelligence│──▶│ Chat        │ │
    │  │             │   │             │   │ Analyzer    │   │             │   │             │ │
    │  │ • Data flow │   │ • Migration │   │             │   │ • Bottleneck│   │ • NL queries│ │
    │  │   explain   │   │   guides    │   │ • Index     │   │   root cause│   │ • Multi-turn│ │
    │  │ • Column    │   │ • Risk      │   │   suggest   │   │ • Anti-     │   │ • Schema Q&A│ │
    │  │   semantics │   │   explain   │   │ • Normal-   │   │   patterns  │   │             │ │
    │  │ • Business  │   │ • SQL patch │   │   ization   │   │ • Trend     │   │ ~1000 lines │ │
    │  │   context   │   │   generate  │   │ • Type      │   │   analysis  │   │             │ │
    │  │             │   │             │   │   suggest   │   │             │   │             │ │
    │  │ ~800 lines  │   │ ~900 lines  │   │ ~1000 lines │   │ ~800 lines  │   │             │ │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘ │
    │                                                                                           │
    │  Prereq: Phase 11 (Data Lineage) | Priority: HIGH | Est: 8-10 days | ~4,500 lines        │
    └───────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐
    │   Table Statistics   │  │   Schema Health      │
    │   (Row counts, size) │  │   (Missing PKs, etc) │
    │   Est: ~280 lines    │  │   Est: ~270 lines    │
    │   Standalone         │  │   (Part of 12.3)     │
    └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                          DATA SOURCE EXPANSION (Phase 13) - NEW                         │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                      CSV & EXCEL FILE SUPPORT (Phase 13) - HIGH PRIORITY                 │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 13.1 Core   │   │ 13.2 DuckDB │   │ 13.3 Cross- │   │ 13.4 Frontend│                  │
    │  │ Backend     │──▶│ Integration │──▶│ Source      │──▶│ UI          │                   │
    │  │             │   │             │   │ Queries     │   │             │                   │
    │  │ • File      │   │ • Virtual   │   │             │   │ • Upload    │                   │
    │  │   upload    │   │   tables    │   │ • DB + File │   │   modal     │                   │
    │  │ • Schema    │   │ • CSV/Excel │   │   JOINs     │   │ • Data      │                   │
    │  │   inference │   │   parsing   │   │ • Result    │   │   sources   │                   │
    │  │ • Storage   │   │ • Query     │   │   merging   │   │   panel     │                   │
    │  │             │   │   execution │   │             │   │ • Preview   │                   │
    │  │ ~5 days     │   │ ~5 days     │   │ ~5 days     │   │ ~5 days     │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: HIGH | Est: 3-4 weeks | ~2,500 lines            │
    │  Plan: CSV_EXCEL_SUPPORT_PLAN.md                                                         │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                         LLM PROVIDER EXPANSION (Phase 14) - NEW                         │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    MULTI-PROVIDER LLM SUPPORT (Phase 14) - HIGH PRIORITY                 │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 14.1 Provider│   │ 14.2 Azure  │   │ 14.3-14.6   │   │ 14.7-14.9   │                  │
    │  │ Abstraction │──▶│ OpenAI      │──▶│ More        │──▶│ Router &    │                   │
    │  │             │   │             │   │ Providers   │   │ Frontend    │                   │
    │  │ • Base class│   │ • Enterprise│   │             │   │             │                   │
    │  │ • Registry  │   │   support   │   │ • OpenAI    │   │ • Multi-    │                   │
    │  │ • Refactor  │   │ • Deployment│   │ • Anthropic │   │   provider  │                   │
    │  │   Ollama    │   │   models    │   │ • Vertex AI │   │   routing   │                   │
    │  │             │   │ • Azure Auth│   │ • Bedrock   │   │ • Fallback  │                   │
    │  │ ~600 lines  │   │ ~500 lines  │   │ • LM Studio │   │ • Config UI │                   │
    │  └─────────────┘   └─────────────┘   │ • vLLM      │   │             │                   │
    │                                       │ ~1,700 lines│   │ ~1,200 lines│                   │
    │                                       └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: HIGH | Est: 3-4 weeks | ~3,000 lines            │
    │  Plan: LLM_PROVIDER_EXPANSION_PLAN.md                                                    │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


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
    │  • Asc/Desc toggle   │       │  • Persist widths    │       │  • Filtered export   │
    │  • Smart type sort   │       │  • Auto-fit option   │       │  • Streaming export  │
    │                      │       │                      │       │                      │
    │  ✅ COMPLETE         │       │  NOT STARTED         │       │  NOT STARTED         │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                      FUTURE PHASES                                       │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │   Streaming Results  │       │   Query Suggestions  │       │   Collaborative      │
    │   (SSE)              │       │   (AI-powered)       │       │   Features           │
    │                      │       │                      │       │                      │
    │  • Real-time stream  │       │  • Schema-aware      │       │  • Share sessions    │
    │  • Progressive render│       │  • History-based     │       │  • Team queries      │
    │  • Large dataset UX  │       │  • Autocomplete      │       │  • Templates library │
    │                      │       │                      │       │                      │
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

    ┌───────────────────────────────────────────────────────────────┐
    │           DATA LINEAGE (Phase 11) - COMPLETE ✅               │
    │                                                               │
    │  11.1 Backend Core ✅    11.2 Frontend Core ✅                │
    │  11.3 Column Lineage ✅  11.4 ER Extensions ✅                │
    │  11.5 Query Patterns ✅  11.6 Polish & Testing ✅             │
    │                                                               │
    │  185 tests (116 backend + 69 frontend)                        │
    └───────────────────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                LINEAGE INTELLIGENCE (Phase 12)                   │  ◀── NEXT
    │                     LLM-Powered Features                         │
    │                                                                  │
    │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │  │ 12.1    │──▶│ 12.2    │──▶│ 12.3    │──▶│ 12.4    │──▶│ 12.5    │
    │  │ Lineage │   │ Impact  │   │ Schema  │   │ Pattern │   │ Lineage │
    │  │ Narrator│   │ Advisor │   │ Health  │   │ Intel.  │   │ Chat    │
    │  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
    │                                                                  │
    └─────────────────────────────────────────────────────────────────┘


    INDEPENDENT FEATURES (Can Start Anytime):
    =========================================

    ┌───────────────────────────────────────────────────────────────────┐
    │        CSV & EXCEL FILE SUPPORT (Phase 13) ◀── HIGH PRIORITY      │
    │                                                                   │
    │  • Upload CSV/Excel as data sources                               │
    │  • Query files alongside databases                                │
    │  • Cross-source JOINs (file + DB)                                 │
    │  • Est: 3-4 weeks | Plan: CSV_EXCEL_SUPPORT_PLAN.md               │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        LLM PROVIDER EXPANSION (Phase 14) ◀── HIGH PRIORITY        │
    │                                                                   │
    │  • Azure OpenAI, OpenAI, Anthropic, Vertex AI, Bedrock            │
    │  • Local alternatives: LM Studio, vLLM                            │
    │  • Multi-provider routing with automatic fallback                 │
    │  • Est: 3-4 weeks | Plan: LLM_PROVIDER_EXPANSION_PLAN.md          │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Table Sorting ✅ │  │  Column Resizing  │  │  Export Options   │
    └───────────────────┘  └───────────────────┘  └───────────────────┘

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Streaming Results│  │  Advanced         │  │  Pattern Learning │
    └───────────────────┘  │  Preprocessing    │  │  (Phase 2.6)      │
                           │  (Phase 2.3)      │  └───────────────────┘
                           └───────────────────┘
```

---

## Recommended Next Steps

### Priority 1: Merge Data Lineage Branch
**Status**: Phase 11 COMPLETE ✅ (185 tests passing)
- All 6 sub-phases complete (11.1-11.6)
- Backend: 116 tests passing
- Frontend: 69 tests passing
- Ready to merge `data-lineage` → `main`

### Priority 2: Lineage Intelligence Phase 12 (LLM-Powered)
**Why**: Transforms Database Guru from query tool to intelligence platform
- **12.1 Lineage Narrator**: Explain data flows in business terms
- **12.2 Impact Advisor**: Migration guides, risk explanations, SQL patches
- **12.3 Schema Health Analyzer**: Index suggestions, normalization, type improvements
- **12.4 Pattern Intelligence**: Bottleneck root cause, anti-pattern detection
- **12.5 Conversational Lineage**: Natural language queries about schema and lineage
- See: [LINEAGE_INTELLIGENCE_PLAN.md](LINEAGE_INTELLIGENCE_PLAN.md) for full details

### Priority 3: Table Sorting ✅ COMPLETE
**Status**: Implemented with reusable hook and accessible component
- Click column header to sort (asc/desc toggle)
- Smart type detection (numbers, dates, strings)
- Keyboard accessible (Enter/Space to sort)
- Visual indicators with Lucide icons
- Integrated into QueryResults, MultiDatabaseResults, StreamingQueryResults

### Priority 4: CSV & Excel File Support (Phase 13) - NEW
**Why**: Major capability expansion - users can analyze spreadsheets alongside databases
- **13.1 Core Backend**: File upload, storage, schema inference
- **13.2 DuckDB Integration**: Virtual tables, CSV/Excel parsing, query execution
- **13.3 Cross-Source Queries**: Database + File JOINs, result merging
- **13.4 Frontend UI**: Upload modal, unified data sources panel, file preview
- See: [CSV_EXCEL_SUPPORT_PLAN.md](CSV_EXCEL_SUPPORT_PLAN.md) for full implementation details

**Key Use Cases**:
- Upload sales.csv and query it with natural language
- JOIN uploaded prospects.xlsx with production CRM database
- Combine multiple spreadsheets into a single analysis

**Technical Approach**: Leverages existing DuckDB integration for file queries

### Priority 5: LLM Provider Expansion (Phase 14) - NEW
**Why**: Enterprise integration and model flexibility - users can leverage cloud LLMs
- **14.1 Provider Abstraction**: Unified interface, registry, refactor Ollama
- **14.2 Azure OpenAI**: Enterprise-first cloud provider with deployment support
- **14.3-14.6 Additional Providers**: OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM
- **14.7-14.9 Enhanced Routing**: Multi-provider routing, fallback chains, frontend config UI
- See: [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) for full implementation details

**Key Use Cases**:
- Connect to existing Azure OpenAI infrastructure
- Use GPT-4 or Claude for complex queries, Ollama for simple ones
- Automatic fallback when primary provider is unavailable
- Cost optimization by routing cheaper tasks to cheaper providers

**Technical Approach**: Abstract provider interface with pluggable implementations

---

## Summary by Category

| Category | Features | Status | Total Effort |
|----------|----------|--------|--------------|
| **Visualization** | ER Diagrams, Data Lineage | Phase 7 ✅, Phase 11 ✅ | COMPLETE |
| **LLM Intelligence** | Lineage Narrator, Impact Advisor, Schema Health, Pattern Intel, Lineage Chat | **NEXT (Phase 12)** | ~4,500 lines |
| **Data Sources** | CSV & Excel File Support | **Phase 13 - NEW** | ~2,500 lines |
| **LLM Integration** | Azure OpenAI, OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM | **Phase 14 - NEW** | ~3,000 lines |
| **Insight Quality** | Preprocessing, Pattern Learning | Not started | ~1,200 lines |
| **Table UX** | Sorting ✅, Resizing, Export | Sorting complete | ~400 lines remaining |
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
| ER Diagrams (Phase 7) | Schema visualization | React Flow + Dagre |
| Data Lineage (Phase 11) | Column-level lineage, impact analysis, query patterns | 185 tests (116 BE + 69 FE) |
| Table Sorting | Click-to-sort columns, smart type detection | 24 tests |

**Total Tests**: 800+ passing

---

## Source Documents

- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Core roadmap
- [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md) - Visualization features
- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - LLM optimization features
- [DATA_LINGEAGE_PLAN.md](DATA_LINGEAGE_PLAN.md) - Data Lineage & Impact Analysis plan (Phase 11)
- [LINEAGE_INTELLIGENCE_PLAN.md](LINEAGE_INTELLIGENCE_PLAN.md) - LLM-Powered Lineage Intelligence (Phase 12)
- [CSV_EXCEL_SUPPORT_PLAN.md](CSV_EXCEL_SUPPORT_PLAN.md) - CSV & Excel File Support (Phase 13)
- [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) - **LLM Provider Expansion (Phase 14)** ← NEW

---

**Updated**: January 28, 2026 (Added LLM Provider Expansion Phase 14 plan)
