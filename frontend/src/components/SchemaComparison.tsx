import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  Check,
  X,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Database,
  RefreshCw,
} from 'lucide-react';
import { schemaAPI } from '../services/api';
import type { SchemaCompareResponse, TableComparison } from '../types/api';

interface SchemaComparisonProps {
  connectionIds: number[];
  connectionNames?: Record<number, string>;
}

export const SchemaComparison: React.FC<SchemaComparisonProps> = ({
  connectionIds,
  connectionNames = {},
}) => {
  const [comparison, setComparison] = useState<SchemaCompareResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'common' | 'different'>('all');

  useEffect(() => {
    if (connectionIds.length >= 2) {
      loadComparison();
    }
  }, [connectionIds]);

  const loadComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await schemaAPI.compareSchemas({ connection_ids: connectionIds });
      setComparison(data);
      // Auto-expand tables with differences
      const tablesWithDiff = data.tables
        .filter((t) => t.missing_from.length > 0 || hasColumnDifferences(t, data.connections.map(c => c.name)))
        .map((t) => t.table_name);
      setExpandedTables(new Set(tablesWithDiff));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare schemas');
    } finally {
      setLoading(false);
    }
  };

  const hasColumnDifferences = (table: TableComparison, dbNames: string[]): boolean => {
    return table.columns.some((col) =>
      dbNames.some((db) => col.databases[db] === null)
    );
  };

  const toggleTable = (tableName: string) => {
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName);
    } else {
      newExpanded.add(tableName);
    }
    setExpandedTables(newExpanded);
  };

  const filteredTables = comparison?.tables.filter((table) => {
    if (filter === 'all') return true;
    if (filter === 'common') return table.missing_from.length === 0;
    if (filter === 'different') {
      return (
        table.missing_from.length > 0 ||
        hasColumnDifferences(table, comparison.connections.map((c) => c.name))
      );
    }
    return true;
  });

  if (connectionIds.length < 2) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-700">Select at least 2 databases to compare schemas.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-5 h-5 animate-spin text-gray-500" />
        <span className="ml-2 text-gray-600">Comparing schemas...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-700">{error}</p>
        <button
          onClick={loadComparison}
          className="mt-2 text-sm text-red-600 hover:text-red-800"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!comparison) return null;

  const dbNames = comparison.connections.map((c) => c.name);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-purple-600" />
            <span className="font-medium text-gray-900">Schema Comparison</span>
          </div>
          <button
            onClick={loadComparison}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
            title="Refresh comparison"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Database list */}
        <div className="mt-2 flex flex-wrap gap-2">
          {comparison.connections.map((conn) => (
            <span
              key={conn.id}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700"
            >
              <Database className="w-3 h-3" />
              {connectionNames[conn.id] || conn.name}
              <span className="text-blue-500">({conn.type})</span>
            </span>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-gray-700">
              <span className="font-semibold">{comparison.common_tables.length}</span> common tables
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-gray-700">
              <span className="font-semibold">
                {comparison.tables.filter((t) => t.missing_from.length > 0).length}
              </span>{' '}
              unique tables
            </span>
          </div>
        </div>

        {/* Filter buttons */}
        <div className="mt-2 flex gap-2">
          {(['all', 'common', 'different'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded-full ${
                filter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Query Compatibility Hints */}
      {comparison.query_compatibility.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-100 bg-amber-50">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800">Query Compatibility</p>
              <ul className="mt-1 space-y-1">
                {comparison.query_compatibility.map((hint, i) => (
                  <li key={i} className="text-xs text-amber-700">
                    {hint.query_type}: Works on{' '}
                    <span className="font-medium">{hint.works_on.join(', ')}</span>
                    {hint.missing_from.length > 0 && (
                      <>
                        , missing from{' '}
                        <span className="font-medium text-red-600">
                          {hint.missing_from.join(', ')}
                        </span>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Table Comparison Grid */}
      <div className="max-h-[500px] overflow-y-auto">
        {/* Header row with database names */}
        <div className="sticky top-0 bg-white border-b border-gray-200 z-10">
          <div className="grid gap-0" style={{ gridTemplateColumns: `200px repeat(${dbNames.length}, 1fr)` }}>
            <div className="px-4 py-2 font-medium text-gray-700 text-sm">Table / Column</div>
            {dbNames.map((name) => (
              <div
                key={name}
                className="px-3 py-2 font-medium text-gray-700 text-sm text-center border-l border-gray-100"
              >
                {name}
              </div>
            ))}
          </div>
        </div>

        {/* Table rows */}
        {filteredTables?.map((table) => (
          <TableComparisonRow
            key={table.table_name}
            table={table}
            dbNames={dbNames}
            expanded={expandedTables.has(table.table_name)}
            onToggle={() => toggleTable(table.table_name)}
          />
        ))}

        {filteredTables?.length === 0 && (
          <div className="p-4 text-center text-gray-500 text-sm">
            No tables match the current filter
          </div>
        )}
      </div>
    </div>
  );
};

interface TableComparisonRowProps {
  table: TableComparison;
  dbNames: string[];
  expanded: boolean;
  onToggle: () => void;
}

const TableComparisonRow: React.FC<TableComparisonRowProps> = ({
  table,
  dbNames,
  expanded,
  onToggle,
}) => {
  const hasMissing = table.missing_from.length > 0;

  return (
    <div className={`border-b border-gray-100 ${hasMissing ? 'bg-yellow-50/30' : ''}`}>
      {/* Table name row */}
      <div
        className="grid gap-0 hover:bg-gray-50 cursor-pointer"
        style={{ gridTemplateColumns: `200px repeat(${dbNames.length}, 1fr)` }}
        onClick={onToggle}
      >
        <div className="px-4 py-2 flex items-center gap-2">
          <button className="p-0.5">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
          </button>
          <span className="font-medium text-gray-800">{table.table_name}</span>
        </div>
        {dbNames.map((db) => (
          <div
            key={db}
            className="px-3 py-2 flex items-center justify-center border-l border-gray-100"
          >
            {table.present_in.includes(db) ? (
              <Check className="w-4 h-4 text-green-600" />
            ) : (
              <X className="w-4 h-4 text-red-500" />
            )}
          </div>
        ))}
      </div>

      {/* Column rows */}
      {expanded && (
        <div className="bg-gray-50/50">
          {table.columns.map((col) => (
            <div
              key={col.column_name}
              className="grid gap-0"
              style={{ gridTemplateColumns: `200px repeat(${dbNames.length}, 1fr)` }}
            >
              <div className="px-4 py-1.5 pl-10 text-sm text-gray-600 font-mono">
                {col.column_name}
              </div>
              {dbNames.map((db) => {
                const colType = col.databases[db];
                return (
                  <div
                    key={db}
                    className={`px-3 py-1.5 text-xs text-center border-l border-gray-100 ${
                      colType === null ? 'bg-red-50 text-red-600' : 'text-gray-600'
                    }`}
                  >
                    {colType ?? 'Missing'}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SchemaComparison;
