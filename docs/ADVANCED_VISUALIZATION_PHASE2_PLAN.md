# Advanced Visualization Phase 2 Implementation Plan

**Feature Branch**: `advanced-visualization-V2`
**Status**: Phase 8 & 10 Complete, Phase 7 Planned
**Created**: December 20, 2025
**Last Updated**: December 26, 2025
**Phases**: 7 (ER Diagrams), 8 (Chart Intelligence), 10 (Advanced Charts), 11 (Data Lineage)

---

## Current Status

| Phase | Feature | Status | Tests | Branch |
|-------|---------|--------|-------|--------|
| **Phase 8** | Chart Intelligence | **COMPLETE** | 71 tests | `advanced-visualization-V2` |
| **Phase 10** | Advanced Charts | **COMPLETE** | 53 tests | `advanced-visualization-V2` |
| **Phase 7** | ER Diagram Generator | Planned | - | - |
| **Phase 11** | Data Lineage & Impact Analysis | Planned | - | - |

**Total Frontend Tests**: 526 (all passing)
**Build Status**: Passing

---

## Executive Summary

This plan covers four major visualization enhancements for Database Guru:

- **Phase 7**: ER Diagram Generator - Interactive entity-relationship diagrams with health indicators (NEXT)
- **Phase 8**: Improved Chart Intelligence - Smarter pattern detection and recommendations (COMPLETE)
- **Phase 10**: Advanced Chart Types - Specialized charts for hierarchical, statistical, and time-series data (COMPLETE)
- **Phase 11**: Data Lineage & Impact Analysis - Query flow visualization and schema change impact (FUTURE)

All phases build on the existing visualization architecture (Phases 1-6 complete).

---

## Completed Work & Bug Fixes (Phase 8 & 10)

### Phase 8 & 10 Implementation (December 20-21, 2025)

#### Files Created

**Phase 8 - Chart Intelligence:**
| File | Lines | Purpose |
|------|-------|---------|
| `src/utils/chartIntelligence.ts` | ~400 | Main intelligence engine with `analyzeData()` |
| `src/utils/timeSeriesDetector.ts` | ~180 | Time-series patterns, periodicity detection |
| `src/utils/hierarchyDetector.ts` | ~150 | Parent-child hierarchical data detection |
| `src/utils/geoDetector.ts` | ~120 | Geographic data (lat/lon, country codes) |
| `src/utils/trendLineCalculator.ts` | ~100 | Linear regression calculations |
| `src/utils/chartIntentParser.ts` | ~240 | Parses NL queries for chart type hints |
| `src/components/visualization/OutlierMarkers.tsx` | ~120 | Visual outlier indicators |
| `src/components/visualization/TrendLine.tsx` | ~150 | Trend line overlay component |

**Phase 10 - Advanced Charts:**
| File | Lines | Purpose |
|------|-------|---------|
| `TreemapView.tsx` | ~180 | Hierarchical treemap with custom renderer |
| `SunburstView.tsx` | ~190 | Radial hierarchical chart |
| `HistogramView.tsx` | ~190 | Distribution histogram with markers |
| `BoxPlotView.tsx` | ~240 | Statistical box plot |
| `AreaChartView.tsx` | ~190 | Time-series area chart |
| `hierarchicalChartUtils.ts` | ~300 | Treemap/Sunburst data preparation |
| `statisticalChartUtils.ts` | ~360 | Box plot, histogram calculations |

### Bug Fixes Applied

#### 1. Chart Type Override Column Selection Bug (December 26, 2025)

**Issue**: When user overrides chart type via dropdown, columns were NOT recalculated for the new chart type. Charts would fail to render or disappear.

**Root Cause**: `ChartVisualization.tsx` spread `autoRecommendation` without recalculating `xColumn`/`yColumn` for the override type.

**Fix**:
- Exported `selectColumnsForChart()` from `chartIntelligence.ts`
- Updated `ChartVisualization.tsx` to recalculate columns when override is set

```typescript
// Fixed: Recalculate columns for overridden chart type
const { xColumn, yColumn } = selectColumnsForChart(
  overrideChartType, classification, autoRecommendation.patterns, data
);
```

#### 2. Logic Integration (December 21, 2025)

**Issue**: `ChartVisualization.tsx` was importing from legacy `chartUtils.ts` instead of new `chartIntelligence.ts`.

**Fix**: Updated imports to use `analyzeData` from `chartIntelligence.ts`.

#### 3. Intent Parsing Mapping (December 21, 2025)

**Issue**: `chartIntentParser.ts` mapped 'area' to 'line' instead of 'area'.

**Fix**: Updated mapping to correctly map 'area' → 'area'.

### Deferred Items

The following were planned but deferred for future iterations:

| Item | Reason | Priority |
|------|--------|----------|
| `SankeyView.tsx` | Requires d3-sankey dependency | Medium |
| `ViolinPlotView.tsx` | Complex kernel density estimation | Low |
| `BubbleChartView.tsx` | Lower priority | Low |
| `SparklineView.tsx` | Lower priority | Low |
| `ConfidenceInterval.tsx` | Future enhancement | Low |

### Related Backend Fixes (December 24, 2025)

These backend fixes were made alongside the visualization work:

1. **Location Query Complexity Scoring** (`query_planning_agent.py`): Increased location keyword weight from +0.2 to +0.5
2. **QueryPlan Attribute Bug** (`self_correcting_agent.py`): Fixed typo `tables_needed` → `tables`
3. **ResultNarrator Model Selection**: Now respects user-selected model from UI
4. **Robust JSON Parsing** (`result_narrator.py`): Added balanced brace extraction for malformed LLM output
5. **Schema Inspection** (`schema_inspector.py`): Added 'city' and 'address' to sampling keywords

---

## Implementation Order

```
Phase 8: Chart Intelligence (Foundation) ────────────────► COMPLETE
    └──► Phase 10: Advanced Charts (Uses Phase 8 detection) ► COMPLETE

Phase 7: ER Diagram Generator ◄──────────────────────────── NEXT
    └──► Phase 11: Data Lineage (Uses Phase 7 schema + query history)
```

**Rationale**:
- Phase 8's enhanced detection logic is foundational for Phase 10's advanced chart types (both COMPLETE).
- Phase 7 (ER Diagrams) is independent and is the next priority.
- Phase 11 (Data Lineage) builds on Phase 7's schema visualization and existing query history.

---

## Phase 8: Improved Chart Intelligence (COMPLETE)

> **Status**: Implemented December 20-21, 2025 | 71 Tests | All Passing

### Purpose

Enhance chart detection with advanced pattern recognition, multi-chart recommendations, and natural language explanations.

### Features

1. **Natural Language Chart Requests** (NEW)
   - Parse chart type from user queries: "Create a bar chart of inventory"
   - Support keywords: "bar chart", "pie chart", "line graph", "scatter plot", etc.
   - Auto-switch to chart view with specified type when detected
   - Example queries:
     - "Show me a bar chart of sales by region"
     - "Create a pie chart showing category distribution"
     - "Graph inventory levels as a line chart"
     - "Scatter plot of price vs quantity"

2. **Advanced Pattern Detection**
   - Periodic patterns (weekly, monthly, quarterly cycles)
   - Hierarchical data structures (parent-child, path columns)
   - Geographic data (lat/lon, country/state codes)
   - Time-series without explicit date columns

3. **Multi-Chart Recommendations**
   - Score each chart type (0-100)
   - Return top 3 alternative recommendations
   - Suggest chart combinations (e.g., bar + line overlay)
   - Detect grouping opportunities (stacked, grouped)

3. **Visual Enhancements**
   - Trend lines on scatter/line charts (linear regression)
   - Outlier markers (z-score > 2)
   - Confidence intervals (95% bands)

4. **Natural Language Explanations**
   - "This data shows an upward trend - try a line chart"
   - "Detected strong correlation (r=0.87) - scatter plot ideal"
   - "Hierarchical data detected - consider a treemap"

### New Files

| File | Purpose | Est. Lines |
|------|---------|------------|
| `frontend/src/utils/chartIntentParser.ts` | Parse chart type from NL queries | ~150 |
| `frontend/src/utils/chartIntelligence.ts` | Advanced pattern detection engine | ~400 |
| `frontend/src/utils/timeSeriesDetector.ts` | Detect periodic patterns | ~180 |
| `frontend/src/utils/hierarchyDetector.ts` | Detect hierarchical/tree data | ~150 |
| `frontend/src/utils/geoDetector.ts` | Detect geographic data | ~120 |
| `frontend/src/utils/trendLineCalculator.ts` | Linear regression calculations | ~100 |
| `frontend/src/components/visualization/ChartRecommendations.tsx` | NL recommendations panel | ~180 |
| `frontend/src/components/visualization/OutlierMarkers.tsx` | Visual outlier indicators | ~120 |
| `frontend/src/components/visualization/TrendLine.tsx` | Trend line overlay component | ~150 |
| `frontend/src/components/visualization/ConfidenceInterval.tsx` | Confidence band component | ~130 |
| `frontend/tests/chartIntelligence.test.tsx` | Test suite | ~250 |
| `frontend/tests/chartIntentParser.test.tsx` | NL parsing tests | ~100 |

**Subtotal: ~2,030 lines**

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/types/api.ts` | Add `preferred_chart_type` to QueryRequest/Response |
| `frontend/src/components/QueryInput.tsx` | Parse chart intent from question text |
| `frontend/src/components/ChatInterface.tsx` | Pass chart preference to API |
| `frontend/src/services/api.ts` | Include chart preference in request |
| `src/models/schemas.py` | Add `preferred_chart_type` field to request/response |
| `src/api/endpoints/query.py` | Pass chart preference through response |
| `frontend/src/components/QueryResults.tsx` | Auto-select chart type from response |
| `frontend/src/utils/chartUtils.ts` | Extend `detectChartType()` to use intelligence engine |
| `frontend/src/components/visualization/ChartVisualization.tsx` | Add recommendations panel, integrate overlays |
| `frontend/src/components/visualization/ScatterChartView.tsx` | Add trend line support |
| `frontend/src/components/visualization/LineChartView.tsx` | Add confidence intervals |

### Dependencies

```json
{
  "simple-statistics": "^7.8.0"
}
```

### Natural Language Chart Request - Data Flow

```
User types: "Create a bar chart of inventory by category"
    │
    ▼
QueryInput.tsx
    │
    ├──► chartIntentParser.parseChartIntent(question)
    │              │
    │              ▼
    │    { chartType: 'bar', cleanedQuestion: 'inventory by category' }
    │
    ▼
ChatInterface.tsx → handleSubmit()
    │
    ├──► api.processQuery({
    │        question: 'inventory by category',
    │        preferred_chart_type: 'bar'  // NEW FIELD
    │    })
    │
    ▼
Backend query.py
    │
    ├──► SQL Generation (question without chart keywords)
    ├──► Execute query
    ├──► Generate narratives
    │
    └──► Response includes:
               {
                 results: [...],
                 preferred_chart_type: 'bar'  // Passed through
               }
    │
    ▼
QueryResults.tsx
    │
    ├──► If preferred_chart_type:
    │        setViewMode('chart')
    │        setSelectedChartType('bar')
    │
    └──► ChartVisualization renders bar chart automatically
```

### Chart Intent Parser Example

```typescript
// frontend/src/utils/chartIntentParser.ts

const CHART_PATTERNS = [
  { pattern: /\b(bar\s*(?:chart|graph)?)\b/i, type: 'bar' },
  { pattern: /\b(pie\s*(?:chart|graph)?)\b/i, type: 'pie' },
  { pattern: /\b(line\s*(?:chart|graph)?)\b/i, type: 'line' },
  { pattern: /\b(scatter\s*(?:plot|chart)?)\b/i, type: 'scatter' },
  { pattern: /\bcreate\s+(?:a\s+)?(\w+)\s+chart\b/i, type: '$1' },
  { pattern: /\bshow\s+(?:as|me)\s+(?:a\s+)?(\w+)\b/i, type: '$1' },
  { pattern: /\bgraph\s+(?:of|showing)\b/i, type: 'line' },
  { pattern: /\bvisualize\s+as\s+(\w+)\b/i, type: '$1' },
];

export function parseChartIntent(question: string): {
  chartType: ChartType | null;
  cleanedQuestion: string;
} {
  for (const { pattern, type } of CHART_PATTERNS) {
    const match = question.match(pattern);
    if (match) {
      const chartType = type.startsWith('$')
        ? match[1].toLowerCase()
        : type;
      return {
        chartType: validateChartType(chartType),
        cleanedQuestion: question.replace(pattern, '').trim()
      };
    }
  }
  return { chartType: null, cleanedQuestion: question };
}
```

### Enhanced Detection Algorithm

```
Input: results[], statistics{}
    │
    ▼
┌──────────────────────────────────────────────────┐
│ 1. Basic Column Classification (existing)        │
│    - numeric, categorical, temporal, id columns  │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ 2. Advanced Pattern Detection (NEW)              │
│    ├── timeSeriesDetector.detectPeriodicPatterns │
│    ├── hierarchyDetector.detectHierarchy         │
│    └── geoDetector.detectGeographic              │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ 3. Multi-Chart Recommendation Engine             │
│    - Score each chart type (0-100)               │
│    - Return top 3 recommendations                │
│    - Generate NL explanation                     │
└──────────────────────────────────────────────────┘
    │
    ▼
Output: EnhancedChartRecommendation
  - primaryChart: { type, xCol, yCol, confidence, reason }
  - alternatives: [...]
  - combinations: [{ type1, type2, reason }]
  - groupingOption: 'stacked' | 'grouped' | null
  - nlExplanation: "This data shows..."
```

---

## Phase 10: Advanced Chart Types (COMPLETE)

> **Status**: Implemented December 20-21, 2025 | 53 Tests | All Passing

### Purpose

Add specialized chart types for hierarchical, statistical, and time-series data patterns.

### New Chart Types

#### Hierarchical Charts
- **Treemap**: Nested rectangles for hierarchical proportions
- **Sunburst**: Radial hierarchy with drill-down
- **Sankey**: Flow diagrams for source-target data

#### Statistical Charts
- **Box Plot**: Distribution quartiles and outliers
- **Histogram**: Frequency distribution bins
- **Violin Plot**: Distribution shape comparison
- **Bubble Chart**: 3-variable scatter (x, y, size)

#### Time-Series Charts
- **Area Chart**: Stacked area for composition over time
- **Sparkline**: Inline mini-charts for tables

### New Files

| File | Purpose | Est. Lines |
|------|---------|------------|
| `frontend/src/components/visualization/TreemapView.tsx` | Treemap chart | ~180 |
| `frontend/src/components/visualization/SunburstView.tsx` | Sunburst chart | ~200 |
| `frontend/src/components/visualization/SankeyView.tsx` | Sankey diagram | ~220 |
| `frontend/src/components/visualization/BoxPlotView.tsx` | Box plot | ~180 |
| `frontend/src/components/visualization/HistogramView.tsx` | Histogram | ~150 |
| `frontend/src/components/visualization/ViolinPlotView.tsx` | Violin plot | ~200 |
| `frontend/src/components/visualization/BubbleChartView.tsx` | Bubble chart | ~160 |
| `frontend/src/components/visualization/AreaChartView.tsx` | Stacked area | ~170 |
| `frontend/src/components/visualization/SparklineView.tsx` | Inline sparklines | ~120 |
| `frontend/src/utils/hierarchicalChartUtils.ts` | Treemap/Sunburst data prep | ~180 |
| `frontend/src/utils/statisticalChartUtils.ts` | Box plot/histogram calculations | ~200 |
| `frontend/tests/AdvancedCharts.test.tsx` | Test suite | ~350 |

**Subtotal: ~2,310 lines**

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/package.json` | Add `d3-hierarchy` for sunburst layout |
| `frontend/src/utils/chartUtils.ts` | Extend `ChartType` union with 9 new types |
| `frontend/src/components/visualization/ChartVisualization.tsx` | Add rendering cases for new charts |
| `frontend/src/components/visualization/ChartToggle.tsx` | Add new types to dropdown selector |

### Extended ChartType

```typescript
export type ChartType =
  // Existing
  | 'bar' | 'line' | 'pie' | 'scatter' | 'table'
  // Phase 10: Hierarchical
  | 'treemap' | 'sunburst' | 'sankey'
  // Phase 10: Statistical
  | 'boxplot' | 'histogram' | 'violin' | 'bubble'
  // Phase 10: Time-series
  | 'area' | 'sparkline';
```

### Dependencies

```json
{
  "d3-hierarchy": "^3.1.2"
}
```

### Detection Integration

```typescript
// In enhanced detectChartType()

// Hierarchical detection → treemap/sunburst
if (hierarchyDetector.detectHierarchy(results)) {
  return {
    chartType: 'treemap',
    confidence: 0.85,
    reason: 'Hierarchical data structure detected',
    alternatives: ['sunburst']
  };
}

// Statistical distribution → boxplot/histogram
if (numericColumns.length === 1 && results.length > 20) {
  return {
    chartType: 'histogram',
    confidence: 0.8,
    reason: 'Single numeric column suitable for distribution analysis',
    alternatives: ['boxplot', 'violin']
  };
}

// Flow data → sankey
if (hasSourceTargetValue(columns)) {
  return {
    chartType: 'sankey',
    confidence: 0.9,
    reason: 'Source-target-value pattern detected'
  };
}
```

---

## Phase 7: ER Diagram Generator (NEXT)

> **Status**: Planned | Estimated: ~1,600 lines | Priority: P1

### Purpose

Generate interactive Entity-Relationship diagrams from database schema for connected databases.

### Features

1. **Schema Extraction**
   - Tables, columns, primary keys from SchemaInspector
   - Foreign key relationships (explicit)
   - Inferred relationships from naming conventions (e.g., `user_id` → `users.id`)

2. **Interactive Diagram**
   - React Flow for rendering
   - Zoom, pan, drag positioning
   - Auto-layout (Dagre algorithm)
   - Tables as nodes with column lists
   - Relationships as connecting lines (1:1, 1:N, M:N)

3. **Multi-Database Support**
   - Color-code tables by database
   - Toggle database visibility
   - Cross-database relationship detection

4. **Export & Search**
   - Export as PNG/SVG
   - Search/filter tables by name
   - Highlight related tables on hover

### Library Choice: React Flow

**Why React Flow over D3.js:**
- Better React integration with hooks
- Built-in zoom/pan/drag functionality
- Easier custom node/edge styling
- Active maintenance and TypeScript support
- Simpler learning curve

### New Files

| File | Purpose | Est. Lines |
|------|---------|------------|
| `frontend/src/components/schema/ERDiagram.tsx` | Main ER diagram container | ~280 |
| `frontend/src/components/schema/TableNode.tsx` | Custom node for tables | ~150 |
| `frontend/src/components/schema/RelationshipEdge.tsx` | Custom edge for FK relationships | ~120 |
| `frontend/src/components/schema/ERDiagramControls.tsx` | Zoom, pan, layout controls | ~100 |
| `frontend/src/components/schema/ERDiagramSearch.tsx` | Table search/filter | ~80 |
| `frontend/src/utils/erDiagramUtils.ts` | Layout algorithms, data transformation | ~250 |
| `frontend/src/utils/relationshipInference.ts` | Infer FKs from naming conventions | ~150 |
| `frontend/src/hooks/useERDiagram.ts` | Custom hook for ER state management | ~120 |
| `frontend/tests/ERDiagram.test.tsx` | Test suite | ~200 |
| `src/api/endpoints/er_diagram.py` | Backend endpoint for enhanced schema | ~150 |

**Subtotal: ~1,600 lines**

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/package.json` | Add `reactflow@11.x`, `dagre@0.8.5` |
| `frontend/src/App.tsx` | Add "Schema" tab with ER diagram |
| `frontend/src/services/api.ts` | Add `getERDiagramSchema()` method |
| `frontend/src/types/api.ts` | Add `ERDiagramSchema`, `ERNode`, `EREdge` types |
| `src/api/router.py` | Register ER diagram router |

### Dependencies

```json
{
  "reactflow": "^11.10.0",
  "@reactflow/node-types": "^1.0.0",
  "dagre": "^0.8.5",
  "@types/dagre": "^0.7.52"
}
```

### Component Architecture

```
ERDiagram (Main Container)
├── ERDiagramControls (Toolbar)
│   ├── LayoutSelector (force-directed, hierarchical, grid)
│   ├── ExportButton (PNG/SVG)
│   ├── ZoomControls
│   └── ResetViewButton
├── ERDiagramSearch
│   ├── SearchInput
│   └── FilterDropdown (by database for multi-DB)
├── ReactFlow
│   ├── TableNode[] (Custom nodes)
│   │   ├── TableHeader (name, PK icon)
│   │   ├── ColumnList (scrollable)
│   │   │   └── ColumnRow (name, type, PK/FK badge)
│   │   └── DatabaseBadge (color-coded for multi-DB)
│   └── RelationshipEdge[] (Custom edges)
│       ├── CardinalityMarker (1:1, 1:N, M:N)
│       └── RelationshipLabel (FK name)
└── ERDiagramLegend
    └── Cardinality symbols explanation
```

### Data Flow

```
User clicks "Schema" tab
    │
    ▼
useERDiagram hook
    │
    ├──► api.getERDiagramSchema(connectionIds)
    │              │
    │              ▼
    │    GET /api/schema/er-diagram?connections=1,2,3
    │
    ▼
Backend (er_diagram.py)
    │
    ├──► SchemaInspector.get_full_schema()
    │              │
    │              ▼
    │    Tables, Columns, PKs, FKs
    │
    ├──► RelationshipInferrer.infer_from_naming()
    │              │
    │              ▼
    │    Inferred: user_id → users.id
    │
    └──► Transform to React Flow format
               │
               ▼
         { nodes: [...], edges: [...] }
               │
               ▼
erDiagramUtils.ts
    │
    ├──► calculateLayout() (Dagre algorithm)
    ├──► colorCodeByDatabase()
    └──► filterBySearch()
```

### Relationship Inference Algorithm

```typescript
// Pattern 1: Explicit FK (from schema)
// Already provided by SchemaInspector

// Pattern 2: Naming convention inference
function inferFromNaming(tables: TableInfo[]): InferredRelationship[] {
  const patterns = [
    // user_id → users.id
    { regex: /^(\w+)_id$/, targetTable: '$1s' },
    // customer_fk → customers.id
    { regex: /^(\w+)_fk$/, targetTable: '$1s' },
    // order_item_id → order_items.id
    { regex: /^(\w+)_(\w+)_id$/, targetTable: '$1_$2s' },
  ];
  // Match columns against patterns, find corresponding tables
}
```

### Phase 7 Extensions: Enhanced Schema Insights

These features extend the base ER diagram with actionable insights:

#### Query Path Visualization

Highlight tables and joins used by the current query directly on the ER diagram:

```
User runs: "Show orders with customer names"
    │
    ▼
ER Diagram highlights:
    ┌─────────┐         ┌───────────┐
    │ orders  │─────────│ customers │
    │ (USED)  │  JOIN   │  (USED)   │
    └─────────┘         └───────────┘
         │
    other tables remain dimmed
```

#### Table Statistics Overlay

Show live statistics on table nodes:

```
┌─────────────────────────┐
│ 📊 orders               │
├─────────────────────────┤
│ Rows: 15,432           │
│ Size: 2.3 MB           │
│ Last query: 2 min ago  │
├─────────────────────────┤
│ id (PK)                │
│ customer_id (FK)       │
│ order_date             │
│ total                  │
└─────────────────────────┘
```

#### Schema Health Indicators

Visual warnings for schema issues:

| Indicator | Meaning | Icon |
|-----------|---------|------|
| 🔴 No Primary Key | Table lacks PK constraint | Red dot |
| 🟡 Orphan FK | FK references missing table | Yellow warning |
| 🟠 Circular Reference | A→B→C→A cycle detected | Orange cycle |
| ⚪ Unused Table | No FK references to/from | Gray badge |
| 🔵 High Cardinality | >1M rows (performance note) | Blue info |

#### Diagram Annotations

Allow users to add notes directly on the diagram:

- **Sticky notes**: Attach to tables or relationships
- **Grouping boxes**: Draw regions around related tables
- **Custom labels**: Add business context ("Legacy - Do Not Use")
- **Persistence**: Save annotations per connection

### New Files for Phase 7 Extensions

| File | Purpose | Est. Lines |
|------|---------|------------|
| `frontend/src/components/schema/QueryPathOverlay.tsx` | Highlights query tables on diagram | ~150 |
| `frontend/src/components/schema/TableStatsNode.tsx` | Extended table node with statistics | ~180 |
| `frontend/src/components/schema/HealthIndicators.tsx` | Schema health warning badges | ~120 |
| `frontend/src/components/schema/DiagramAnnotations.tsx` | Sticky notes and annotations | ~200 |
| `frontend/src/utils/schemaHealthAnalyzer.ts` | Detect schema issues | ~150 |
| `frontend/src/hooks/useQueryPath.ts` | Track which tables current query uses | ~80 |
| `src/api/endpoints/table_stats.py` | Backend for table statistics | ~100 |

**Phase 7 Extensions Subtotal: ~980 lines**

---

## Phase 11: Data Lineage & Impact Analysis (FUTURE)

> **Status**: Planned | Estimated: ~2,200 lines | Priority: P2
> **Prerequisite**: Phase 7 (ER Diagrams) must be complete

### Purpose

Visualize how data flows through queries and transformations, enabling impact analysis before schema changes.

### Features

1. **Query Lineage Graph**
   - Parse SQL to extract source tables → transformations → result columns
   - Visualize data flow as a directed graph
   - Show JOIN paths and aggregation points

2. **Column-Level Lineage**
   - Track individual columns through SELECT, JOIN, GROUP BY
   - Show which source columns contribute to each result column
   - Detect column transformations (CONCAT, SUM, CASE, etc.)

3. **Impact Analysis**
   - "What breaks if I drop this column?" - show affected queries
   - "What uses this table?" - list all queries referencing it
   - Preview impact before schema migrations

4. **Query Pattern Analytics**
   - Heatmap of table usage frequency
   - Most common JOIN patterns
   - Identify performance bottlenecks (frequently joined large tables)

### Architecture

```
User asks: "What happens if I rename orders.total to orders.amount?"
    │
    ▼
ImpactAnalyzer
    │
    ├──► Query history scan (existing query_history table)
    │              │
    │              ▼
    │    Found 47 queries using orders.total
    │
    ├──► Parse each query for column references
    │              │
    │              ▼
    │    SELECT o.total FROM orders o...
    │    SELECT SUM(total) FROM orders...
    │
    └──► Generate Impact Report
               │
               ▼
         {
           affected_queries: 47,
           query_types: { select: 42, aggregate: 5 },
           sample_queries: [...],
           risk_level: 'high'
         }
```

### New Files

| File | Purpose | Est. Lines |
|------|---------|------------|
| `frontend/src/components/lineage/LineageGraph.tsx` | Main lineage visualization | ~300 |
| `frontend/src/components/lineage/ColumnLineage.tsx` | Column-level tracing UI | ~250 |
| `frontend/src/components/lineage/ImpactAnalysisPanel.tsx` | Impact preview panel | ~200 |
| `frontend/src/components/lineage/QueryPatternHeatmap.tsx` | Usage frequency heatmap | ~180 |
| `frontend/src/utils/sqlLineageParser.ts` | Parse SQL for lineage extraction | ~350 |
| `frontend/src/utils/impactAnalyzer.ts` | Calculate change impact | ~250 |
| `frontend/src/hooks/useLineage.ts` | Lineage state management | ~120 |
| `src/api/endpoints/lineage.py` | Backend lineage API | ~200 |
| `src/core/sql_parser.py` | SQL parsing for column extraction | ~250 |
| `frontend/tests/Lineage.test.tsx` | Test suite | ~300 |

**Phase 11 Subtotal: ~2,400 lines**

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Lineage View                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐      ┌──────────┐      ┌──────────────┐     │
│   │ customers│──┐   │  orders  │──┐   │    Result    │     │
│   │          │  │   │          │  │   │              │     │
│   │ • id     │  └──►│ • cust_id│  └──►│ • cust_name  │     │
│   │ • name ──┼─────►│ • total ─┼─────►│ • order_total│     │
│   │ • email  │      │ • date   │      │ • order_date │     │
│   └──────────┘      └──────────┘      └──────────────┘     │
│                                                              │
│   Legend: ──► Column flows to result                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies

```json
{
  "sql-parser-cst": "^0.25.0"
}
```

---

## Detailed Task Checklist

### Phase 8: Chart Intelligence (COMPLETE)

#### 8.1 Natural Language Chart Requests
- [x] Create `chartIntentParser.ts` with keyword matching for chart types
- [x] Add regex patterns for "bar chart", "pie chart", "line graph", "scatter plot"
- [x] Handle variations: "show as bar", "create a graph", "visualize as pie"
- [x] Add `preferred_chart_type` to `QueryRequest` interface in `api.ts`
- [x] Update `QueryInput.tsx` to parse chart intent before submit
- [x] Update `ChatInterface.tsx` to pass preference to API
- [x] Add `preferred_chart_type` field to backend `QueryRequest` schema
- [x] Pass preference through `query.py` response
- [x] Update `QueryResults.tsx` to auto-select chart type from response
- [x] Auto-switch to chart view when chart type is specified

#### 8.2 Core Detection Engine
- [x] Create `chartIntelligence.ts` with `analyzeData()` main function
- [x] Create `timeSeriesDetector.ts` with periodic pattern detection
- [x] Create `hierarchyDetector.ts` with parent-child detection
- [x] Create `geoDetector.ts` with lat/lon and code detection
- [x] Create `trendLineCalculator.ts` with linear regression

#### 8.3 Enhanced ChartRecommendation Type
- [x] Update `ChartRecommendation` interface with alternatives, nlExplanation
- [x] Modify `detectChartType()` to use intelligence engine
- [x] Add grouping detection (stacked, grouped)

#### 8.4 Visual Components
- [x] Create `ChartRecommendations.tsx` panel (integrated into ChartInfoBadge)
- [x] Create `OutlierMarkers.tsx` overlay
- [x] Create `TrendLine.tsx` overlay
- [ ] Create `ConfidenceInterval.tsx` overlay (DEFERRED)
- [x] Integrate overlays into ScatterChartView, LineChartView

#### 8.5 Testing
- [x] Write tests for pattern detection (36 tests)
- [x] Test NL recommendation generation (35 tests)
- [x] Test trend line calculations

#### 8.6 Bug Fixes
- [x] Fix column selection when chart type is overridden (Dec 26, 2025)
- [x] Export `selectColumnsForChart()` for override recalculation

---

### Phase 10: Advanced Chart Types (COMPLETE)

#### 10.1 Hierarchical Charts
- [x] Create `TreemapView.tsx` following BarChartView pattern
- [x] Create `SunburstView.tsx` with drill-down support
- [ ] Create `SankeyView.tsx` for flow data (DEFERRED - requires d3-sankey)
- [x] Create `hierarchicalChartUtils.ts` for data preparation

#### 10.2 Statistical Charts
- [x] Create `BoxPlotView.tsx` with quartile calculations
- [x] Create `HistogramView.tsx` with binning logic
- [ ] Create `ViolinPlotView.tsx` for distribution shape (DEFERRED)
- [ ] Create `BubbleChartView.tsx` for 3-variable scatter (DEFERRED)
- [x] Create `statisticalChartUtils.ts` for calculations

#### 10.3 Time-Series Charts
- [x] Create `AreaChartView.tsx` with stacking
- [ ] Create `SparklineView.tsx` for inline trends (DEFERRED)

#### 10.4 Integration
- [x] Extend `ChartType` in chartUtils.ts (5 → 11 types)
- [x] Add rendering cases in ChartVisualization.tsx
- [x] Add new types to ChartToggle dropdown
- [x] Update detection to recommend new types

#### 10.5 Testing
- [x] Write tests for each new chart (53 tests total)
- [x] Test data preparation utilities

---

### Phase 7: ER Diagram Generator (NEXT)

#### 7.1 Backend
- [ ] Create `er_diagram.py` endpoint
- [ ] Add relationship inference logic
- [ ] Register router in main app

#### 7.2 Frontend Core
- [ ] Create `ERDiagram.tsx` main container
- [ ] Create `TableNode.tsx` custom node
- [ ] Create `RelationshipEdge.tsx` custom edge
- [ ] Create `useERDiagram.ts` hook

#### 7.3 Utilities
- [ ] Create `erDiagramUtils.ts` with layout algorithms
- [ ] Create `relationshipInference.ts` for naming convention inference

#### 7.4 UI Components
- [ ] Create `ERDiagramControls.tsx` toolbar
- [ ] Create `ERDiagramSearch.tsx` filter
- [ ] Add "Schema" tab to App.tsx

#### 7.5 Features
- [ ] Implement auto-layout (Dagre)
- [ ] Add zoom/pan controls
- [ ] Add PNG/SVG export
- [ ] Add multi-database color coding

#### 7.6 Testing
- [ ] Write ER diagram tests (15+ tests)
- [ ] Test relationship inference
- [ ] Test layout algorithm

#### 7.7 Query Path Visualization (Extension)
- [ ] Create `QueryPathOverlay.tsx` component
- [ ] Parse current query for table references
- [ ] Highlight used tables on ER diagram
- [ ] Animate JOIN edges
- [ ] Dim unused tables

#### 7.8 Table Statistics Overlay (Extension)
- [ ] Create `TableStatsNode.tsx` extended node
- [ ] Create `table_stats.py` backend endpoint
- [ ] Fetch row counts from database
- [ ] Display size and last query time
- [ ] Add toggle to show/hide stats

#### 7.9 Schema Health Indicators (Extension)
- [ ] Create `schemaHealthAnalyzer.ts` utility
- [ ] Create `HealthIndicators.tsx` component
- [ ] Detect missing primary keys
- [ ] Detect orphaned foreign keys
- [ ] Detect circular references
- [ ] Add health summary panel

#### 7.10 Diagram Annotations (Extension)
- [ ] Create `DiagramAnnotations.tsx` component
- [ ] Implement sticky note creation
- [ ] Implement grouping boxes
- [ ] Save annotations to localStorage/backend
- [ ] Export annotations with diagram

---

### Phase 11: Data Lineage & Impact Analysis (FUTURE)

#### 11.1 Query Lineage Graph
- [ ] Create `LineageGraph.tsx` main component
- [ ] Create `sqlLineageParser.ts` for SQL parsing
- [ ] Extract source tables and result columns
- [ ] Visualize as directed graph
- [ ] Show JOIN paths and aggregations

#### 11.2 Column-Level Lineage
- [ ] Create `ColumnLineage.tsx` component
- [ ] Track columns through transformations
- [ ] Detect column operations (SUM, CONCAT, CASE)
- [ ] Show source → result column mappings

#### 11.3 Impact Analysis
- [ ] Create `ImpactAnalysisPanel.tsx` component
- [ ] Create `impactAnalyzer.ts` utility
- [ ] Create `lineage.py` backend endpoint
- [ ] Query history scanning for column usage
- [ ] Generate impact reports with risk levels

#### 11.4 Query Pattern Analytics
- [ ] Create `QueryPatternHeatmap.tsx` component
- [ ] Track table usage frequency from history
- [ ] Identify common JOIN patterns
- [ ] Highlight performance bottlenecks

#### 11.5 Integration
- [ ] Add "Lineage" tab to App.tsx
- [ ] Connect to existing query history
- [ ] Add "Impact Analysis" button to Schema tab

#### 11.6 Testing
- [ ] Write lineage parser tests (20+ tests)
- [ ] Test impact analysis calculations
- [ ] Test UI components

---

## Test Strategy

Following existing Vitest patterns with component mocking:

```typescript
// Mock new chart components
vi.mock('recharts', () => ({
  // Existing...
  Treemap: ({ children }) => <div data-testid="treemap">{children}</div>,
  Sankey: ({ children }) => <div data-testid="sankey">{children}</div>,
}));

// Mock reactflow for Phase 7
vi.mock('reactflow', () => ({
  ReactFlow: ({ children }) => <div data-testid="react-flow">{children}</div>,
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
}));
```

### Test Categories

| Phase | Category | Count | Status |
|-------|----------|-------|--------|
| 8 | Pattern detection | 36 | ✅ Complete |
| 8 | NL recommendations | 35 | ✅ Complete |
| 10 | Chart rendering | 53 | ✅ Complete |
| 7 | ER diagram core | 15+ | Planned |
| 7 | Relationship inference | 5+ | Planned |
| 7 | Extensions (stats, health) | 10+ | Planned |
| 11 | Lineage parser | 20+ | Future |
| 11 | Impact analysis | 10+ | Future |
| 11 | UI components | 10+ | Future |

---

## Documentation Updates

### New Files
- [ ] `docs/ER_DIAGRAM_GUIDE.md` - User guide for ER diagrams

### Updates to Existing
- [ ] `docs/ADVANCED_VISUALIZATION_GUIDE.md` - Add Phase 7/8/10 sections
- [ ] `docs/MULTI_DB_VISUALIZATION_PLAN.md` - Mark phases as complete when done
- [ ] `CLAUDE.md` - Add new component locations

---

## Summary

| Phase | Feature | Status | New Files | New Lines | Tests |
|-------|---------|--------|-----------|-----------|-------|
| 8 | Chart Intelligence + NL Requests | **COMPLETE** | 8 | ~1,660 | 71 |
| 10 | Advanced Charts | **COMPLETE** | 7 | ~1,650 | 53 |
| 7 | ER Diagrams (Core) | Planned | 10 | ~1,600 | 15+ |
| 7 | ER Diagrams (Extensions) | Planned | 7 | ~980 | 10+ |
| 11 | Data Lineage & Impact | Future | 10 | ~2,400 | 40+ |
| **Total** | | | **42** | **~8,290** | **189+** |

---

## Priority Matrix

| Phase | Feature | Impact | Effort | Status |
|-------|---------|--------|--------|--------|
| 8 | Chart Intelligence | High | Medium | **COMPLETE** |
| 10 | Advanced Charts | Medium | Medium | **COMPLETE** |
| 7 | ER Diagrams (Core) | High | Medium | **NEXT** |
| 7 | ER Diagrams (Extensions) | Medium | Low | **NEXT** |
| 11 | Data Lineage | High | High | **FUTURE** |

---

## Next Steps

### Phase 7: ER Diagram Generator (NEXT)

1. **Core Implementation** (~1,600 lines)
   - Install dependencies: `reactflow`, `dagre`
   - Create backend endpoint for enhanced schema
   - Build React Flow components (TableNode, RelationshipEdge)
   - Implement auto-layout and export

2. **Extensions** (~980 lines)
   - Query Path Visualization - highlight tables used by queries
   - Table Statistics Overlay - show row counts, size
   - Schema Health Indicators - warnings for missing PKs, orphan FKs
   - Diagram Annotations - sticky notes, grouping

### Phase 11: Data Lineage (FUTURE)

After Phase 7 is complete:
- Query lineage graph visualization
- Column-level lineage tracking
- Impact analysis for schema changes
- Query pattern analytics and heatmaps

### Deferred Chart Items (Lower Priority)
- SankeyView.tsx (requires d3-sankey)
- ViolinPlotView.tsx
- BubbleChartView.tsx
- SparklineView.tsx
- ConfidenceInterval.tsx

---

## Related Documentation

- [Multi-DB Visualization Plan](MULTI_DB_VISUALIZATION_PLAN.md) - Phases 1-6 complete
- [Advanced Visualization Guide](ADVANCED_VISUALIZATION_GUIDE.md) - Current feature docs
- [PR Review: Phase 8 & 10](PR_REVIEW_PHASE_8_10.md) - Detailed review and fixes
- [Future Plans](FUTURE_PLANS.md) - Overall roadmap

---

**Last Updated**: December 26, 2025
