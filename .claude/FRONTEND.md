# Frontend Reference

Detailed documentation for frontend components and structure.

## Directory Structure

```
frontend/src/
├── components/     # React components
├── services/       # API clients (axios)
├── hooks/          # Custom React hooks
├── types/          # TypeScript definitions
└── utils/          # Utility functions
```

## State Management
- **TanStack Query** - Server state management
- **Zustand** - Client state (if used)

## Component Groups

### Learned Mapping Components (November 10, 2025)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `LearnedMappingsPanel.tsx` | 95 | Main tabbed interface for browsing mappings |
| `ColumnMappingsList.tsx` | 165 | Column mappings with filtering and delete |
| `TableMappingsList.tsx` | 170 | Table mappings with filtering and delete |
| `ResultPatternsList.tsx` | 195 | Result patterns with helpfulness tracking |
| `MappingStatsDisplay.tsx` | 315 | Statistics dashboard with charts |
| `mappingsApi.ts` | 155 | API service layer for mapping endpoints |
| **Total** | **1,095** | |

### Tool-Using Agent UI Components (November 22, 2025)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `ToolsPanel.tsx` | 112 | Main tabbed container (Overview, Directory, Usage Stats) |
| `ToolsOverview.tsx` | 271 | Summary dashboard with stats cards, category breakdown |
| `ToolDirectory.tsx` | 237 | Browsable tool list with filtering and expandable details |
| `ToolUsageStats.tsx` | 277 | Per-tool execution metrics with visual bars |
| `toolsApi.ts` | 100 | API service layer (6 methods) |
| **Total** | **~1,000** | |

**Tests**: `ToolsPanel.test.tsx` (30 tests)

### Row Limit & Pagination Components (December 27, 2025)
| Component | Purpose |
|-----------|---------|
| `QueryInput.tsx` | Row limit dropdown selector (10-10,000 rows) |
| `QueryResults.tsx` | Pagination with 10/25/50/100 rows per page, navigation |
| `MultiDatabaseResults.tsx` | Per-database pagination with independent controls |

**Tests**: `QueryResults.test.tsx` (10 tests), `MultiDatabaseResults.test.tsx` (16 tests)

### Table Sorting Components (January 28, 2026)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `hooks/useTableSort.ts` | 192 | Reusable hook for client-side table sorting |
| `SortableTableHeader.tsx` | 101 | Accessible sortable column header with visual indicators |

**Features**:
- Smart type detection: numbers, dates (ISO), strings sorted appropriately
- Nulls always sort to end regardless of direction
- Keyboard accessible (Enter/Space to sort)
- Visual indicators using Lucide icons (ArrowUp, ArrowDown, ArrowUpDown)
- `onSortChange` callback for pagination reset
- ARIA attributes for screen readers (`aria-sort`, `role="columnheader"`)

**Integrated Into**: `QueryResults.tsx`, `MultiDatabaseResults.tsx`, `StreamingQueryResults.tsx`

**Tests**: `useTableSort.test.ts` (14 tests), `SortableTableHeader.test.tsx` (10 tests)

### Semantic Cache UI Components (November 22, 2025)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `SemanticCachePanel.tsx` | 110 | Main tabbed container (Overview, Statistics, Recent) |
| `CacheOverview.tsx` | 370 | Summary dashboard with stats cards, cache breakdown |
| `CacheStatistics.tsx` | 270 | Hit rate distribution charts, performance metrics |
| `RecentCachedQueries.tsx` | 230 | Browsable cached query list with expandable SQL |
| `QueryResults.tsx` | - | Updated with inline cache badge (exact/semantic hit) |
| `cacheApi.ts` | 150 | API service layer (6 methods) |
| **Total** | **~2,100** | |

**Tests**: `SemanticCachePanel.test.tsx` (34 tests), `test_cache_endpoints.py` (9 backend tests)

### Small Model Optimization UI (January 2-11, 2026)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `ModelConfigPanel.tsx` | 465 | Per-task model configuration |

**Features**:
- 4 task cards: SQL Generation, Narratives, Query Planning, Error Correction
- Model dropdown for each task (fetches from Ollama)
- Timeout slider (5-120s) with default indicators
- Optimization feature toggles: Query Templates, Location Preprocessing
- **Prompt Optimization toggle**: Schema compression, example selection, model size detection
  - Sub-options: Model size (auto/small/medium/large), Schema compression toggle, Max tables slider, Example selection toggle, Max examples slider
- Color-coded task cards (blue, green, purple, orange)

### Data Lineage UI Components (January 2026)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `lineage/LineagePanel.tsx` | 238 | Main 4-tab container (Explore, History, Impact, Patterns) |
| `lineage/LineageGraph.tsx` | 214 | React Flow visualization with custom nodes/edges |
| `lineage/LineageNode.tsx` | 102 | Custom node component with 4 types and color coding |
| `lineage/LineageEdge.tsx` | 85 | Custom animated edge with 7 edge types |
| `lineage/ColumnLineage.tsx` | 224 | Table view of column-to-column transformations |
| `lineage/ImpactAnalysisPanel.tsx` | 105 | Schema change impact with risk badges |
| `lineage/ImpactedQueryCard.tsx` | 42 | Individual impacted query display |
| `lineage/QueryPatternHeatmap.tsx` | 100 | 3-view heatmap (Frequency, Joins, Performance) |
| `types/lineage.ts` | - | TypeScript interfaces |
| `services/lineageApi.ts` | 100 | API client (6 methods) |
| `utils/lineageLayoutUtils.ts` | - | Dagre layout engine |
| **Total** | **~1,200** | |

**Tests**: `LineageGraph.test.tsx` (15+ tests), `QueryPatternHeatmap.test.tsx`

### Advanced Visualization Components (December 20-26, 2025)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `visualization/TreemapView.tsx` | 180 | Treemap chart |
| `visualization/SunburstView.tsx` | 190 | Radial hierarchy chart |
| `visualization/HistogramView.tsx` | 190 | Distribution histogram |
| `visualization/BoxPlotView.tsx` | 240 | Statistical box plot |
| `visualization/AreaChartView.tsx` | 190 | Time-series area chart |
| `visualization/BubbleChartView.tsx` | 140 | 3-variable scatter chart |
| `visualization/ChartVisualization.tsx` | - | Main chart container |
| `visualization/ChartToggle.tsx` | - | Table/chart toggle with type selector |

**Utilities**:
| Utility | Lines | Purpose |
|---------|-------|---------|
| `chartIntelligence.ts` | 700 | Pattern detection engine |
| `chartIntentParser.ts` | 240 | NL chart request parsing |
| `timeSeriesDetector.ts` | 180 | Periodic pattern detection |
| `hierarchyDetector.ts` | 150 | Parent-child data detection |
| `hierarchicalChartUtils.ts` | 300 | Treemap/Sunburst data prep |
| `statisticalChartUtils.ts` | 360 | Box plot/histogram calculations |

**Tests**: `AdvancedCharts.test.tsx` (61 tests), `chartIntelligence.test.ts`

## App.tsx Tab Structure

| Tab | Color | Purpose |
|-----|-------|---------|
| Query | Default | Main query interface |
| Connections | Default | Database connection management |
| Lineage | Purple | Data lineage visualization |
| Tools | Orange | Tool-Using Agent management |
| Cache | Amber | Semantic cache monitoring |
| Settings | Default | System configuration |
