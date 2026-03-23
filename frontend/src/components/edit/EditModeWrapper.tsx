// Wraps a single database result with edit mode — Phase 18
import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useEditMode } from '../../hooks/useEditMode';
import { useChangeTracker } from '../../hooks/useChangeTracker';
import { dmlAPI } from '../../services/dmlApi';
import { EditModeToggle } from './EditModeToggle';
import { EditableQueryResults } from './EditableQueryResults';
import { AddRowForm } from './AddRowForm';
import type { TableInfo, RowChange } from '../../types/dml';

interface EditModeWrapperProps {
  connectionId: number;
  databaseType: string;
  sql: string;
  results: Record<string, any>[];
  children: React.ReactNode; // Regular table/chart rendering
}

/**
 * Extract the target table/collection name from a query string.
 * Supports SQL (SELECT ... FROM ...), MongoDB (db.collection.find/aggregate/...),
 * Elasticsearch (GET /index/_search), and Redis key patterns.
 * Returns null for JOINs, subqueries, or unparseable queries.
 */
function extractTableName(sql: string): string | null {
  if (!sql) return null;
  const normalized = sql.replace(/\s+/g, ' ').trim();

  // MongoDB: db.collection.find(...) / db.collection.aggregate(...) etc.
  const mongoMatch = normalized.match(
    /^db\.([A-Za-z_]\w*)\.(?:find|findOne|aggregate|countDocuments|distinct)\s*\(/
  );
  if (mongoMatch) return mongoMatch[1];

  // Elasticsearch: GET /index/_search
  const esMatch = normalized.match(/^GET\s+\/([A-Za-z_][\w.\-]*)\/_(search|count)/i);
  if (esMatch) return esMatch[1];

  // Redis: HGETALL key, GET key, etc. — extract the key as table name
  const redisMatch = normalized.match(
    /^(HGETALL|HGET|GET|MGET|SMEMBERS|LRANGE|ZRANGE|TYPE|TTL)\s+(\S+)/i
  );
  if (redisMatch) return redisMatch[2];

  // SQL / CQL / PartiQL: SELECT ... FROM table_name
  // Reject JOINs and subqueries
  if (/\bJOIN\b/i.test(normalized)) return null;
  if (/\(\s*SELECT\b/i.test(normalized)) return null;

  // Match: FROM table_name (with optional schema prefix)
  const match = normalized.match(
    /\bFROM\s+(?:["'`\[]?(\w+)["'`\]]?\.)?["'`\[]?([\w:.\-]+)["'`\]]?/i
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
  const [displayResults, setDisplayResults] = useState(results);

  // Sync local state when parent provides new results (e.g. new query)
  useEffect(() => {
    setDisplayResults(results);
  }, [results]);

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

  const handleSaveSuccess = useCallback(
    (savedChanges: RowChange[]) => {
      setDisplayResults((prev) => {
        let rows = [...prev];
        for (const change of savedChanges) {
          if (change.change_type === 'UPDATE') {
            rows = rows.map((row) => {
              const matches = Object.entries(change.primary_key).every(
                ([col, val]) => row[col] === val
              );
              if (!matches) return row;
              const updated = { ...row };
              for (const cell of change.changes) {
                updated[cell.column] = cell.new_value;
              }
              return updated;
            });
          } else if (change.change_type === 'DELETE') {
            rows = rows.filter(
              (row) =>
                !Object.entries(change.primary_key).every(
                  ([col, val]) => row[col] === val
                )
            );
          } else if (change.change_type === 'INSERT' && change.new_row_data) {
            rows = [...rows, { ...change.new_row_data }];
          }
        }
        return rows;
      });
    },
    []
  );

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
            results={displayResults}
            connectionId={connectionId}
            tableInfo={tableInfo}
            permissions={editMode.permissions}
            changeTracker={changeTracker}
            onPreview={() => {}}
            onAddRow={() => setShowAddRow(true)}
            onSaveSuccess={handleSaveSuccess}
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
