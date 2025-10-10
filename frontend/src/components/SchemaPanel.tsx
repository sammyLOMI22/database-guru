import { useState } from 'react';
import { RefreshCw, ChevronDown, ChevronRight, Database } from 'lucide-react';
import { useSchema, useRefreshSchema } from '../hooks/useSchema';

export default function SchemaPanel() {
  const { data: schema, isLoading } = useSchema();
  const refreshMutation = useRefreshSchema();
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
      }
      return next;
    });
  };

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-spin w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full mx-auto"></div>
        <p className="mt-2 text-sm text-gray-500">Loading schema...</p>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="p-4 text-center text-gray-500">
        <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No schema available</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Stats */}
      <div className="p-4 bg-gray-50 border-b border-gray-200">
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary-600">
              {schema.table_count}
            </div>
            <div className="text-xs text-gray-600">Tables</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-primary-600">
              {schema.column_count}
            </div>
            <div className="text-xs text-gray-600">Columns</div>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshMutation.isPending}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 flex items-center justify-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tables list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {Object.entries(schema.schema.tables).map(([tableName, tableInfo]) => {
          const isExpanded = expandedTables.has(tableName);

          return (
            <div key={tableName} className="border border-gray-200 rounded-lg overflow-hidden">
              {/* Table header */}
              <button
                onClick={() => toggleTable(tableName)}
                className="w-full px-3 py-2 bg-white hover:bg-gray-50 flex items-center justify-between text-left"
              >
                <div className="flex items-center space-x-2">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                  <span className="font-medium text-sm text-gray-900">{tableName}</span>
                </div>
                <span className="text-xs text-gray-500">
                  {tableInfo.columns.length} columns
                </span>
              </button>

              {/* Columns (expanded) */}
              {isExpanded && (
                <div className="bg-gray-50 border-t border-gray-200 p-3">
                  <div className="space-y-2">
                    {tableInfo.columns.map((column) => (
                      <div key={column.name} className="text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-medium text-gray-900">
                            {column.name}
                          </span>
                          <div className="flex items-center space-x-2">
                            {tableInfo.primary_keys.includes(column.name) && (
                              <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">
                                PK
                              </span>
                            )}
                            {tableInfo.foreign_keys.some(fk => fk.column === column.name) && (
                              <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                                FK
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="text-gray-500 mt-0.5">
                          {column.type}
                          {!column.nullable && (
                            <span className="ml-2 text-red-600">NOT NULL</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Foreign keys */}
                  {tableInfo.foreign_keys.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <div className="text-xs font-medium text-gray-700 mb-2">Foreign Keys:</div>
                      {tableInfo.foreign_keys.map((fk, idx) => (
                        <div key={idx} className="text-xs text-gray-600">
                          {fk.column} → {fk.referred_table}.{fk.referred_column}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
