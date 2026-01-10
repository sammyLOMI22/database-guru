# Chart Type Selector - PR Review & Testing Guide

**Feature**: Manual Chart Type Selection
**Branch**: Advanced-Visualization-and-Dashboards
**Date**: December 19, 2025

---

## Summary

This PR adds the ability for users to manually select chart types instead of relying solely on auto-detection. The feature is implemented across three areas:

1. **Single Query Results** - QueryResults.tsx
2. **Multi-Database Per-DB Charts** - MultiDatabaseResults.tsx
3. **Cross-Database Comparison** - CrossDatabaseChart.tsx

---

## Files Changed

### Core Components

| File | Changes |
|------|---------|
| `src/components/visualization/ChartToggle.tsx` | Added chart type dropdown with selector props |
| `src/components/visualization/ChartVisualization.tsx` | Added `overrideChartType` prop support |
| `src/components/visualization/CrossDatabaseChart.tsx` | Added 4 chart types with auto-detection |
| `src/components/QueryResults.tsx` | Wired up chart type selection state |
| `src/components/MultiDatabaseResults.tsx` | Wired up per-database chart type selection |

### Tests Updated

| File | Changes |
|------|---------|
| `tests/CrossDatabaseChart.test.tsx` | Added mocks for new chart components, updated selectors |

### Documentation

| File | Changes |
|------|---------|
| `../guides/ADVANCED_VISUALIZATION_GUIDE.md` | Added section 5 for manual chart type selection |

---

## Code Review Checklist

### ChartToggle.tsx

- [ ] New props are optional and backwards compatible
- [ ] Dropdown closes when clicking outside
- [ ] "(recommended)" label shows for auto-detected type
- [ ] Icon and label update when chart type changes
- [ ] Clicking chart type also switches to chart view mode

### ChartVisualization.tsx

- [ ] `overrideChartType` prop is optional
- [ ] When override is set, info badge shows "Manually selected X chart"
- [ ] Original auto-detection still works when no override

### CrossDatabaseChart.tsx

- [ ] Auto-detection logic is correct:
  - Scatter: 2+ metrics AND 3+ databases
  - Pie: 1 metric AND 2-6 databases
  - Bar: default fallback
- [ ] All 4 chart types render correctly
- [ ] Metric selector shows for bar/line/pie with multiple metrics
- [ ] X/Y axis selectors show for scatter plot
- [ ] Chart type dropdown works independently of other controls

### State Management

- [ ] QueryResults: `selectedChartType` state initialized to null
- [ ] MultiDatabaseResults: `selectedChartTypes` is per-database Record
- [ ] State updates don't cause unnecessary re-renders

---

## Manual Testing Guide

### Prerequisites

1. Start the frontend: `cd frontend && npm run dev`
2. Start the backend: `cd .. && python -m uvicorn src.main:app --reload`
3. Have at least 2 database connections configured

---

### Test 1: Single Query Chart Type Selector

**Steps:**
1. Run a query that returns numeric data (e.g., "Show me sales by region")
2. Click "Chart" to switch to chart view
3. Observe the auto-detected chart type (should show icon + label)
4. Click the dropdown chevron (▼) next to the toggle

**Expected:**
- [ ] Dropdown appears with 4 options: Bar, Line, Pie, Scatter
- [ ] Current chart type is highlighted in blue
- [ ] "(recommended)" label appears next to auto-detected type

**Steps (continued):**
5. Select a different chart type (e.g., Pie)
6. Close and reopen the dropdown

**Expected:**
- [ ] Chart changes to selected type
- [ ] Toggle button shows new icon and label
- [ ] Info badge shows "Manually selected pie chart"
- [ ] Selected type is highlighted, recommended still shows label

---

### Test 2: Multi-Database Per-DB Charts

**Steps:**
1. Run a multi-database query (select 2+ connections)
2. Expand one database result
3. Click "Chart" for that database
4. Click the dropdown chevron (▼)

**Expected:**
- [ ] Dropdown appears with chart type options
- [ ] "(recommended)" shows for auto-detected type

**Steps (continued):**
5. Select a different chart type
6. Expand another database result
7. Check its chart type selector

**Expected:**
- [ ] First database shows selected chart type
- [ ] Second database is independent (still shows default)
- [ ] Each database can have different chart type

---

### Test 3: Cross-Database Comparison Chart

**Steps:**
1. Run a multi-database query with numeric columns
2. Scroll to "Cross-Database Comparison" section
3. Check the chart type dropdown button

**Expected:**
- [ ] Chart type dropdown shows current type (e.g., "Bar")
- [ ] "(recommended)" label on auto-detected type in dropdown

**Steps (continued):**
4. If query has 2+ metrics, select Scatter from dropdown

**Expected:**
- [ ] Chart changes to scatter plot
- [ ] X-Axis and Y-Axis dropdowns appear
- [ ] Each database is a point on the chart
- [ ] Metric selector is hidden (replaced by axis selectors)

**Steps (continued):**
5. Select Pie chart from dropdown

**Expected:**
- [ ] Chart changes to pie chart
- [ ] Metric selector reappears
- [ ] Pie shows distribution of selected metric across databases
- [ ] Legend shows database names with colors

**Steps (continued):**
6. Select Line chart from dropdown

**Expected:**
- [ ] Chart changes to line chart
- [ ] Databases on x-axis, metric value on y-axis
- [ ] Metric selector available

---

### Test 4: Auto-Detection Logic (Cross-Database)

**Scenario A: Single Metric, 2-6 Databases**
1. Run query returning 1 numeric column across 3 databases

**Expected:**
- [ ] Pie chart is auto-recommended

**Scenario B: 2+ Metrics, 3+ Databases**
1. Run query returning 2+ numeric columns across 3+ databases

**Expected:**
- [ ] Scatter plot is auto-recommended

**Scenario C: Multiple Metrics, 2 Databases**
1. Run query returning 2 numeric columns across 2 databases

**Expected:**
- [ ] Bar chart is auto-recommended (dbCount < 3 for scatter)

---

### Test 5: Edge Cases

**No Data:**
1. Run a query that returns 0 rows

**Expected:**
- [ ] Chart toggle is disabled
- [ ] No chart type dropdown shown

**Single Row:**
1. Run a query that returns exactly 1 row

**Expected:**
- [ ] Chart may be disabled or show limited visualization
- [ ] No errors in console

**Very Long Category Names:**
1. Run a query with long text values in categorical column
2. View as bar chart

**Expected:**
- [ ] Labels are readable (angled or truncated)
- [ ] Chart doesn't break layout

---

### Test 6: Persistence & State

**Steps:**
1. Select a chart type for a query
2. Switch to table view
3. Switch back to chart view

**Expected:**
- [ ] Previously selected chart type is remembered
- [ ] Chart renders with the saved type

---

## Regression Testing

Ensure these existing features still work:

- [ ] Table view toggle works
- [ ] Export dropdown (CSV, JSON, Clipboard) works
- [ ] Chart animations work
- [ ] Chart tooltips show on hover
- [ ] Legend displays correctly
- [ ] Cross-database comparison collapses/expands
- [ ] Metric selector in cross-db chart works
- [ ] Per-database export in multi-db results works
- [ ] Combined export (stacked/separate) works

---

## Known Limitations

1. **Line chart for cross-database**: Databases don't have a natural order, so line chart may not be meaningful
2. **Scatter with 1 metric**: Will show all points on same vertical line (both axes = same metric)
3. **Pie with many databases**: Legend may be crowded with 6+ databases

---

## Performance Notes

- Chart type changes should be instant (no API calls)
- useMemo prevents unnecessary re-detection
- Chart data transformations are memoized

---

## Approval Checklist

- [ ] All code review items checked
- [ ] All manual tests pass
- [ ] No console errors during testing
- [ ] Build passes: `npm run build`
- [ ] Tests pass: `npm test -- --run`
- [ ] Documentation is accurate

---

**Reviewer**: _______________
**Date**: _______________
**Status**: [ ] Approved / [ ] Changes Requested
