import React, { useEffect, useState } from 'react';
import { TrendingUp, CheckCircle, Target, Award, Database, Table, ArrowRight } from 'lucide-react';
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-32 glass-panel rounded-2xl"></div>
          <div className="h-32 glass-panel rounded-2xl"></div>
          <div className="h-32 glass-panel rounded-2xl"></div>
        </div>
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

  if (!columnStats || !tableStats || !patternStats) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Column Mappings */}
        <div className="glass-card rounded-2xl p-5 bg-gradient-to-br from-blue-500/10 via-transparent to-cyan-500/5 border-blue-500/20 hover:scale-[1.02] transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Column Mappings</p>
              <p className="text-3xl font-black text-gray-900 dark:text-white mt-1">{columnStats.total_mappings}</p>
              <p className="text-[11px] font-black uppercase tracking-[0.15em] text-blue-600 dark:text-blue-400 mt-1">
                {columnStats.total_applications} applications
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-blue-500/20 flex items-center justify-center text-blue-500">
              <Database className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Table Mappings */}
        <div className="glass-card rounded-2xl p-5 bg-gradient-to-br from-emerald-500/10 via-transparent to-green-500/5 border-emerald-500/20 hover:scale-[1.02] transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Table Mappings</p>
              <p className="text-3xl font-black text-gray-900 dark:text-white mt-1">{tableStats.total_mappings}</p>
              <p className="text-[11px] font-black uppercase tracking-[0.15em] text-emerald-600 dark:text-emerald-400 mt-1">
                {tableStats.total_applications} applications
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center text-emerald-500">
              <Table className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Result Patterns */}
        <div className="glass-card rounded-2xl p-5 bg-gradient-to-br from-purple-500/10 via-transparent to-indigo-500/5 border-purple-500/20 hover:scale-[1.02] transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Validation Patterns</p>
              <p className="text-3xl font-black text-gray-900 dark:text-white mt-1">{patternStats.total_patterns}</p>
              <p className="text-[11px] font-black uppercase tracking-[0.15em] text-purple-600 dark:text-purple-400 mt-1">
                {patternStats.total_triggers} triggers
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-purple-500/20 flex items-center justify-center text-purple-500">
              <Target className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Success Rates */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel rounded-2xl p-4 border-white/5 hover:scale-[1.02] transition-all">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-xl bg-blue-500/20 flex items-center justify-center text-blue-500">
              <CheckCircle className="w-4 h-4" />
            </div>
            <p className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-600 dark:text-gray-400">Column Success</p>
          </div>
          <p className="text-2xl font-black text-blue-600 dark:text-blue-400">
            {(columnStats.average_success_rate * 100).toFixed(1)}%
          </p>
        </div>

        <div className="glass-panel rounded-2xl p-4 border-white/5 hover:scale-[1.02] transition-all">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-500">
              <CheckCircle className="w-4 h-4" />
            </div>
            <p className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-600 dark:text-gray-400">Table Success</p>
          </div>
          <p className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
            {(tableStats.average_success_rate * 100).toFixed(1)}%
          </p>
        </div>

        <div className="glass-panel rounded-2xl p-4 border-white/5 hover:scale-[1.02] transition-all">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-xl bg-purple-500/20 flex items-center justify-center text-purple-500">
              <Award className="w-4 h-4" />
            </div>
            <p className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-600 dark:text-gray-400">Helpfulness</p>
          </div>
          <p className="text-2xl font-black text-purple-600 dark:text-purple-400">
            {patternStats.helpfulness_rate.toFixed(1)}%
          </p>
          <p className="text-[11px] font-black uppercase tracking-[0.1em] text-gray-400 mt-1">
            {patternStats.total_helpful} / {patternStats.total_triggers}
          </p>
        </div>
      </div>

      {/* Most Used Mappings */}
      {columnStats.most_used.length > 0 && (
        <div className="glass-panel rounded-2xl p-5 border-white/5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-xl bg-blue-500/20 flex items-center justify-center text-blue-500">
              <TrendingUp className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-300">
              Top Column Mappings
            </h3>
          </div>
          <div className="space-y-2">
            {columnStats.most_used.map((mapping, index) => (
              <div key={index} className="flex items-center justify-between glass-card rounded-xl p-3 border-white/5 hover:scale-[1.005] transition-all">
                <div className="flex items-center gap-3">
                  <span className="text-[11px] font-black text-gray-400 w-4">#{index + 1}</span>
                  <span className="font-mono text-[11px] text-red-500 line-through bg-red-500/10 px-1.5 py-0.5 rounded-lg">
                    {mapping.source}
                  </span>
                  <ArrowRight className="w-3 h-3 text-gray-400" />
                  <span className="font-mono text-[11px] text-emerald-500 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded-lg">
                    {mapping.target}
                  </span>
                  {mapping.table && (
                    <span className="text-[11px] font-medium text-gray-400">in {mapping.table}</span>
                  )}
                </div>
                <span className="text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  {mapping.times_applied}x
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Most Used Table Mappings */}
      {tableStats.most_used.length > 0 && (
        <div className="glass-panel rounded-2xl p-5 border-white/5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-500">
              <TrendingUp className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-300">
              Top Table Mappings
            </h3>
          </div>
          <div className="space-y-2">
            {tableStats.most_used.map((mapping, index) => (
              <div key={index} className="flex items-center justify-between glass-card rounded-xl p-3 border-white/5 hover:scale-[1.005] transition-all">
                <div className="flex items-center gap-3">
                  <span className="text-[11px] font-black text-gray-400 w-4">#{index + 1}</span>
                  <span className="font-mono text-[11px] text-red-500 line-through bg-red-500/10 px-1.5 py-0.5 rounded-lg">
                    {mapping.source}
                  </span>
                  <ArrowRight className="w-3 h-3 text-gray-400" />
                  <span className="font-mono text-[11px] text-emerald-500 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded-lg">
                    {mapping.target}
                  </span>
                  {mapping.type && (
                    <span className="text-[11px] font-black uppercase tracking-[0.15em] px-1.5 py-0.5 rounded-lg bg-gray-500/10 text-gray-500">
                      {mapping.type}
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-black uppercase tracking-[0.15em] px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
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
          <div className="glass-panel rounded-2xl p-5 border-white/5">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-300 mb-4">
              Columns by Database
            </h3>
            <div className="space-y-3">
              {Object.entries(columnStats.by_database_type).map(([dbType, count]) => (
                <div key={dbType}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-600 dark:text-gray-400">{dbType}</span>
                    <span className="text-[11px] font-black text-blue-600 dark:text-blue-400">{count}</span>
                  </div>
                  <div className="w-full bg-black/5 dark:bg-white/5 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
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
          <div className="glass-panel rounded-2xl p-5 border-white/5">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-300 mb-4">
              Patterns by Type
            </h3>
            <div className="space-y-3">
              {Object.entries(patternStats.by_type).map(([type, count]) => (
                <div key={type}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-600 dark:text-gray-400">
                      {type.replace('_', ' ')}
                    </span>
                    <span className="text-[11px] font-black text-purple-600 dark:text-purple-400">{count}</span>
                  </div>
                  <div className="w-full bg-black/5 dark:bg-white/5 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
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
