# Enhanced Export Options Feature Plan

**Created:** 2026-01-25
**Status:** Planning
**Priority:** Enhancement

## Overview

Enhance the data export capabilities to support additional formats, customization options, and advanced export features. This builds upon the existing CSV/JSON export functionality.

## Current State

### Existing Export Components

| Component | File | Capabilities |
|-----------|------|--------------|
| ExportDropdown | `frontend/src/components/visualization/ExportDropdown.tsx` | CSV, JSON, Clipboard |
| CombinedExportDropdown | `frontend/src/components/visualization/CombinedExportDropdown.tsx` | Multi-DB stacked/separate exports, ZIP |
| exportUtils | `frontend/src/utils/exportUtils.ts` | Core export functions |

### Current Capabilities

**Single Database Results:**
- CSV export (comma-delimited, escaped fields)
- JSON export (with metadata: query, SQL, timestamp, rowCount, connection)
- Copy to clipboard (tab-separated for spreadsheet paste)

**Multi-Database Results:**
- Stacked CSV (all rows with `database_name` column)
- Stacked JSON (combined with per-database metadata)
- Separate files as ZIP archive (CSV or JSON per database)

### Current Limitations

- No Excel (.xlsx) native format
- No PDF export
- No column selection before export
- No data filtering before export
- No chart/visualization export
- No Markdown table export
- No SQL INSERT statement generation
- No export presets/templates

## Implementation Plan

### Phase 1: Excel Export (.xlsx)

**New Dependency:** `xlsx` (SheetJS)

```bash
npm install xlsx
```

**File:** `frontend/src/utils/exportUtils.ts`

```typescript
export async function exportToExcel(
  data: Record<string, unknown>[],
  options: ExcelExportOptions
): Promise<void> {
  const XLSX = await import('xlsx');

  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Query Results');

  // Apply column widths based on content
  const colWidths = calculateColumnWidths(data);
  worksheet['!cols'] = colWidths;

  // Add header styling (requires xlsx-style or similar)

  XLSX.writeFile(workbook, `${filename}.xlsx`);
}
```

**Features:**
- Auto-sized column widths
- Header row styling (bold, background color)
- Data type preservation (numbers, dates, strings)
- Multiple sheets for multi-database exports
- Frozen header row

**Multi-Database Excel:**
- Each database as separate worksheet tab
- Summary sheet with metadata

### Phase 2: PDF Export

**New Dependency:** `jspdf` + `jspdf-autotable`

```bash
npm install jspdf jspdf-autotable
```

**File:** `frontend/src/utils/pdfExport.ts`

```typescript
export async function exportToPDF(
  data: Record<string, unknown>[],
  options: PDFExportOptions
): Promise<void> {
  const { jsPDF } = await import('jspdf');
  await import('jspdf-autotable');

  const doc = new jsPDF({
    orientation: data[0] && Object.keys(data[0]).length > 6 ? 'landscape' : 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  // Add header with metadata
  doc.setFontSize(16);
  doc.text('Query Results', 14, 15);

  doc.setFontSize(10);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 22);
  if (options.sql) {
    doc.text(`SQL: ${truncate(options.sql, 80)}`, 14, 28);
  }

  // Add table
  doc.autoTable({
    head: [Object.keys(data[0])],
    body: data.map(row => Object.values(row)),
    startY: 35,
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [79, 70, 229] }, // Indigo
  });

  doc.save(`${filename}.pdf`);
}
```

**Features:**
- Auto page orientation based on column count
- Header with query metadata
- Pagination for large datasets
- Professional table styling
- Page numbers in footer
- Optional: Include SQL query
- Optional: Include chart visualization

### Phase 3: Markdown Table Export

**File:** `frontend/src/utils/exportUtils.ts`

```typescript
export function exportToMarkdown(
  data: Record<string, unknown>[],
  options: MarkdownExportOptions = {}
): void {
  const headers = Object.keys(data[0]);
  const rows: string[] = [];

  // Header row
  rows.push(`| ${headers.join(' | ')} |`);

  // Separator row
  rows.push(`| ${headers.map(() => '---').join(' | ')} |`);

  // Data rows
  for (const row of data) {
    const values = headers.map(h => escapeMarkdown(String(row[h] ?? '')));
    rows.push(`| ${values.join(' | ')} |`);
  }

  const mdContent = rows.join('\n');

  if (options.copyToClipboard) {
    navigator.clipboard.writeText(mdContent);
  } else {
    downloadFile(mdContent, `${filename}.md`, 'text/markdown');
  }
}

function escapeMarkdown(str: string): string {
  return str.replace(/\|/g, '\\|').replace(/\n/g, ' ');
}
```

**Use Cases:**
- Paste into GitHub issues/PRs
- Documentation
- Slack/Discord messages (code blocks)

### Phase 4: SQL INSERT Statements

**File:** `frontend/src/utils/exportUtils.ts`

```typescript
export function exportToSQL(
  data: Record<string, unknown>[],
  options: SQLExportOptions
): void {
  const { tableName = 'exported_data', dialect = 'standard' } = options;
  const columns = Object.keys(data[0]);
  const statements: string[] = [];

  // Optional: CREATE TABLE statement
  if (options.includeCreate) {
    statements.push(generateCreateTable(columns, data, dialect));
  }

  // INSERT statements
  for (const row of data) {
    const values = columns.map(col => formatSQLValue(row[col], dialect));
    statements.push(
      `INSERT INTO ${quoteIdentifier(tableName, dialect)} (${columns.map(c => quoteIdentifier(c, dialect)).join(', ')}) VALUES (${values.join(', ')});`
    );
  }

  const sqlContent = statements.join('\n');
  downloadFile(sqlContent, `${tableName}.sql`, 'text/plain');
}

function formatSQLValue(value: unknown, dialect: string): string {
  if (value === null || value === undefined) return 'NULL';
  if (typeof value === 'number') return String(value);
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE';
  // Escape single quotes
  return `'${String(value).replace(/'/g, "''")}'`;
}
```

**Options:**
- Table name (user input)
- SQL dialect (PostgreSQL, MySQL, SQLite, Standard)
- Include CREATE TABLE
- Batch INSERT (multiple rows per statement)

### Phase 5: Export Customization Modal

**File:** `frontend/src/components/ExportOptionsModal.tsx`

```typescript
interface ExportOptionsModalProps {
  data: Record<string, unknown>[];
  columns: string[];
  onExport: (options: ExportConfiguration) => void;
  onClose: () => void;
}

interface ExportConfiguration {
  format: 'csv' | 'json' | 'excel' | 'pdf' | 'markdown' | 'sql';
  selectedColumns: string[];
  includeHeaders: boolean;
  rowLimit?: number;
  filterExpression?: string;
  // Format-specific options
  csvDelimiter?: ',' | ';' | '\t';
  jsonPrettyPrint?: boolean;
  pdfOrientation?: 'portrait' | 'landscape';
  sqlTableName?: string;
  sqlDialect?: string;
}
```

**Modal Sections:**

1. **Format Selection**
   - Radio buttons or cards for each format
   - Format description and file size estimate

2. **Column Selection**
   - Checkbox list of all columns
   - Select All / Deselect All buttons
   - Drag to reorder columns

3. **Row Filtering**
   - Row limit input (e.g., "First 1000 rows")
   - Simple filter builder (column, operator, value)

4. **Format-Specific Options**
   - CSV: Delimiter selection, quote style
   - JSON: Pretty print toggle, include metadata
   - Excel: Sheet name, freeze header row
   - PDF: Orientation, include SQL, page size
   - SQL: Table name, dialect, include CREATE

5. **Preview**
   - Show first 5 rows in selected format
   - File size estimate

### Phase 6: Chart/Visualization Export

**File:** `frontend/src/utils/chartExport.ts`

```typescript
export async function exportChartAsPNG(
  chartRef: React.RefObject<HTMLDivElement>,
  filename: string
): Promise<void> {
  const html2canvas = (await import('html2canvas')).default;

  const canvas = await html2canvas(chartRef.current, {
    backgroundColor: '#ffffff',
    scale: 2, // Higher resolution
  });

  const link = document.createElement('a');
  link.download = `${filename}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

export async function exportChartAsSVG(
  chartRef: React.RefObject<SVGSVGElement>,
  filename: string
): Promise<void> {
  const svgElement = chartRef.current;
  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svgElement);

  const blob = new Blob([svgString], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.download = `${filename}.svg`;
  link.href = url;
  link.click();

  URL.revokeObjectURL(url);
}
```

**Supported Exports:**
- PNG (rasterized, high-resolution)
- SVG (vector, scalable)
- Include in PDF export option

**Integration with Recharts:**
- Add export button to chart components
- Capture current chart state (zoom, selection)

### Phase 7: Export Presets/Templates

**File:** `frontend/src/hooks/useExportPresets.ts`

```typescript
interface ExportPreset {
  id: string;
  name: string;
  format: string;
  options: ExportConfiguration;
  createdAt: string;
}

function useExportPresets() {
  const [presets, setPresets] = useState<ExportPreset[]>([]);

  // Load from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('exportPresets');
    if (saved) setPresets(JSON.parse(saved));
  }, []);

  const savePreset = (name: string, options: ExportConfiguration) => {
    const newPreset: ExportPreset = {
      id: crypto.randomUUID(),
      name,
      format: options.format,
      options,
      createdAt: new Date().toISOString(),
    };
    const updated = [...presets, newPreset];
    setPresets(updated);
    localStorage.setItem('exportPresets', JSON.stringify(updated));
  };

  const deletePreset = (id: string) => { /* ... */ };
  const applyPreset = (id: string) => { /* ... */ };

  return { presets, savePreset, deletePreset, applyPreset };
}
```

**Features:**
- Save current export configuration as preset
- Quick-apply saved presets
- Default presets (e.g., "Excel with all columns", "CSV for import")
- Sync across browser sessions (localStorage)

### Phase 8: Updated Export Dropdown UI

**File:** `frontend/src/components/visualization/ExportDropdown.tsx` (refactored)

**New Structure:**
```
Export Button
  └── Dropdown Menu
        ├── Quick Export
        │     ├── CSV
        │     ├── JSON
        │     ├── Excel
        │     └── Copy to Clipboard
        ├── ─────────────
        ├── More Formats
        │     ├── PDF Report
        │     ├── Markdown Table
        │     └── SQL INSERT
        ├── ─────────────
        ├── Custom Export... (opens modal)
        ├── ─────────────
        └── Saved Presets
              ├── Preset 1
              └── Preset 2
```

**Visual Design:**
- Grouped sections with dividers
- Icons for each format
- Keyboard shortcuts (Ctrl+Shift+E for modal)
- Recently used format highlighted

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/utils/exportUtils.ts` | Modify | Add Markdown, SQL export functions |
| `frontend/src/utils/excelExport.ts` | Create | Excel-specific export logic |
| `frontend/src/utils/pdfExport.ts` | Create | PDF generation with jsPDF |
| `frontend/src/utils/chartExport.ts` | Create | Chart PNG/SVG export |
| `frontend/src/components/ExportOptionsModal.tsx` | Create | Customization modal |
| `frontend/src/components/visualization/ExportDropdown.tsx` | Modify | Enhanced dropdown UI |
| `frontend/src/components/visualization/CombinedExportDropdown.tsx` | Modify | Add new formats |
| `frontend/src/hooks/useExportPresets.ts` | Create | Preset management |
| `frontend/package.json` | Modify | Add xlsx, jspdf, html2canvas |

## New Dependencies

| Package | Purpose | Size |
|---------|---------|------|
| `xlsx` | Excel file generation | ~400KB |
| `jspdf` | PDF generation | ~300KB |
| `jspdf-autotable` | PDF table formatting | ~50KB |
| `html2canvas` | Chart to image capture | ~200KB |

**Note:** Consider lazy loading these packages to avoid bundle size impact.

```typescript
// Lazy load on demand
const exportToExcel = async (data) => {
  const XLSX = await import('xlsx');
  // ...
};
```

## Testing Strategy

### Unit Tests

**`frontend/src/utils/__tests__/exportUtils.test.ts`:**
- CSV escaping handles special characters
- JSON metadata correctly populated
- Markdown table formatting correct
- SQL escaping prevents injection
- Column selection filters correctly
- Row limit applied correctly

**`frontend/src/utils/__tests__/excelExport.test.ts`:**
- Workbook created with correct sheets
- Column widths calculated properly
- Data types preserved

**`frontend/src/utils/__tests__/pdfExport.test.ts`:**
- PDF document has correct pages
- Table fits within margins
- Metadata header rendered

### Integration Tests

- Export modal opens and closes correctly
- Column selection updates preview
- Preset save/load from localStorage
- Multi-database exports include all databases

### E2E Tests

**`frontend/e2e/export.spec.ts`:**
- Execute query, export as CSV, verify download
- Execute query, export as Excel, verify file opens
- Export as PDF, verify page count matches data
- Copy to clipboard, paste in test field, verify content
- Save export preset, reload page, preset persists
- Export chart as PNG, verify image dimensions

## Accessibility

- Export modal keyboard navigable
- Format options have clear labels
- Screen reader announces export completion
- Focus management when modal opens/closes

## Performance Considerations

1. **Large Dataset Handling:**
   - Stream CSV generation for >10,000 rows
   - Warn user before exporting >100,000 rows
   - Show progress indicator for long exports

2. **Bundle Size:**
   - Lazy load export libraries
   - Tree-shake unused xlsx features
   - Consider lighter PDF library alternatives

3. **Memory Management:**
   - Release object URLs after download
   - Clear canvas elements after chart export

## Security Considerations

- SQL export escapes all values to prevent injection if re-imported
- Filename sanitization (remove path characters)
- No sensitive data in export metadata unless user chooses

## Future Enhancements

Out of scope for initial implementation:

1. **Parquet/Arrow Export** - Binary columnar format for data science
2. **Google Sheets Integration** - Direct export to Sheets
3. **Scheduled Exports** - Export on a schedule via backend
4. **Email Export** - Send export as email attachment
5. **Cloud Storage** - Export directly to S3/GCS/Azure
6. **Export History** - Track previous exports
7. **Collaborative Exports** - Share export configurations

## Format Comparison

| Format | Best For | File Size | Editable | Preserves Types |
|--------|----------|-----------|----------|-----------------|
| CSV | Import to databases, simple data | Small | Yes | No |
| JSON | APIs, JavaScript apps | Medium | Yes | Partial |
| Excel | Business users, analysis | Medium | Yes | Yes |
| PDF | Reports, printing, sharing | Large | No | N/A |
| Markdown | Documentation, GitHub | Small | Yes | No |
| SQL | Database import | Medium | Yes | Yes |

## Acceptance Criteria

### Phase 1: Excel
- [ ] Export button shows Excel option
- [ ] Excel file downloads with correct extension
- [ ] Column headers in first row, bold
- [ ] Column widths auto-sized
- [ ] Multi-database creates multiple sheets

### Phase 2: PDF
- [ ] PDF downloads with correct page count
- [ ] Table headers on each page
- [ ] Metadata header shows query/timestamp
- [ ] Landscape mode for wide tables
- [ ] Page numbers in footer

### Phase 3: Markdown
- [ ] Valid Markdown table syntax
- [ ] Pipe characters escaped in data
- [ ] Copy to clipboard option works
- [ ] Renders correctly in GitHub preview

### Phase 4: SQL
- [ ] Valid SQL INSERT syntax
- [ ] Values properly escaped
- [ ] Table name configurable
- [ ] Dialect-specific quoting (optional)

### Phase 5: Customization Modal
- [ ] Modal opens from dropdown
- [ ] All columns listed with checkboxes
- [ ] Row limit input works
- [ ] Preview updates on option change
- [ ] Export button triggers download

### Phase 6: Chart Export
- [ ] PNG export captures full chart
- [ ] SVG export is valid XML
- [ ] High resolution (2x) option
- [ ] Transparent background option

### Phase 7: Presets
- [ ] Save preset with name
- [ ] Presets persist across sessions
- [ ] Apply preset populates options
- [ ] Delete preset removes from list

## Estimated Complexity

| Phase | Complexity | New Dependencies |
|-------|------------|------------------|
| Phase 1: Excel | Medium | xlsx |
| Phase 2: PDF | Medium | jspdf, jspdf-autotable |
| Phase 3: Markdown | Low | None |
| Phase 4: SQL | Low | None |
| Phase 5: Modal | High | None |
| Phase 6: Chart Export | Medium | html2canvas |
| Phase 7: Presets | Low | None |
| Phase 8: UI Update | Medium | None |

## Implementation Order Recommendation

1. **Markdown** (Phase 3) - Low effort, immediate value
2. **SQL INSERT** (Phase 4) - Low effort, useful for data migration
3. **Excel** (Phase 1) - High demand from business users
4. **PDF** (Phase 2) - Common request for reports
5. **UI Update** (Phase 8) - Accommodate new formats
6. **Customization Modal** (Phase 5) - Power user feature
7. **Chart Export** (Phase 6) - Nice to have
8. **Presets** (Phase 7) - Power user feature

## Notes

- Excel export is likely the most requested feature
- PDF is useful but may have formatting challenges with wide tables
- SQL export should warn about large datasets
- Consider adding "Export All" for multi-database that exports each format
- Lazy loading is critical for bundle size management
