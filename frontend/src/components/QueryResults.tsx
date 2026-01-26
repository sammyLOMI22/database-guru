import { Copy, Check, MessageSquare, Zap, Database, ChevronLeft, ChevronRight } from 'lucide-react';
import { useTableSort } from '../hooks/useTableSort';
import { SortableTableHeader } from './SortableTableHeader';
import { useState, useMemo, useEffect } from 'react';
import {
  AgentTrace as AgentTraceType,
  QueryPlan,
  CorrectionAttempt,
  ParallelExecutionMetrics,
  ParallelCorrectionMetrics,
  ResultAnalysis
} from '../types/api';
import { AgentTrace } from './AgentTrace';
import { CorrectionHistory } from './CorrectionHistory';
import { QueryPlanVisualization } from './QueryPlanVisualization';
import { VerificationWarnings } from './VerificationWarnings';
import { FeedbackModal, FeedbackData } from './FeedbackModal';
import { ParallelDatabaseMetrics, ParallelCorrectionsMetrics } from './ParallelExecutionMetrics';
import { ResultSummary } from './ResultSummary';
import { feedbackAPI } from '../services/api';
import { ChartVisualization } from './visualization/ChartVisualization';
import { ChartToggle, ViewMode } from './visualization/ChartToggle';
import { ExportDropdown } from './visualization/ExportDropdown';
import { ChartType } from '../utils/chartUtils';
import { analyzeData } from '../utils/chartIntelligence';

interface QueryResultsProps {
  sql: string;
  results: Record<string, any>[] | null;
  rowCount: number | null;
  executionTime: number | null;
  isValid: boolean;
  warnings: string[];
  queryId?: number | null; // Added for feedback functionality
  // Option 2: Observability props
  agentTrace?: AgentTraceType | null;
  queryPlan?: QueryPlan | null;
  attempts?: CorrectionAttempt[] | null;
  selfCorrected?: boolean;
  totalAttempts?: number;
  verificationWarnings?: string[];
  usedPlanning?: boolean;
  // Parallel Execution Metrics
  parallelExecutionMetrics?: ParallelExecutionMetrics | null;
  parallelCorrectionMetrics?: ParallelCorrectionMetrics | null;
  // Cache Information
  cacheType?: 'exact' | 'semantic' | null;
  semanticSimilarity?: number | null;
  matchedQuestion?: string | null;
  // Intelligent Data Narratives
  resultAnalysis?: ResultAnalysis | null;
  // Chart Intent (Phase 8: Chart Intelligence)
  preferredChartType?: ChartType | null;
}

export default function QueryResults({
  sql,
  results,
  rowCount,
  executionTime,
  isValid,
  warnings,
  queryId,
  agentTrace,
  queryPlan,
  attempts,
  selfCorrected = false,
  totalAttempts: _totalAttempts = 1,
  verificationWarnings = [],
  usedPlanning = false,
  parallelExecutionMetrics,
  parallelCorrectionMetrics,
  cacheType,
  semanticSimilarity,
  matchedQuestion,
  resultAnalysis,
  preferredChartType,
}: QueryResultsProps) {
  const [copied, setCopied] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [selectedChartType, setSelectedChartType] = useState<ChartType | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Sorting state
  const { sortedData, sortConfig, handleSort, resetSort } = useTableSort(
    results ?? [],
    {
      onSortChange: () => setCurrentPage(1), // Reset to page 1 on sort change
    }
  );

  // Reset pagination, sorting, and selection when results change
  useEffect(() => {
    setCurrentPage(1);
    setSelectedChartType(null);
    resetSort();
  }, [results, resetSort]);

  // Auto-select chart type and view mode when preferred chart type is provided
  useEffect(() => {
    if (preferredChartType && preferredChartType !== 'table' && results && results.length > 0) {
      setSelectedChartType(preferredChartType);
      setViewMode('chart');
    }
  }, [preferredChartType, results]);

  // Detect chart availability based on data and statistics
  const chartRecommendation = useMemo(() => {
    if (!results || results.length === 0) {
      return { chartType: 'table' as const, confidence: 0, xColumn: null, yColumn: null, reason: 'No data' };
    }
    const analysis = analyzeData(results, resultAnalysis?.statistics || {});
    return {
      chartType: analysis.primaryChart,
      confidence: analysis.confidence,
      xColumn: analysis.xColumn,
      yColumn: analysis.yColumn,
      reason: analysis.reason
    };
  }, [results, resultAnalysis]);

  const chartAvailable = chartRecommendation.chartType !== 'table';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedbackSubmit = async (feedback: FeedbackData) => {
    try {
      await feedbackAPI.submitFeedback(feedback);
      // Success notification could be added here
      setShowFeedbackModal(false);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      // Error is logged but not re-thrown to avoid unhandled rejections
      // FeedbackModal can display its own error handling if needed
    }
  };

  return (
    <div className="space-y-4">
      {/* Cache Badge */}
      {cacheType && (
        <div className={`glass-card rounded-2xl p-4 border-white/10 bg-gradient-to-r ${cacheType === 'exact'
          ? 'from-emerald-500/10 via-transparent to-green-500/5'
          : 'from-amber-500/10 via-transparent to-yellow-500/5'
          }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl glass-panel flex items-center justify-center ${cacheType === 'exact' ? 'text-emerald-500' : 'text-amber-500'}`}>
                {cacheType === 'exact' ? (
                  <Database className="w-5 h-5" />
                ) : (
                  <Zap className="w-5 h-5" />
                )}
              </div>
              <div>
                <span className={`text-xs font-black uppercase tracking-widest ${cacheType === 'exact' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                  {cacheType === 'exact' ? 'Exact Cache Hit' : 'Semantic Cache Hit'}
                </span>
                {semanticSimilarity && cacheType === 'semantic' && (
                  <span className="ml-2 text-[11px] font-bold text-amber-500 uppercase tracking-widest">
                    ({(semanticSimilarity * 100).toFixed(0)}% match)
                  </span>
                )}
              </div>
            </div>
            <span className={`text-[11px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg glass-panel ${cacheType === 'exact'
              ? 'text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
              : 'text-amber-600 dark:text-amber-400 border-amber-500/20'
              }`}>
              Instant
            </span>
          </div>
          {matchedQuestion && cacheType === 'semantic' && (
            <p className="text-[11px] font-medium text-amber-600 dark:text-amber-400 mt-3 pl-13">
              <span className="font-bold uppercase tracking-widest">Matched:</span> "{matchedQuestion}"
            </p>
          )}
        </div>
      )}

      {/* Result Narratives - Intelligent Data Insights */}
      {resultAnalysis && (
        <ResultSummary
          analysis={resultAnalysis}
          rowCount={rowCount || undefined}
          executionTime={executionTime || undefined}
        />
      )}

      {/* SQL Display */}
      <div className="glass-panel rounded-2xl overflow-hidden border-white/10">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-black/20">
          <span className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Generated SQL
          </span>
          <div className="flex items-center gap-1">
            {queryId && (
              <button
                onClick={() => setShowFeedbackModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
                title="Provide Feedback"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Feedback</span>
              </button>
            )}
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-emerald-400 hover:bg-white/10 transition-all"
              title="Copy SQL"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>
        <div className="p-5 bg-gray-900 dark:bg-black">
          <pre className="text-sm text-emerald-400 font-mono overflow-x-auto">
            {sql}
          </pre>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-r from-amber-500/10 via-transparent to-yellow-500/5">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-amber-500 flex-shrink-0">
              <span className="text-lg">⚠️</span>
            </div>
            <div className="flex-1">
              <p className="text-xs font-black uppercase tracking-widest text-amber-600 dark:text-amber-400">Warnings</p>
              <ul className="mt-2 space-y-1">
                {warnings.map((warning, index) => (
                  <li key={index} className="text-sm font-medium text-amber-700 dark:text-amber-300 flex items-start gap-2">
                    <span className="text-amber-500 mt-1.5">•</span>
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Option 2: Observability Components */}
      {/* Verification Warnings */}
      {verificationWarnings && verificationWarnings.length > 0 && (
        <VerificationWarnings warnings={verificationWarnings} />
      )}

      {/* Correction History */}
      {selfCorrected && attempts && attempts.length > 0 && (
        <CorrectionHistory attempts={attempts} selfCorrected={selfCorrected} />
      )}

      {/* Parallel Correction Metrics */}
      {parallelCorrectionMetrics && (
        <ParallelCorrectionsMetrics metrics={parallelCorrectionMetrics} />
      )}

      {/* Parallel Execution Metrics */}
      {parallelExecutionMetrics && (
        <ParallelDatabaseMetrics metrics={parallelExecutionMetrics} />
      )}

      {/* Query Plan */}
      {usedPlanning && queryPlan && (
        <QueryPlanVisualization plan={queryPlan} usedPlanning={usedPlanning} />
      )}

      {/* Agent Trace */}
      {agentTrace && (
        <AgentTrace trace={agentTrace} />
      )}

      {/* Results */}
      {results && results.length > 0 ? (
        <div className="glass-panel rounded-2xl border-white/10 overflow-hidden">
          {/* Header with stats, toggle, and export */}
          <div className="px-5 py-4 border-b border-white/5 bg-black/5 dark:bg-white/5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 glass-panel px-3 py-1.5 rounded-lg">
                <span className="text-[11px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">Rows</span>
                <span className="text-sm font-black text-gray-900 dark:text-white">{rowCount}</span>
              </div>
              {executionTime !== null && (
                <div className="flex items-center gap-2 glass-panel px-3 py-1.5 rounded-lg">
                  <span className="text-[11px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">Time</span>
                  <span className="text-sm font-black text-gray-900 dark:text-white">{executionTime.toFixed(2)}ms</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <ChartToggle
                mode={viewMode}
                onModeChange={setViewMode}
                chartAvailable={chartAvailable}
                chartType={chartRecommendation.chartType}
                selectedChartType={selectedChartType}
                onChartTypeChange={setSelectedChartType}
              />
              <ExportDropdown data={results} sql={sql} />
            </div>
          </div>

          {/* Chart or Table View */}
          {viewMode === 'chart' && chartAvailable ? (
            <div className="p-4">
              <ChartVisualization
                data={results}
                statistics={resultAnalysis?.statistics || {}}
                height={350}
                showLegend={true}
                animate={true}
                overrideChartType={selectedChartType}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              {(() => {
                // Sort the full dataset first, then paginate
                const totalRows = sortedData.length;
                const totalPages = Math.ceil(totalRows / pageSize);
                const startIdx = (currentPage - 1) * pageSize;
                const endIdx = Math.min(startIdx + pageSize, totalRows);
                const paginatedResults = sortedData.slice(startIdx, endIdx);

                return (
                  <>
                    <table className="w-full">
                      <thead className="border-b border-white/10 bg-black/5 dark:bg-white/5">
                        <tr>
                          {Object.keys(results[0]).map((column) => (
                            <SortableTableHeader
                              key={column}
                              column={column}
                              sortConfig={sortConfig}
                              onSort={handleSort}
                              className="px-5 py-3 text-left text-[11px] font-black text-gray-600 dark:text-gray-400 uppercase tracking-[0.15em] hover:bg-white/10 transition-colors"
                            />
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {paginatedResults.map((row, rowIndex) => (
                          <tr
                            key={startIdx + rowIndex}
                            className="hover:bg-white/5 dark:hover:bg-white/5 transition-colors"
                          >
                            {Object.values(row).map((value, colIndex) => (
                              <td
                                key={colIndex}
                                className="px-5 py-3 text-sm text-gray-900 dark:text-gray-100 font-mono"
                              >
                                {value === null ? (
                                  <span className="text-gray-400 dark:text-gray-500 italic text-xs">null</span>
                                ) : typeof value === 'object' ? (
                                  JSON.stringify(value)
                                ) : (
                                  String(value)
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {/* Pagination Controls */}
                    {totalRows > 10 && (
                      <div className="flex items-center justify-between px-5 py-4 border-t border-white/5 bg-black/5 dark:bg-white/5">
                        <div className="flex items-center gap-3">
                          <span className="text-[11px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">Per page</span>
                          <div className="relative">
                            <select
                              value={pageSize}
                              onChange={(e) => {
                                setPageSize(parseInt(e.target.value));
                                setCurrentPage(1);
                              }}
                              className="appearance-none glass-panel rounded-lg px-3 py-1.5 pr-8 text-xs font-bold text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all cursor-pointer border-white/10"
                            >
                              <option value={10}>10</option>
                              <option value={25}>25</option>
                              <option value={50}>50</option>
                              <option value={100}>100</option>
                            </select>
                            <ChevronRight className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 rotate-90 pointer-events-none" />
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <span className="text-[11px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">
                            {startIdx + 1}-{endIdx} of {totalRows}
                          </span>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                              disabled={currentPage === 1}
                              className="p-1.5 rounded-lg glass-panel hover:bg-white/10 text-gray-600 dark:text-gray-400 disabled:opacity-30 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95"
                            >
                              <ChevronLeft className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                              disabled={currentPage === totalPages}
                              className="p-1.5 rounded-lg glass-panel hover:bg-white/10 text-gray-600 dark:text-gray-400 disabled:opacity-30 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95"
                            >
                              <ChevronRight className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          )}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-12 text-center border-white/10">
          <div className="w-16 h-16 rounded-2xl glass-card flex items-center justify-center mx-auto mb-4">
            <Database className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
            {isValid ? 'No results returned' : 'Query could not be executed'}
          </p>
        </div>
      )}

      {/* Feedback Modal */}
      {showFeedbackModal && queryId && (
        <FeedbackModal
          queryId={queryId}
          originalSQL={sql}
          onSubmit={handleFeedbackSubmit}
          onClose={() => setShowFeedbackModal(false)}
        />
      )}
    </div>
  );
}
