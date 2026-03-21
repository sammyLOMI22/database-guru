// Editable query results table — Phase 18
// Replaces QueryResults table when edit mode is active
import { useState, useMemo } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { useTableSort } from '../../hooks/useTableSort';
import { hashPK } from '../../utils/dmlUtils';
import { SortableTableHeader } from '../SortableTableHeader';
import { EditableCell } from './EditableCell';
import { ChangesSummaryBar } from './ChangesSummaryBar';
import type { WritePermission, TableInfo, RowChange } from '../../types/dml';
import type { useChangeTracker } from '../../hooks/useChangeTracker';

interface EditableQueryResultsProps {
  results: Record<string, any>[];
  connectionId: number;
  tableInfo: TableInfo;
  permissions: WritePermission;
  changeTracker: ReturnType<typeof useChangeTracker>;
  onPreview: () => void;
  onAddRow: () => void;
}

export function EditableQueryResults({
  results,
  connectionId,
  tableInfo,
  permissions,
  changeTracker,
  onPreview,
  onAddRow,
}: EditableQueryResultsProps) {
  const [pageSize, setPageSize] = useState(25);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());

  const columns = useMemo(() => {
    if (!results || results.length === 0) return [];
    return Object.keys(results[0]);
  }, [results]);

  const pkColumns = new Set(tableInfo.primary_key_columns);

  const { sortedData, sortConfig, handleSort } = useTableSort(results);

  // Include new rows from change tracker
  const newRows = useMemo(() => {
    return changeTracker
      .getChanges()
      .filter((c): c is RowChange & { new_row_data: Record<string, any> } =>
        c.change_type === 'INSERT' && c.new_row_data != null
      );
  }, [changeTracker]);

  const totalRows = sortedData.length + newRows.length;
  const startIdx = (currentPage - 1) * pageSize;
  const endIdx = Math.min(startIdx + pageSize, sortedData.length);
  const paginatedResults = sortedData.slice(startIdx, endIdx);
  const totalPages = Math.ceil(totalRows / pageSize);

  const buildPK = (row: Record<string, any>): Record<string, any> => {
    const pk: Record<string, any> = {};
    for (const col of tableInfo.primary_key_columns) {
      pk[col] = row[col];
    }
    return pk;
  };

  const toggleRowSelection = (pk: Record<string, any>) => {
    const key = hashPK(pk);
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleDeleteSelected = () => {
    for (const row of paginatedResults) {
      const pk = buildPK(row);
      if (selectedRows.has(hashPK(pk))) {
        changeTracker.trackDelete(pk);
      }
    }
    setSelectedRows(new Set());
  };

  const handleDeleteRow = (row: Record<string, any>) => {
    changeTracker.trackDelete(buildPK(row));
  };

  return (
    <div className="relative">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-2 border-b border-white/10">
        <div className="flex items-center gap-3">
          {permissions.allow_insert && (
            <button
              onClick={onAddRow}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-emerald-400 hover:bg-emerald-500/10 transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Row
            </button>
          )}
          {permissions.allow_delete && selectedRows.size > 0 && (
            <button
              onClick={handleDeleteSelected}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-red-400 hover:bg-red-500/10 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete {selectedRows.size}
            </button>
          )}
        </div>
        <span className="text-[11px] text-gray-500 uppercase tracking-widest">
          {totalRows} row{totalRows !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-white/10 bg-black/5 dark:bg-white/5">
            <tr>
              {permissions.allow_delete && (
                <th className="w-10 px-3 py-3" />
              )}
              {columns.map((column) => (
                <SortableTableHeader
                  key={column}
                  column={column}
                  sortConfig={sortConfig}
                  onSort={handleSort}
                  className={`px-5 py-3 text-left text-[11px] font-black uppercase tracking-[0.15em] transition-colors ${
                    pkColumns.has(column)
                      ? 'text-blue-400'
                      : 'text-gray-600 dark:text-gray-400'
                  } hover:bg-white/10`}
                />
              ))}
              {permissions.allow_delete && (
                <th className="w-10 px-3 py-3" />
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {paginatedResults.map((row) => {
              const pk = buildPK(row);
              const pkHash = hashPK(pk);
              const isDeleted = changeTracker.isRowDeleted(pk);
              const isModified = changeTracker.isRowModified(pk);

              return (
                <tr
                  key={pkHash}
                  className={`transition-colors ${
                    isDeleted
                      ? 'bg-red-500/5'
                      : isModified
                      ? 'bg-amber-500/5'
                      : 'hover:bg-white/5'
                  }`}
                >
                  {permissions.allow_delete && (
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={selectedRows.has(pkHash)}
                        onChange={() => toggleRowSelection(pk)}
                        disabled={isDeleted}
                        className="rounded border-gray-600 bg-transparent text-amber-500 focus:ring-amber-500/30"
                      />
                    </td>
                  )}
                  {columns.map((column) => (
                    <EditableCell
                      key={column}
                      value={row[column]}
                      column={column}
                      isPrimaryKey={pkColumns.has(column)}
                      isDeleted={isDeleted}
                      cellChange={changeTracker.getCellChange(pk, column)}
                      onUpdate={(col, oldVal, newVal) =>
                        changeTracker.trackUpdate(pk, col, oldVal, newVal)
                      }
                    />
                  ))}
                  {permissions.allow_delete && (
                    <td className="px-3 py-3">
                      {!isDeleted ? (
                        <button
                          onClick={() => handleDeleteRow(row)}
                          className="text-gray-600 hover:text-red-400 transition-colors"
                          title="Delete row"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => changeTracker.discardChange(pk)}
                          className="text-red-400/60 hover:text-gray-400 transition-colors text-xs"
                          title="Undo delete"
                        >
                          Undo
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}

            {/* New rows (from inserts) */}
            {newRows.map((change, idx) => (
              <tr
                key={`new-${idx}`}
                className="bg-emerald-500/5"
              >
                {permissions.allow_delete && <td className="px-3 py-3" />}
                {columns.map((column) => (
                  <td
                    key={column}
                    className="px-5 py-3 text-sm font-mono text-emerald-300"
                  >
                    {change.new_row_data[column] === undefined ? (
                      <span className="text-gray-500 italic text-xs">-</span>
                    ) : change.new_row_data[column] === null ? (
                      <span className="text-gray-400 italic text-xs">null</span>
                    ) : (
                      String(change.new_row_data[column])
                    )}
                  </td>
                ))}
                {permissions.allow_delete && <td className="px-3 py-3" />}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalRows > 10 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-white/5 bg-black/5 dark:bg-white/5">
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-black uppercase tracking-widest text-gray-500">
              Per page
            </span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(parseInt(e.target.value));
                setCurrentPage(1);
              }}
              className="glass-panel px-2 py-1 text-xs text-gray-300 border-0 focus:ring-1 focus:ring-emerald-500/30"
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2 py-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              Prev
            </button>
            <span className="text-xs text-gray-400">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2 py-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Changes summary bar */}
      {changeTracker.hasChanges && (
        <ChangesSummaryBar
          summary={changeTracker.getSummary()}
          onPreview={onPreview}
          onDiscard={changeTracker.discardAll}
          connectionId={connectionId}
          changes={changeTracker.getChanges()}
        />
      )}
    </div>
  );
}
