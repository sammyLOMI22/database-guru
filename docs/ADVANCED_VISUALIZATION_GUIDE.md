# Advanced Visualization and Dashboards

**Feature Branch**: Advanced-Visualization-and-Dashboards
**Status**: Phase 1 Complete - Core Implementation + Chart Type Selector
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
| **Scatter Plot** | Correlation detected (≥10 rows, r > 0.7) | Relationships, correlations |
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
- **Requires minimum 10 data points** to avoid spurious correlations in small datasets

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

### 5. Manual Chart Type Selection

While the system auto-detects the best chart type, users can manually override the selection:

**How It Works:**
1. Click the dropdown chevron (▼) next to the Table/Chart toggle
2. A dropdown menu appears with all available chart types
3. The recommended (auto-detected) type shows **(recommended)** label
4. Select any chart type to switch the visualization
5. The toggle button icon and label update to reflect the selection

**Available Chart Types:**
| Icon | Type | Description |
|------|------|-------------|
| 📊 | Bar | Vertical bars for comparisons |
| 📈 | Line | Connected points for trends |
| 🥧 | Pie | Circular segments for proportions |
| ⚬ | Scatter | Points for correlations |

**Where Available:**
- Single query results (QueryResults.tsx)
- Per-database charts in multi-database queries (MultiDatabaseResults.tsx)
- Cross-database comparison chart (CrossDatabaseChart.tsx)

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
5. Supports chart type override via `overrideChartType` prop

```tsx
<ChartVisualization
  data={results}
  statistics={resultAnalysis?.statistics || {}}
  height={350}
  showLegend={true}
  animate={true}
  overrideChartType={selectedChartType}  // Optional: override auto-detection
/>
```

When `overrideChartType` is provided, the component uses that chart type instead of the auto-detected one, and the info badge displays "Manually selected X chart".

### ChartToggle.tsx

Toggle button group for switching between table and chart views, with optional chart type selector:

```tsx
<ChartToggle
  mode={viewMode}                    // 'table' | 'chart'
  onModeChange={setViewMode}
  chartAvailable={chartAvailable}
  chartType={recommendation.chartType}  // Auto-detected type
  selectedChartType={selectedChartType} // User-selected override (optional)
  onChartTypeChange={setSelectedChartType} // Callback for type changes
  showChartTypeSelector={true}       // Show dropdown to change chart type
/>
```

**Chart Type Selector Features:**
- Dropdown button (▼) appears next to the Table/Chart toggle
- Shows all available chart types: Bar, Line, Pie, Scatter
- Displays **(recommended)** label next to the auto-detected type
- Selecting a type switches the view and updates the chart
- Icon and label on the toggle button update to reflect the selected type

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
   - Correlations detected in statistics (minimum 10 rows required)
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

## Multi-Database Visualization

The visualization system extends to multi-database query results, providing per-database charts, combined exports, and cross-database comparison charts.

### Per-Database Charts

Each database result in a multi-database query can independently toggle between table and chart views, with manual chart type selection:

```tsx
// Each database has independent view mode and chart type
const [viewModes, setViewModes] = useState<Record<number, ViewMode>>(() =>
  Object.fromEntries(results.map(r => [r.connection_id, 'table']))
);
const [selectedChartTypes, setSelectedChartTypes] = useState<Record<number, ChartType | null>>(() =>
  Object.fromEntries(results.map(r => [r.connection_id, null]))
);
```

Features:
- **Independent toggles**: Each database's view mode is controlled separately
- **Chart detection**: Uses the same intelligent detection as single queries
- **Chart type selector**: Users can override the recommended chart type per database
- **Per-database export**: Each database has its own export dropdown

### Combined Export

Export all database results together with format choice:

| Mode | Description | Output |
|------|-------------|--------|
| **Stacked CSV** (default) | All rows merged with `database_name` column | Single CSV file |
| **Stacked JSON** | All data with database metadata | Single JSON file |
| **Separate Files** | One file per database | ZIP archive |

```tsx
<CombinedExportDropdown
  results={results}
  question={question}
/>
```

### Cross-Database Comparison Chart

Automatically detects common numeric columns across databases and displays a comparison chart with intelligent chart type selection:

```tsx
// Detection
const crossDbConfig = detectCrossDbComparison(results);

// Rendering
{crossDbConfig && <CrossDatabaseChart config={crossDbConfig} />}
```

**Chart Type Auto-Detection:**

| Chart Type | Detection Criteria | Use Case |
|------------|-------------------|----------|
| **Scatter Plot** | 2+ metrics AND 3+ databases | Show relationships between metrics across databases |
| **Pie Chart** | Single metric with 2-6 databases | Show proportional distribution |
| **Bar Chart** | Default fallback | Compare values across databases |
| **Line Chart** | User-selectable | Trend visualization (databases on x-axis) |

Features:
- **Common column detection**: Finds numeric columns present in all successful results
- **Aggregation**: Sums values per database for comparison
- **Chart type selector**: Dropdown to switch between Bar, Line, Pie, and Scatter charts
- **Auto-detection**: System recommends best chart type with "(recommended)" label
- **Metric selector**: Switch between different metrics when multiple are available (for bar/line/pie)
- **Axis selectors**: Choose X and Y metrics for scatter plot
- **Collapsible section**: Toggle visibility of the comparison chart
- **Summary stats**: Shows aggregated values and row counts per database

### New Components

| Component | Purpose |
|-----------|---------|
| `CombinedExportDropdown.tsx` | Multi-database export with format selection |
| `CrossDatabaseChart.tsx` | Cross-database comparison visualization |

### New Utilities

| File | Functions |
|------|-----------|
| `crossDbUtils.ts` | `findCommonNumericColumns()`, `aggregateByDatabase()`, `detectCrossDbComparison()`, `formatMetricValue()` |
| `exportUtils.ts` | `exportCombinedCSV()`, `exportCombinedJSON()`, `exportSeparateFiles()` |

### Test Coverage

| Test File | Tests |
|-----------|-------|
| `crossDbUtils.test.ts` | 19 tests for cross-database utilities |
| `CombinedExportDropdown.test.tsx` | 17 tests for combined export component |
| `CrossDatabaseChart.test.tsx` | 17 tests for comparison chart component |

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

**Document Version**: 2.2
**Last Updated**: December 20, 2025

### Changelog

**v2.2** - Improved correlation detection reliability
- Scatter plot now requires minimum 10 data points to avoid spurious correlations
- Added test for small dataset rejection in correlation analysis

**v2.1** - Added manual chart type selection feature
- Chart type selector dropdown for single queries, per-database charts, and cross-database comparison
- Auto-detection with "(recommended)" labels
- Cross-database chart supports Bar, Line, Pie, and Scatter with smart detection
