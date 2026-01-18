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
  compact?: boolean;
}

export const SchemaExplorer: React.FC<SchemaExplorerProps> = ({
  connectionId,
  connectionName,
  onTableSelect,
  compact = false,
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
    <div className={`${compact ? 'bg-transparent border-0' : 'glass-panel rounded-3xl border-white/10 shadow-2xl'} overflow-hidden transition-all duration-500 animate-fadeIn`}>
      {/* Header */}
      <div className={`${compact ? 'px-2 py-3' : 'px-6 py-5 bg-white/5 dark:bg-black/20'} border-b border-white/5`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {!compact && (
              <div className="w-10 h-10 rounded-2xl glass-panel flex items-center justify-center text-blue-500 shadow-lg shadow-blue-500/10">
                <Database className="w-5 h-5" />
              </div>
            )}
            <div>
              <h3 className={`${compact ? 'text-xs' : 'text-sm'} font-black uppercase tracking-tight text-gray-900 dark:text-white`}>
                {connectionName || schema.connection_name}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs font-black uppercase tracking-widest text-gray-400 dark:text-gray-500 bg-black/5 dark:bg-white/5 px-2 py-0.5 rounded">
                  {schema.database_type}
                </span>
                {schema.cached && !compact && (
                  <span className="text-xs font-bold text-blue-500 uppercase tracking-widest flex items-center gap-1">
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
              className={`${compact ? 'p-1.5' : 'p-2.5'} glass-panel rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:scale-110 active:scale-95 transition-all`}
              title="Refresh schema"
            >
              <RefreshCw className={`${compact ? 'w-3 h-3' : 'w-4 h-4'}`} />
            </button>
            {!compact && (
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
            )}
          </div>
        </div>

        {/* Stats */}
        {!compact && (
          <div className="mt-4 flex items-center gap-6 text-xs font-black uppercase tracking-widest text-gray-500 dark:text-gray-500">
            <div className="flex items-center gap-2">
              <span className="text-gray-900 dark:text-gray-300">{schema.table_count}</span> Tables
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-900 dark:text-gray-300">{schema.total_columns}</span> Columns
            </div>
          </div>
        )}
      </div>

      {/* Search and Controls */}
      <div className={`${compact ? 'px-2 py-3' : 'px-6 py-4'} border-b border-white/5 flex items-center gap-3 bg-white/5 dark:bg-black/10`}>
        <div className="flex-1 relative group">
          <Search className={`${compact ? 'w-3 h-3 left-2.5' : 'w-4 h-4 left-3'} absolute top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-blue-500`} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={compact ? "Search..." : "Search tables and columns..."}
            className={`w-full ${compact ? 'pl-8 pr-2 py-1.5 text-xs rounded-lg' : 'pl-10 pr-4 py-2.5 text-xs rounded-[1.25rem]'} font-bold bg-black/5 dark:bg-white/5 border border-white/5 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-gray-500`}
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="text-xs font-black uppercase tracking-widest text-blue-500 hover:text-blue-600 transition-colors whitespace-nowrap"
          >
            {compact ? 'All' : 'Expand All'}
          </button>
          {!compact && (
            <button
              onClick={collapseAll}
              className="text-xs font-black uppercase tracking-widest text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              Collapse All
            </button>
          )}
        </div>
      </div>

      {/* Table List */}
      <div className={`${compact ? 'max-h-[500px]' : 'max-h-[600px]'} overflow-y-auto custom-scrollbar p-1`}>
        <div className="space-y-1">
          {filteredTables?.map((table) => (
            <TableRow
              key={table.name}
              table={table}
              expanded={expandedTables.has(table.name)}
              onToggle={() => toggleTable(table.name)}
              onSelect={() => onTableSelect?.(table.name)}
              searchTerm={searchTerm}
              compact={compact}
            />
          ))}
        </div>

        {filteredTables?.length === 0 && (
          <div className="py-10 text-center animate-fadeIn">
            <Search className="w-8 h-8 mx-auto mb-3 text-gray-300 opacity-20" />
            <p className="text-xs font-black uppercase tracking-widest text-gray-400 px-4">No matches for "{searchTerm}"</p>
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
  compact: boolean;
}

const TableRow: React.FC<TableRowProps> = ({
  table,
  expanded,
  onToggle,
  onSelect,
  searchTerm,
  compact,
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
        className={`flex items-center gap-2 ${compact ? 'px-2 py-2' : 'px-4 py-3'} cursor-pointer group`}
        onClick={onToggle}
      >
        <div className={`${compact ? 'w-4 h-4' : 'w-6 h-6 rounded-lg'} flex items-center justify-center transition-all ${expanded ? 'bg-blue-500/20 text-blue-500 rotate-90' : 'text-gray-400 group-hover:text-gray-300'}`}>
          <ChevronRight className={compact ? 'w-3 h-3' : 'w-4 h-4'} />
        </div>
        <div className={`${compact ? 'w-6 h-6' : 'w-8 h-8'} rounded-lg flex items-center justify-center ${expanded ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}`}>
          <Table className={compact ? 'w-3 h-3' : 'w-4 h-4'} />
        </div>
        <div className="flex-1 min-w-0">
          <div className={`${compact ? 'flex-col items-start gap-0.5' : 'items-center gap-2'} flex`}>
            <span
              className={`${compact ? 'text-xs' : 'text-sm'} font-black uppercase tracking-wider transition-colors ${expanded ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-200 group-hover:text-blue-500'} truncate`}
              onClick={(e) => {
                e.stopPropagation();
                onSelect?.();
              }}
            >
              {table.name}
            </span>
            {table.row_count !== null && (
              <span className="text-xs font-bold text-gray-400 uppercase tracking-widest opacity-60">
                {table.row_count.toLocaleString()} ROWS
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Columns */}
      {expanded && (
        <div className={`${compact ? 'pl-10 pr-2 pb-3' : 'pl-14 pr-4 pb-4'} space-y-1.5 animate-fadeIn`}>
          {matchingColumns.map((col) => (
            <ColumnRow key={col.name} column={col} searchTerm={searchTerm} compact={compact} />
          ))}
        </div>
      )}
    </div>
  );
};

interface ColumnRowProps {
  column: SchemaColumnInfo;
  searchTerm: string;
  compact: boolean;
}

const ColumnRow: React.FC<ColumnRowProps> = ({ column, searchTerm, compact }) => {
  const [showSamples, setShowSamples] = useState(false);

  const highlightMatch = (text: string) => {
    if (!searchTerm) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-blue-500/20 text-blue-600 dark:text-blue-400 rounded px-0.5 py-0.5 font-bold">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="group/col py-1 border-b border-white/[0.03] last:border-0">
      <div className={`flex items-wrap items-center gap-2 ${compact ? 'text-xs' : 'text-xs'}`}>
        {/* Column indicators */}
        <div className="flex items-center gap-1 min-w-[20px] justify-end">
          {column.primary_key && (
            <div className={`${compact ? 'w-4 h-4' : 'w-5 h-5'} rounded-md bg-amber-500/10 flex items-center justify-center`} title="Primary Key">
              <Key className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} text-amber-500 />
            </div>
          )}
          {column.foreign_key && (
            <div className={`${compact ? 'w-4 h-4' : 'w-5 h-5'} rounded-md bg-blue-500/10 flex items-center justify-center`} title={`FK: ${column.foreign_key}`}>
              <Link className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} text-blue-500 />
            </div>
          )}
        </div>

        {/* Column name & type */}
        <div className={`flex ${compact ? 'flex-col items-start gap-0.5' : 'items-center gap-2'} flex-1 min-w-0`}>
          <span className="font-black text-gray-700 dark:text-gray-300 uppercase tracking-wider truncate">{highlightMatch(column.name)}</span>
          <span className={`${compact ? 'text-xs' : 'text-xs'} font-bold text-gray-400 dark:text-gray-500 uppercase`}>{column.type}</span>
        </div>

        {/* Nullable indicator */}
        {!column.nullable && (
          <span className="text-red-500 font-black animate-pulse" title="NOT NULL">*</span>
        )}

        {/* Semantic type badge */}
        {column.semantic_type && (
          <span
            className={`${compact ? 'text-xs px-1.5' : 'text-xs px-2'} font-black uppercase tracking-widest py-0.5 rounded-full ${column.semantic_type === 'location'
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
            className={`ml-auto ${compact ? 'text-xs' : 'text-xs'} font-black uppercase tracking-widest text-blue-500/60 hover:text-blue-500 transition-colors whitespace-nowrap`}
          >
            {showSamples ? 'HIDE' : `${column.sample_values.length} VALS`}
          </button>
        )}
      </div>

      {/* Sample values display */}
      {showSamples && column.sample_values.length > 0 && (
        <div className={`mt-1.5 ${compact ? 'ml-6' : 'ml-11'} flex flex-wrap gap-1 animate-slideInLeft`}>
          {column.sample_values.map((v, i) => (
            <span key={i} className="px-1.5 py-0.5 bg-black/5 dark:bg-white/5 border border-white/5 rounded text-xs font-bold text-gray-500 dark:text-gray-400">
              {String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default SchemaExplorer;
