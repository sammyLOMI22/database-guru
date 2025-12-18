# Advanced Visualization and Dashboards

**Feature Branch**: Advanced-Visualization-and-Dashboards
**Status**: Phase 1 Complete - Core Implementation
**Created**: December 18, 2025

---

## Overview

The Advanced Visualization feature provides intelligent, auto-detected chart visualizations for query results, with export capabilities to CSV, JSON, and clipboard formats. The system analyzes query results and statistics to automatically recommend the most appropriate chart type.

## Features

### 1. Intelligent Chart Detection

The system automatically analyzes query results to determine the best visualization:

| Chart Type | Detection Criteria | Use Case |
|------------|-------------------|----------|
| **Line Chart** | Temporal column + numeric column, or trend detected | Time-series, trends |
| **Scatter Plot** | Correlation detected between numeric columns | Relationships, correlations |
| **Pie Chart** | Categorical column + numeric, 2-8 unique values | Distribution, proportions |
| **Bar Chart** | Categorical column + numeric, 9-15 unique values | Comparisons |
| **Table** | Default fallback, or too many unique values | Raw data viewing |

### 2. Chart Types

#### Bar Chart
- Displays categorical data as vertical bars
- Handles up to 50 data points
- Shows value on hover with tooltips
- Angled labels for long category names

#### Line Chart
- Time-series or trend visualization
- Auto-sorted by x-axis values
- Handles up to 100 data points
- Smooth line with data point markers

#### Pie Chart
- Categorical distribution visualization
- Percentage labels for segments > 5%
- Aggregates values by category
- Color-coded legend

#### Scatter Plot
- Correlation visualization between two numeric columns
- Displays correlation coefficient (r value)
- Handles up to 200 data points
- Correlation strength indicator

### 3. Export Capabilities

| Format | Description | Features |
|--------|-------------|----------|
| **CSV** | Comma-separated values | Excel compatible, special char escaping |
| **JSON** | JavaScript Object Notation | Includes metadata, timestamps, SQL |
| **Clipboard** | Tab-separated for spreadsheets | Quick paste into Excel/Sheets |

### 4. User Preferences

Chart preferences are persisted in localStorage:

- **Default View Mode**: Table or Chart
- **Chart Height**: Customizable height (default: 300px)
- **Show Legend**: Toggle legend visibility
- **Animations**: Enable/disable chart animations

---

## Architecture

### File Structure

```
frontend/src/
├── components/visualization/
│   ├── ChartVisualization.tsx   # Main container (auto-detection)
│   ├── ChartToggle.tsx          # Table/Chart toggle button
│   ├── ExportDropdown.tsx       # Export menu dropdown
│   ├── BarChartView.tsx         # Bar chart component
│   ├── LineChartView.tsx        # Line chart component
│   ├── PieChartView.tsx         # Pie chart component
│   └── ScatterChartView.tsx     # Scatter chart component
├── utils/
│   ├── chartUtils.ts            # Chart detection & data prep
│   └── exportUtils.ts           # Export utilities
├── hooks/
│   └── useChartPreferences.ts   # Preferences persistence
└── components/
    └── QueryResults.tsx         # Integration point
```

### Dependencies

- **recharts** (^2.x): React charting library
- **lucide-react**: Icons for UI

### Data Flow

```
Query Results + Statistics
       ↓
  detectChartType()          # chartUtils.ts
       ↓
  ChartRecommendation {
    chartType: 'bar' | 'line' | 'pie' | 'scatter' | 'table',
    confidence: number,
    xColumn: string,
    yColumn: string,
    reason: string
  }
       ↓
  ChartVisualization          # Renders appropriate chart
       ↓
  [Bar|Line|Pie|Scatter]ChartView
```

---

## Component Details

### ChartVisualization.tsx

Main orchestrator component that:
1. Calls `detectChartType()` with data and statistics
2. Displays info badge with chart type and reason
3. Renders the appropriate chart component
4. Handles "no visualization available" state

```tsx
<ChartVisualization
  data={results}
  statistics={resultAnalysis?.statistics || {}}
  height={350}
  showLegend={true}
  animate={true}
/>
```

### ChartToggle.tsx

Toggle button group for switching between table and chart views:

```tsx
<ChartToggle
  mode={viewMode}              // 'table' | 'chart'
  onModeChange={setViewMode}
  chartAvailable={chartAvailable}
  chartType={recommendation.chartType}
/>
```

### ExportDropdown.tsx

Dropdown menu with export options:

```tsx
<ExportDropdown
  data={results}
  sql={sql}
  question={question}
  connectionName={connectionName}
  databaseType={databaseType}
/>
```

---

## Chart Detection Algorithm

### Priority Order

1. **Line Chart** (highest priority for time-series)
   - Has temporal column (date, time, year, etc.) + numeric column
   - OR trends detected in ResultNarrator statistics

2. **Scatter Plot**
   - Correlations detected in statistics
   - Two numeric columns available

3. **Pie Chart**
   - Categorical column with 2-8 unique values
   - Numeric column for values

4. **Bar Chart**
   - Categorical column with 9-15 unique values
   - OR numeric values suitable for comparison (≤20 rows)

5. **Table** (fallback)
   - Too many unique values
   - No suitable columns for visualization
   - Insufficient data (< 2 rows)

### Column Classification

Columns are classified based on:

- **Name patterns**: `date`, `time`, `year`, `_at`, `_id`, etc.
- **Value inspection**: typeof check on first non-null value
- **Statistics**: Type info from ResultNarrator

### ID Column Exclusion

Columns matching these patterns are excluded from charts:
- `^id$`, `_id$`, `^pk$`, `^key$`, `uuid`

---

## Export Utilities

### CSV Export

```typescript
exportToCSV(data, {
  filename: 'query-results',
  includeHeaders: true,
  delimiter: ','
});
```

Features:
- Proper escaping of commas, quotes, newlines
- Automatic filename with timestamp
- UTF-8 encoding

### JSON Export

```typescript
exportToJSON(data, {
  query: 'Show me sales by region',
  sql: 'SELECT region, SUM(amount) ...',
  timestamp: '2025-12-18T...',
  rowCount: 100,
  connectionName: 'Production DB',
  databaseType: 'postgresql'
});
```

Output structure:
```json
{
  "metadata": {
    "query": "...",
    "sql": "...",
    "exportedAt": "...",
    "totalRows": 100
  },
  "columns": ["region", "total"],
  "data": [...]
}
```

### Clipboard Copy

- Tab-separated values for Excel/Sheets compatibility
- Async clipboard API with error handling
- Visual feedback on success

---

## Integration with ResultNarrator

The visualization system integrates with the Intelligent Data Narratives feature:

```typescript
// Statistics from ResultNarrator enhance chart detection
const statistics = {
  trends: {
    found: true,
    detected_trends: [{ column: 'revenue', temporal_column: 'month', ... }]
  },
  correlations: {
    found: true,
    significant_correlations: [{ column1: 'price', column2: 'quantity', correlation: -0.82 }]
  }
};

// Chart detection uses these for better recommendations
detectChartType(results, statistics);
```

---

## Color Palette

Tailwind-aligned colors for consistent styling:

```typescript
CHART_COLORS = {
  primary: '#3b82f6',    // blue-500
  secondary: '#8b5cf6',  // violet-500
  success: '#10b981',    // emerald-500
  warning: '#f59e0b',    // amber-500
  danger: '#ef4444',     // red-500
  info: '#06b6d4',       // cyan-500
  pink: '#ec4899',       // pink-500
  lime: '#84cc16',       // lime-500
};
```

---

## User Preferences Persistence

### localStorage Key
`dbguru-chart-prefs`

### Default Values
```typescript
{
  defaultViewMode: 'table',
  preferredChartHeight: 300,
  showChartLegend: true,
  chartAnimations: true
}
```

### Hook Usage
```typescript
const { preferences, updatePreferences, resetPreferences } = useChartPreferences();

// Update single preference
updatePreferences({ defaultViewMode: 'chart' });

// Reset to defaults
resetPreferences();
```

---

## Performance Considerations

### Data Limits

| Chart Type | Max Points | Reason |
|------------|-----------|--------|
| Bar | 50 | Readability |
| Line | 100 | Performance |
| Pie | 20 | Visibility |
| Scatter | 200 | Rendering |

### Optimization Strategies

1. **useMemo** for chart data preparation
2. **Animation toggle** for low-end devices
3. **Responsive containers** for proper sizing
4. **Truncation warnings** when data is limited

---

## Testing

### Test Files (To Be Created)

```
frontend/tests/
├── ChartVisualization.test.tsx    # Main container tests
├── ChartToggle.test.tsx           # Toggle component tests
├── ExportDropdown.test.tsx        # Export menu tests
├── chartUtils.test.ts             # Chart detection tests
└── exportUtils.test.ts            # Export utility tests
```

### Test Categories

1. **Chart Detection Tests**
   - Temporal data → Line chart
   - Correlations → Scatter plot
   - Few categories → Pie chart
   - Many categories → Bar chart
   - Edge cases → Table fallback

2. **Export Tests**
   - CSV special character escaping
   - JSON metadata inclusion
   - Clipboard format correctness

3. **Component Tests**
   - Toggle state management
   - Chart rendering with mock data
   - Export dropdown menu behavior

---

## Future Enhancements (Phase 2)

### Dashboard Feature
- [ ] Save chart configurations
- [ ] Multiple charts per dashboard
- [ ] Dashboard templates
- [ ] Share dashboards

### Additional Chart Types
- [ ] Area chart
- [ ] Stacked bar chart
- [ ] Donut chart
- [ ] Heatmap

### Advanced Features
- [ ] Drill-down on chart elements
- [ ] Chart annotations
- [ ] Custom color schemes
- [ ] Chart print/screenshot

### Interactivity
- [ ] Zoom/pan on charts
- [ ] Brush selection
- [ ] Cross-chart filtering
- [ ] Live refresh

---

## API Reference

### chartUtils.ts

```typescript
// Main detection function
function detectChartType(
  results: Record<string, unknown>[],
  statistics: Record<string, unknown>
): ChartRecommendation;

// Column classification
function classifyColumns(
  results: Record<string, unknown>[],
  statistics: Record<string, unknown>
): ColumnClassification;

// Data preparation
function prepareChartData(
  results: Record<string, unknown>[],
  xColumn: string,
  yColumn: string,
  chartType: ChartType,
  maxItems?: number
): Record<string, unknown>[];
```

### exportUtils.ts

```typescript
// Export functions
function exportToCSV(data: Record<string, unknown>[], options?: ExportOptions): void;
function exportToJSON(data: Record<string, unknown>[], metadata: JSONExportMetadata): void;
function copyToClipboard(data: Record<string, unknown>[]): Promise<boolean>;

// Formatting helpers
function formatNumber(value: number): string;
function truncateString(str: string, maxLength?: number): string;
```

---

## Troubleshooting

### Chart Not Showing

1. Check data has ≥2 rows
2. Verify numeric columns exist
3. Check console for errors
4. Try table view to confirm data

### Export Not Working

1. Check browser popup blocker
2. Verify data is not empty
3. Check clipboard permissions

### Performance Issues

1. Disable animations: `animate={false}`
2. Reduce data points manually
3. Check for large result sets

---

## Related Documentation

- [Intelligent Data Narratives Guide](DATA_NARRATIVES_GUIDE.md) - Statistics integration
- [Future Plans](FUTURE_PLANS.md) - Roadmap for visualizations
- [Frontend Test Coverage](FRONTEND_TEST_COVERAGE.md) - Testing patterns

---

**Document Version**: 1.0
**Last Updated**: December 18, 2025
