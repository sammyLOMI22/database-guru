/**
 * useTableSort Hook Tests
 *
 * Tests the table sorting hook with various data types and edge cases
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTableSort } from '../../src/hooks/useTableSort';

describe('useTableSort', () => {
  describe('string sorting', () => {
    it('sorts strings ascending', () => {
      const data = [{ name: 'Charlie' }, { name: 'Alice' }, { name: 'Bob' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([
        { name: 'Alice' },
        { name: 'Bob' },
        { name: 'Charlie' },
      ]);
      expect(result.current.sortConfig.direction).toBe('asc');
    });

    it('sorts strings descending on second click', () => {
      const data = [{ name: 'Charlie' }, { name: 'Alice' }, { name: 'Bob' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));
      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([
        { name: 'Charlie' },
        { name: 'Bob' },
        { name: 'Alice' },
      ]);
      expect(result.current.sortConfig.direction).toBe('desc');
    });

    it('sorts strings case-insensitively', () => {
      const data = [{ name: 'bob' }, { name: 'Alice' }, { name: 'CHARLIE' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData.map((r) => r.name)).toEqual([
        'Alice',
        'bob',
        'CHARLIE',
      ]);
    });
  });

  describe('number sorting', () => {
    it('sorts numbers numerically ascending', () => {
      const data = [{ value: 100 }, { value: 20 }, { value: 3 }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('value'));

      expect(result.current.sortedData).toEqual([
        { value: 3 },
        { value: 20 },
        { value: 100 },
      ]);
    });

    it('sorts numbers numerically descending', () => {
      const data = [{ value: 100 }, { value: 20 }, { value: 3 }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('value'));
      act(() => result.current.handleSort('value'));

      expect(result.current.sortedData).toEqual([
        { value: 100 },
        { value: 20 },
        { value: 3 },
      ]);
    });

    it('sorts numeric strings numerically (not lexicographically)', () => {
      const data = [{ value: '100' }, { value: '20' }, { value: '3' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('value'));

      expect(result.current.sortedData).toEqual([
        { value: '3' },
        { value: '20' },
        { value: '100' },
      ]);
    });

    it('handles negative numbers correctly', () => {
      const data = [{ value: 5 }, { value: -10 }, { value: 0 }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('value'));

      expect(result.current.sortedData).toEqual([
        { value: -10 },
        { value: 0 },
        { value: 5 },
      ]);
    });
  });

  describe('date sorting', () => {
    it('sorts date strings chronologically ascending', () => {
      const data = [
        { date: '2024-03-15' },
        { date: '2024-01-01' },
        { date: '2024-02-20' },
      ];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('date'));

      expect(result.current.sortedData).toEqual([
        { date: '2024-01-01' },
        { date: '2024-02-20' },
        { date: '2024-03-15' },
      ]);
    });

    it('sorts date strings chronologically descending', () => {
      const data = [
        { date: '2024-03-15' },
        { date: '2024-01-01' },
        { date: '2024-02-20' },
      ];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('date'));
      act(() => result.current.handleSort('date'));

      expect(result.current.sortedData).toEqual([
        { date: '2024-03-15' },
        { date: '2024-02-20' },
        { date: '2024-01-01' },
      ]);
    });

    it('handles ISO datetime strings', () => {
      const data = [
        { date: '2024-03-15T10:30:00Z' },
        { date: '2024-03-15T08:00:00Z' },
        { date: '2024-03-15T15:45:00Z' },
      ];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('date'));

      expect(result.current.sortedData).toEqual([
        { date: '2024-03-15T08:00:00Z' },
        { date: '2024-03-15T10:30:00Z' },
        { date: '2024-03-15T15:45:00Z' },
      ]);
    });
  });

  describe('null handling', () => {
    it('sorts null values to end when ascending', () => {
      const data = [{ name: null }, { name: 'Alice' }, { name: 'Bob' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([
        { name: 'Alice' },
        { name: 'Bob' },
        { name: null },
      ]);
    });

    it('sorts null values to end when descending', () => {
      const data = [{ name: null }, { name: 'Alice' }, { name: 'Bob' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));
      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([
        { name: 'Bob' },
        { name: 'Alice' },
        { name: null },
      ]);
    });

    it('sorts undefined values to end', () => {
      const data = [{ name: undefined }, { name: 'Alice' }, { name: 'Bob' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([
        { name: 'Alice' },
        { name: 'Bob' },
        { name: undefined },
      ]);
    });

    it('keeps multiple null values at end', () => {
      const data = [
        { name: null },
        { name: 'Alice' },
        { name: null },
        { name: 'Bob' },
      ];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData.slice(0, 2)).toEqual([
        { name: 'Alice' },
        { name: 'Bob' },
      ]);
      expect(result.current.sortedData.slice(2).every((r) => r.name === null)).toBe(true);
    });
  });

  describe('state management', () => {
    it('returns unsorted data when no column selected', () => {
      const data = [{ name: 'Charlie' }, { name: 'Alice' }];
      const { result } = renderHook(() => useTableSort(data));

      expect(result.current.sortedData).toEqual(data);
      expect(result.current.sortConfig.column).toBeNull();
    });

    it('resets to ascending when clicking new column', () => {
      const data = [
        { name: 'Charlie', age: 30 },
        { name: 'Alice', age: 25 },
      ];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));
      act(() => result.current.handleSort('name')); // Now descending
      act(() => result.current.handleSort('age')); // New column

      expect(result.current.sortConfig.column).toBe('age');
      expect(result.current.sortConfig.direction).toBe('asc');
    });

    it('calls onSortChange callback when sort changes', () => {
      const onSortChange = vi.fn();
      const data = [{ name: 'Alice' }];
      const { result } = renderHook(() =>
        useTableSort(data, { onSortChange })
      );

      act(() => result.current.handleSort('name'));

      expect(onSortChange).toHaveBeenCalledWith({
        column: 'name',
        direction: 'asc',
      });
    });

    it('getSortDirection returns correct value for sorted column', () => {
      const data = [{ name: 'Alice' }];
      const { result } = renderHook(() => useTableSort(data));

      expect(result.current.getSortDirection('name')).toBeNull();

      act(() => result.current.handleSort('name'));
      expect(result.current.getSortDirection('name')).toBe('asc');

      act(() => result.current.handleSort('name'));
      expect(result.current.getSortDirection('name')).toBe('desc');
    });

    it('getSortDirection returns null for unsorted columns', () => {
      const data = [{ name: 'Alice', age: 25 }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.getSortDirection('name')).toBe('asc');
      expect(result.current.getSortDirection('age')).toBeNull();
    });

    it('resetSort clears sort state', () => {
      const data = [{ name: 'Charlie' }, { name: 'Alice' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));
      expect(result.current.sortConfig.column).toBe('name');

      act(() => result.current.resetSort());
      expect(result.current.sortConfig.column).toBeNull();
      expect(result.current.sortedData).toEqual(data);
    });

    it('resetSort calls onSortChange callback', () => {
      const onSortChange = vi.fn();
      const data = [{ name: 'Alice' }];
      const { result } = renderHook(() =>
        useTableSort(data, { onSortChange })
      );

      act(() => result.current.handleSort('name'));
      onSortChange.mockClear();

      act(() => result.current.resetSort());

      expect(onSortChange).toHaveBeenCalledWith({
        column: null,
        direction: 'asc',
      });
    });
  });

  describe('edge cases', () => {
    it('handles empty array', () => {
      const { result } = renderHook(() => useTableSort([]));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([]);
    });

    it('handles single item array', () => {
      const data = [{ name: 'Alice' }];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(result.current.sortedData).toEqual([{ name: 'Alice' }]);
    });

    it('does not mutate original array', () => {
      const data = [{ name: 'Charlie' }, { name: 'Alice' }];
      const originalData = [...data];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('name'));

      expect(data).toEqual(originalData);
      expect(result.current.sortedData).not.toBe(data);
    });

    it('handles objects with many columns', () => {
      const data = [
        { a: 1, b: 2, c: 3, d: 4, e: 5 },
        { a: 5, b: 4, c: 3, d: 2, e: 1 },
      ];
      const { result } = renderHook(() => useTableSort(data));

      act(() => result.current.handleSort('e'));

      expect(result.current.sortedData[0].e).toBe(1);
      expect(result.current.sortedData[1].e).toBe(5);
    });

    it('handles mixed type values gracefully', () => {
      const data = [
        { value: 'hello' },
        { value: 123 },
        { value: null },
      ];
      const { result } = renderHook(() => useTableSort(data));

      // Should not throw
      act(() => result.current.handleSort('value'));

      expect(result.current.sortedData.length).toBe(3);
      // null should be at end
      expect(result.current.sortedData[2].value).toBeNull();
    });
  });

  describe('default options', () => {
    it('uses default column when provided', () => {
      const data = [{ name: 'Charlie' }, { name: 'Alice' }];
      const { result } = renderHook(() =>
        useTableSort(data, { defaultColumn: 'name' })
      );

      expect(result.current.sortConfig.column).toBe('name');
      expect(result.current.sortedData).toEqual([
        { name: 'Alice' },
        { name: 'Charlie' },
      ]);
    });

    it('uses default direction when provided', () => {
      const data = [{ name: 'Alice' }, { name: 'Charlie' }];
      const { result } = renderHook(() =>
        useTableSort(data, { defaultColumn: 'name', defaultDirection: 'desc' })
      );

      expect(result.current.sortConfig.direction).toBe('desc');
      expect(result.current.sortedData).toEqual([
        { name: 'Charlie' },
        { name: 'Alice' },
      ]);
    });
  });
});
