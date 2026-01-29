import { useState, useMemo, useCallback } from 'react';

/**
 * Configuration for current sort state
 */
export interface SortConfig {
  /** Column name to sort by, null if unsorted */
  column: string | null;
  /** Sort direction */
  direction: 'asc' | 'desc';
}

/**
 * Return type for useTableSort hook
 */
export interface UseTableSortReturn<T> {
  /** Data sorted according to current config */
  sortedData: T[];
  /** Current sort configuration */
  sortConfig: SortConfig;
  /** Handler to toggle/set sort on a column */
  handleSort: (column: string) => void;
  /** Get sort direction for a column (null if not sorted by this column) */
  getSortDirection: (column: string) => 'asc' | 'desc' | null;
  /** Reset sort to initial state */
  resetSort: () => void;
}

/**
 * Options for useTableSort hook
 */
export interface UseTableSortOptions {
  /** Default column to sort by */
  defaultColumn?: string | null;
  /** Default sort direction */
  defaultDirection?: 'asc' | 'desc';
  /** Callback when sort changes (for resetting pagination) */
  onSortChange?: (config: SortConfig) => void;
}

/**
 * Check if a value is a numeric string (type predicate)
 */
function isNumericString(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  if (value.trim() === '') return false;
  return !isNaN(parseFloat(value)) && isFinite(Number(value));
}

/**
 * Check if a value is a date string (ISO format with dashes) (type predicate)
 */
function isDateString(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  // Must contain dashes and parse to valid date
  if (!value.includes('-')) return false;
  const date = new Date(value);
  return !isNaN(date.getTime());
}

/**
 * Compare two values for sorting
 */
function compareValues(a: unknown, b: unknown, direction: 'asc' | 'desc'): number {
  // Nulls/undefined always sort to end regardless of direction
  const aIsNull = a === null || a === undefined;
  const bIsNull = b === null || b === undefined;

  if (aIsNull && bIsNull) return 0;
  if (aIsNull) return 1;
  if (bIsNull) return -1;

  const multiplier = direction === 'asc' ? 1 : -1;

  // Number comparison
  if (typeof a === 'number' && typeof b === 'number') {
    return (a - b) * multiplier;
  }

  // Numeric string detection - sort numerically
  if (isNumericString(a) && isNumericString(b)) {
    return (parseFloat(a) - parseFloat(b)) * multiplier;
  }

  // Date string detection - sort chronologically
  if (isDateString(a) && isDateString(b)) {
    return (new Date(a).getTime() - new Date(b).getTime()) * multiplier;
  }

  // String comparison (case-insensitive)
  const strA = String(a).toLowerCase();
  const strB = String(b).toLowerCase();
  return strA.localeCompare(strB) * multiplier;
}

/**
 * Sort an array of objects by a column with smart type detection
 *
 * @param data - Array of objects to sort
 * @param config - Sort configuration (column and direction)
 * @returns Sorted array (new array, does not mutate original)
 *
 * @example
 * ```tsx
 * const sorted = sortData(results, { column: 'name', direction: 'asc' });
 * ```
 */
export function sortData<T extends Record<string, unknown>>(
  data: T[],
  config: SortConfig
): T[] {
  if (!config.column || data.length === 0) {
    return data;
  }

  return [...data].sort((a, b) =>
    compareValues(
      a[config.column!],
      b[config.column!],
      config.direction
    )
  );
}

/**
 * A reusable hook for client-side table sorting
 *
 * @param data - Array of objects to sort
 * @param options - Configuration options
 * @returns Sorted data and sort control functions
 *
 * @example
 * ```tsx
 * const { sortedData, sortConfig, handleSort } = useTableSort(results, {
 *   onSortChange: () => setCurrentPage(1)
 * });
 * ```
 */
export function useTableSort<T extends Record<string, unknown>>(
  data: T[],
  options: UseTableSortOptions = {}
): UseTableSortReturn<T> {
  const {
    defaultColumn = null,
    defaultDirection = 'asc',
    onSortChange
  } = options;

  const [sortConfig, setSortConfig] = useState<SortConfig>({
    column: defaultColumn,
    direction: defaultDirection,
  });

  const handleSort = useCallback((column: string) => {
    setSortConfig((prev) => {
      const newConfig: SortConfig = {
        column,
        // Toggle direction if same column, otherwise start with ascending
        direction: prev.column === column && prev.direction === 'asc' ? 'desc' : 'asc',
      };
      onSortChange?.(newConfig);
      return newConfig;
    });
  }, [onSortChange]);

  const getSortDirection = useCallback(
    (column: string): 'asc' | 'desc' | null => {
      return sortConfig.column === column ? sortConfig.direction : null;
    },
    [sortConfig]
  );

  const resetSort = useCallback(() => {
    const initialConfig: SortConfig = {
      column: defaultColumn,
      direction: defaultDirection
    };
    setSortConfig(initialConfig);
    onSortChange?.(initialConfig);
  }, [defaultColumn, defaultDirection, onSortChange]);

  const sortedData = useMemo(() => sortData(data, sortConfig), [data, sortConfig.column, sortConfig.direction]);

  return {
    sortedData,
    sortConfig,
    handleSort,
    getSortDirection,
    resetSort,
  };
}
