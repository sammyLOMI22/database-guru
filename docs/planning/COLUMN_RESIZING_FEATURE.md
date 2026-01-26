# Column Resizing Feature Plan

**Created:** 2026-01-25
**Status:** Planning
**Priority:** Enhancement
**Dependency:** Can be implemented independently or after Table Sorting Feature

## Overview

Implement column resizing for query result tables, allowing users to drag column borders to adjust widths. This improves readability when columns contain varying content lengths.

## Current State

### Tables Requiring Column Resizing

| Component | File | Current Width Behavior |
|-----------|------|------------------------|
| QueryResults | `frontend/src/components/QueryResults.tsx` | Auto-width based on content |
| MultiDatabaseResults | `frontend/src/components/MultiDatabaseResults.tsx` | Auto-width based on content |
| StreamingQueryResults | `frontend/src/components/StreamingQueryResults.tsx` | Auto-width based on content |

### Current Implementation

Tables use basic HTML `<table>` with no explicit column widths:
- Columns auto-size based on content
- Long content truncated with `truncate` class or wraps
- No user control over column width
- No `table-layout: fixed` applied

## Implementation Plan

### Phase 1: Table Layout Foundation

**CSS Changes Required:**

```css
/* Enable fixed table layout for predictable column sizing */
.resizable-table {
  table-layout: fixed;
  width: 100%;
}

/* Column cells respect assigned widths */
.resizable-table th,
.resizable-table td {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

**Considerations:**
- `table-layout: fixed` required for column widths to be respected
- Content overflow must be handled (truncate with ellipsis)
- May need tooltip/popover for truncated content

### Phase 2: Column Width State Management

**File:** `frontend/src/hooks/useColumnResize.ts`

```typescript
interface ColumnWidths {
  [columnName: string]: number; // width in pixels
}

interface UseColumnResizeReturn {
  columnWidths: ColumnWidths;
  getColumnStyle: (column: string) => React.CSSProperties;
  handleResizeStart: (column: string, event: React.MouseEvent) => void;
  handleResizeEnd: () => void;
  resetColumnWidths: () => void;
  isResizing: boolean;
  resizingColumn: string | null;
}

function useColumnResize(
  columns: string[],
  defaultWidth?: number,
  minWidth?: number,
  maxWidth?: number
): UseColumnResizeReturn
```

**Default Values:**
- `defaultWidth`: 150px
- `minWidth`: 50px
- `maxWidth`: 500px

**Initial Width Calculation:**
```typescript
// Option A: Equal distribution
const initialWidth = tableWidth / columns.length;

// Option B: Content-aware (measure first row)
const initialWidth = measureColumnContent(column, data[0]);

// Option C: Hybrid - start equal, allow resize
const initialWidth = Math.max(minWidth, tableWidth / columns.length);
```

### Phase 3: Resize Handle Component

**File:** `frontend/src/components/ResizeHandle.tsx`

```typescript
interface ResizeHandleProps {
  column: string;
  onResizeStart: (column: string, event: React.MouseEvent) => void;
  isResizing: boolean;
}
```

**Visual Design:**
```css
.resize-handle {
  @apply absolute right-0 top-0 h-full w-1 cursor-col-resize;
  @apply hover:bg-indigo-400/50 transition-colors;
}

.resize-handle-active {
  @apply bg-indigo-500;
}

/* Visual guide line during resize */
.resize-indicator {
  @apply fixed top-0 bottom-0 w-0.5 bg-indigo-500 pointer-events-none z-50;
}
```

**Handle Placement:**
- Positioned at right edge of each column header
- 4-8px wide hit area for easy grabbing
- Visual feedback on hover and during drag

### Phase 4: Drag Resize Logic

**Mouse Event Handling:**

```typescript
const handleResizeStart = (column: string, event: React.MouseEvent) => {
  event.preventDefault();
  setResizingColumn(column);
  setStartX(event.clientX);
  setStartWidth(columnWidths[column]);

  // Add document-level listeners for drag
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

const handleMouseMove = (event: MouseEvent) => {
  if (!resizingColumn) return;

  const delta = event.clientX - startX;
  const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidth + delta));

  setColumnWidths(prev => ({
    ...prev,
    [resizingColumn]: newWidth
  }));
};

const handleMouseUp = () => {
  setResizingColumn(null);
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
};
```

**Touch Support:**
```typescript
// Mirror mouse events for touch devices
onTouchStart → handleResizeStart (use touch.clientX)
onTouchMove → handleMouseMove
onTouchEnd → handleMouseUp
```

### Phase 5: Resizable Table Header Component

**File:** `frontend/src/components/ResizableTableHeader.tsx`

```typescript
interface ResizableTableHeaderProps {
  column: string;
  label?: string;
  width: number;
  onResizeStart: (column: string, event: React.MouseEvent) => void;
  isResizing: boolean;
  // Optional: integrate with sorting
  sortConfig?: SortConfig;
  onSort?: (column: string) => void;
}
```

**Structure:**
```tsx
<th style={{ width: `${width}px` }} className="relative">
  <div className="flex items-center justify-between">
    <span className="truncate">{label || column}</span>
    {/* Sort icon if sorting enabled */}
  </div>
  <ResizeHandle
    column={column}
    onResizeStart={onResizeStart}
    isResizing={isResizing}
  />
</th>
```

### Phase 6: QueryResults Integration

**File:** `frontend/src/components/QueryResults.tsx`

**Changes:**
1. Import `useColumnResize` hook
2. Calculate columns from result keys
3. Apply `table-layout: fixed` to table
4. Replace `<th>` with `ResizableTableHeader`
5. Apply column widths to `<td>` elements via `colgroup`
6. Reset widths when columns change (new query)

**Table Structure with Colgroup:**
```tsx
<table className="w-full" style={{ tableLayout: 'fixed' }}>
  <colgroup>
    {columns.map(col => (
      <col key={col} style={{ width: columnWidths[col] }} />
    ))}
  </colgroup>
  <thead>
    <tr>
      {columns.map(col => (
        <ResizableTableHeader
          key={col}
          column={col}
          width={columnWidths[col]}
          onResizeStart={handleResizeStart}
          isResizing={resizingColumn === col}
        />
      ))}
    </tr>
  </thead>
  <tbody>
    {/* ... */}
  </tbody>
</table>
```

### Phase 7: MultiDatabaseResults Integration

**File:** `frontend/src/components/MultiDatabaseResults.tsx`

**Changes:**
- Each database result section maintains independent column widths
- State structure per connection:
  ```typescript
  const [columnWidthsMap, setColumnWidthsMap] = useState<
    Record<string, ColumnWidths>
  >({});
  ```
- Reset widths for a connection when its results change

### Phase 8: StreamingQueryResults Integration

**File:** `frontend/src/components/StreamingQueryResults.tsx`

**Special Considerations:**
- Columns known from metadata before data arrives
- Can set initial widths early
- Width should remain stable as rows stream in
- No special streaming-specific logic needed

### Phase 9: Content Overflow Handling

**Truncation with Tooltip:**

```tsx
<td className="truncate" title={fullValue}>
  {displayValue}
</td>
```

**Or with Popover (for long content):**

```tsx
const CellContent = ({ value }: { value: string }) => {
  const [showPopover, setShowPopover] = useState(false);
  const isTruncated = value.length > 50; // or measure actual overflow

  return (
    <div
      className="truncate cursor-default"
      onMouseEnter={() => isTruncated && setShowPopover(true)}
      onMouseLeave={() => setShowPopover(false)}
    >
      {value}
      {showPopover && (
        <div className="absolute z-50 p-2 bg-gray-900 rounded shadow-lg max-w-md">
          {value}
        </div>
      )}
    </div>
  );
};
```

### Phase 10: Double-Click Auto-Fit

**Feature:** Double-click resize handle to auto-fit column to content.

```typescript
const handleDoubleClick = (column: string) => {
  // Measure max content width in column
  const maxWidth = measureColumnContent(column);
  setColumnWidths(prev => ({
    ...prev,
    [column]: Math.min(maxWidth + padding, MAX_WIDTH)
  }));
};

const measureColumnContent = (column: string): number => {
  // Create hidden measurement element
  const measurer = document.createElement('span');
  measurer.style.visibility = 'hidden';
  measurer.style.position = 'absolute';
  measurer.style.whiteSpace = 'nowrap';
  measurer.className = 'font-mono text-sm'; // match table cell styles
  document.body.appendChild(measurer);

  let maxWidth = 0;
  data.forEach(row => {
    measurer.textContent = String(row[column] ?? '');
    maxWidth = Math.max(maxWidth, measurer.offsetWidth);
  });

  // Also measure header
  measurer.textContent = column;
  measurer.className = 'text-[11px] font-black';
  maxWidth = Math.max(maxWidth, measurer.offsetWidth);

  document.body.removeChild(measurer);
  return maxWidth;
};
```

### Phase 11: Cursor Management

**During Resize:**
```typescript
useEffect(() => {
  if (isResizing) {
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  } else {
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  return () => {
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };
}, [isResizing]);
```

### Phase 12: Accessibility

- Resize handles should be keyboard accessible
- Arrow keys (Left/Right) to adjust width when handle focused
- Announce width changes to screen readers
- Provide reset button or keyboard shortcut

```tsx
<div
  role="separator"
  aria-orientation="vertical"
  aria-valuenow={width}
  aria-valuemin={minWidth}
  aria-valuemax={maxWidth}
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'ArrowLeft') adjustWidth(-10);
    if (e.key === 'ArrowRight') adjustWidth(10);
  }}
/>
```

## Visual Design

### Resize Handle States

| State | Appearance |
|-------|------------|
| Default | Invisible or subtle 1px border |
| Hover | Highlighted bar (indigo-400/50) |
| Active/Dragging | Solid color (indigo-500) |
| Disabled | No cursor change, grayed out |

### Cursor States

| Context | Cursor |
|---------|--------|
| Over resize handle | `col-resize` |
| During drag | `col-resize` (document-wide) |
| Normal cell | `default` |

### Visual Indicator During Drag

Option A: **Ghost line** - Vertical line follows cursor
Option B: **Live resize** - Column resizes in real-time (recommended)
Option C: **Outline** - Show target width outline, apply on release

**Recommendation:** Live resize (Option B) for immediate feedback.

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/hooks/useColumnResize.ts` | Create | Resize state management hook |
| `frontend/src/components/ResizeHandle.tsx` | Create | Draggable resize handle |
| `frontend/src/components/ResizableTableHeader.tsx` | Create | Header with resize capability |
| `frontend/src/components/QueryResults.tsx` | Modify | Integrate column resizing |
| `frontend/src/components/MultiDatabaseResults.tsx` | Modify | Per-DB column resizing |
| `frontend/src/components/StreamingQueryResults.tsx` | Modify | Integrate column resizing |

## Testing Strategy

### Unit Tests

**`frontend/src/hooks/__tests__/useColumnResize.test.ts`:**
- Initial widths calculated correctly
- Resize updates width within min/max bounds
- Cannot resize below minimum
- Cannot resize above maximum
- Reset returns to initial widths
- Multiple columns resize independently

**`frontend/src/components/__tests__/ResizeHandle.test.tsx`:**
- Calls onResizeStart on mousedown
- Shows active state during resize
- Cursor changes on hover
- Touch events work correctly

### Integration Tests

- Resize persists across pagination
- Resize persists during sort changes
- New query results reset column widths
- Multi-database independent resizing
- Content truncates properly at new width

### E2E Tests

**`frontend/e2e/column-resizing.spec.ts`:**
- Drag resize handle to increase column width
- Drag resize handle to decrease column width
- Double-click to auto-fit column
- Column width respects min/max bounds
- Content truncates with ellipsis
- Hover on truncated content shows tooltip

## Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | Full | - |
| Firefox | Full | - |
| Safari | Full | Test touch events on iOS |
| Edge | Full | - |

**Pointer Events API:**
Consider using Pointer Events for unified mouse/touch handling:
```typescript
onPointerDown, onPointerMove, onPointerUp
```

## Performance Considerations

1. **Throttle resize updates:**
   ```typescript
   const handleMouseMove = throttle((event: MouseEvent) => {
     // Update width
   }, 16); // ~60fps
   ```

2. **Avoid layout thrashing:**
   - Use `transform` for visual indicator if not live-resizing
   - Batch DOM reads and writes

3. **Large tables:**
   - `table-layout: fixed` improves performance (no content measurement)
   - Consider virtualization for very long tables

## Future Enhancements

Out of scope for initial implementation:

1. **Persist column widths** - Save to localStorage per query/table
2. **Column width presets** - Save/load width configurations
3. **Proportional resizing** - Maintain table width, adjust adjacent column
4. **Min-content/max-content** - Quick-set to content bounds
5. **Column hiding** - Hide columns entirely (0 width or visibility toggle)
6. **Column reordering** - Drag columns to rearrange order

## Dependencies

No new npm packages required. Uses:
- Native DOM events (mouse, touch, pointer)
- Existing React hooks
- Existing Tailwind classes

**Optional Enhancement:**
- `use-gesture` library for smoother gesture handling
- Only add if native implementation proves problematic

## Integration with Table Sorting

If implementing both features, combine into single header component:

**File:** `frontend/src/components/InteractiveTableHeader.tsx`

```typescript
interface InteractiveTableHeaderProps {
  column: string;
  label?: string;
  // Sorting props
  sortConfig?: SortConfig;
  onSort?: (column: string) => void;
  // Resizing props
  width: number;
  onResizeStart: (column: string, event: React.MouseEvent) => void;
  isResizing: boolean;
}
```

## Acceptance Criteria

- [ ] Resize handle visible on column header hover
- [ ] Drag handle to resize column width
- [ ] Column width respects minimum (50px)
- [ ] Column width respects maximum (500px)
- [ ] Live resize feedback during drag
- [ ] Cursor shows `col-resize` during resize
- [ ] Double-click auto-fits column to content
- [ ] Content truncates with ellipsis when column narrowed
- [ ] Tooltip shows full content on truncated cells
- [ ] Column widths persist during pagination
- [ ] Column widths persist during sorting
- [ ] New query results reset column widths
- [ ] Multi-database results have independent widths
- [ ] Works on touch devices
- [ ] Keyboard accessible (arrow keys adjust width)
- [ ] No performance degradation during resize

## Estimated Complexity

| Phase | Complexity |
|-------|------------|
| Phase 1: Table Layout | Low |
| Phase 2: State Management | Medium |
| Phase 3: Resize Handle | Low |
| Phase 4: Drag Logic | Medium |
| Phase 5: Header Component | Low |
| Phase 6-8: Table Integration | Medium |
| Phase 9: Overflow Handling | Low |
| Phase 10: Auto-Fit | Medium |
| Phase 11: Cursor Management | Low |
| Phase 12: Accessibility | Low |

## Notes

- Consider implementing Table Sorting first as it's simpler
- The combined `InteractiveTableHeader` component reduces duplication
- `table-layout: fixed` is required - this changes table behavior significantly
- Test thoroughly with varying content lengths (very short, very long, nulls)
- Consider adding a "Reset widths" button to table toolbar
