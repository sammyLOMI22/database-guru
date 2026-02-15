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
| `lineage/QueryPatternHeatmap.tsx` | 429 | Enhanced 3-view heatmap (Frequency, Joins, Performance) |
| `types/lineage.ts` | 264 | TypeScript interfaces |
| `services/lineageApi.ts` | 165 | API client (11 methods) |
| `utils/lineageLayoutUtils.ts` | - | Dagre layout engine |
| **Total** | **~1,200** | |

**Tests**: `LineageGraph.test.tsx` (15+ tests), `QueryPatternHeatmap.test.tsx`

### Lineage Intelligence UI Components (Phase 12 - January 2026)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `lineage/LineageNarrative.tsx` | 215 | LLM-generated narrative display (12.1) |
| `lineage/ImpactAdvisorPanel.tsx` | 408 | Migration plans & SQL patches (12.2) |
| `lineage/LineageChat.tsx` | 363 | Natural language Q&A interface (12.5) |
| `schema/SchemaHealthDashboard.tsx` | 739 | Health grades, index suggestions, anti-patterns (12.3) |
| `lineage/QueryPatternHeatmap.tsx` | 429 | Enhanced with pattern intelligence (12.4) |
| **Total** | **~2,154** | |

**Phase 12 Features**:
- **LineageNarrative**: Displays summary, data flow, column explanations, confidence
- **ImpactAdvisorPanel**: Change type selector, migration steps, SQL patch copy buttons
- **SchemaHealthDashboard**: Grade badge (A-F), score bar, expandable sections, copy SQL
- **LineageChat**: Chat interface with question type badges, follow-up suggestions
- **QueryPatternHeatmap**: Bottleneck analysis, anti-pattern badges, trend charts

**New Types** (`types/lineage.ts`):
- `LineageNarrative`, `TransformationExplanation`
- `ImpactAdvice`, `MigrationPlan`, `MigrationStep`, `SQLPatch`
- `SchemaHealthReport`, `IndexSuggestion`, `SchemaIssue`, `HealthGrade`
- `PatternIntelligenceReport`, `BottleneckAnalysis`, `QueryAntiPattern`
- `LineageAnswer`, `QuestionType`

**New API Methods** (`services/lineageApi.ts`):
- `parseWithNarrative()` - Parse SQL with LLM explanation
- `getImpactAdvice()` - Get migration plan and SQL patches
- `getSchemaHealth()` - Get schema health report
- `getPatternIntelligence()` - Get pattern analysis
- `getBottleneckAnalysis()` - Get table bottleneck details
- `askQuestion()` - Natural language Q&A

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

### File Data Source UI Components (Phase 13 - January 2026)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `FileUploadModal.tsx` | ~400 | Drag-and-drop file upload modal |
| `FilePreviewPanel.tsx` | ~350 | Schema and data preview panel |
| **Total** | **~750** | |

**FileUploadModal Features**:
- Drag-and-drop interface using `react-dropzone`
- Supported formats: CSV, XLSX, XLS (max 100MB)
- Multi-stage workflow: Idle → Selecting Sheet → Uploading → Success/Error
- Excel sheet selection dropdown
- Display name input field
- File icon indicators (CSV vs Excel)
- Progress indicator with timeout handling

**FilePreviewPanel Features**:
- Two-tab interface: Schema tab and Preview tab
- Schema tab: Column list with types, nullability, sample values
- Preview tab: Data table with configurable row limit
- Type color coding (INT=blue, FLOAT=purple, VARCHAR=green, DATE=orange, BOOL=pink)
- Refresh schema button
- DuckDB table name display for SQL reference
- Truncation indicator for large datasets

**API Service** (`services/api.ts:filesAPI`):
| Method | Purpose |
|--------|---------|
| `uploadFile(file, options)` | FormData multipart upload |
| `listFiles(sessionId?, includeGlobal?)` | List with filters |
| `getFile(fileId)` | Get file details |
| `deleteFile(fileId)` | Delete file |
| `getFileSchema(fileId)` | Get inferred schema |
| `getFilePreview(fileId, limit)` | Get data preview |
| `refreshFileSchema(fileId)` | Re-infer schema |
| `getExcelSheets(file)` | Inspect sheets before upload |

**Type Definitions** (`types/api.ts`):
- `FileSource`: Complete file source interface
- `FilePreviewResponse`: Preview data with columns and rows
- `ExcelSheetsResponse`: Available sheets
- `FileUploadOptions`: Upload configuration

### LLM Usage Monitoring UI Components (Phase 16 - February 2026)
| Component | Lines | Purpose |
|-----------|-------|---------|
| `dashboard/LLMUsageDashboard.tsx` | ~384 | Full usage monitoring dashboard |
| `UsageSummary.tsx` | ~133 | Per-session expandable usage summary |
| `SessionUsageBadge.tsx` | ~64 | Inline token/cost badge in chat header |
| `services/llmUsageApi.ts` | ~82 | API service layer (7 methods) |
| **Total** | **~663** | |

**LLMUsageDashboard Features**:
- Time range selector (1-90 days)
- 4 stat cards: Total Calls, Total Tokens, Avg Response Time, Est. Cost
- Usage by Agent breakdown (bar chart)
- Usage by Model breakdown (pie chart)
- Usage by Provider breakdown
- Time series chart (hourly/daily granularity)
- Recent LLM Calls table with filtering

**UsageSummary Features**:
- Expandable panel showing session-level stats
- Total Tokens, LLM Calls, Avg Latency, Est. Cost
- Agent breakdown with proportional progress bars

**SessionUsageBadge Features**:
- Compact inline display (tokens + calls + cost)
- Auto-refreshes every 30 seconds
- Hover tooltips for each metric

**API Service** (`services/llmUsageApi.ts`):
| Method | Purpose |
|--------|---------|
| `getStats(days)` | Fetch overall usage statistics |
| `getByAgent(days)` | Fetch agent breakdown |
| `getByModel(days)` | Fetch model breakdown |
| `getByProvider(days)` | Fetch provider breakdown |
| `getTimeSeries(days, granularity)` | Fetch time series data |
| `getRecent(limit)` | Fetch recent call records |
| `getSessionUsage(sessionId)` | Fetch per-session usage |

## App.tsx Tab Structure

| Tab | Color | Purpose |
|-----|-------|---------|
| Query | Default | Main query interface |
| Connections | Default | Database connection management |
| Lineage | Purple | Data lineage visualization |
| Tools | Orange | Tool-Using Agent management |
| Cache | Amber | Semantic cache monitoring |
| Usage | Default | LLM usage monitoring dashboard |
| Settings | Default | System configuration |
