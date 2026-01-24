/**
 * LineagePanel - Top-level panel for the Lineage tab.
 *
 * Sub-views:
 * - Explore: SQL textarea → parse → LineageGraph
 * - History: Dropdown of recent queries → LineageGraph
 * - Impact: Table/column input → list of affected queries with risk badges
 */

import React, { useState, useCallback } from 'react';
import LineageGraph from './LineageGraph';
import { lineageAPI } from '../../services/lineageApi';
import type { LineageGraphResponse, ImpactAnalysisResponse, ImpactedQuery } from '../../types/lineage';

type TabId = 'explore' | 'history' | 'impact';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'explore', label: 'Explore', icon: '🔍' },
  { id: 'history', label: 'History', icon: '📜' },
  { id: 'impact', label: 'Impact', icon: '💥' },
];

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export function LineagePanel() {
  const [activeTab, setActiveTab] = useState<TabId>('explore');
  const [lineageResult, setLineageResult] = useState<LineageGraphResponse | null>(null);

  // History tab state
  const [queryId, setQueryId] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyGraph, setHistoryGraph] = useState<LineageGraphResponse | null>(null);

  // Impact tab state
  const [impactTable, setImpactTable] = useState('');
  const [impactColumn, setImpactColumn] = useState('');
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactError, setImpactError] = useState<string | null>(null);
  const [impactResult, setImpactResult] = useState<ImpactAnalysisResponse | null>(null);

  const handleHistoryLoad = useCallback(async () => {
    const id = parseInt(queryId);
    if (isNaN(id)) return;

    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const result = await lineageAPI.getQueryLineage(id);
      setHistoryGraph(result);
    } catch (err: any) {
      setHistoryError(err.response?.data?.detail || err.message || 'Failed to load query lineage');
      setHistoryGraph(null);
    } finally {
      setHistoryLoading(false);
    }
  }, [queryId]);

  const handleImpactAnalyze = useCallback(async () => {
    if (!impactTable.trim()) return;

    setImpactLoading(true);
    setImpactError(null);
    try {
      const result = await lineageAPI.analyzeImpact(
        impactTable.trim(),
        impactColumn.trim() || undefined
      );
      setImpactResult(result);
    } catch (err: any) {
      setImpactError(err.response?.data?.detail || err.message || 'Impact analysis failed');
      setImpactResult(null);
    } finally {
      setImpactLoading(false);
    }
  }, [impactTable, impactColumn]);

  return (
    <div className="flex flex-col h-full">
      {/* Tab Navigation */}
      <div className="flex-shrink-0 px-4 pt-4 pb-2">
        <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wide transition-all duration-300 ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-white/50 dark:hover:bg-gray-700/50'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0">
        {activeTab === 'explore' && (
          <LineageGraph onParseComplete={setLineageResult} />
        )}

        {activeTab === 'history' && (
          <div className="flex flex-col h-full">
            <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                    Query ID
                  </label>
                  <input
                    type="number"
                    value={queryId}
                    onChange={(e) => setQueryId(e.target.value)}
                    placeholder="Enter query history ID..."
                    className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                    data-testid="query-id-input"
                  />
                </div>
                <button
                  onClick={handleHistoryLoad}
                  disabled={historyLoading || !queryId}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-sm font-bold transition-all shadow-lg"
                >
                  {historyLoading ? 'Loading...' : 'Load'}
                </button>
              </div>
              {historyError && (
                <p className="mt-2 text-sm text-red-600 dark:text-red-400">{historyError}</p>
              )}
            </div>
            <div className="flex-1 min-h-0">
              <LineageGraph graphData={historyGraph} />
            </div>
          </div>
        )}

        {activeTab === 'impact' && (
          <div className="flex flex-col h-full overflow-auto p-4">
            {/* Impact Input */}
            <div className="flex-shrink-0 mb-4">
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                    Table Name
                  </label>
                  <input
                    type="text"
                    value={impactTable}
                    onChange={(e) => setImpactTable(e.target.value)}
                    placeholder="e.g., customers"
                    className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                    data-testid="impact-table-input"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                    Column (optional)
                  </label>
                  <input
                    type="text"
                    value={impactColumn}
                    onChange={(e) => setImpactColumn(e.target.value)}
                    placeholder="e.g., email"
                    className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                    data-testid="impact-column-input"
                  />
                </div>
                <button
                  onClick={handleImpactAnalyze}
                  disabled={impactLoading || !impactTable.trim()}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-sm font-bold transition-all shadow-lg"
                  data-testid="impact-analyze-button"
                >
                  {impactLoading ? 'Analyzing...' : 'Analyze'}
                </button>
              </div>
              {impactError && (
                <p className="mt-2 text-sm text-red-600 dark:text-red-400">{impactError}</p>
              )}
            </div>

            {/* Impact Results */}
            {impactResult && (
              <div className="space-y-4">
                {/* Summary */}
                <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                      Impact: {impactResult.changed_object}
                    </h3>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${RISK_COLORS[impactResult.risk_level]}`}>
                      {impactResult.risk_level.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{impactResult.summary}</p>
                  <div className="flex gap-4 mt-3 text-xs">
                    <span className="text-green-600 dark:text-green-400">Low: {impactResult.risk_counts.low}</span>
                    <span className="text-yellow-600 dark:text-yellow-400">Medium: {impactResult.risk_counts.medium}</span>
                    <span className="text-red-600 dark:text-red-400">High: {impactResult.risk_counts.high}</span>
                  </div>
                </div>

                {/* Affected Queries */}
                {impactResult.impacted_queries.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                      Affected Queries ({impactResult.total_affected})
                    </h4>
                    {impactResult.impacted_queries.map((q) => (
                      <ImpactedQueryCard key={q.query_id} query={q} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ImpactedQueryCard({ query }: { query: ImpactedQuery }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="p-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${RISK_COLORS[query.risk_level]}`}>
            {query.risk_level}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            {query.impact_type}
          </span>
          <span className="text-sm text-gray-900 dark:text-white truncate">
            {query.natural_language_query}
          </span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex-shrink-0 ml-2"
        >
          {expanded ? 'Hide SQL' : 'Show SQL'}
        </button>
      </div>
      {expanded && (
        <pre className="mt-2 p-2 text-xs font-mono bg-gray-50 dark:bg-gray-900 rounded-lg overflow-x-auto text-gray-700 dark:text-gray-300">
          {query.generated_sql}
        </pre>
      )}
    </div>
  );
}

export default LineagePanel;
