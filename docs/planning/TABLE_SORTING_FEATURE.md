# Table Sorting Feature Plan

**Created:** 2026-01-25
**Status:** Planning
**Priority:** Enhancement

## Overview

Implement client-side column sorting for all query result tables in the Database Guru frontend. Users will be able to click on column headers to sort data ascending/descending.

## Current State

### Tables Requiring Sorting

| Component | File | Current Sorting |
|-----------|------|-----------------|
| QueryResults | `frontend/src/components/QueryResults.tsx` | None |
| MultiDatabaseResults | `frontend/src/components/MultiDatabaseResults.tsx` | None |
| StreamingQueryResults | `frontend/src/components/StreamingQueryResults.tsx` | None |

### Existing Pattern Reference

`ToolUsageStats.tsx` has basic client-side sorting implementation:
- Dropdown-based sort selection
- State management with `sortBy` state variable
- Sorted array computed on render

## Implementation Plan

### Phase 1: Core Sorting Hook

Create a reusable sorting hook for consistent behavior across all tables.

**File:** `frontend/src/hooks/useTableSort.ts`

```typescript
interface SortConfig {
  column: string | null;
  direction: 'asc' | 'desc';
}

interface UseTableSortReturn<T> {
  sortedData: T[];
  sortConfig: SortConfig;
  handleSort: (column: string) => void;
  getSortIcon: (column: string) => 'asc' | 'desc' | null;
}

function useTableSort<T extends Record<string, any>>(
  data: T[],
  defaultColumn?: string,
  defaultDirection?: 'asc' | 'desc'
): UseTableSortReturn<T>
```

**Sorting Logic:**
- Handle multiple data types: strings, numbers, dates, nulls
- Null values sorted to end regardless of direction
- Case-insensitive string sorting
- Numeric string detection (sort "100" > "20" numerically)
- Date string detection and proper chronological sorting

### Phase 2: Sortable Header Component

Create a reusable sortable column header component.

**File:** `frontend/src/components/SortableTableHeader.tsx`

```typescript
interface SortableTableHeaderProps {
  column: string;
  label?: string;
  sortConfig: SortConfig;
  onSort: (column: string) => void;
  className?: string;
}
```

**Features:**
- Click handler to toggle sort direction
- Visual indicator (arrow icon) for current sort state
- Hover state to indicate sortability
- Keyboard accessible (Enter/Space to sort)

**Icons (from Lucide):**
- `ArrowUp` - Ascending sort active
- `ArrowDown` - Descending sort active
- `ArrowUpDown` - Unsorted/hover state

### Phase 3: QueryResults Integration

**File:** `frontend/src/components/QueryResults.tsx`

**Changes:**
1. Import and use `useTableSort` hook
2. Replace static `<th>` elements with `SortableTableHeader`
3. Apply sorting before pagination (sort full dataset, then paginate)
4. Persist sort state across pagination changes
5. Reset sort when new query results arrive

**Sort Flow:**
```
Raw Results → Sort → Paginate → Render
```

**Considerations:**
- Sorting must happen on the full dataset before pagination slicing
- Page number should reset to 1 when sort changes
- Sort state could optionally persist in URL query params

### Phase 4: MultiDatabaseResults Integration

**File:** `frontend/src/components/MultiDatabaseResults.tsx`

**Changes:**
1. Each database result section gets independent sorting
2. Maintain sort state per connection ID
3. Use same `useTableSort` hook per result set

**State Structure:**
```typescript
const [sortConfigs, setSortConfigs] = useState<Record<string, SortConfig>>({});
```

### Phase 5: StreamingQueryResults Integration

**File:** `frontend/src/components/StreamingQueryResults.tsx`

**Special Considerations:**
- Data arrives progressively in batches
- Sorting a growing dataset has UX implications
- Two approaches:

  **Option A: Sort on complete** (Recommended)
  - Disable sorting while streaming
  - Enable sort headers after stream completes
  - Simpler UX, no jarring re-sorts during load

  **Option B: Live re-sort**
  - Sort after each batch arrival
  - Can cause visual instability
  - Higher performance cost

**Recommendation:** Option A - Sort only after streaming completes

### Phase 6: Visual Design

**Header Styling (Tailwind classes):**

```css
/* Base header */
.sortable-header {
  @apply cursor-pointer select-none hover:bg-white/10 transition-colors;
}

/* Sort indicator */
.sort-icon {
  @apply ml-1 h-3 w-3 opacity-50;
}

.sort-icon-active {
  @apply opacity-100 text-indigo-400;
}

/* Hover state */
.sortable-header:hover .sort-icon {
  @apply opacity-75;
}
```

**Visual States:**
| State | Appearance |
|-------|------------|
| Unsorted | No icon or faded `ArrowUpDown` |
| Hover (unsorted) | Faded `ArrowUpDown` appears |
| Ascending | `ArrowUp` icon, highlighted |
| Descending | `ArrowDown` icon, highlighted |

### Phase 7: Accessibility

- Column headers must have `role="columnheader"`
- Add `aria-sort="ascending"`, `aria-sort="descending"`, or `aria-sort="none"`
- Headers must be keyboard focusable (`tabindex="0"`)
- Support Enter and Space key to trigger sort
- Screen reader announcement on sort change

### Phase 8: Performance Optimization

**For large datasets (1000+ rows):**

1. **Memoization:**
   ```typescript
   const sortedData = useMemo(() => {
     return sortData(data, sortConfig);
   }, [data, sortConfig.column, sortConfig.direction]);
   ```

2. **Virtualization consideration:**
   - If performance issues arise with very large tables
   - Consider `react-window` or `@tanstack/react-virtual`
   - Document as future enhancement if needed

3. **Web Worker option:**
   - For datasets >10,000 rows
   - Offload sorting to worker thread
   - Mark as stretch goal

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/hooks/useTableSort.ts` | Create | Reusable sorting hook |
| `frontend/src/components/SortableTableHeader.tsx` | Create | Sortable header component |
| `frontend/src/components/QueryResults.tsx` | Modify | Integrate sorting |
| `frontend/src/components/MultiDatabaseResults.tsx` | Modify | Integrate sorting per DB |
| `frontend/src/components/StreamingQueryResults.tsx` | Modify | Integrate post-stream sorting |

## Testing Strategy

### Unit Tests

**`frontend/src/hooks/__tests__/useTableSort.test.ts`:**
- Sort strings ascending/descending
- Sort numbers ascending/descending
- Sort dates ascending/descending
- Handle null/undefined values
- Handle mixed type columns
- Handle empty arrays
- Toggle direction on same column click
- Reset to ascending on new column click

**`frontend/src/components/__tests__/SortableTableHeader.test.tsx`:**
- Renders correct sort icon based on state
- Calls onSort with correct column
- Keyboard accessibility (Enter/Space)
- Correct ARIA attributes

### Integration Tests

- Sort persists across pagination
- Sort resets on new query
- Multi-database independent sorting
- Streaming table sort activation after complete

### E2E Tests

**`frontend/e2e/table-sorting.spec.ts`:**
- Execute query, click column header, verify sorted order
- Click same header again, verify reversed order
- Click different column, verify new sort
- Navigate pagination, verify sort preserved
- New query clears previous sort

## Future Enhancements

These are out of scope for initial implementation but documented for future reference:

1. **Multi-column sorting** - Shift+click for secondary sort
2. **Custom sort functions** - Per-column sort comparators
3. **Server-side sorting** - For very large result sets
4. **Sort persistence** - Remember sort preference per query/table
5. **Column filtering** - Filter values within sorted column
6. **Column resizing** - Adjust column widths
7. **Column reordering** - Drag to rearrange columns
8. **Pin/freeze columns** - Keep columns visible while scrolling

## Dependencies

No new npm packages required. Uses:
- Existing React hooks (useState, useMemo, useCallback)
- Existing Lucide icons (ArrowUp, ArrowDown, ArrowUpDown)
- Existing Tailwind classes

## Acceptance Criteria

- [ ] Clicking any column header sorts table by that column
- [ ] First click sorts ascending, second click sorts descending
- [ ] Third click on same column returns to ascending
- [ ] Sort indicator icon shows current sort state
- [ ] Sorting works with pagination (sort full data, then paginate)
- [ ] Page resets to 1 when sort changes
- [ ] New query results clear sort state
- [ ] Multi-database results have independent sorting
- [ ] Streaming results support sorting after stream completes
- [ ] Null values sort to bottom regardless of direction
- [ ] Numbers sort numerically (not lexicographically)
- [ ] Dates sort chronologically
- [ ] Keyboard accessible (Enter/Space to sort)
- [ ] Screen reader announces sort changes
- [ ] No performance degradation for tables with <1000 rows

## Estimated Complexity

| Phase | Complexity |
|-------|------------|
| Phase 1: Core Hook | Low |
| Phase 2: Header Component | Low |
| Phase 3: QueryResults | Medium |
| Phase 4: MultiDatabaseResults | Medium |
| Phase 5: StreamingQueryResults | Medium |
| Phase 6: Visual Design | Low |
| Phase 7: Accessibility | Low |
| Phase 8: Performance | Low (unless virtualization needed) |

## Notes

- The existing `ToolUsageStats.tsx` sorting can remain as-is (uses dropdown, not column headers)
- Card-based list components (mappings, patterns) are out of scope for this feature
- Consider adding a user preference to disable sorting if requested
