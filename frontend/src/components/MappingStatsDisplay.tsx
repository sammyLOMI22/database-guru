import React, { useEffect, useState } from 'react';
import { TrendingUp, CheckCircle, Target, Award, Database, Table } from 'lucide-react';
import { mappingsAPI } from '../services/mappingsApi';
import type { MappingStats, PatternStats } from '../types/api';

interface MappingStatsDisplayProps {
  connectionName?: string;
}

export const MappingStatsDisplay: React.FC<MappingStatsDisplayProps> = ({ connectionName }) => {
  const [columnStats, setColumnStats] = useState<MappingStats | null>(null);
  const [tableStats, setTableStats] = useState<MappingStats | null>(null);
  const [patternStats, setPatternStats] = useState<PatternStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, [connectionName]);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const [colStats, tblStats, ptnStats] = await Promise.all([
        mappingsAPI.getColumnMappingStats({ connection_name: connectionName }),
        mappingsAPI.getTableMappingStats({ connection_name: connectionName }),
        mappingsAPI.getResultPatternStats(),
      ]);
      setColumnStats(colStats);
      setTableStats(tblStats);
      setPatternStats(ptnStats);
    } catch (err: any) {
      setError(err.message || 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 rounded w-1/3"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="text-red-600">Error: {error}</div>;
  }

  if (!columnStats || !tableStats || !patternStats) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Column Mappings */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Column Mappings</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{columnStats.total_mappings}</p>
              <p className="text-xs text-gray-500 mt-1">
                {columnStats.total_applications} applications
              </p>
            </div>
            <Database className="w-10 h-10 text-blue-500 opacity-50" />
          </div>
        </div>

        {/* Table Mappings */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Table Mappings</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{tableStats.total_mappings}</p>
              <p className="text-xs text-gray-500 mt-1">
                {tableStats.total_applications} applications
              </p>
            </div>
            <Table className="w-10 h-10 text-green-500 opacity-50" />
          </div>
        </div>

        {/* Result Patterns */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Validation Patterns</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{patternStats.total_patterns}</p>
              <p className="text-xs text-gray-500 mt-1">
                {patternStats.total_triggers} triggers
              </p>
            </div>
            <Target className="w-10 h-10 text-purple-500 opacity-50" />
          </div>
        </div>
      </div>

      {/* Success Rates */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-blue-600" />
            <p className="text-sm font-semibold text-gray-700">Column Success Rate</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">
            {(columnStats.average_success_rate * 100).toFixed(1)}%
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <p className="text-sm font-semibold text-gray-700">Table Success Rate</p>
          </div>
          <p className="text-2xl font-bold text-green-600">
            {(tableStats.average_success_rate * 100).toFixed(1)}%
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <Award className="w-5 h-5 text-purple-600" />
            <p className="text-sm font-semibold text-gray-700">Pattern Helpfulness</p>
          </div>
          <p className="text-2xl font-bold text-purple-600">
            {patternStats.helpfulness_rate.toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {patternStats.total_helpful} / {patternStats.total_triggers} helpful
          </p>
        </div>
      </div>

      {/* Most Used Mappings */}
      {columnStats.most_used.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            Most Used Column Mappings
          </h3>
          <div className="space-y-2">
            {columnStats.most_used.map((mapping, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-600">#{index + 1}</span>
                  <span className="font-mono text-sm text-red-700 line-through">
                    {mapping.source}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="font-mono text-sm text-green-700 font-semibold">
                    {mapping.target}
                  </span>
                  {mapping.table && (
                    <span className="text-xs text-gray-500">in {mapping.table}</span>
                  )}
                </div>
                <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-semibold">
                  {mapping.times_applied}x
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Most Used Table Mappings */}
      {tableStats.most_used.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-600" />
            Most Used Table Mappings
          </h3>
          <div className="space-y-2">
            {tableStats.most_used.map((mapping, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-600">#{index + 1}</span>
                  <span className="font-mono text-sm text-red-700 line-through">
                    {mapping.source}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="font-mono text-sm text-green-700 font-semibold">
                    {mapping.target}
                  </span>
                  {mapping.type && (
                    <span className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded">
                      {mapping.type}
                    </span>
                  )}
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded font-semibold">
                  {mapping.times_applied}x
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Distribution Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* By Database Type */}
        {Object.keys(columnStats.by_database_type).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Column Mappings by Database</h3>
            <div className="space-y-3">
              {Object.entries(columnStats.by_database_type).map(([dbType, count]) => (
                <div key={dbType}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 capitalize">{dbType}</span>
                    <span className="text-sm text-gray-600">{count}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(count / columnStats.total_mappings) * 100}%`,
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pattern Types */}
        {Object.keys(patternStats.by_type).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Patterns by Type</h3>
            <div className="space-y-3">
              {Object.entries(patternStats.by_type).map(([type, count]) => (
                <div key={type}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 capitalize">
                      {type.replace('_', ' ')}
                    </span>
                    <span className="text-sm text-gray-600">{count}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(count / patternStats.total_patterns) * 100}%`,
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
