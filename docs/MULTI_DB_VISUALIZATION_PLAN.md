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
- [ ] Add imports for ChartVisualization, ChartToggle, ExportDropdown, detectChartType
- [ ] Add ViewMode type import from ChartToggle
- [ ] Add useMemo import if not present
- [ ] Add state: `viewModes` - Record<number, ViewMode> for per-database view modes
- [ ] Add memoized `chartRecommendations` - detectChartType for each database
- [ ] Add `showCrossDbChart` state for collapsible comparison section

#### 1.2 Per-Database Header Controls
- [ ] Add ChartToggle to each database's expanded section header
- [ ] Add ExportDropdown next to ChartToggle
- [ ] Wire up onModeChange to update viewModes state
- [ ] Pass correct chartAvailable and chartType to ChartToggle

#### 1.3 Conditional Chart/Table Rendering
- [ ] Replace hardcoded table (lines 282-310) with conditional
- [ ] Render ChartVisualization when viewMode is 'chart' and chart available
- [ ] Render table when viewMode is 'table' or no chart available
- [ ] Pass result.results and result.result_analysis?.statistics to ChartVisualization

#### 1.4 Verify Phase 1
- [ ] Test toggle works independently for each database
- [ ] Test chart detection works with various data types
- [ ] Test export works for individual databases
- [ ] Verify no TypeScript errors

---

### Phase 2: Combined Export

#### 2.1 Add Export Utilities
- [ ] Add `exportCombinedCSV()` to exportUtils.ts - merges all DBs with source column
- [ ] Add `exportSeparateFiles()` to exportUtils.ts - creates ZIP with jszip
- [ ] Add jszip dependency if needed: `npm install jszip`

#### 2.2 Create CombinedExportDropdown.tsx
- [ ] Create component file in frontend/src/components/visualization/
- [ ] Add dropdown button with "Export All" label
- [ ] Add dropdown menu with radio options: "Stacked CSV" (default), "Separate Files"
- [ ] Add format selection state
- [ ] Add CSV export handler (stacked format)
- [ ] Add JSON export handler (stacked format)
- [ ] Add ZIP export handler (separate files)
- [ ] Show total row count from all databases
- [ ] Handle empty/failed results gracefully

#### 2.3 Integrate Combined Export
- [ ] Add CombinedExportDropdown to MultiDatabaseResults summary header
- [ ] Pass results array and question prop
- [ ] Position next to existing summary stats

#### 2.4 Verify Phase 2
- [ ] Test stacked CSV export includes database_name column
- [ ] Test separate files creates valid ZIP
- [ ] Test handles mixed success/failure results
- [ ] Test with empty results

---

### Phase 3: Cross-Database Comparison Chart

#### 3.1 Create crossDbUtils.ts
- [ ] Create file in frontend/src/utils/
- [ ] Add `findCommonNumericColumns()` - finds columns present in all DBs
- [ ] Add `aggregateByDatabase()` - sums/averages numeric columns per DB
- [ ] Add `detectCrossDbComparison()` - returns config or null
- [ ] Add CrossDbChartConfig type definition

#### 3.2 Create CrossDatabaseChart.tsx
- [ ] Create component file in frontend/src/components/visualization/
- [ ] Accept results and config props
- [ ] Use Recharts BarChart with grouped bars
- [ ] Color-code bars by database (use existing color palette)
- [ ] Add legend showing database names
- [ ] Add axis labels for metric names
- [ ] Handle single database gracefully (no comparison needed)

#### 3.3 Integrate Cross-Database Chart
- [ ] Add crossDbConfig memoized detection to MultiDatabaseResults
- [ ] Add showCrossDbChart toggle state (default: true if config exists)
- [ ] Add collapsible section after Combined Analysis
- [ ] Add expand/collapse button with chevron icon
- [ ] Render CrossDatabaseChart when expanded and config exists

#### 3.4 Verify Phase 3
- [ ] Test detection finds common numeric columns
- [ ] Test chart renders with multiple databases
- [ ] Test collapsible toggle works
- [ ] Test graceful handling when no common columns

---

### Phase 4: Testing

#### 4.1 Create MultiDatabaseVisualization.test.tsx
- [ ] Test per-database toggle independence
- [ ] Test chart detection per database
- [ ] Test ExportDropdown renders for each database
- [ ] Test view mode state management
- [ ] Test chart/table conditional rendering

#### 4.2 Create CombinedExportDropdown.test.tsx
- [ ] Test dropdown opens/closes
- [ ] Test format selection
- [ ] Test stacked export generates correct data
- [ ] Test handles empty results
- [ ] Test row count display

#### 4.3 Create CrossDatabaseChart.test.tsx
- [ ] Test common column detection
- [ ] Test aggregation logic
- [ ] Test chart renders with mock data
- [ ] Test handles no common columns
- [ ] Test collapsible state

#### 4.4 Run All Tests
- [ ] Run `npm test` and verify all pass
- [ ] Fix any failing tests
- [ ] Verify build succeeds: `npm run build`

---

### Phase 5: Documentation & Cleanup

#### 5.1 Update Documentation
- [ ] Update ADVANCED_VISUALIZATION_GUIDE.md with multi-database section
- [ ] Add examples for cross-database comparison
- [ ] Document combined export formats

#### 5.2 Code Cleanup
- [ ] Remove any debug console.logs
- [ ] Ensure consistent code style
- [ ] Add JSDoc comments to new utility functions

#### 5.3 Final Verification
- [ ] Manual test with real multi-database query
- [ ] Verify all features work end-to-end
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
