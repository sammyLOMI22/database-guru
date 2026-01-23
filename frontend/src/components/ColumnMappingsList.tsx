import React, { useEffect, useState } from 'react';
import { Trash2, ArrowRight, Database, CheckCircle, Search } from 'lucide-react';
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
        <div className="h-10 glass-panel rounded-2xl"></div>
        <div className="h-24 glass-panel rounded-2xl"></div>
        <div className="h-24 glass-panel rounded-2xl"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card rounded-2xl p-4 bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/5 border-red-500/20">
        <p className="text-xs font-black uppercase tracking-[0.15em] text-red-600 dark:text-red-400">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by table..."
            value={filterTable}
            onChange={(e) => setFilterTable(e.target.value)}
            className="w-full glass-panel rounded-xl pl-10 pr-4 py-2.5 text-xs font-medium text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 border-white/5 transition-all"
          />
        </div>
        <div className="flex-1 relative">
          <Database className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by database type..."
            value={filterDbType}
            onChange={(e) => setFilterDbType(e.target.value)}
            className="w-full glass-panel rounded-xl pl-10 pr-4 py-2.5 text-xs font-medium text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 border-white/5 transition-all"
          />
        </div>
      </div>

      {/* Mappings List */}
      {mappings.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-2xl border-white/10">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl glass-panel flex items-center justify-center text-gray-400">
            <Database className="w-7 h-7" />
          </div>
          <p className="text-xs font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">No column mappings</p>
          <p className="text-[11px] font-medium text-gray-400 mt-2">
            Submit column name corrections via feedback to start learning
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {mappings.map((mapping) => (
            <div
              key={mapping.id}
              className="glass-card rounded-2xl p-4 hover:scale-[1.005] transition-all border-white/10 hover:border-blue-500/20"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="font-mono text-xs text-red-500 line-through bg-red-500/10 px-2.5 py-1 rounded-lg">
                      {mapping.source_column}
                    </span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                    <span className="font-mono text-xs text-emerald-500 font-bold bg-emerald-500/10 px-2.5 py-1 rounded-lg">
                      {mapping.target_column}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {mapping.table_name && (
                      <span className="text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                        {mapping.table_name}
                      </span>
                    )}
                    {mapping.connection_name && (
                      <span className="text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
                        {mapping.connection_name}
                      </span>
                    )}
                    <span className="text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg bg-gray-500/10 text-gray-600 dark:text-gray-400">
                      {mapping.database_type}
                    </span>
                    {mapping.times_applied > 0 && (
                      <span className="text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        {mapping.times_applied}x
                      </span>
                    )}
                    <span className={`text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg ${
                      mapping.confidence_score >= 0.8 ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
                      mapping.confidence_score >= 0.5 ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
                      'bg-red-500/10 text-red-600 dark:text-red-400'
                    }`}>
                      {Math.round(mapping.confidence_score * 100)}%
                    </span>
                  </div>

                  {mapping.description && (
                    <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-2">{mapping.description}</p>
                  )}
                </div>

                <button
                  onClick={() => handleDelete(mapping.id)}
                  className="flex-shrink-0 ml-4 w-9 h-9 rounded-xl glass-panel flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-500/10 hover:scale-105 active:scale-95 transition-all"
                  title="Delete mapping"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {mappings.length > 0 && (
        <div className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-400 text-center pt-4 border-t border-white/5">
          {mappings.length} mapping{mappings.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};
