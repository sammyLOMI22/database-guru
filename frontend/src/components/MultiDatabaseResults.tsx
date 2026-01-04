import { useState, useMemo } from 'react';
import { MessageSquare, Copy, Check, Zap, Database, ChevronLeft, ChevronRight, AlertCircle, XCircle } from 'lucide-react';
import type { DatabaseQueryResult, CacheInfo } from '../types/api';
import { AgentTrace } from './AgentTrace';
import { CorrectionHistory } from './CorrectionHistory';
import { QueryPlanVisualization } from './QueryPlanVisualization';
import { VerificationWarnings } from './VerificationWarnings';
import { FeedbackModal, FeedbackData } from './FeedbackModal';
import { ResultSummary } from './ResultSummary';
import { feedbackAPI } from '../services/api';
import { ChartVisualization } from './visualization/ChartVisualization';
import { ChartToggle, ViewMode } from './visualization/ChartToggle';
import { ExportDropdown } from './visualization/ExportDropdown';
import { CombinedExportDropdown } from './visualization/CombinedExportDropdown';
import { CrossDatabaseChart } from './visualization/CrossDatabaseChart';
import { detectChartType, ChartRecommendation, ChartType } from '../utils/chartUtils';
import { detectCrossDbComparison } from '../utils/crossDbUtils';

interface MultiDatabaseResultsProps {
  results: DatabaseQueryResult[];
  totalRows: number;
  totalExecutionTime: number;
  question: string;
  cacheInfo?: CacheInfo | null;
  combinedAnalysis?: any; // ResultAnalysis from multi-db response
}

export default function MultiDatabaseResults({
  results,
  totalRows,
  totalExecutionTime,
  question,
  cacheInfo,
  combinedAnalysis,
}: MultiDatabaseResultsProps) {
  console.log('DEBUG: MultiDatabaseResults props:', { combinedAnalysis, resultAnalysis0: results[0]?.result_analysis });

  const [expandedDatabases, setExpandedDatabases] = useState<Set<number>>(
    new Set(results.map((r) => r.connection_id))
  );
  const [feedbackModal, setFeedbackModal] = useState<{ queryId: number; sql: string } | null>(null);
  const [copiedStates, setCopiedStates] = useState<Record<number, boolean>>({});

  // Per-database view modes for chart/table toggle
  const [viewModes, setViewModes] = useState<Record<number, ViewMode>>(() =>
    Object.fromEntries(results.map((r) => [r.connection_id, 'table']))
  );

  // Per-database selected chart types (overrides auto-detection when set)
  const [selectedChartTypes, setSelectedChartTypes] = useState<Record<number, ChartType | null>>(() =>
    Object.fromEntries(results.map((r) => [r.connection_id, null]))
  );

  // Pagination state per database
  const [currentPages, setCurrentPages] = useState<Record<number, number>>(() =>
    Object.fromEntries(results.map((r) => [r.connection_id, 1]))
  );
  const [pageSizes, setPageSizes] = useState<Record<number, number>>(() =>
    Object.fromEntries(results.map((r) => [r.connection_id, 10]))
  );

  // Memoized chart recommendations for each database
  const chartRecommendations = useMemo<Record<number, ChartRecommendation>>(() => {
    return Object.fromEntries(
      results.map((r) => [
        r.connection_id,
        r.results && r.results.length > 0
          ? detectChartType(r.results, r.result_analysis?.statistics || {})
          : { chartType: 'table' as const, confidence: 0, xColumn: null, yColumn: null, reason: 'No data' },
      ])
    );
  }, [results]);

  // Memoized cross-database comparison configuration
  const crossDbConfig = useMemo(() => detectCrossDbComparison(results), [results]);

  const toggleDatabase = (connectionId: number) => {
    setExpandedDatabases((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(connectionId)) {
        newSet.delete(connectionId);
      } else {
        newSet.add(connectionId);
      }
      return newSet;
    });
  };

  const handleCopy = async (connectionId: number, sql: string) => {
    await navigator.clipboard.writeText(sql);
    setCopiedStates((prev) => ({ ...prev, [connectionId]: true }));
    setTimeout(() => {
      setCopiedStates((prev) => ({ ...prev, [connectionId]: false }));
    }, 2000);
  };

  const handleFeedbackSubmit = async (feedback: FeedbackData) => {
    try {
      await feedbackAPI.submitFeedback(feedback);
      setFeedbackModal(null);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      throw error;
    }
  };

  // Helper to determine if an error is "Cannot Answer" (schema limitation) vs actual error
  const isCannotAnswer = (result: DatabaseQueryResult): boolean => {
    if (result.success) return false;
    const error = result.error?.toLowerCase() || '';
    return (
      error.includes('cannot execute query on this database') ||
      error.includes('required column(s) not found') ||
      error.includes('required table(s) not found') ||
      error.includes('location column for filtering') ||
      error.includes('missing required')
    );
  };

  // Get result status: 'success' | 'cannot_answer' | 'error'
  const getResultStatus = (result: DatabaseQueryResult): 'success' | 'cannot_answer' | 'error' => {
    if (result.success) return 'success';
    if (isCannotAnswer(result)) return 'cannot_answer';
    return 'error';
  };

  const successfulQueries = results.filter((r) => r.success).length;
  const cannotAnswerQueries = results.filter((r) => !r.success && isCannotAnswer(r)).length;
  const failedQueries = results.filter((r) => !r.success && !isCannotAnswer(r)).length;

  return (
    <div className="space-y-4">
      {/* Combined Multi-Database Analysis (if available) */}
      {combinedAnalysis && (
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Cross-Database Insights</h3>
          <ResultSummary
            analysis={combinedAnalysis}
            rowCount={totalRows}
            executionTime={totalExecutionTime}
          />
        </div>
      )}

      {/* Cross-Database Comparison Chart */}
      {crossDbConfig && <CrossDatabaseChart config={crossDbConfig} />}

      {/* Summary header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900">Multi-Database Query Results</h3>
          <CombinedExportDropdown results={results} question={question} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-600">Databases Queried</p>
            <p className="text-lg font-semibold text-gray-900">{results.length}</p>
          </div>
          <div>
            <p className="text-gray-600">Total Rows</p>
            <p className="text-lg font-semibold text-gray-900">{totalRows.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-600">Execution Time</p>
            <p className="text-lg font-semibold text-gray-900">{totalExecutionTime.toFixed(1)}ms</p>
          </div>
          <div>
            <p className="text-gray-600">Status</p>
            <p className="text-lg font-semibold flex items-center gap-2">
              {successfulQueries > 0 && <span className="text-green-600">{successfulQueries} ✓</span>}
              {cannotAnswerQueries > 0 && <span className="text-amber-600">{cannotAnswerQueries} ⊘</span>}
              {failedQueries > 0 && <span className="text-red-600">{failedQueries} ✗</span>}
            </p>
          </div>
        </div>

        {/* Cache Info Banner */}
        {cacheInfo && (cacheInfo.semantic_hits > 0 || cacheInfo.results_stored > 0) && (
          <div className="mt-3 pt-3 border-t border-blue-200">
            <div className="flex items-center gap-4 text-sm">
              {cacheInfo.semantic_hits > 0 && (
                <div className="flex items-center gap-1.5 text-amber-700 bg-amber-50 px-2 py-1 rounded-full">
                  <Zap className="w-3.5 h-3.5" />
                  <span className="font-medium">
                    {cacheInfo.semantic_hits} cache hit{cacheInfo.semantic_hits !== 1 ? 's' : ''}
                  </span>
                  {cacheInfo.hit_databases.length > 0 && (
                    <span className="text-amber-600 text-xs">
                      ({cacheInfo.hit_databases.join(', ')})
                    </span>
                  )}
                </div>
              )}
              {cacheInfo.semantic_misses > 0 && (
                <div className="flex items-center gap-1.5 text-slate-600 bg-slate-50 px-2 py-1 rounded-full">
                  <Database className="w-3.5 h-3.5" />
                  <span className="font-medium">
                    {cacheInfo.semantic_misses} fresh quer{cacheInfo.semantic_misses !== 1 ? 'ies' : 'y'}
                  </span>
                </div>
              )}
              {cacheInfo.results_stored > 0 && (
                <div className="flex items-center gap-1.5 text-teal-700 bg-teal-50 px-2 py-1 rounded-full text-xs">
                  <span>+{cacheInfo.results_stored} cached</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Individual database results */}
      <div className="space-y-3">
        {results.map((result) => {
          const status = getResultStatus(result);
          const borderClass = {
            success: 'border-gray-200',
            cannot_answer: 'border-amber-300 bg-amber-50/50',
            error: 'border-red-300 bg-red-50',
          }[status];
          const dotClass = {
            success: 'bg-green-500',
            cannot_answer: 'bg-amber-500',
            error: 'bg-red-500',
          }[status];

          return (
          <div
            key={result.connection_id}
            className={`border rounded-lg overflow-hidden ${borderClass}`}
          >
            {/* Database header */}
            <button
              onClick={() => toggleDatabase(result.connection_id)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${dotClass}`} />
                <div className="text-left">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-gray-900">{result.connection_name}</h4>
                    {status === 'cannot_answer' && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                        Cannot Answer
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">
                    {result.database_type}
                    {result.success && (
                      <>
                        {' '}• {result.row_count} row{result.row_count !== 1 ? 's' : ''} • {result.execution_time_ms?.toFixed(1)}ms
                      </>
                    )}
                    {status === 'cannot_answer' && (
                      <span className="text-amber-600"> • Missing required data</span>
                    )}
                  </p>
                </div>
              </div>
              <svg
                className={`w-5 h-5 text-gray-400 transition-transform ${
                  expandedDatabases.has(result.connection_id) ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Expanded content */}
            {expandedDatabases.has(result.connection_id) && (
              <div className="border-t border-gray-200 p-4 bg-white space-y-4">
                {/* Result Analysis / Narrative (if available) */}
                {result.result_analysis && (
                  <div>
                    <ResultSummary
                      analysis={result.result_analysis}
                      rowCount={result.row_count}
                      executionTime={result.execution_time_ms}
                    />
                  </div>
                )}

                {/* SQL Query */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h5 className="text-xs font-semibold text-gray-700">
                      Generated SQL {/* DEBUG */}
                      {result.query_id ? ` (ID: ${result.query_id})` : ' (No query_id)'}
                    </h5>
                    <div className="flex items-center gap-2">
                      {result.query_id ? (
                        <button
                          onClick={() => setFeedbackModal({ queryId: result.query_id!, sql: result.sql })}
                          className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 text-xs font-bold"
                          title="Provide Feedback"
                        >
                          <MessageSquare className="w-3 h-3 inline mr-1" />
                          FEEDBACK
                        </button>
                      ) : (
                        <span className="text-xs text-red-500 font-bold">NO QUERY_ID</span>
                      )}
                      <button
                        onClick={() => handleCopy(result.connection_id, result.sql)}
                        className="text-gray-400 hover:text-gray-600 transition-colors p-1"
                        title="Copy SQL"
                      >
                        {copiedStates[result.connection_id] ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                  <pre className="bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
                    <code>{result.sql}</code>
                  </pre>
                </div>

                {/* Option 2: Observability Components */}
                {/* Verification Warnings */}
                {result.verification_warnings && result.verification_warnings.length > 0 && (
                  <div>
                    <VerificationWarnings warnings={result.verification_warnings} />
                  </div>
                )}

                {/* Correction History */}
                {result.self_corrected && result.attempts && result.attempts.length > 0 && (
                  <div>
                    <CorrectionHistory
                      attempts={result.attempts}
                      selfCorrected={result.self_corrected}
                    />
                  </div>
                )}

                {/* Query Plan */}
                {result.used_planning && result.query_plan && (
                  <div>
                    <QueryPlanVisualization
                      plan={result.query_plan}
                      usedPlanning={result.used_planning}
                    />
                  </div>
                )}

                {/* Agent Trace */}
                {result.agent_trace && (
                  <div>
                    <AgentTrace trace={result.agent_trace} />
                  </div>
                )}

                {/* Results or Error */}
                {result.success ? (
                  result.results && result.results.length > 0 ? (
                    <div>
                      {/* Results header with controls */}
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="text-xs font-semibold text-gray-700">
                          Results ({result.row_count} row{result.row_count !== 1 ? 's' : ''})
                        </h5>
                        <div className="flex items-center gap-2">
                          <ChartToggle
                            mode={viewModes[result.connection_id] || 'table'}
                            onModeChange={(mode) =>
                              setViewModes((prev) => ({ ...prev, [result.connection_id]: mode }))
                            }
                            chartAvailable={chartRecommendations[result.connection_id]?.chartType !== 'table'}
                            chartType={chartRecommendations[result.connection_id]?.chartType || 'table'}
                            selectedChartType={selectedChartTypes[result.connection_id]}
                            onChartTypeChange={(type) =>
                              setSelectedChartTypes((prev) => ({ ...prev, [result.connection_id]: type }))
                            }
                          />
                          <ExportDropdown
                            data={result.results || []}
                            sql={result.sql}
                            connectionName={result.connection_name}
                            databaseType={result.database_type}
                          />
                        </div>
                      </div>

                      {/* Conditional Chart or Table rendering */}
                      {viewModes[result.connection_id] === 'chart' &&
                      chartRecommendations[result.connection_id]?.chartType !== 'table' ? (
                        <ChartVisualization
                          data={result.results}
                          statistics={result.result_analysis?.statistics || {}}
                          height={300}
                          showLegend={true}
                          animate={true}
                          overrideChartType={selectedChartTypes[result.connection_id]}
                        />
                      ) : (
                        <div className="overflow-x-auto">
                          {(() => {
                            const pageSize = pageSizes[result.connection_id] || 10;
                            const currentPage = currentPages[result.connection_id] || 1;
                            const totalRows = result.results.length;
                            const totalPages = Math.ceil(totalRows / pageSize);
                            const startIdx = (currentPage - 1) * pageSize;
                            const endIdx = Math.min(startIdx + pageSize, totalRows);
                            const paginatedResults = result.results.slice(startIdx, endIdx);

                            return (
                              <>
                                <table className="min-w-full divide-y divide-gray-200 text-sm">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      {Object.keys(result.results[0]).map((key) => (
                                        <th
                                          key={key}
                                          className="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
                                        >
                                          {key}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white divide-y divide-gray-200">
                                    {paginatedResults.map((row, idx) => (
                                      <tr key={startIdx + idx} className="hover:bg-gray-50">
                                        {Object.values(row).map((value, vidx) => (
                                          <td key={vidx} className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                                            {value === null ? (
                                              <span className="text-gray-400 italic">null</span>
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
                                  <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-t border-gray-200">
                                    <div className="flex items-center gap-2 text-xs text-gray-600">
                                      <span>Rows per page:</span>
                                      <select
                                        value={pageSize}
                                        onChange={(e) => {
                                          const newSize = parseInt(e.target.value);
                                          setPageSizes((prev) => ({ ...prev, [result.connection_id]: newSize }));
                                          setCurrentPages((prev) => ({ ...prev, [result.connection_id]: 1 }));
                                        }}
                                        className="border border-gray-300 rounded px-1 py-0.5 text-xs"
                                      >
                                        <option value={10}>10</option>
                                        <option value={25}>25</option>
                                        <option value={50}>50</option>
                                        <option value={100}>100</option>
                                      </select>
                                    </div>

                                    <div className="flex items-center gap-2 text-xs text-gray-600">
                                      <span>
                                        {startIdx + 1}-{endIdx} of {totalRows}
                                      </span>
                                      <div className="flex items-center gap-1">
                                        <button
                                          onClick={() =>
                                            setCurrentPages((prev) => ({
                                              ...prev,
                                              [result.connection_id]: Math.max(1, currentPage - 1),
                                            }))
                                          }
                                          disabled={currentPage === 1}
                                          className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                          <ChevronLeft className="w-4 h-4" />
                                        </button>
                                        <button
                                          onClick={() =>
                                            setCurrentPages((prev) => ({
                                              ...prev,
                                              [result.connection_id]: Math.min(totalPages, currentPage + 1),
                                            }))
                                          }
                                          disabled={currentPage === totalPages}
                                          className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
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
                    <p className="text-sm text-gray-500 italic">No results returned</p>
                  )
                ) : status === 'cannot_answer' ? (
                  <div className="bg-amber-50 border border-amber-200 rounded p-3">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <h5 className="text-sm font-semibold text-amber-800 mb-1">Cannot Answer This Query</h5>
                        <p className="text-sm text-amber-700">
                          {result.error?.replace('Cannot execute query on this database: ', '') || 'This database does not have the required data to answer this query.'}
                        </p>
                        <p className="text-xs text-amber-600 mt-2">
                          This is expected when databases have different schemas. The query will only run on databases that have the required tables and columns.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <div className="flex items-start gap-2">
                      <XCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <h5 className="text-xs font-semibold text-red-700 mb-1">Error</h5>
                        <p className="text-sm text-red-600">{result.error}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          );
        })}
      </div>

      {/* Expand/Collapse all button */}
      {results.length > 1 && (
        <div className="flex justify-center">
          <button
            onClick={() => {
              if (expandedDatabases.size === results.length) {
                setExpandedDatabases(new Set());
              } else {
                setExpandedDatabases(new Set(results.map((r) => r.connection_id)));
              }
            }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
          >
            {expandedDatabases.size === results.length ? 'Collapse All' : 'Expand All'}
          </button>
        </div>
      )}

      {/* Feedback Modal */}
      {feedbackModal && (
        <FeedbackModal
          queryId={feedbackModal.queryId}
          originalSQL={feedbackModal.sql}
          onSubmit={handleFeedbackSubmit}
          onClose={() => setFeedbackModal(null)}
        />
      )}
    </div>
  );
}
