// Wraps a single database result with edit mode — Phase 18
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useEditMode } from '../../hooks/useEditMode';
import { useChangeTracker } from '../../hooks/useChangeTracker';
import { dmlAPI } from '../../services/dmlApi';
import { EditModeToggle } from './EditModeToggle';
import { EditableQueryResults } from './EditableQueryResults';
import { AddRowForm } from './AddRowForm';
import type { TableInfo } from '../../types/dml';

interface EditModeWrapperProps {
  connectionId: number;
  databaseType: string;
  sql: string;
  results: Record<string, any>[];
  children: React.ReactNode; // Regular table/chart rendering
}

/**
 * Parse a simple "SELECT ... FROM table_name ..." to extract the table name.
 * Returns null for JOINs, subqueries, or unparseable SQL.
 */
function extractTableName(sql: string): string | null {
  if (!sql) return null;
  const normalized = sql.replace(/\s+/g, ' ').trim();

  // Reject JOINs and subqueries
  if (/\bJOIN\b/i.test(normalized)) return null;
  if (/\(\s*SELECT\b/i.test(normalized)) return null;

  // Match: FROM table_name (with optional schema prefix)
  const match = normalized.match(
    /\bFROM\s+(?:["'`\[]?(\w+)["'`\]]?\.)?["'`\[]?(\w+)["'`\]]?/i
  );
  if (!match) return null;
  return match[2]; // table name without schema
}

export function EditModeWrapper({
  connectionId,
  databaseType,
  sql,
  results,
  children,
}: EditModeWrapperProps) {
  const [showAddRow, setShowAddRow] = useState(false);

  const tableName = useMemo(() => extractTableName(sql), [sql]);

  const editMode = useEditMode({
    connectionId,
    databaseType,
  });

  const changeTracker = useChangeTracker(tableName || '');

  // Fetch table info when edit mode is active and we have a table name
  const { data: tableInfo } = useQuery<TableInfo>({
    queryKey: ['table-info', connectionId, tableName],
    queryFn: () => dmlAPI.getTableInfo(connectionId, tableName!),
    enabled: editMode.isEditMode && tableName !== null,
    staleTime: 60_000,
  });

  const effectiveDisabledReason =
    editMode.disabledReason ||
    (!tableName
      ? 'Edit mode requires a single-table query (no JOINs or subqueries)'
      : null);

  const canEdit = editMode.canEdit && tableName !== null;

  const handleToggle = () => {
    if (canEdit) {
      if (editMode.isEditMode && changeTracker.hasChanges) {
        if (!window.confirm('You have unsaved changes. Discard them?')) {
          return;
        }
        changeTracker.discardAll();
      }
      editMode.toggleEditMode();
    }
  };

  return (
    <div>
      {/* Edit mode toggle bar */}
      <div className="flex items-center justify-end px-2 py-1">
        <EditModeToggle
          isEditMode={editMode.isEditMode}
          canEdit={canEdit}
          onToggle={handleToggle}
          disabledReason={effectiveDisabledReason}
        />
      </div>

      {/* Conditional rendering: editable table or regular children */}
      {editMode.isEditMode && tableInfo && editMode.permissions ? (
        <>
          <EditableQueryResults
            results={results}
            connectionId={connectionId}
            tableInfo={tableInfo}
            permissions={editMode.permissions}
            changeTracker={changeTracker}
            onPreview={() => {}}
            onAddRow={() => setShowAddRow(true)}
          />
          <AddRowForm
            isOpen={showAddRow}
            onClose={() => setShowAddRow(false)}
            onAdd={(rowData) => changeTracker.trackInsert(rowData)}
            tableInfo={tableInfo}
          />
        </>
      ) : (
        children
      )}
    </div>
  );
}
