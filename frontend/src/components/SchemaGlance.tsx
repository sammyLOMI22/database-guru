import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Database, Table, Key, MapPin, AlertTriangle } from 'lucide-react';
import { schemaAPI } from '../services/api';
import type { SchemaExploreResponse, SchemaTableInfo } from '../types/api';

interface SchemaGlanceProps {
  connectionIds: number[];
  connectionNames?: Record<number, string>;
}

interface DatabaseSchema {
  connectionId: number;
  connectionName: string;
  databaseType: string;
  schema: SchemaExploreResponse | null;
  loading: boolean;
  error: string | null;
}

export const SchemaGlance: React.FC<SchemaGlanceProps> = ({
  connectionIds,
  connectionNames = {},
}) => {
  const [expanded, setExpanded] = useState(false);
  const [schemas, setSchemas] = useState<DatabaseSchema[]>([]);
  const [expandedDbs, setExpandedDbs] = useState<Set<number>>(new Set());
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (connectionIds.length > 0) {
      loadSchemas();
    }
  }, [connectionIds]);

  const loadSchemas = async () => {
    const initialSchemas = connectionIds.map((id) => ({
      connectionId: id,
      connectionName: connectionNames[id] || `Database ${id}`,
      databaseType: '',
      schema: null,
      loading: true,
      error: null,
    }));
    setSchemas(initialSchemas);

    // Load schemas in parallel
    const results = await Promise.all(
      connectionIds.map(async (id) => {
        try {
          const schema = await schemaAPI.exploreSchema(id);
          return {
            connectionId: id,
            connectionName: schema.connection_name,
            databaseType: schema.database_type,
            schema,
            loading: false,
            error: null,
          };
        } catch (err) {
          return {
            connectionId: id,
            connectionName: connectionNames[id] || `Database ${id}`,
            databaseType: '',
            schema: null,
            loading: false,
            error: err instanceof Error ? err.message : 'Failed to load',
          };
        }
      })
    );
    setSchemas(results);
  };

  const toggleDb = (id: number) => {
    setExpandedDbs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleTable = (connectionId: number, tableName: string) => {
    const key = `${connectionId}-${tableName}`;
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Get location columns across all schemas
  const getLocationInfo = () => {
    const locationColumns: { db: string; table: string; column: string }[] = [];
    const dbsWithLocation: string[] = [];
    const dbsWithoutLocation: string[] = [];

    schemas.forEach((dbSchema) => {
      if (!dbSchema.schema) return;
      let hasLocation = false;

      dbSchema.schema.tables.forEach((table) => {
        table.columns.forEach((col) => {
          if (col.semantic_type === 'location') {
            hasLocation = true;
            locationColumns.push({
              db: dbSchema.connectionName,
              table: table.name,
              column: col.name,
            });
          }
        });
      });

      if (hasLocation) {
        dbsWithLocation.push(dbSchema.connectionName);
      } else {
        dbsWithoutLocation.push(dbSchema.connectionName);
      }
    });

    return { locationColumns, dbsWithLocation, dbsWithoutLocation };
  };

  const locationInfo = getLocationInfo();
  const totalTables = schemas.reduce(
    (sum, s) => sum + (s.schema?.table_count || 0),
    0
  );
  const totalColumns = schemas.reduce(
    (sum, s) => sum + (s.schema?.total_columns || 0),
    0
  );

  if (connectionIds.length === 0) return null;

  return (
    <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/10 dark:to-emerald-900/10 rounded-lg border border-green-200 dark:border-green-800/50 overflow-hidden transition-colors">
      {/* Header - Always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-2 hover:bg-green-100/50 dark:hover:bg-green-800/20 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">🗂️</span>
          <div>
            <span className="font-medium text-green-800 dark:text-green-300 text-sm">
              Schema at a Glance
            </span>
            <span className="text-xs text-green-600 dark:text-green-500 ml-2">
              {schemas.length} db{schemas.length !== 1 ? 's' : ''} • {totalTables} tables • {totalColumns} columns
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Location warning badge */}
          {locationInfo.dbsWithoutLocation.length > 0 && locationInfo.dbsWithLocation.length > 0 && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full"
              title={`Location columns missing from: ${locationInfo.dbsWithoutLocation.join(', ')}`}
            >
              <AlertTriangle className="w-3 h-3" />
              {locationInfo.dbsWithoutLocation.length} missing location
            </span>
          )}
          <ChevronDown
            className={`w-4 h-4 text-green-600 dark:text-green-500 transition-transform ${expanded ? 'rotate-180' : ''
              }`}
          />
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-3 space-y-3">
          {/* Location compatibility hint */}
          {locationInfo.dbsWithLocation.length > 0 && locationInfo.dbsWithoutLocation.length > 0 && (
            <div className="text-xs bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded px-3 py-2 text-amber-800 dark:text-amber-300 transition-colors">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium">Location queries limited</p>
                  <p className="text-amber-700">
                    Location filtering works on:{' '}
                    <span className="font-medium">{locationInfo.dbsWithLocation.join(', ')}</span>
                  </p>
                  <p className="text-amber-600">
                    Missing location data:{' '}
                    <span>{locationInfo.dbsWithoutLocation.join(', ')}</span>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Database schemas */}
          {schemas.map((dbSchema) => (
            <div
              key={dbSchema.connectionId}
              className="bg-white dark:bg-gray-800 rounded border border-green-100 dark:border-green-900/30 overflow-hidden transition-colors"
            >
              {/* Database header */}
              <button
                onClick={() => toggleDb(dbSchema.connectionId)}
                className="flex items-center justify-between w-full px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {expandedDbs.has(dbSchema.connectionId) ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                  <Database className="w-4 h-4 text-green-600 dark:text-green-400" />
                  <span className="font-medium text-sm text-gray-800 dark:text-gray-200">
                    {dbSchema.connectionName}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-gray-500 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded transition-colors">
                    {dbSchema.databaseType}
                  </span>
                </div>
                {dbSchema.schema && (
                  <span className="text-xs text-gray-500">
                    {dbSchema.schema.table_count} tables
                  </span>
                )}
              </button>

              {/* Tables list */}
              {expandedDbs.has(dbSchema.connectionId) && (
                <div className="px-3 pb-3 border-t border-gray-100 dark:border-gray-700">
                  {dbSchema.loading ? (
                    <div className="text-xs text-gray-500 py-2">Loading...</div>
                  ) : dbSchema.error ? (
                    <div className="text-xs text-red-500 py-2">{dbSchema.error}</div>
                  ) : dbSchema.schema ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-3">
                      {dbSchema.schema.tables.map((table) => (
                        <TableSummary
                          key={`${dbSchema.connectionId}-${table.name}`}
                          table={table}
                          isExpanded={expandedTables.has(`${dbSchema.connectionId}-${table.name}`)}
                          onToggle={() => toggleTable(dbSchema.connectionId, table.name)}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

interface TableSummaryProps {
  table: SchemaTableInfo;
  isExpanded: boolean;
  onToggle: () => void;
}

const TableSummary: React.FC<TableSummaryProps> = ({ table, isExpanded, onToggle }) => {
  const pkCount = table.primary_keys.length;
  const locationCols = table.columns.filter((c) => c.semantic_type === 'location');

  return (
    <div className="text-xs border border-gray-100 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800 transition-colors">
      {/* Table Header */}
      <button
        onClick={onToggle}
        className="flex items-center gap-2 w-full text-left py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
        )}
        <Table className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
        <span className="font-semibold text-gray-800 dark:text-gray-200">{table.name}</span>
        <span className="text-gray-400 dark:text-gray-500 text-[10px] ml-1">
          ({table.columns.length} cols)
        </span>
        {table.row_count !== null && (
          <span className="text-gray-400 dark:text-gray-500 ml-auto text-[10px]">
            {table.row_count.toLocaleString()} rows
          </span>
        )}
        {/* Badges */}
        <div className="flex items-center gap-1 ml-2">
          {pkCount > 0 && (
            <span className="inline-flex items-center px-1.5 py-0.5 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded text-[9px] transition-colors">
              <Key className="w-2.5 h-2.5 mr-0.5" />
              {pkCount}
            </span>
          )}
          {locationCols.length > 0 && (
            <span className="inline-flex items-center px-1.5 py-0.5 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-[9px] transition-colors">
              <MapPin className="w-2.5 h-2.5 mr-0.5" />
              {locationCols.length}
            </span>
          )}
        </div>
      </button>

      {/* Columns Table */}
      {isExpanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/30">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
                <th className="text-left py-1.5 px-3 font-medium">Column</th>
                <th className="text-left py-1.5 px-2 font-medium">Type</th>
                <th className="text-center py-1.5 px-2 font-medium w-16">Nullable</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((col, idx) => (
                <tr
                  key={col.name}
                  className={`border-b border-gray-50 dark:border-gray-700 last:border-0 ${idx % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50/30 dark:bg-gray-700/30'} transition-colors`}
                >
                  <td className="py-1.5 px-3">
                    <div className="flex items-center gap-1.5">
                      {col.primary_key && (
                        <span title="Primary Key">
                          <Key className="w-3 h-3 text-amber-500 flex-shrink-0" />
                        </span>
                      )}
                      {col.semantic_type === 'location' && (
                        <span title="Location Column">
                          <MapPin className="w-3 h-3 text-green-500 flex-shrink-0" />
                        </span>
                      )}
                      <span className={`font-mono ${col.primary_key ? 'font-semibold text-amber-800 dark:text-amber-500' : 'text-gray-700 dark:text-gray-300'}`}>
                        {col.name}
                      </span>
                    </div>
                  </td>
                  <td className="py-1.5 px-2">
                    <code className="px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded font-mono text-[10px] transition-colors">
                      {col.type}
                    </code>
                  </td>
                  <td className="py-1.5 px-2 text-center">
                    {col.nullable ? (
                      <span className="text-gray-400">✓</span>
                    ) : (
                      <span className="text-red-400 font-medium">NOT NULL</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Foreign Keys Section */}
          {table.foreign_keys.length > 0 && (
            <div className="border-t border-gray-100 dark:border-gray-700 px-3 py-2 bg-purple-50/50 dark:bg-purple-900/10 transition-colors">
              <div className="text-[10px] font-medium text-purple-700 dark:text-purple-400 mb-1">Foreign Keys:</div>
              {table.foreign_keys.map((fk, idx) => (
                <div key={idx} className="text-[10px] text-purple-600 dark:text-purple-500 font-mono">
                  {fk.column} → {fk.referred_table}.{fk.referred_column}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SchemaGlance;
