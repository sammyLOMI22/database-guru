/**
 * LineagePanel - Top-level panel for the Lineage tab.
 *
 * Sub-views:
 * - Explore: SQL textarea → parse → LineageGraph + ColumnLineage table
 * - History: Dropdown of recent queries → LineageGraph
 * - Impact: Table/column input → ImpactAnalysisPanel
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import LineageGraph from './LineageGraph';
import { ColumnLineage } from './ColumnLineage';
import { ImpactAnalysisPanel } from './ImpactAnalysisPanel';
import { lineageAPI } from '../../services/lineageApi';
import type { LineageGraphResponse } from '../../types/lineage';

type TabId = 'explore' | 'history' | 'impact';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'explore', label: 'Explore', icon: '🔍' },
  { id: 'history', label: 'History', icon: '📜' },
  { id: 'impact', label: 'Impact', icon: '💥' },
];

interface LineagePanelProps {
  initialSql?: string;
  initialTab?: TabId;
  initialImpactTable?: string;
}

export function LineagePanel({ initialSql, initialTab, initialImpactTable }: LineagePanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>(initialTab || 'explore');
  const [lineageResult, setLineageResult] = useState<LineageGraphResponse | null>(null);
  const [showColumnLineage, setShowColumnLineage] = useState(true);

  // History tab state
  const [queryId, setQueryId] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyGraph, setHistoryGraph] = useState<LineageGraphResponse | null>(null);

  // Impact tab state
  const [impactTable, setImpactTable] = useState(initialImpactTable || '');
  const [impactColumn, setImpactColumn] = useState('');
  const [impactKey, setImpactKey] = useState(0);
  const [submittedImpact, setSubmittedImpact] = useState<{ table: string; column?: string } | null>(
    initialImpactTable ? { table: initialImpactTable } : null
  );

  // React to prop changes for cross-component navigation
  const prevPropsRef = useRef({ initialTab, initialImpactTable, initialSql });
  useEffect(() => {
    const prev = prevPropsRef.current;
    if (initialTab && initialTab !== prev.initialTab) {
      setActiveTab(initialTab);
    }
    if (initialImpactTable && initialImpactTable !== prev.initialImpactTable) {
      setImpactTable(initialImpactTable);
      setSubmittedImpact({ table: initialImpactTable });
      setImpactKey((k) => k + 1);
    }
    prevPropsRef.current = { initialTab, initialImpactTable, initialSql };
  }, [initialTab, initialImpactTable, initialSql]);

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

  const handleImpactAnalyze = useCallback(() => {
    if (!impactTable.trim()) return;
    setSubmittedImpact({ table: impactTable.trim(), column: impactColumn.trim() || undefined });
    setImpactKey((k) => k + 1);
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
          <div className="flex flex-col h-full">
            <div className={`min-h-0 ${lineageResult && showColumnLineage ? 'h-[60%]' : 'flex-1'}`}>
              <LineageGraph onParseComplete={setLineageResult} initialSql={initialSql} />
            </div>
            {lineageResult && (
              <>
                <button
                  onClick={() => setShowColumnLineage(!showColumnLineage)}
                  className="flex-shrink-0 flex items-center justify-center gap-2 px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 transition-colors"
                >
                  Column Lineage
                  {showColumnLineage ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
                </button>
                {showColumnLineage && (
                  <div className="h-[40%] min-h-0 border-t border-gray-200 dark:border-gray-700 overflow-auto">
                    <ColumnLineage graphData={lineageResult} />
                  </div>
                )}
              </>
            )}
          </div>
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
                  disabled={!impactTable.trim()}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-sm font-bold transition-all shadow-lg"
                  data-testid="impact-analyze-button"
                >
                  Analyze
                </button>
              </div>
            </div>

            {/* Impact Results (delegated to ImpactAnalysisPanel) */}
            {submittedImpact && (
              <ImpactAnalysisPanel
                key={impactKey}
                tableName={submittedImpact.table}
                columnName={submittedImpact.column}
                autoAnalyze
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default LineagePanel;
