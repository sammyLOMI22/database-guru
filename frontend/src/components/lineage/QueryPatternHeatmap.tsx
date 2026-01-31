/**
 * QueryPatternHeatmap - Phase 11.5 + Phase 12.4
 *
 * Visualizes query patterns as a color-coded grid of table cells.
 * Supports view modes (Frequency, Joins, Performance),
 * time range filtering, and per-connection scoping.
 *
 * Phase 12.4 adds Pattern Intelligence panel with:
 * - Anti-pattern detection
 * - Bottleneck root cause analysis
 * - Optimization suggestions
 */

import { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Zap,
  TrendingUp,
  TrendingDown,
  Brain,
} from 'lucide-react';
import { lineageAPI } from '../../services/lineageApi';
import { connectionsAPI } from '../../services/api';
import { useDarkMode } from '../../hooks/useDarkMode';
import type {
  HeatmapDataResponse,
  TableUsageEntry,
  JoinPattern,
  PatternIntelligenceReport,
  BottleneckAnalysis,
} from '../../types/lineage';
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

  // Pattern Intelligence state (Phase 12.4)
  const [intelligenceReport, setIntelligenceReport] = useState<PatternIntelligenceReport | null>(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);
  const [intelligenceError, setIntelligenceError] = useState<string | null>(null);
  const [showIntelligence, setShowIntelligence] = useState(false);
  const [selectedBottleneck, setSelectedBottleneck] = useState<BottleneckAnalysis | null>(null);

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
    // Reset intelligence when connection/time changes
    setIntelligenceReport(null);
    setShowIntelligence(false);
  }, [fetchData]);

  // Fetch pattern intelligence
  const fetchIntelligence = async () => {
    setIntelligenceLoading(true);
    setIntelligenceError(null);
    try {
      const report = await lineageAPI.analyzePatterns(connectionId, timeRange ?? 30, true);
      setIntelligenceReport(report);
      setShowIntelligence(true);
    } catch (err: any) {
      setIntelligenceError(err.response?.data?.detail || err.message || 'Failed to analyze patterns');
    } finally {
      setIntelligenceLoading(false);
    }
  };

  // Fetch detailed bottleneck analysis
  const fetchBottleneckDetail = async (tableName: string) => {
    if (selectedBottleneck?.table_name === tableName) {
      setSelectedBottleneck(null);
      return;
    }
    try {
      const analysis = await lineageAPI.analyzeBottleneck(connectionId, tableName);
      setSelectedBottleneck(analysis);
    } catch (err: any) {
      console.error('Failed to fetch bottleneck details:', err);
    }
  };

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

        {/* Pattern Intelligence button (Phase 12.4) */}
        {heatmapData && heatmapData.total_queries_analyzed > 0 && (
          <button
            onClick={fetchIntelligence}
            disabled={intelligenceLoading}
            className={`ml-auto flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              isDark
                ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                : 'bg-cyan-500 hover:bg-cyan-600 text-white'
            } disabled:opacity-50`}
          >
            {intelligenceLoading ? (
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Brain className="w-3 h-3" />
            )}
            {intelligenceLoading ? 'Analyzing...' : 'AI Analysis'}
          </button>
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
              <button
                key={b.table_name}
                onClick={() => fetchBottleneckDetail(b.table_name)}
                className={`w-full flex items-center gap-3 text-xs p-2 rounded-lg transition-colors ${
                  selectedBottleneck?.table_name === b.table_name
                    ? isDark ? 'bg-red-900/30' : 'bg-red-100'
                    : isDark ? 'hover:bg-red-900/20' : 'hover:bg-red-100/50'
                }`}
              >
                <span className="font-medium w-32 truncate text-left">{b.table_name}</span>
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  {b.query_count} queries
                </span>
                <span className={isDark ? 'text-orange-400' : 'text-orange-600'}>
                  avg {formatMs(b.avg_execution_time_ms)}
                </span>
                <span className={isDark ? 'text-red-400' : 'text-red-600'}>
                  max {formatMs(b.max_execution_time_ms)}
                </span>
                <Zap className={`w-3 h-3 ml-auto ${isDark ? 'text-cyan-400' : 'text-cyan-600'}`} />
              </button>
            ))}
          </div>

          {/* Bottleneck Detail Panel */}
          {selectedBottleneck && (
            <div className={`mt-3 p-3 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold">{selectedBottleneck.table_name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  isDark ? 'bg-cyan-500/20 text-cyan-400' : 'bg-cyan-100 text-cyan-700'
                }`}>
                  AI Analysis
                </span>
              </div>

              {selectedBottleneck.root_causes.length > 0 && (
                <div className="mb-2">
                  <span className={`text-[10px] font-bold uppercase ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                    Root Causes
                  </span>
                  <ul className="mt-1 space-y-0.5">
                    {selectedBottleneck.root_causes.map((cause, i) => (
                      <li key={i} className="text-xs flex items-start gap-1">
                        <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0 text-red-500" />
                        <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>{cause}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedBottleneck.optimization_suggestions.length > 0 && (
                <div>
                  <span className={`text-[10px] font-bold uppercase ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                    Suggestions
                  </span>
                  <ul className="mt-1 space-y-0.5">
                    {selectedBottleneck.optimization_suggestions.map((sug, i) => (
                      <li key={i} className="text-xs flex items-start gap-1">
                        <Lightbulb className="w-3 h-3 mt-0.5 flex-shrink-0 text-emerald-500" />
                        <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>{sug}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Pattern Intelligence Panel (Phase 12.4) */}
      {showIntelligence && intelligenceReport && (
        <PatternIntelligencePanel
          report={intelligenceReport}
          isDark={isDark}
          onClose={() => setShowIntelligence(false)}
        />
      )}

      {/* Intelligence Error */}
      {intelligenceError && (
        <div className={`p-3 rounded-lg text-xs ${isDark ? 'bg-red-900/20 text-red-400' : 'bg-red-50 text-red-600'}`}>
          {intelligenceError}
        </div>
      )}
    </div>
  );
}

// Pattern Intelligence Panel Component
function PatternIntelligencePanel({
  report,
  isDark,
  onClose,
}: {
  report: PatternIntelligenceReport;
  isDark: boolean;
  onClose: () => void;
}) {
  const [expandedSection, setExpandedSection] = useState<string | null>('antipatterns');

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className={`mt-2 rounded-xl border overflow-hidden ${
      isDark ? 'bg-cyan-900/10 border-cyan-800/30' : 'bg-cyan-50 border-cyan-200'
    }`}>
      {/* Header */}
      <div className={`px-4 py-3 flex items-center justify-between ${
        isDark ? 'bg-cyan-900/20' : 'bg-cyan-100/50'
      }`}>
        <div className="flex items-center gap-2">
          <Brain className={`w-4 h-4 ${isDark ? 'text-cyan-400' : 'text-cyan-600'}`} />
          <span className={`text-xs font-bold uppercase tracking-wide ${isDark ? 'text-cyan-300' : 'text-cyan-700'}`}>
            Pattern Intelligence
          </span>
          {report.llm_used && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${isDark ? 'bg-cyan-500/20 text-cyan-400' : 'bg-cyan-200 text-cyan-700'}`}>
              AI Enhanced
            </span>
          )}
        </div>
        <button onClick={onClose} className={`text-xs ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`}>
          Close
        </button>
      </div>

      {/* Summary */}
      {report.summary && (
        <div className={`px-4 py-3 text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          {report.summary}
        </div>
      )}

      {/* Anti-Patterns Section */}
      {report.anti_patterns.length > 0 && (
        <div className={`border-t ${isDark ? 'border-cyan-800/30' : 'border-cyan-200'}`}>
          <button
            onClick={() => toggleSection('antipatterns')}
            className={`w-full px-4 py-3 flex items-center justify-between ${
              isDark ? 'hover:bg-cyan-900/20' : 'hover:bg-cyan-100/50'
            }`}
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className={`w-4 h-4 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
              <span className={`text-xs font-bold uppercase ${isDark ? 'text-amber-300' : 'text-amber-700'}`}>
                Anti-Patterns ({report.anti_patterns.length})
              </span>
            </div>
            {expandedSection === 'antipatterns' ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {expandedSection === 'antipatterns' && (
            <div className={`px-4 pb-3 space-y-2 ${isDark ? 'bg-gray-800/30' : 'bg-white/50'}`}>
              {report.anti_patterns.map((ap, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg border ${
                    ap.severity === 'warning'
                      ? isDark ? 'border-amber-800/30 bg-amber-900/10' : 'border-amber-200 bg-amber-50'
                      : isDark ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-bold ${
                      ap.severity === 'warning'
                        ? isDark ? 'text-amber-300' : 'text-amber-700'
                        : isDark ? 'text-gray-300' : 'text-gray-700'
                    }`}>
                      {ap.title}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      ap.severity === 'warning'
                        ? isDark ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-100 text-amber-700'
                        : isDark ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {ap.occurrence_count}x
                    </span>
                  </div>
                  <p className={`text-xs mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    {ap.description}
                  </p>
                  <div className={`flex items-start gap-1 text-xs ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                    <Lightbulb className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    {ap.recommendation}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Optimization Suggestions Section */}
      {report.optimization_suggestions.length > 0 && (
        <div className={`border-t ${isDark ? 'border-cyan-800/30' : 'border-cyan-200'}`}>
          <button
            onClick={() => toggleSection('optimizations')}
            className={`w-full px-4 py-3 flex items-center justify-between ${
              isDark ? 'hover:bg-cyan-900/20' : 'hover:bg-cyan-100/50'
            }`}
          >
            <div className="flex items-center gap-2">
              <Zap className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`} />
              <span className={`text-xs font-bold uppercase ${isDark ? 'text-emerald-300' : 'text-emerald-700'}`}>
                Optimizations ({report.optimization_suggestions.length})
              </span>
            </div>
            {expandedSection === 'optimizations' ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {expandedSection === 'optimizations' && (
            <div className={`px-4 pb-3 space-y-2 ${isDark ? 'bg-gray-800/30' : 'bg-white/50'}`}>
              {report.optimization_suggestions.map((opt, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg border ${isDark ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-gray-50'}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      opt.estimated_impact === 'high'
                        ? isDark ? 'bg-red-500/20 text-red-400' : 'bg-red-100 text-red-700'
                        : opt.estimated_impact === 'medium'
                        ? isDark ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-100 text-amber-700'
                        : isDark ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {opt.estimated_impact} impact
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${isDark ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'}`}>
                      {opt.category}
                    </span>
                  </div>
                  <p className={`text-xs font-medium mb-1 ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                    {opt.title}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    {opt.description}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Trends Section */}
      {report.trend_analysis && (
        <div className={`border-t ${isDark ? 'border-cyan-800/30' : 'border-cyan-200'}`}>
          <button
            onClick={() => toggleSection('trends')}
            className={`w-full px-4 py-3 flex items-center justify-between ${
              isDark ? 'hover:bg-cyan-900/20' : 'hover:bg-cyan-100/50'
            }`}
          >
            <div className="flex items-center gap-2">
              <TrendingUp className={`w-4 h-4 ${isDark ? 'text-indigo-400' : 'text-indigo-600'}`} />
              <span className={`text-xs font-bold uppercase ${isDark ? 'text-indigo-300' : 'text-indigo-700'}`}>
                Usage Trends
              </span>
            </div>
            {expandedSection === 'trends' ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {expandedSection === 'trends' && (
            <div className={`px-4 pb-3 ${isDark ? 'bg-gray-800/30' : 'bg-white/50'}`}>
              <p className={`text-xs mb-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {report.trend_analysis.summary}
              </p>

              <div className="grid grid-cols-3 gap-3">
                {/* Busiest */}
                <div>
                  <span className={`text-[10px] font-bold uppercase ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                    Most Active
                  </span>
                  <div className="mt-1 space-y-1">
                    {report.trend_analysis.busiest_tables.slice(0, 3).map((t) => (
                      <div key={t} className={`text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                        {t}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Emerging */}
                <div>
                  <span className={`text-[10px] font-bold uppercase flex items-center gap-1 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                    <TrendingUp className="w-3 h-3" /> Emerging
                  </span>
                  <div className="mt-1 space-y-1">
                    {report.trend_analysis.emerging_tables.slice(0, 3).map((t) => (
                      <div key={t} className={`text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                        {t}
                      </div>
                    ))}
                    {report.trend_analysis.emerging_tables.length === 0 && (
                      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>-</span>
                    )}
                  </div>
                </div>

                {/* Declining */}
                <div>
                  <span className={`text-[10px] font-bold uppercase flex items-center gap-1 ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
                    <TrendingDown className="w-3 h-3" /> Declining
                  </span>
                  <div className="mt-1 space-y-1">
                    {report.trend_analysis.declining_tables.slice(0, 3).map((t) => (
                      <div key={t} className={`text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                        {t}
                      </div>
                    ))}
                    {report.trend_analysis.declining_tables.length === 0 && (
                      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>-</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Top Recommendations */}
      {report.recommendations.length > 0 && (
        <div className={`px-4 py-3 border-t ${isDark ? 'border-cyan-800/30 bg-cyan-900/20' : 'border-cyan-200 bg-cyan-100/30'}`}>
          <span className={`text-[10px] font-bold uppercase ${isDark ? 'text-cyan-400' : 'text-cyan-700'}`}>
            Top Recommendations
          </span>
          <ul className="mt-2 space-y-1">
            {report.recommendations.slice(0, 3).map((rec, i) => (
              <li key={i} className={`text-xs flex items-start gap-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                <Lightbulb className="w-3 h-3 mt-0.5 flex-shrink-0 text-cyan-500" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
