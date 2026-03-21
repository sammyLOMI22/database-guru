// Client-side change tracker for Edit Mode — Phase 18
import { useCallback, useState } from 'react';
import type { RowChange, CellChange, ChangeSummary } from '../types/dml';
import { hashPK } from '../utils/dmlUtils';

export function useChangeTracker(tableName: string) {
  const [changes, setChanges] = useState<Map<string, RowChange>>(new Map());

  const trackUpdate = useCallback(
    (
      primaryKey: Record<string, any>,
      column: string,
      oldValue: any,
      newValue: any
    ) => {
      setChanges((prev) => {
        const next = new Map(prev);
        const key = hashPK(primaryKey);
        const existing = next.get(key);

        if (existing && existing.change_type === 'UPDATE') {
          // Merge with existing update
          const cellIdx = existing.changes.findIndex(
            (c) => c.column === column
          );
          const cellChange: CellChange = {
            column,
            old_value: oldValue,
            new_value: newValue,
          };
          if (cellIdx >= 0) {
            // Check if value reverted to original
            if (existing.changes[cellIdx].old_value === newValue) {
              existing.changes.splice(cellIdx, 1);
              if (existing.changes.length === 0) {
                next.delete(key);
              }
            } else {
              existing.changes[cellIdx] = cellChange;
            }
          } else {
            existing.changes.push(cellChange);
          }
        } else {
          next.set(key, {
            change_type: 'UPDATE',
            table_name: tableName,
            primary_key: primaryKey,
            changes: [{ column, old_value: oldValue, new_value: newValue }],
          });
        }

        return next;
      });
    },
    [tableName]
  );

  const trackInsert = useCallback(
    (rowData: Record<string, any>) => {
      setChanges((prev) => {
        const next = new Map(prev);
        const tempKey = `__new_${Date.now()}_${Math.random().toString(36).slice(2)}`;
        next.set(tempKey, {
          change_type: 'INSERT',
          table_name: tableName,
          primary_key: {},
          changes: [],
          new_row_data: rowData,
        });
        return next;
      });
    },
    [tableName]
  );

  const trackDelete = useCallback(
    (primaryKey: Record<string, any>) => {
      setChanges((prev) => {
        const next = new Map(prev);
        const key = hashPK(primaryKey);

        // If this was a pending insert, just remove it
        if (key.startsWith('__new_')) {
          next.delete(key);
        } else {
          // Remove any pending UPDATE for this row
          next.delete(key);
          // Add DELETE
          next.set(key, {
            change_type: 'DELETE',
            table_name: tableName,
            primary_key: primaryKey,
            changes: [],
          });
        }

        return next;
      });
    },
    [tableName]
  );

  const discardChange = useCallback((primaryKey: Record<string, any>) => {
    setChanges((prev) => {
      const next = new Map(prev);
      next.delete(hashPK(primaryKey));
      return next;
    });
  }, []);

  const discardAll = useCallback(() => {
    setChanges(new Map());
  }, []);

  const getChanges = useCallback((): RowChange[] => {
    return Array.from(changes.values());
  }, [changes]);

  const getSummary = useCallback((): ChangeSummary => {
    const summary: ChangeSummary = { INSERT: 0, UPDATE: 0, DELETE: 0, total: 0 };
    for (const change of changes.values()) {
      summary[change.change_type]++;
      summary.total++;
    }
    return summary;
  }, [changes]);

  const hasChanges = changes.size > 0;

  const isRowModified = useCallback(
    (primaryKey: Record<string, any>): boolean => {
      return changes.has(hashPK(primaryKey));
    },
    [changes]
  );

  const isRowDeleted = useCallback(
    (primaryKey: Record<string, any>): boolean => {
      const change = changes.get(hashPK(primaryKey));
      return change?.change_type === 'DELETE';
    },
    [changes]
  );

  const getCellChange = useCallback(
    (primaryKey: Record<string, any>, column: string): CellChange | undefined => {
      const change = changes.get(hashPK(primaryKey));
      if (!change || change.change_type !== 'UPDATE') return undefined;
      return change.changes.find((c) => c.column === column);
    },
    [changes]
  );

  return {
    changes,
    trackUpdate,
    trackInsert,
    trackDelete,
    discardChange,
    discardAll,
    getChanges,
    getSummary,
    hasChanges,
    isRowModified,
    isRowDeleted,
    getCellChange,
  };
}
