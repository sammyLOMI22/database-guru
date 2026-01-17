import React, { useState, useEffect } from 'react';
import {
  ChevronRight,
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
    <div className="glass-panel rounded-3xl border-white/10 overflow-hidden shadow-2xl transition-all duration-500 animate-fadeIn">
      {/* Header */}
      <div className="px-6 py-5 bg-white/5 dark:bg-black/20 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-2xl glass-panel flex items-center justify-center text-blue-500 shadow-lg shadow-blue-500/10">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-tight text-gray-900 dark:text-white">
                {connectionName || schema.connection_name}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] font-black uppercase tracking-widest text-gray-400 dark:text-gray-500 bg-black/5 dark:bg-white/5 px-2 py-0.5 rounded">
                  {schema.database_type}
                </span>
                {schema.cached && (
                  <span className="text-[9px] font-bold text-blue-500 uppercase tracking-widest flex items-center gap-1">
                    <div className="w-1 h-1 rounded-full bg-blue-500 animate-pulse" />
                    Cached
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadSchema(true)}
              className="p-2.5 glass-panel rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:scale-110 active:scale-95 transition-all"
              title="Refresh schema"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={copySchema}
              className="p-2.5 glass-panel rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:scale-110 active:scale-95 transition-all"
              title="Copy schema as text"
            >
              {copied ? (
                <Check className="w-4 h-4 text-emerald-500" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-4 flex items-center gap-6 text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-500">
          <div className="flex items-center gap-2">
            <span className="text-gray-900 dark:text-gray-300">{schema.table_count}</span> Tables
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-900 dark:text-gray-300">{schema.total_columns}</span> Columns
          </div>
        </div>
      </div>

      {/* Search and Controls */}
      <div className="px-6 py-4 border-b border-white/5 flex items-center gap-4 bg-white/5 dark:bg-black/10">
        <div className="flex-1 relative group">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-blue-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search tables and columns..."
            className="w-full pl-10 pr-4 py-2.5 text-xs font-bold bg-black/5 dark:bg-white/5 border border-white/5 text-gray-900 dark:text-white rounded-[1.25rem] focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500"
          />
        </div>
        <div className="flex gap-4">
          <button
            onClick={expandAll}
            className="text-[10px] font-black uppercase tracking-widest text-blue-500 hover:text-blue-600 transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="text-[10px] font-black uppercase tracking-widest text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Table List */}
      <div className="max-h-[600px] overflow-y-auto custom-scrollbar p-2">
        <div className="space-y-1">
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
        </div>

        {filteredTables?.length === 0 && (
          <div className="py-20 text-center animate-fadeIn">
            <Search className="w-12 h-12 mx-auto mb-4 text-gray-300 opacity-20" />
            <p className="text-sm font-black uppercase tracking-widest text-gray-400">No matches found for "{searchTerm}"</p>
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
    <div className={`rounded-xl transition-all duration-300 ${expanded ? 'bg-white/5 dark:bg-white/5 shadow-inner' : 'hover:bg-white/5'}`}>
      {/* Table Header */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer group"
        onClick={onToggle}
      >
        <div className={`w-6 h-6 rounded-lg flex items-center justify-center transition-all ${expanded ? 'bg-blue-500/20 text-blue-500 rotate-90' : 'text-gray-400 group-hover:text-gray-300'}`}>
          <ChevronRight className="w-4 h-4" />
        </div>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${expanded ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}`}>
          <Table className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`text-sm font-black uppercase tracking-wider transition-colors ${expanded ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-200 group-hover:text-blue-500'}`}
              onClick={(e) => {
                e.stopPropagation();
                onSelect?.();
              }}
            >
              {table.name}
            </span>
            {table.row_count !== null && (
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest opacity-60">
                {table.row_count.toLocaleString()} ROWS
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Columns */}
      {expanded && (
        <div className="pl-14 pr-4 pb-4 space-y-2 animate-fadeIn">
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
        <mark key={i} className="bg-blue-500/20 text-blue-600 dark:text-blue-400 rounded px-1 py-0.5 font-bold">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="group/col py-1.5 border-b border-white/[0.03] last:border-0">
      <div className="flex items-center gap-3 text-xs">
        {/* Column indicators */}
        <div className="flex items-center gap-1.5 min-w-[32px] justify-end">
          {column.primary_key && (
            <div className="w-5 h-5 rounded-md bg-amber-500/10 flex items-center justify-center" title="Primary Key">
              <Key className="w-3 h-3 text-amber-500" />
            </div>
          )}
          {column.foreign_key && (
            <div className="w-5 h-5 rounded-md bg-blue-500/10 flex items-center justify-center" title={`FK: ${column.foreign_key}`}>
              <Link className="w-3 h-3 text-blue-500" />
            </div>
          )}
        </div>

        {/* Column name */}
        <span className="font-black text-gray-700 dark:text-gray-300 uppercase tracking-wider">{highlightMatch(column.name)}</span>

        {/* Type */}
        <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase">{column.type}</span>

        {/* Nullable indicator */}
        {!column.nullable && (
          <span className="text-red-500 font-black animate-pulse" title="NOT NULL">*</span>
        )}

        {/* Semantic type badge */}
        {column.semantic_type && (
          <span
            className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${column.semantic_type === 'location'
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
              : column.semantic_type === 'categorical'
                ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                : column.semantic_type === 'temporal'
                  ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                  : 'bg-gray-500/10 text-gray-600 dark:text-gray-400'
              }`}
          >
            {column.semantic_type}
          </span>
        )}

        {/* Sample values toggle */}
        {column.sample_values.length > 0 && (
          <button
            onClick={() => setShowSamples(!showSamples)}
            className="ml-auto text-[9px] font-black uppercase tracking-widest text-blue-500/60 hover:text-blue-500 transition-colors"
          >
            {showSamples ? 'HIDE SAMPLES' : `${column.sample_values.length} VALUES`}
          </button>
        )}
      </div>

      {/* Sample values display */}
      {showSamples && column.sample_values.length > 0 && (
        <div className="mt-2 ml-11 flex flex-wrap gap-1.5 animate-slideInLeft">
          {column.sample_values.map((v, i) => (
            <span key={i} className="px-2 py-1 bg-black/5 dark:bg-white/5 border border-white/5 rounded-lg text-[9px] font-bold text-gray-500 dark:text-gray-400">
              {String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default SchemaExplorer;
