/**
 * QueryPatternHeatmap - Phase 11.5
 *
 * Visualizes query patterns as a color-coded grid of table cells.
 * Supports view modes (Frequency, Joins, Performance),
 * time range filtering, and per-connection scoping.
 */

import { useState, useEffect, useCallback } from 'react';
import { lineageAPI } from '../../services/lineageApi';
import { connectionsAPI } from '../../services/api';
import { useDarkMode } from '../../hooks/useDarkMode';
import type { HeatmapDataResponse, TableUsageEntry, JoinPattern } from '../../types/lineage';
import type { DatabaseConnection } from '../../types/api';

type ViewMode = 'frequency' | 'joins' | 'performance';
type TimeRange = 7 | 30 | 90 | null;

const TIME_RANGES: { label: string; value: TimeRange }[] = [
  { label: '7d', value: 7 },
  { label: '30d', value: 30 },
  { label: '90d', value: 90 },
  { label: 'All', value: null },
];

const VIEW_MODES: { id: ViewMode; label: string }[] = [
  { id: 'frequency', label: 'Frequency' },
  { id: 'joins', label: 'Joins' },
  { id: 'performance', label: 'Performance' },
];

function getFrequencyColor(count: number, maxCount: number, isDark: boolean): string {
  if (maxCount === 0) return isDark ? 'bg-gray-800' : 'bg-gray-100';
  const ratio = count / maxCount;
  if (ratio > 0.8) return isDark ? 'bg-blue-700 text-white' : 'bg-blue-600 text-white';
  if (ratio > 0.6) return isDark ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white';
  if (ratio > 0.4) return isDark ? 'bg-blue-500/80 text-white' : 'bg-blue-400 text-white';
  if (ratio > 0.2) return isDark ? 'bg-blue-400/60 text-blue-100' : 'bg-blue-300 text-blue-900';
  if (ratio > 0) return isDark ? 'bg-blue-300/40 text-blue-200' : 'bg-blue-200 text-blue-800';
  return isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-100 text-gray-500';
}

function getJoinColor(count: number, maxCount: number, isDark: boolean): string {
  if (maxCount === 0) return isDark ? 'bg-gray-800' : 'bg-gray-100';
  const ratio = count / maxCount;
  if (ratio > 0.8) return isDark ? 'bg-purple-700 text-white' : 'bg-purple-600 text-white';
  if (ratio > 0.6) return isDark ? 'bg-purple-600 text-white' : 'bg-purple-500 text-white';
  if (ratio > 0.4) return isDark ? 'bg-purple-500/80 text-white' : 'bg-purple-400 text-white';
  if (ratio > 0.2) return isDark ? 'bg-purple-400/60 text-purple-100' : 'bg-purple-300 text-purple-900';
  if (ratio > 0) return isDark ? 'bg-purple-300/40 text-purple-200' : 'bg-purple-200 text-purple-800';
  return isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-100 text-gray-500';
}

function getPerformanceColor(avgMs: number | null | undefined, isDark: boolean): string {
  if (avgMs == null) return isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-100 text-gray-500';
  if (avgMs > 2000) return isDark ? 'bg-red-700 text-white' : 'bg-red-500 text-white';
  if (avgMs > 500) return isDark ? 'bg-orange-600 text-white' : 'bg-orange-400 text-white';
  if (avgMs > 100) return isDark ? 'bg-yellow-600/80 text-yellow-100' : 'bg-yellow-300 text-yellow-900';
  return isDark ? 'bg-green-600/60 text-green-100' : 'bg-green-200 text-green-900';
}

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '-';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function QueryPatternHeatmap() {
  const [viewMode, setViewMode] = useState<ViewMode>('frequency');
  const [timeRange, setTimeRange] = useState<TimeRange>(30);
  const [connectionId, setConnectionId] = useState<number>(0);
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [heatmapData, setHeatmapData] = useState<HeatmapDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  const { isDarkMode: isDark } = useDarkMode();

  // Fetch connections
  useEffect(() => {
    connectionsAPI.listConnections().then((res) => {
      setConnections(res.connections);
    }).catch(() => {});
  }, []);

  // Fetch heatmap data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await lineageAPI.getHeatmapData(connectionId, timeRange ?? undefined);
      setHeatmapData(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load patterns');
    } finally {
      setLoading(false);
    }
  }, [connectionId, timeRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function getCellLabel(table: TableUsageEntry): string {
    switch (viewMode) {
      case 'frequency': return `${table.query_count}`;
      case 'joins': return `${table.join_count}`;
      case 'performance': return formatMs(table.avg_execution_time_ms);
    }
  }

  function getCellColor(table: TableUsageEntry, maxVal: number): string {
    switch (viewMode) {
      case 'frequency': return getFrequencyColor(table.query_count, maxVal, isDark);
      case 'joins': return getJoinColor(table.join_count, maxVal, isDark);
      case 'performance': return getPerformanceColor(table.avg_execution_time_ms, isDark);
    }
  }

  // Get join partners for selected table
  function getJoinPartnersForTable(tableName: string): JoinPattern[] {
    if (!heatmapData) return [];
    return heatmapData.join_patterns.filter(
      (j) => j.table_a === tableName || j.table_b === tableName
    );
  }

  const tables = heatmapData?.table_usage ?? [];
  const maxFrequency = tables.length > 0 ? Math.max(...tables.map((t) => t.query_count)) : 0;
  const maxJoins = tables.length > 0 ? Math.max(...tables.map((t) => t.join_count)) : 0;
  const maxVal = viewMode === 'frequency' ? maxFrequency : viewMode === 'joins' ? maxJoins : 0;

  const selectedEntry = selectedTable ? tables.find((t) => t.table_name === selectedTable) : null;
  const selectedJoinPartners = selectedTable ? getJoinPartnersForTable(selectedTable) : [];

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Connection selector */}
        <select
          value={connectionId}
          onChange={(e) => { setConnectionId(Number(e.target.value)); setSelectedTable(null); }}
          className={`text-xs px-3 py-1.5 rounded-lg border ${
            isDark ? 'bg-gray-800 border-gray-600 text-gray-200' : 'bg-white border-gray-300 text-gray-700'
          }`}
        >
          <option value={0}>All Connections</option>
          {connections.map((c) => (
            <option key={c.id} value={c.id}>{c.name} ({c.database_type})</option>
          ))}
        </select>

        {/* View mode toggle */}
        <div className={`flex rounded-lg overflow-hidden border ${isDark ? 'border-gray-600' : 'border-gray-300'}`}>
          {VIEW_MODES.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setViewMode(mode.id)}
              className={`text-xs px-3 py-1.5 font-medium transition-colors ${
                viewMode === mode.id
                  ? 'bg-indigo-600 text-white'
                  : isDark ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>

        {/* Time range */}
        <div className={`flex rounded-lg overflow-hidden border ${isDark ? 'border-gray-600' : 'border-gray-300'}`}>
          {TIME_RANGES.map((tr) => (
            <button
              key={tr.label}
              onClick={() => { setTimeRange(tr.value); setSelectedTable(null); }}
              className={`text-xs px-3 py-1.5 font-medium transition-colors ${
                timeRange === tr.value
                  ? 'bg-indigo-600 text-white'
                  : isDark ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {tr.label}
            </button>
          ))}
        </div>

        {/* Stats summary */}
        {heatmapData && (
          <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            {heatmapData.total_queries_analyzed} queries analyzed
          </span>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className={`text-center py-8 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          Loading patterns...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-8 text-sm text-red-500">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && tables.length === 0 && (
        <div className={`text-center py-12 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          <p className="text-lg font-medium mb-2">No query patterns found</p>
          <p className="text-sm">Run some queries first, then come back to see usage patterns here.</p>
        </div>
      )}

      {/* Heatmap Grid */}
      {!loading && tables.length > 0 && (
        <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 gap-2">
          {tables.map((table) => (
            <button
              key={table.table_name}
              onClick={() => setSelectedTable(
                selectedTable === table.table_name ? null : table.table_name
              )}
              className={`
                relative p-3 rounded-xl text-center transition-all duration-200 border
                ${getCellColor(table, maxVal)}
                ${selectedTable === table.table_name
                  ? 'ring-2 ring-indigo-500 scale-105 shadow-lg'
                  : 'hover:scale-102 hover:shadow-md'
                }
                ${isDark ? 'border-white/10' : 'border-black/5'}
              `}
              title={`${table.table_name}: ${table.query_count} queries, ${formatMs(table.avg_execution_time_ms)} avg`}
            >
              <div className="text-xs font-bold truncate">{table.table_name}</div>
              <div className="text-xs mt-1 opacity-80">{getCellLabel(table)}</div>
            </button>
          ))}
        </div>
      )}

      {/* Detail Panel */}
      {selectedEntry && (
        <div className={`mt-2 p-4 rounded-xl border ${
          isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'
        }`}>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm font-bold">{selectedEntry.table_name}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              isDark ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-100 text-blue-700'
            }`}>
              {selectedEntry.query_count} queries
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              isDark ? 'bg-purple-500/20 text-purple-300' : 'bg-purple-100 text-purple-700'
            }`}>
              {selectedEntry.join_count} joins
            </span>
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              avg {formatMs(selectedEntry.avg_execution_time_ms)}
            </span>
          </div>

          {/* JOIN partners */}
          {selectedJoinPartners.length > 0 && (
            <div>
              <span className={`text-xs font-medium ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                Common JOINs:
              </span>
              <div className="flex flex-wrap gap-2 mt-1">
                {selectedJoinPartners.map((jp) => {
                  const partner = jp.table_a === selectedTable ? jp.table_b : jp.table_a;
                  return (
                    <span
                      key={`${jp.table_a}-${jp.table_b}`}
                      className={`text-xs px-2 py-1 rounded-lg ${
                        isDark ? 'bg-gray-700 text-gray-200' : 'bg-white text-gray-700 border border-gray-200'
                      }`}
                    >
                      {partner} ({jp.join_count}x)
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {selectedJoinPartners.length === 0 && (
            <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              No JOIN patterns recorded for this table
            </span>
          )}
        </div>
      )}

      {/* Bottlenecks section */}
      {!loading && heatmapData && heatmapData.bottlenecks.length > 0 && viewMode === 'performance' && (
        <div className={`mt-2 p-4 rounded-xl border ${
          isDark ? 'bg-red-900/10 border-red-800/30' : 'bg-red-50 border-red-100'
        }`}>
          <div className={`text-xs font-bold uppercase tracking-wide mb-2 ${
            isDark ? 'text-red-400' : 'text-red-600'
          }`}>
            Performance Bottlenecks
          </div>
          <div className="space-y-1">
            {heatmapData.bottlenecks.slice(0, 5).map((b) => (
              <div key={b.table_name} className="flex items-center gap-3 text-xs">
                <span className="font-medium w-32 truncate">{b.table_name}</span>
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  {b.query_count} queries
                </span>
                <span className={isDark ? 'text-orange-400' : 'text-orange-600'}>
                  avg {formatMs(b.avg_execution_time_ms)}
                </span>
                <span className={isDark ? 'text-red-400' : 'text-red-600'}>
                  max {formatMs(b.max_execution_time_ms)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
