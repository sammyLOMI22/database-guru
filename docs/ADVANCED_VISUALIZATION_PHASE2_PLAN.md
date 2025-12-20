# Advanced Visualization Phase 2 Implementation Plan

**Feature Branch**: Advanced-Visualization-and-Dashboards
**Status**: Planned
**Created**: December 20, 2025
**Phases**: 7 (ER Diagrams), 8 (Chart Intelligence), 10 (Advanced Charts)
**Estimated New Code**: ~5,700 lines

---

## Executive Summary

This plan covers three major visualization enhancements for Database Guru:

- **Phase 7**: ER Diagram Generator - Interactive entity-relationship diagrams
- **Phase 8**: Improved Chart Intelligence - Smarter pattern detection and recommendations
- **Phase 10**: Advanced Chart Types - Specialized charts for hierarchical, statistical, and time-series data

All phases build on the existing visualization architecture (Phases 1-6 complete).

---

## Implementation Order

```
Phase 8: Chart Intelligence (Foundation)
    └──► Phase 10: Advanced Charts (Uses Phase 8 detection)

Phase 7: ER Diagram Generator (Independent, can parallel Phase 10)
```

**Rationale**: Phase 8's enhanced detection logic is foundational for Phase 10's advanced chart types. Phase 7 is independent and can be implemented in parallel with later stages.

---

## Phase 8: Improved Chart Intelligence

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

## Phase 10: Advanced Chart Types

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

## Phase 7: ER Diagram Generator

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

---

## Detailed Task Checklist

### Phase 8: Chart Intelligence

#### 8.1 Natural Language Chart Requests
- [ ] Create `chartIntentParser.ts` with keyword matching for chart types
- [ ] Add regex patterns for "bar chart", "pie chart", "line graph", "scatter plot"
- [ ] Handle variations: "show as bar", "create a graph", "visualize as pie"
- [ ] Add `preferred_chart_type` to `QueryRequest` interface in `api.ts`
- [ ] Update `QueryInput.tsx` to parse chart intent before submit
- [ ] Update `ChatInterface.tsx` to pass preference to API
- [ ] Add `preferred_chart_type` field to backend `QueryRequest` schema
- [ ] Pass preference through `query.py` response
- [ ] Update `QueryResults.tsx` to auto-select chart type from response
- [ ] Auto-switch to chart view when chart type is specified

#### 8.2 Core Detection Engine
- [ ] Create `chartIntelligence.ts` with `analyzeData()` main function
- [ ] Create `timeSeriesDetector.ts` with periodic pattern detection
- [ ] Create `hierarchyDetector.ts` with parent-child detection
- [ ] Create `geoDetector.ts` with lat/lon and code detection
- [ ] Create `trendLineCalculator.ts` with linear regression

#### 8.3 Enhanced ChartRecommendation Type
- [ ] Update `ChartRecommendation` interface with alternatives, nlExplanation
- [ ] Modify `detectChartType()` to use intelligence engine
- [ ] Add grouping detection (stacked, grouped)

#### 8.3 Visual Components
- [ ] Create `ChartRecommendations.tsx` panel
- [ ] Create `OutlierMarkers.tsx` overlay
- [ ] Create `TrendLine.tsx` overlay
- [ ] Create `ConfidenceInterval.tsx` overlay
- [ ] Integrate overlays into ScatterChartView, LineChartView

#### 8.4 Testing
- [ ] Write tests for pattern detection (20+ tests)
- [ ] Test NL recommendation generation
- [ ] Test trend line calculations

---

### Phase 10: Advanced Chart Types

#### 10.1 Hierarchical Charts
- [ ] Create `TreemapView.tsx` following BarChartView pattern
- [ ] Create `SunburstView.tsx` with drill-down support
- [ ] Create `SankeyView.tsx` for flow data
- [ ] Create `hierarchicalChartUtils.ts` for data preparation

#### 10.2 Statistical Charts
- [ ] Create `BoxPlotView.tsx` with quartile calculations
- [ ] Create `HistogramView.tsx` with binning logic
- [ ] Create `ViolinPlotView.tsx` for distribution shape
- [ ] Create `BubbleChartView.tsx` for 3-variable scatter
- [ ] Create `statisticalChartUtils.ts` for calculations

#### 10.3 Time-Series Charts
- [ ] Create `AreaChartView.tsx` with stacking
- [ ] Create `SparklineView.tsx` for inline trends

#### 10.4 Integration
- [ ] Extend `ChartType` in chartUtils.ts
- [ ] Add rendering cases in ChartVisualization.tsx
- [ ] Add new types to ChartToggle dropdown
- [ ] Update detection to recommend new types

#### 10.5 Testing
- [ ] Write tests for each new chart (25+ tests)
- [ ] Test data preparation utilities

---

### Phase 7: ER Diagram Generator

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

| Phase | Category | Count |
|-------|----------|-------|
| 8 | Pattern detection | 10+ |
| 8 | Trend/outlier calculations | 5+ |
| 8 | NL recommendations | 5+ |
| 10 | Chart rendering (9 charts × 2) | 18+ |
| 10 | Data preparation | 7+ |
| 7 | ER diagram rendering | 8+ |
| 7 | Relationship inference | 5+ |
| 7 | Layout/export | 5+ |

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

| Phase | Feature | New Files | New Lines | Dependencies |
|-------|---------|-----------|-----------|--------------|
| 8 | Chart Intelligence + NL Requests | 12 | ~2,030 | simple-statistics |
| 10 | Advanced Charts | 12 | ~2,310 | d3-hierarchy |
| 7 | ER Diagrams | 10 | ~1,600 | reactflow, dagre |
| **Total** | | **34** | **~5,940** | **4 packages** |

---

## Priority Matrix

| Phase | Feature | Impact | Effort | Priority |
|-------|---------|--------|--------|----------|
| 8 | Chart Intelligence | High | Medium | **P1** |
| 10 | Advanced Charts | Medium | Medium | **P1** |
| 7 | ER Diagrams | High | Medium | **P1** |

---

## Related Documentation

- [Multi-DB Visualization Plan](MULTI_DB_VISUALIZATION_PLAN.md) - Phases 1-6 complete
- [Advanced Visualization Guide](ADVANCED_VISUALIZATION_GUIDE.md) - Current feature docs
- [Future Plans](FUTURE_PLANS.md) - Overall roadmap

---

**Last Updated**: December 20, 2025
