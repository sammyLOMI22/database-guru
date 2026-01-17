/**
 * TableNode - Custom React Flow node for database tables.
 *
 * Displays table name, columns with types, and PK/FK indicators.
 * Supports collapsed/expanded states and dark mode.
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Key,
  Link,
  ChevronDown,
  ChevronRight,
  Database,
  MapPin,
  Tag,
} from 'lucide-react';
import type { TableNodeData } from '../../types/erDiagram';
import { NODE_BASE_WIDTH, MAX_VISIBLE_COLUMNS } from '../../types/erDiagram';

interface TableNodeProps extends NodeProps<TableNodeData> {}

const TableNode: React.FC<TableNodeProps> = ({ data, selected }) => {
  const {
    tableName,
    columns,
    primaryKeys,
    foreignKeys,
    rowCount,
    connectionName,
    databaseType,
    isExpanded,
    isHighlighted,
    isDimmed,
    isDarkMode,
  } = data;

  // Create a set of FK column names for quick lookup
  const fkColumns = new Set(foreignKeys.map((fk) => fk.column));

  // Limit columns shown when expanded
  const visibleColumns = isExpanded ? columns.slice(0, MAX_VISIBLE_COLUMNS) : [];
  const hasMoreColumns = columns.length > MAX_VISIBLE_COLUMNS;

  // Determine opacity based on search state
  const opacity = isDimmed ? 0.4 : 1;

  return (
    <div
      className={`
        rounded-xl shadow-2xl border transition-all duration-300 node-enter
        ${selected ? 'ring-2 ring-blue-500 ring-offset-4' : ''}
        ${isHighlighted ? 'ring-2 ring-yellow-400 ring-offset-2' : ''}
        ${isDarkMode ? 'glass-node' : 'bg-white'}
      `}
      style={{
        opacity,
        minWidth: NODE_BASE_WIDTH,
        borderColor: isHighlighted
          ? '#FBBF24'
          : isDarkMode
            ? 'rgba(75, 85, 99, 0.4)'
            : '#E5E7EB',
      }}
    >
      {/* Handles for connections */}
      <Handle
        type="target"
        position={Position.Top}
        className={`w-3 h-3 ${isDarkMode ? 'bg-gray-600' : 'bg-gray-400'}`}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className={`w-3 h-3 ${isDarkMode ? 'bg-gray-600' : 'bg-gray-400'}`}
      />

      {/* Table Header */}
      <div
        className={`
          px-4 py-3 flex items-center justify-between cursor-pointer
          ${isDarkMode
            ? 'bg-gradient-to-r from-blue-600/20 to-indigo-600/20 hover:from-blue-600/30 hover:to-indigo-600/30'
            : 'bg-gray-50 hover:bg-gray-100'}
          border-b ${isDarkMode ? 'border-gray-700/50' : 'border-gray-200'}
          transition-colors duration-200
        `}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          )}
          <Database className={`w-4 h-4 ${isDarkMode ? 'text-blue-400' : 'text-blue-500'}`} />
          <span
            className={`font-bold text-sm tracking-tight ${isDarkMode ? 'text-white' : 'text-gray-900'
              }`}
          >
            {tableName}
          </span>
        </div>
        {rowCount !== null && (
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${isDarkMode ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-50 text-blue-600'
              }`}
          >
            {rowCount.toLocaleString()}
          </span>
        )}
      </div>

      {/* Columns (when expanded) */}
      {isExpanded && (
        <div className="max-h-60 overflow-y-auto">
          {visibleColumns.map((column) => {
            const isPK = primaryKeys.includes(column.name);
            const isFK = fkColumns.has(column.name);
            const semanticType = column.semantic_type;

            return (
              <div
                key={column.name}
                className={`
                  px-4 py-2 flex items-center justify-between text-[11px]
                  border-b last:border-b-0
                  ${isDarkMode ? 'border-gray-800/50' : 'border-gray-100'}
                  ${isDarkMode ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50'}
                  group transition-colors duration-150
                `}
              >
                <div className="flex items-center gap-2.5">
                  {/* Indicators */}
                  <div className="flex items-center justify-center w-4">
                    {isPK ? (
                      <Key className="w-3.5 h-3.5 text-yellow-500 drop-shadow-[0_0_8px_rgba(234,179,8,0.4)]" />
                    ) : isFK ? (
                      <Link className="w-3.5 h-3.5 text-purple-400" />
                    ) : semanticType === 'location' ? (
                      <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                    ) : semanticType === 'categorical' ? (
                      <Tag className="w-3.5 h-3.5 text-orange-400" />
                    ) : (
                      <div className="w-3.5" />
                    )}
                  </div>

                  <span
                    className={`${isDarkMode ? 'text-gray-300 group-hover:text-blue-300' : 'text-gray-800'
                      } ${isPK ? 'font-semibold' : 'font-medium'} transition-colors duration-150`}
                  >
                    {column.name}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`
                      px-1.5 py-0.5 rounded text-[9px] font-mono leading-none
                      ${isDarkMode ? 'bg-gray-800 text-gray-500' : 'bg-gray-100 text-gray-400'}
                    `}
                  >
                    {formatColumnType(column.type)}
                  </span>
                </div>
              </div>
            );
          })}

          {/* More columns indicator */}
          {hasMoreColumns && (
            <div
              className={`
                px-3 py-1.5 text-xs text-center
                ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}
              `}
            >
              +{columns.length - MAX_VISIBLE_COLUMNS} more columns
            </div>
          )}
        </div>
      )}

      {/* Collapsed summary */}
      {!isExpanded && (
        <div
          className={`px-4 py-2 text-[10px] italic ${isDarkMode ? 'text-gray-500' : 'text-gray-400'
            }`}
        >
          {columns.length} columns
          {primaryKeys.length > 0 && ` · ${primaryKeys.length} PK`}
          {foreignKeys.length > 0 && ` · ${foreignKeys.length} FK`}
        </div>
      )}

      {/* Database badge */}
      <div
        className={`
          px-4 py-1.5 text-[10px] flex items-center gap-1.5 font-medium
          ${isDarkMode ? 'bg-blue-900/10 text-gray-500' : 'bg-gray-50 text-gray-400'}
        `}
      >
        <Database className="w-3 h-3 opacity-50" />
        <span className="uppercase tracking-wider">{databaseType}</span>
        <span className="opacity-30">|</span>
        <span className="truncate max-w-24" title={connectionName}>
          {connectionName}
        </span>
      </div>
    </div>
  );
};

/**
 * Format column type for display (shorten long types).
 */
function formatColumnType(type: string): string {
  const lower = type.toLowerCase();

  // Handle common type abbreviations
  const shortTypes: Record<string, string> = {
    'character varying': 'varchar',
    'timestamp without time zone': 'timestamp',
    'timestamp with time zone': 'timestamptz',
    'double precision': 'double',
    'bigint': 'bigint',
    'integer': 'int',
    'smallint': 'smallint',
    'boolean': 'bool',
  };

  for (const [long, short] of Object.entries(shortTypes)) {
    if (lower.startsWith(long)) {
      return type.toLowerCase().replace(long, short);
    }
  }

  // Handle generic type patterns (use word boundaries to avoid false positives)
  // Match integer types but not words like "point" that contain "int"
  if (/\bint\b/i.test(lower) || lower === 'tinyint' || lower === 'mediumint') return 'int';
  // Match text/char types
  if (/\b(var)?char\b/i.test(lower) || lower === 'text' || lower === 'clob') return 'text';
  // Match date/time types
  if (/\b(date|time)\b/i.test(lower)) return 'date';
  // Match boolean types
  if (/\bbool(ean)?\b/i.test(lower)) return 'bool';
  // Match numeric types
  if (/\b(float|double|decimal|numeric|real)\b/i.test(lower)) return 'num';

  // Truncate very long types
  if (type.length > 10) {
    return type.substring(0, 8) + '..';
  }

  return type.toLowerCase();
}

export default memo(TableNode);
