import { useState } from 'react';
import { MessageSquare, Copy, Check } from 'lucide-react';
import type { DatabaseQueryResult } from '../types/api';
import { AgentTrace } from './AgentTrace';
import { CorrectionHistory } from './CorrectionHistory';
import { QueryPlanVisualization } from './QueryPlanVisualization';
import { VerificationWarnings } from './VerificationWarnings';
import { FeedbackModal, FeedbackData } from './FeedbackModal';
import { feedbackAPI } from '../services/api';

interface MultiDatabaseResultsProps {
  results: DatabaseQueryResult[];
  totalRows: number;
  totalExecutionTime: number;
  question: string;
}

export default function MultiDatabaseResults({
  results,
  totalRows,
  totalExecutionTime,
}: MultiDatabaseResultsProps) {
  const [expandedDatabases, setExpandedDatabases] = useState<Set<number>>(
    new Set(results.map((r) => r.connection_id))
  );
  const [feedbackModal, setFeedbackModal] = useState<{ queryId: number; sql: string } | null>(null);
  const [copiedStates, setCopiedStates] = useState<Record<number, boolean>>({});

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

  const successfulQueries = results.filter((r) => r.success).length;
  const failedQueries = results.filter((r) => !r.success).length;

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-gray-900 mb-2">Multi-Database Query Results</h3>
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
            <p className="text-lg font-semibold">
              <span className="text-green-600">{successfulQueries} ✓</span>
              {failedQueries > 0 && <span className="text-red-600 ml-2">{failedQueries} ✗</span>}
            </p>
          </div>
        </div>
      </div>

      {/* Individual database results */}
      <div className="space-y-3">
        {results.map((result) => (
          <div
            key={result.connection_id}
            className={`border rounded-lg overflow-hidden ${
              result.success ? 'border-gray-200' : 'border-red-300 bg-red-50'
            }`}
          >
            {/* Database header */}
            <button
              onClick={() => toggleDatabase(result.connection_id)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`w-3 h-3 rounded-full ${
                    result.success ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <div className="text-left">
                  <h4 className="font-semibold text-gray-900">{result.connection_name}</h4>
                  <p className="text-sm text-gray-600">
                    {result.database_type}
                    {result.success && (
                      <>
                        {' '}• {result.row_count} row{result.row_count !== 1 ? 's' : ''} • {result.execution_time_ms?.toFixed(1)}ms
                      </>
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
              <div className="border-t border-gray-200 p-4 bg-white">
                {/* SQL Query */}
                <div className="mb-4">
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
                  <div className="mb-4">
                    <VerificationWarnings warnings={result.verification_warnings} />
                  </div>
                )}

                {/* Correction History */}
                {result.self_corrected && result.attempts && result.attempts.length > 0 && (
                  <div className="mb-4">
                    <CorrectionHistory
                      attempts={result.attempts}
                      selfCorrected={result.self_corrected}
                    />
                  </div>
                )}

                {/* Query Plan */}
                {result.used_planning && result.query_plan && (
                  <div className="mb-4">
                    <QueryPlanVisualization
                      plan={result.query_plan}
                      usedPlanning={result.used_planning}
                    />
                  </div>
                )}

                {/* Agent Trace */}
                {result.agent_trace && (
                  <div className="mb-4">
                    <AgentTrace trace={result.agent_trace} />
                  </div>
                )}

                {/* Results or Error */}
                {result.success ? (
                  result.results && result.results.length > 0 ? (
                    <div>
                      <h5 className="text-xs font-semibold text-gray-700 mb-2">
                        Results ({result.row_count} row{result.row_count !== 1 ? 's' : ''})
                      </h5>
                      <div className="overflow-x-auto">
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
                            {result.results.slice(0, 10).map((row, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
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
                        {result.row_count && result.row_count > 10 && (
                          <p className="mt-2 text-xs text-gray-500 text-center">
                            Showing 10 of {result.row_count} rows
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic">No results returned</p>
                  )
                ) : (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <h5 className="text-xs font-semibold text-red-700 mb-1">Error</h5>
                    <p className="text-sm text-red-600">{result.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
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
