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
  Database,
  MapPin,
  Tag,
} from 'lucide-react';
import type { TableNodeData } from '../../types/erDiagram';
import { NODE_BASE_WIDTH, MAX_VISIBLE_COLUMNS } from '../../types/erDiagram';

interface TableNodeProps extends NodeProps<TableNodeData> { }

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
    isDarkMode = false,
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
        rounded-2xl shadow-2xl border transition-all duration-500 node-enter
        ${selected ? 'ring-2 ring-blue-500 ring-offset-8 scale-[1.02]' : ''}
        ${isHighlighted ? 'ring-2 ring-yellow-400 ring-offset-4 scale-[1.02] glow-accent' : ''}
        ${isDarkMode ? 'glass-node' : 'bg-white/90 backdrop-blur-md border-gray-200/50'}
      `}
      style={{
        opacity,
        minWidth: NODE_BASE_WIDTH,
        borderColor: isHighlighted
          ? '#FBBF24'
          : isDarkMode
            ? 'rgba(255, 255, 255, 0.1)'
            : '#E5E7EB',
      }}
    >
      {/* Handles for connections */}
      <Handle
        type="target"
        position={Position.Top}
        className={`w-3.5 h-3.5 border-2 ${isDarkMode ? 'bg-gray-800 border-blue-500' : 'bg-white border-blue-400'}`}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className={`w-3.5 h-3.5 border-2 ${isDarkMode ? 'bg-gray-800 border-blue-500' : 'bg-white border-blue-400'}`}
      />

      {/* Table Header */}
      <div
        className={`
          px-5 py-4 flex items-center justify-between cursor-pointer rounded-t-2xl
          ${isDarkMode
            ? 'bg-gradient-to-br from-blue-600/30 via-indigo-600/20 to-transparent hover:from-blue-600/40 hover:via-indigo-600/30'
            : 'bg-gradient-to-br from-blue-50 via-indigo-50/50 to-transparent hover:from-blue-100 hover:via-indigo-100/50'}
          border-b ${isDarkMode ? 'border-white/5' : 'border-gray-200/50'}
          transition-all duration-300 group
        `}
      >
        <div className="flex items-center gap-3">
          <div className={`
            p-1.5 rounded-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3
            ${isDarkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-100 text-blue-600'}
          `}>
            <Database className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <span
              className={`font-extrabold text-sm tracking-tight ${isDarkMode ? 'text-white' : 'text-gray-900'
                }`}
            >
              {tableName}
            </span>
            <span className={`text-[9px] font-bold uppercase tracking-widest opacity-60 ${isDarkMode ? 'text-blue-300' : 'text-blue-600'}`}>
              {databaseType}
            </span>
          </div>
        </div>
        {rowCount !== null && (
          <span
            className={`text-[10px] px-2.5 py-1 rounded-full font-bold shadow-sm ${isDarkMode ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'bg-blue-50 text-blue-700 border border-blue-100'
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
  const lower = type.toLowerCase().trim();

  // Handle exact matches and common type abbreviations first
  const exactTypes: Record<string, string> = {
    'character varying': 'varchar',
    'timestamp without time zone': 'timestamp',
    'timestamp with time zone': 'timestamptz',
    'double precision': 'double',
    'bigint': 'bigint',
    'integer': 'int',
    'smallint': 'smallint',
    'tinyint': 'tinyint',
    'mediumint': 'int',
    'boolean': 'bool',
    'interval': 'interval',
    'point': 'point',
    'text': 'text',
    'clob': 'text',
  };

  // Check exact matches first
  if (exactTypes[lower]) {
    return exactTypes[lower];
  }

  // Check prefix matches for compound types
  for (const [long, short] of Object.entries(exactTypes)) {
    if (lower.startsWith(long)) {
      return type.toLowerCase().replace(long, short);
    }
  }

  // Handle integer types explicitly (int, int4, int8, etc.)
  // Exclude 'interval' and 'point' which contain 'int' substring
  if (/^int\d*$/i.test(lower)) {
    return 'int';
  }

  // Match text/char types (varchar, char, nvarchar, nchar)
  if (/^n?(var)?char/i.test(lower)) return 'text';

  // Match date/time types
  if (/^timestamp/i.test(lower)) return 'date';
  if (/^date$/i.test(lower)) return 'date';
  if (/^time$/i.test(lower)) return 'time';
  if (/^datetime/i.test(lower)) return 'date';

  // Match boolean types
  if (/^bool(ean)?$/i.test(lower)) return 'bool';

  // Match numeric types
  if (/^(float|double|decimal|numeric|real|money)/i.test(lower)) return 'num';

  // Truncate very long types
  if (type.length > 10) {
    return type.substring(0, 8) + '..';
  }

  return type.toLowerCase();
}

export default memo(TableNode);
