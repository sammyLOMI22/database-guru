import React, { useState, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Database,
  Table,
  Key,
  Link,
  Search,
  RefreshCw,
  Copy,
  Check,
} from 'lucide-react';
import { schemaAPI } from '../services/api';
import type { SchemaExploreResponse, SchemaTableInfo, SchemaColumnInfo } from '../types/api';

interface SchemaExplorerProps {
  connectionId: number;
  connectionName?: string;
  onTableSelect?: (tableName: string) => void;
}

export const SchemaExplorer: React.FC<SchemaExplorerProps> = ({
  connectionId,
  connectionName,
  onTableSelect,
}) => {
  const [schema, setSchema] = useState<SchemaExploreResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadSchema();
  }, [connectionId]);

  const loadSchema = async (refresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await schemaAPI.exploreSchema(connectionId, refresh);
      setSchema(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schema');
    } finally {
      setLoading(false);
    }
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

  const expandAll = () => {
    if (schema) {
      setExpandedTables(new Set(schema.tables.map((t) => t.name)));
    }
  };

  const collapseAll = () => {
    setExpandedTables(new Set());
  };

  const copySchema = async () => {
    if (!schema) return;

    const schemaText = schema.tables
      .map((table) => {
        const cols = table.columns
          .map((col) => {
            let line = `  ${col.name}: ${col.type}`;
            if (col.primary_key) line += ' [PK]';
            if (col.foreign_key) line += ` [FK -> ${col.foreign_key}]`;
            return line;
          })
          .join('\n');
        return `${table.name} (${table.row_count ?? '?'} rows)\n${cols}`;
      })
      .join('\n\n');

    await navigator.clipboard.writeText(schemaText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredTables = schema?.tables.filter((table) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    if (table.name.toLowerCase().includes(term)) return true;
    return table.columns.some((col) => col.name.toLowerCase().includes(term));
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-5 h-5 animate-spin text-gray-400 dark:text-gray-500" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">Loading schema...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/50 rounded-lg">
        <p className="text-red-700 dark:text-red-400">{error}</p>
        <button
          onClick={() => loadSchema()}
          className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!schema) return null;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {connectionName || schema.connection_name}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 px-2 py-0.5 bg-gray-200 dark:bg-gray-800 rounded">
              {schema.database_type}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadSchema(true)}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              title="Refresh schema"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={copySchema}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              title="Copy schema"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span>{schema.table_count} tables</span>
          <span>{schema.total_columns} columns</span>
          {schema.cached && <span className="text-blue-600 dark:text-blue-400">cached</span>}
        </div>
      </div>

      {/* Search and Controls */}
      <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-800 flex items-center gap-3 bg-gray-50/30 dark:bg-gray-900/30">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search tables and columns..."
            className="w-full pl-8 pr-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
          />
        </div>
        <button
          onClick={expandAll}
          className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
        >
          Expand All
        </button>
        <button
          onClick={collapseAll}
          className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
        >
          Collapse All
        </button>
      </div>

      {/* Table List */}
      <div className="max-h-[500px] overflow-y-auto">
        {filteredTables?.map((table) => (
          <TableRow
            key={table.name}
            table={table}
            expanded={expandedTables.has(table.name)}
            onToggle={() => toggleTable(table.name)}
            onSelect={() => onTableSelect?.(table.name)}
            searchTerm={searchTerm}
          />
        ))}

        {filteredTables?.length === 0 && (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
            No tables match "{searchTerm}"
          </div>
        )}
      </div>
    </div>
  );
};

interface TableRowProps {
  table: SchemaTableInfo;
  expanded: boolean;
  onToggle: () => void;
  onSelect?: () => void;
  searchTerm: string;
}

const TableRow: React.FC<TableRowProps> = ({
  table,
  expanded,
  onToggle,
  onSelect,
  searchTerm,
}) => {
  const matchingColumns = searchTerm
    ? table.columns.filter((col) =>
      col.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    : table.columns;

  return (
    <div className="border-b border-gray-100 dark:border-gray-800 last:border-b-0">
      {/* Table Header */}
      <div
        className="flex items-center gap-2 px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
        onClick={onToggle}
      >
        <button className="p-0.5">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          )}
        </button>
        <Table className="w-4 h-4 text-gray-400 dark:text-gray-500" />
        <span
          className="font-medium text-gray-800 dark:text-gray-100 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onSelect?.();
          }}
        >
          {table.name}
        </span>
        {table.row_count !== null && (
          <span className="text-xs text-gray-400 dark:text-gray-500">
            ({table.row_count.toLocaleString()} rows)
          </span>
        )}
      </div>

      {/* Columns */}
      {expanded && (
        <div className="pl-10 pr-4 pb-2 space-y-1">
          {matchingColumns.map((col) => (
            <ColumnRow key={col.name} column={col} searchTerm={searchTerm} />
          ))}
        </div>
      )}
    </div>
  );
};

interface ColumnRowProps {
  column: SchemaColumnInfo;
  searchTerm: string;
}

const ColumnRow: React.FC<ColumnRowProps> = ({ column, searchTerm }) => {
  const [showSamples, setShowSamples] = useState(false);

  const highlightMatch = (text: string) => {
    if (!searchTerm) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-200 dark:bg-yellow-900/50 dark:text-yellow-100 rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="flex items-center gap-2 text-sm py-0.5">
      {/* Column indicators */}
      <div className="flex items-center gap-1 w-8">
        {column.primary_key && (
          <span title="Primary Key">
            <Key className="w-3 h-3 text-amber-500" />
          </span>
        )}
        {column.foreign_key && (
          <span title={`FK: ${column.foreign_key}`}>
            <Link className="w-3 h-3 text-blue-500 dark:text-blue-400" />
          </span>
        )}
      </div>

      {/* Column name */}
      <span className="font-mono text-gray-700 dark:text-gray-300">{highlightMatch(column.name)}</span>

      {/* Type */}
      <span className="text-xs text-gray-400 dark:text-gray-500">{column.type}</span>

      {/* Nullable indicator */}
      {!column.nullable && (
        <span className="text-xs text-red-400" title="NOT NULL">
          *
        </span>
      )}

      {/* Semantic type badge */}
      {column.semantic_type && (
        <span
          className={`text-xs px-1.5 py-0.5 rounded ${column.semantic_type === 'location'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : column.semantic_type === 'categorical'
                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                : column.semantic_type === 'temporal'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            }`}
        >
          {column.semantic_type}
        </span>
      )}

      {/* Sample values toggle */}
      {column.sample_values.length > 0 && (
        <button
          onClick={() => setShowSamples(!showSamples)}
          className="text-xs text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
        >
          {showSamples ? 'hide' : `${column.sample_values.length} values`}
        </button>
      )}

      {/* Sample values display */}
      {showSamples && column.sample_values.length > 0 && (
        <div className="ml-2 text-xs text-gray-500 dark:text-gray-400">
          {column.sample_values.map((v, i) => (
            <span key={i} className="inline-block px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded mr-1 mb-1 border border-gray-200 dark:border-gray-700">
              {String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default SchemaExplorer;
