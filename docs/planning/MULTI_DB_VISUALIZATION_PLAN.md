# Multi-Database Visualization Implementation Plan

**Feature Branch**: Advanced-Visualization-and-Dashboards
**Date**: December 18, 2025

---

## Overview

Add visualization capabilities to multi-database query results, replicating the pattern from single-query `QueryResults.tsx` to `MultiDatabaseResults.tsx`.

## User Decisions

- **View Mode**: Per-database toggles (each database has independent table/chart toggle)
- **Combined Export**: User chooses between stacked CSV (with source column) or separate files - default: stacked
- **Cross-DB Chart Position**: After Combined Analysis, collapsible section

## Features to Implement

### 1. Per-Database Charts
Add ChartToggle and ChartVisualization to each expanded database result section.

### 2. Export Per Database
Add ExportDropdown for each database's results with connection metadata.

### 3. Combined Export
Add ability to export all databases' results together with format choice:
- **Stacked CSV** (default): All rows merged with `database_name` source column
- **Separate files**: Download as ZIP with one file per database

### 4. Cross-Database Comparison Chart
New collapsible visualization comparing the same metric across multiple databases.

---

## Implementation Details

### File Changes

#### `frontend/src/components/MultiDatabaseResults.tsx`

**Current State**: Hardcoded table view (lines 282-310), no visualization.

**Changes**:

1. **Add imports**:
```typescript
import { ChartVisualization } from './visualization/ChartVisualization';
import { ChartToggle, ViewMode } from './visualization/ChartToggle';
import { ExportDropdown } from './visualization/ExportDropdown';
import { detectChartType } from '../utils/chartUtils';
```

2. **Add state for per-database view modes**:
```typescript
const [viewModes, setViewModes] = useState<Record<number, ViewMode>>(() =>
  Object.fromEntries(results.map(r => [r.connection_id, 'table']))
);
```

3. **Add chart detection per database** (memoized):
```typescript
const chartRecommendations = useMemo(() => {
  return Object.fromEntries(
    results.map(r => [
      r.connection_id,
      r.results?.length > 0
        ? detectChartType(r.results, r.result_analysis?.statistics || {})
        : { chartType: 'table', confidence: 0, xColumn: null, yColumn: null, reason: 'No data' }
    ])
  );
}, [results]);
```

4. **Add header controls for each database** (after line 231):
```typescript
<div className="flex items-center gap-2">
  <ChartToggle
    mode={viewModes[result.connection_id]}
    onModeChange={(mode) => setViewModes(prev => ({ ...prev, [result.connection_id]: mode }))}
    chartAvailable={chartRecommendations[result.connection_id].chartType !== 'table'}
    chartType={chartRecommendations[result.connection_id].chartType}
  />
  <ExportDropdown
    data={result.results || []}
    sql={result.sql}
    connectionName={result.connection_name}
    databaseType={result.database_type}
  />
</div>
```

5. **Replace hardcoded table with conditional rendering** (lines 275-320):
```typescript
{viewModes[result.connection_id] === 'chart' &&
 chartRecommendations[result.connection_id].chartType !== 'table' ? (
  <ChartVisualization
    data={result.results}
    statistics={result.result_analysis?.statistics || {}}
    height={300}
    showLegend={true}
    animate={true}
  />
) : (
  <div className="overflow-x-auto">
    <table>...</table>
  </div>
)}
```

---

### Combined Export Feature

**Add new component**: `frontend/src/components/visualization/CombinedExportDropdown.tsx`

Features:
- Dropdown with two export mode options
- **Stacked CSV** (default): Merges all rows with `database_name` column
- **Separate Files**: Creates ZIP with individual CSV/JSON per database
- Radio button selection in dropdown UI

**Location in MultiDatabaseResults**: Summary header area (after line 106)

```typescript
<CombinedExportDropdown
  results={results}
  question={question}
/>
```

---

### Cross-Database Comparison Chart

**Add new component**: `frontend/src/components/visualization/CrossDatabaseChart.tsx`

Purpose: Compare the same metric across multiple databases side-by-side.

**Requirements**:
- Identify common columns across databases
- Show grouped bar chart comparing aggregated values per database
- Color-code by database with legend
- Collapsible section (default: expanded if comparison available)

**Detection Logic**:
```typescript
function detectCrossDbComparison(results: DatabaseQueryResult[]): CrossDbChartConfig | null {
  // Find common numeric columns across all successful results
  // Aggregate (sum/avg) per database for comparison
  // If found, recommend a comparison chart
  // Return null if not comparable (no common numeric columns)
}
```

**UI Location**: After Combined Analysis section, collapsible

```typescript
{crossDbConfig && (
  <div className="border rounded-lg">
    <button onClick={() => setShowCrossDbChart(!showCrossDbChart)}>
      Cross-Database Comparison {showCrossDbChart ? '▼' : '▶'}
    </button>
    {showCrossDbChart && (
      <CrossDatabaseChart results={results} config={crossDbConfig} />
    )}
  </div>
)}
```

---

## Component Tree After Changes

```
MultiDatabaseResults
├── Combined Analysis (ResultSummary)
├── Cross-Database Comparison Chart (NEW)
├── Combined Export Dropdown (NEW)
├── Per-Database Results
│   └── For each database:
│       ├── Header with toggle
│       ├── Per-DB ResultSummary
│       ├── SQL Display
│       ├── ChartToggle + ExportDropdown (NEW)
│       ├── ChartVisualization OR Table (conditional)
│       └── Observability components
└── Expand/Collapse All
```

---

## New Files to Create

1. `frontend/src/components/visualization/CombinedExportDropdown.tsx` (~150 lines)
2. `frontend/src/components/visualization/CrossDatabaseChart.tsx` (~200 lines)
3. `frontend/src/utils/crossDbUtils.ts` (~100 lines) - Cross-database analysis utilities

---

## Files to Modify

1. `frontend/src/components/MultiDatabaseResults.tsx` - Main integration
2. `frontend/src/utils/exportUtils.ts` - Add combined export functions

---

## Test Files to Create

1. `frontend/tests/MultiDatabaseVisualization.test.tsx` (~200 lines)
2. `frontend/tests/CombinedExportDropdown.test.tsx` (~100 lines)
3. `frontend/tests/CrossDatabaseChart.test.tsx` (~150 lines)

---

## Implementation Order

1. **Phase 1**: Per-database charts + export (Features 1 & 2)
   - Modify MultiDatabaseResults.tsx
   - Add ChartToggle, ChartVisualization, ExportDropdown per database
   - Test and verify

2. **Phase 2**: Combined export (Feature 3)
   - Create CombinedExportDropdown component
   - Add to summary header
   - Test merged/separate export modes

3. **Phase 3**: Cross-database comparison (Feature 4)
   - Create crossDbUtils.ts for detection
   - Create CrossDatabaseChart component
   - Integrate into MultiDatabaseResults
   - Test with various data shapes

---

## Detailed Task Checklist

### Phase 1: Per-Database Charts + Export

#### 1.1 Modify MultiDatabaseResults.tsx
- [x] Add imports for ChartVisualization, ChartToggle, ExportDropdown, detectChartType
- [x] Add ViewMode type import from ChartToggle
- [x] Add useMemo import if not present
- [x] Add state: `viewModes` - Record<number, ViewMode> for per-database view modes
- [x] Add memoized `chartRecommendations` - detectChartType for each database
- [x] Add `showCrossDbChart` state for collapsible comparison section

#### 1.2 Per-Database Header Controls
- [x] Add ChartToggle to each database's expanded section header
- [x] Add ExportDropdown next to ChartToggle
- [x] Wire up onModeChange to update viewModes state
- [x] Pass correct chartAvailable and chartType to ChartToggle

#### 1.3 Conditional Chart/Table Rendering
- [x] Replace hardcoded table (lines 282-310) with conditional
- [x] Render ChartVisualization when viewMode is 'chart' and chart available
- [x] Render table when viewMode is 'table' or no chart available
- [x] Pass result.results and result.result_analysis?.statistics to ChartVisualization

#### 1.4 Verify Phase 1
- [x] Test toggle works independently for each database
- [x] Test chart detection works with various data types
- [x] Test export works for individual databases
- [x] Verify no TypeScript errors

---

### Phase 2: Combined Export

#### 2.1 Add Export Utilities
- [x] Add `exportCombinedCSV()` to exportUtils.ts - merges all DBs with source column
- [x] Add `exportSeparateFiles()` to exportUtils.ts - creates ZIP with jszip
- [x] Add jszip dependency if needed: `npm install jszip`

#### 2.2 Create CombinedExportDropdown.tsx
- [x] Create component file in frontend/src/components/visualization/
- [x] Add dropdown button with "Export All" label
- [x] Add dropdown menu with radio options: "Stacked CSV" (default), "Separate Files"
- [x] Add format selection state
- [x] Add CSV export handler (stacked format)
- [x] Add JSON export handler (stacked format)
- [x] Add ZIP export handler (separate files)
- [x] Show total row count from all databases
- [x] Handle empty/failed results gracefully

#### 2.3 Integrate Combined Export
- [x] Add CombinedExportDropdown to MultiDatabaseResults summary header
- [x] Pass results array and question prop
- [x] Position next to existing summary stats

#### 2.4 Verify Phase 2
- [x] Test stacked CSV export includes database_name column
- [x] Test separate files creates valid ZIP
- [x] Test handles mixed success/failure results
- [x] Test with empty results

---

### Phase 3: Cross-Database Comparison Chart

#### 3.1 Create crossDbUtils.ts
- [x] Create file in frontend/src/utils/
- [x] Add `findCommonNumericColumns()` - finds columns present in all DBs
- [x] Add `aggregateByDatabase()` - sums/averages numeric columns per DB
- [x] Add `detectCrossDbComparison()` - returns config or null
- [x] Add CrossDbChartConfig type definition

#### 3.2 Create CrossDatabaseChart.tsx
- [x] Create component file in frontend/src/components/visualization/
- [x] Accept results and config props
- [x] Use Recharts BarChart with grouped bars
- [x] Color-code bars by database (use existing color palette)
- [x] Add legend showing database names
- [x] Add axis labels for metric names
- [x] Handle single database gracefully (no comparison needed)

#### 3.3 Integrate Cross-Database Chart
- [x] Add crossDbConfig memoized detection to MultiDatabaseResults
- [x] Add showCrossDbChart toggle state (default: true if config exists)
- [x] Add collapsible section after Combined Analysis
- [x] Add expand/collapse button with chevron icon
- [x] Render CrossDatabaseChart when expanded and config exists

#### 3.4 Verify Phase 3
- [x] Test detection finds common numeric columns
- [x] Test chart renders with multiple databases
- [x] Test collapsible toggle works
- [x] Test graceful handling when no common columns

---

### Phase 4: Testing

#### 4.1 Create MultiDatabaseVisualization.test.tsx
- [x] Test per-database toggle independence
- [x] Test chart detection per database
- [x] Test ExportDropdown renders for each database
- [x] Test view mode state management
- [x] Test chart/table conditional rendering

#### 4.2 Create CombinedExportDropdown.test.tsx
- [x] Test dropdown opens/closes
- [x] Test format selection
- [x] Test stacked export generates correct data
- [x] Test handles empty results
- [x] Test row count display

#### 4.3 Create CrossDatabaseChart.test.tsx
- [x] Test common column detection
- [x] Test aggregation logic
- [x] Test chart renders with mock data
- [x] Test handles no common columns
- [x] Test collapsible state

#### 4.4 Run All Tests
- [x] Run `npm test` and verify all pass
- [x] Fix any failing tests
- [x] Verify build succeeds: `npm run build`

---

### Phase 5: Documentation & Cleanup

#### 5.1 Update Documentation
- [x] Update ADVANCED_VISUALIZATION_GUIDE.md with multi-database section
- [x] Add examples for cross-database comparison
- [x] Document combined export formats

#### 5.2 Code Cleanup
- [x] Remove any debug console.logs
- [x] Ensure consistent code style
- [x] Add JSDoc comments to new utility functions

#### 5.3 Final Verification
- [x] Manual test with real multi-database query
- [x] Verify all features work end-to-end
- [ ] Create commit with descriptive message

---

## Dependencies

### Existing (already installed)
- recharts - for charts
- lucide-react - for icons

### New (may need to install)
- jszip - for ZIP file creation (if using separate files export)

```bash
cd frontend && npm install jszip
```

---

## Estimated Effort

| Phase | Feature | Tasks | Effort |
|-------|---------|-------|--------|
| 1 | Per-database charts + export | 12 tasks | 2-3 hours |
| 2 | Combined export | 12 tasks | 1-2 hours |
| 3 | Cross-database comparison | 12 tasks | 2-3 hours |
| 4 | Testing | 12 tasks | 1-2 hours |
| 5 | Documentation & cleanup | 6 tasks | 0.5-1 hour |
| **Total** | | **54 tasks** | **7-11 hours**

---

## Quick Reference - Files Summary

### New Files (3)
| File | Purpose |
|------|---------|
| `frontend/src/components/visualization/CombinedExportDropdown.tsx` | Combined export with format selection |
| `frontend/src/components/visualization/CrossDatabaseChart.tsx` | Cross-database comparison chart |
| `frontend/src/utils/crossDbUtils.ts` | Detection and aggregation utilities |

### Modified Files (2)
| File | Changes |
|------|---------|
| `frontend/src/components/MultiDatabaseResults.tsx` | Add visualization, toggles, exports |
| `frontend/src/utils/exportUtils.ts` | Add combined export functions |

### Test Files (3)
| File | Coverage |
|------|----------|
| `frontend/tests/MultiDatabaseVisualization.test.tsx` | Integration tests |
| `frontend/tests/CombinedExportDropdown.test.tsx` | Export component tests |
| `frontend/tests/CrossDatabaseChart.test.tsx` | Chart component tests |

---

## Phase 6: Chart Type Selector (COMPLETED)

### 6.1 ChartToggle Enhancement
- [x] Add `selectedChartType` and `onChartTypeChange` props
- [x] Add `showChartTypeSelector` prop (default: true)
- [x] Create dropdown menu with chart type options
- [x] Show "(recommended)" label for auto-detected type
- [x] Update icon and label based on selected type
- [x] Close dropdown on outside click

### 6.2 ChartVisualization Enhancement
- [x] Add `overrideChartType` prop
- [x] Use override when provided, otherwise auto-detect
- [x] Update info badge for manually selected charts

### 6.3 QueryResults Integration
- [x] Add `selectedChartType` state
- [x] Wire up ChartToggle with new props
- [x] Pass override to ChartVisualization

### 6.4 MultiDatabaseResults Integration
- [x] Add `selectedChartTypes` state (per-database Record)
- [x] Wire up per-database ChartToggle
- [x] Pass per-database override to ChartVisualization

### 6.5 CrossDatabaseChart Enhancement
- [x] Add auto-detection logic (scatter/pie/bar based on data)
- [x] Add chart type dropdown with 4 options (Bar, Line, Pie, Scatter)
- [x] Add axis selectors for scatter plot
- [x] Implement all 4 chart type renderings
- [x] Update tests with new recharts mocks

---

## Future Improvements Roadmap

### Phase 7: Entity Relationship Diagram Generator

**Priority**: High
**Estimated Effort**: 3-5 days

Generate visual ER diagrams from database schema for connected databases.

#### 7.1 Schema Analysis
- [ ] Extract tables, columns, primary keys from schema
- [ ] Detect foreign key relationships
- [ ] Infer relationships from naming conventions (e.g., `user_id` → `users.id`)
- [ ] Support multiple databases in single diagram

#### 7.2 Diagram Rendering
- [ ] Use react-flow or d3.js for interactive diagrams
- [ ] Display tables as nodes with column lists
- [ ] Show relationships as connecting lines (1:1, 1:N, M:N)
- [ ] Support zoom, pan, and drag positioning
- [ ] Auto-layout algorithm for clean arrangement

#### 7.3 Interactivity
- [ ] Click table to see full column details
- [ ] Highlight related tables on hover
- [ ] Filter by schema/table prefix
- [ ] Search for tables/columns
- [ ] Export diagram as PNG/SVG

#### 7.4 Multi-Database Support
- [ ] Show cross-database relationships (if any)
- [ ] Color-code tables by database
- [ ] Toggle database visibility

---

### Phase 8: Improved Chart Intelligence

**Priority**: High
**Estimated Effort**: 2-3 days

Enhance chart detection and recommendations with smarter analysis.

#### 8.1 Data Pattern Recognition
- [ ] Detect time-series patterns (even without date columns)
- [ ] Identify periodic data (weekly, monthly cycles)
- [ ] Recognize hierarchical data for treemaps
- [ ] Detect geographic data for map visualizations

#### 8.2 Multi-Column Analysis
- [ ] Suggest multiple charts for complex datasets
- [ ] Recommend chart combinations (e.g., bar + line overlay)
- [ ] Detect grouping opportunities (stacked/grouped bars)
- [ ] Identify suitable drill-down hierarchies

#### 8.3 Statistical Intelligence
- [ ] Show outliers with visual markers
- [ ] Add trend lines to scatter/line charts
- [ ] Display confidence intervals where applicable
- [ ] Highlight statistically significant differences

#### 8.4 Natural Language Chart Recommendations
- [ ] "This data shows a strong upward trend - try a line chart"
- [ ] "With 5 categories, a pie chart works well for proportions"
- [ ] "Consider a scatter plot to explore the correlation between X and Y"

---

### Phase 9: Dashboard Builder

**Priority**: Medium
**Estimated Effort**: 5-7 days

Create and save custom dashboards with multiple visualizations.

#### 9.1 Dashboard Layout
- [ ] Drag-and-drop grid layout
- [ ] Resizable chart panels
- [ ] Multiple layout templates (2x2, 3-column, etc.)
- [ ] Responsive design for different screen sizes

#### 9.2 Chart Management
- [ ] Add charts from saved queries
- [ ] Configure chart settings per panel
- [ ] Duplicate/remove charts
- [ ] Reorder panels

#### 9.3 Persistence
- [ ] Save dashboards to database
- [ ] Load saved dashboards
- [ ] Share dashboard links
- [ ] Export dashboard as PDF/image

#### 9.4 Real-time Updates
- [ ] Auto-refresh interval setting
- [ ] Manual refresh button
- [ ] Last updated timestamp
- [ ] Connection status indicator

---

### Phase 10: Advanced Chart Types

**Priority**: Medium
**Estimated Effort**: 3-4 days

Add specialized chart types for specific data patterns.

#### 10.1 Hierarchical Charts
- [ ] Treemap for hierarchical data
- [ ] Sunburst chart for nested categories
- [ ] Sankey diagram for flow data

#### 10.2 Geographic Charts
- [ ] Choropleth maps for regional data
- [ ] Point maps for location data
- [ ] Heat maps for density visualization

#### 10.3 Statistical Charts
- [ ] Box plots for distribution analysis
- [ ] Histogram for frequency distribution
- [ ] Violin plots for density comparison
- [ ] Bubble charts (3-variable scatter)

#### 10.4 Time-Series Enhancements
- [ ] Area charts with stacking
- [ ] Candlestick charts for OHLC data
- [ ] Sparklines for inline trends
- [ ] Gantt charts for timeline data

---

### Phase 11: Chart Annotations & Insights

**Priority**: Low
**Estimated Effort**: 2-3 days

Add interactive annotations and AI-generated insights.

#### 11.1 Manual Annotations
- [ ] Add text notes to specific data points
- [ ] Draw reference lines (targets, thresholds)
- [ ] Highlight date ranges
- [ ] Add callout boxes

#### 11.2 Automated Insights
- [ ] "Peak value on [date]"
- [ ] "23% increase from previous period"
- [ ] "Anomaly detected at [point]"
- [ ] "Category X accounts for 45% of total"

#### 11.3 Comparison Features
- [ ] Period-over-period comparison
- [ ] Benchmark lines from historical data
- [ ] Goal tracking visualization

---

### Phase 12: Export & Sharing Enhancements

**Priority**: Low
**Estimated Effort**: 1-2 days

Improve export options and collaboration features.

#### 12.1 Chart Export
- [ ] Export chart as PNG/SVG/PDF
- [ ] Include/exclude legend option
- [ ] Custom dimensions for export
- [ ] Batch export multiple charts

#### 12.2 Sharing
- [ ] Generate shareable chart links
- [ ] Embed code for external sites
- [ ] Email chart directly
- [ ] Slack/Teams integration

#### 12.3 Scheduling
- [ ] Schedule recurring exports
- [ ] Email reports on schedule
- [ ] Webhook notifications

---

## Implementation Priority Matrix

| Phase | Feature | Impact | Effort | Priority |
|-------|---------|--------|--------|----------|
| 7 | ER Diagram Generator | High | Medium | **P1** |
| 8 | Improved Chart Intelligence | High | Low | **P1** |
| 9 | Dashboard Builder | High | High | **P2** |
| 10 | Advanced Chart Types | Medium | Medium | **P2** |
| 11 | Annotations & Insights | Medium | Low | **P3** |
| 12 | Export & Sharing | Low | Low | **P3** |

---

## Status Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Per-database charts + export | ✅ Complete |
| 2 | Combined export | ✅ Complete |
| 3 | Cross-database comparison | ✅ Complete |
| 4 | Testing | ✅ Complete |
| 5 | Documentation & cleanup | ✅ Complete |
| 6 | Chart type selector | ✅ Complete |
| 7-12 | Future improvements | 📋 Planned |

**Last Updated**: December 19, 2025
