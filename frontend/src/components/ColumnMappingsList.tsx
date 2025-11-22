import React, { useEffect, useState } from 'react';
import { Trash2, ArrowRight, Database, CheckCircle } from 'lucide-react';
import { mappingsAPI } from '../services/mappingsApi';
import type { ColumnMapping } from '../types/api';

interface ColumnMappingsListProps {
  connectionName?: string;
}

export const ColumnMappingsList: React.FC<ColumnMappingsListProps> = ({ connectionName }) => {
  const [mappings, setMappings] = useState<ColumnMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterTable, setFilterTable] = useState('');
  const [filterDbType, setFilterDbType] = useState('');

  useEffect(() => {
    loadMappings();
  }, [connectionName, filterTable, filterDbType]);

  const loadMappings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mappingsAPI.getColumnMappings({
        connection_name: connectionName,
        table_name: filterTable || undefined,
        database_type: filterDbType || undefined,
        limit: 100,
      });
      setMappings(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load column mappings');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (mappingId: number) => {
    if (!confirm('Are you sure you want to delete this column mapping?')) {
      return;
    }

    try {
      await mappingsAPI.deleteColumnMapping(mappingId);
      await loadMappings();
    } catch (err: any) {
      alert(`Failed to delete mapping: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 rounded w-1/3"></div>
        <div className="h-20 bg-gray-200 rounded"></div>
        <div className="h-20 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (error) {
    return <div className="text-red-600">Error: {error}</div>;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Filter by table name..."
          value={filterTable}
          onChange={(e) => setFilterTable(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <input
          type="text"
          placeholder="Filter by database type..."
          value={filterDbType}
          onChange={(e) => setFilterDbType(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Mappings List */}
      {mappings.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No column mappings learned yet</p>
          <p className="text-sm mt-1">
            Submit column name corrections via feedback to start learning patterns
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {mappings.map((mapping) => (
            <div
              key={mapping.id}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono text-sm text-red-700 line-through">
                    {mapping.source_column}
                  </span>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                  <span className="font-mono text-sm text-green-700 font-semibold">
                    {mapping.target_column}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  {mapping.table_name && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                      Table: {mapping.table_name}
                    </span>
                  )}
                  {mapping.connection_name && (
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                      {mapping.connection_name}
                    </span>
                  )}
                  <span className="px-2 py-1 bg-gray-200 text-gray-700 rounded">
                    {mapping.database_type}
                  </span>
                  {mapping.times_applied > 0 && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Used {mapping.times_applied}x
                    </span>
                  )}
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded">
                    {Math.round(mapping.confidence_score * 100)}% confidence
                  </span>
                </div>

                {mapping.description && (
                  <p className="text-xs text-gray-600 mt-2">{mapping.description}</p>
                )}
              </div>

              <button
                onClick={() => handleDelete(mapping.id)}
                className="flex-shrink-0 ml-4 p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Delete mapping"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {mappings.length > 0 && (
        <div className="text-sm text-gray-600 text-center pt-4 border-t border-gray-200">
          Showing {mappings.length} column mapping{mappings.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};
