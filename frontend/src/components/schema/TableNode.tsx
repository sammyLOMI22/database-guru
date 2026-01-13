/**
 * TableNode - Custom React Flow node for database tables.
 *
 * Displays table name, columns with types, and PK/FK indicators.
 * Supports collapsed/expanded states and dark mode.
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Key, Link, ChevronDown, ChevronRight, Database } from 'lucide-react';
import type { TableNodeData } from '../../types/erDiagram';
import { useDarkMode } from '../../hooks/useDarkMode';

/** Maximum number of columns to display before showing "X more columns" */
const MAX_VISIBLE_COLUMNS = 10;

interface TableNodeProps extends NodeProps<TableNodeData> {}

const TableNode: React.FC<TableNodeProps> = ({ data, selected }) => {
  const { isDarkMode } = useDarkMode();

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
        rounded-lg shadow-lg border-2 overflow-hidden transition-all duration-200
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
        ${isHighlighted ? 'ring-2 ring-yellow-400 ring-offset-1' : ''}
        ${isDarkMode ? 'bg-gray-800' : 'bg-white'}
      `}
      style={{
        opacity,
        minWidth: 200,
        borderColor: isHighlighted
          ? '#FBBF24'
          : isDarkMode
          ? '#374151'
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
          px-3 py-2 flex items-center justify-between cursor-pointer
          ${isDarkMode ? 'bg-gray-700' : 'bg-gray-100'}
          border-b ${isDarkMode ? 'border-gray-600' : 'border-gray-200'}
        `}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <Database className="w-4 h-4 text-blue-500" />
          <span
            className={`font-semibold text-sm ${
              isDarkMode ? 'text-white' : 'text-gray-900'
            }`}
          >
            {tableName}
          </span>
        </div>
        {rowCount !== null && (
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'
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

            return (
              <div
                key={column.name}
                className={`
                  px-3 py-1.5 flex items-center justify-between text-xs
                  border-b last:border-b-0
                  ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}
                  ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}
                `}
              >
                <div className="flex items-center gap-2">
                  {/* PK/FK indicators */}
                  {isPK && (
                    <span title="Primary Key">
                      <Key className="w-3 h-3 text-yellow-500" />
                    </span>
                  )}
                  {isFK && (
                    <span title="Foreign Key">
                      <Link className="w-3 h-3 text-purple-500" />
                    </span>
                  )}
                  {!isPK && !isFK && <div className="w-3" />}

                  <span
                    className={`${
                      isDarkMode ? 'text-gray-200' : 'text-gray-800'
                    } ${isPK ? 'font-medium' : ''}`}
                  >
                    {column.name}
                  </span>
                </div>

                <span
                  className={`${
                    isDarkMode ? 'text-gray-500' : 'text-gray-400'
                  } font-mono`}
                >
                  {formatColumnType(column.type)}
                </span>
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
          className={`px-3 py-1.5 text-xs ${
            isDarkMode ? 'text-gray-400' : 'text-gray-500'
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
          px-3 py-1 text-xs flex items-center gap-1
          ${isDarkMode ? 'bg-gray-900 text-gray-500' : 'bg-gray-50 text-gray-400'}
        `}
      >
        <span>{databaseType}</span>
        <span>·</span>
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
  // Shorten common types
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

  const lower = type.toLowerCase();
  for (const [long, short] of Object.entries(shortTypes)) {
    if (lower.startsWith(long)) {
      return type.toLowerCase().replace(long, short);
    }
  }

  // Truncate very long types
  if (type.length > 15) {
    return type.substring(0, 12) + '...';
  }

  return type.toLowerCase();
}

export default memo(TableNode);
