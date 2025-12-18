import { Copy, Check, MessageSquare, Zap, Database } from 'lucide-react';
import { useState, useMemo } from 'react';
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
import { detectChartType } from '../utils/chartUtils';

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
}: QueryResultsProps) {
  const [copied, setCopied] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('table');

  // Detect chart availability based on data and statistics
  const chartRecommendation = useMemo(() => {
    if (!results || results.length === 0) {
      return { chartType: 'table' as const, confidence: 0, xColumn: null, yColumn: null, reason: 'No data' };
    }
    return detectChartType(results, resultAnalysis?.statistics || {});
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
      throw error;
    }
  };

  return (
    <div className="space-y-4">
      {/* Cache Badge */}
      {cacheType && (
        <div className={`rounded-lg p-3 border ${
          cacheType === 'exact'
            ? 'bg-green-50 border-green-200'
            : 'bg-amber-50 border-amber-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {cacheType === 'exact' ? (
                <Database className="w-5 h-5 text-green-600" />
              ) : (
                <Zap className="w-5 h-5 text-amber-600" />
              )}
              <div>
                <span className={`font-medium ${
                  cacheType === 'exact' ? 'text-green-800' : 'text-amber-800'
                }`}>
                  {cacheType === 'exact' ? 'Exact Cache Hit' : 'Semantic Cache Hit'}
                </span>
                {semanticSimilarity && cacheType === 'semantic' && (
                  <span className="ml-2 text-sm text-amber-600">
                    ({(semanticSimilarity * 100).toFixed(0)}% match)
                  </span>
                )}
              </div>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full ${
              cacheType === 'exact'
                ? 'bg-green-100 text-green-700'
                : 'bg-amber-100 text-amber-700'
            }`}>
              Instant Response
            </span>
          </div>
          {matchedQuestion && cacheType === 'semantic' && (
            <p className="text-sm text-amber-600 mt-2">
              <span className="font-medium">Matched:</span> "{matchedQuestion}"
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
      <div className="bg-gray-900 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-400 uppercase">Generated SQL</span>
          <div className="flex items-center gap-2">
            {queryId && (
              <button
                onClick={() => setShowFeedbackModal(true)}
                className="text-gray-400 hover:text-white transition-colors p-1 flex items-center gap-1 text-xs"
                title="Provide Feedback"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Feedback</span>
              </button>
            )}
            <button
              onClick={handleCopy}
              className="text-gray-400 hover:text-white transition-colors p-1"
              title="Copy SQL"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
        <pre className="text-sm text-green-400 font-mono overflow-x-auto">
          {sql}
        </pre>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start space-x-2">
            <span className="text-yellow-600">⚠️</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-800">Warnings:</p>
              <ul className="mt-1 text-sm text-yellow-700 list-disc list-inside">
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
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
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {/* Header with stats, toggle, and export */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>
                <strong className="text-gray-900">{rowCount}</strong> rows
              </span>
              {executionTime !== null && (
                <span>
                  <strong className="text-gray-900">{executionTime.toFixed(2)}</strong> ms
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <ChartToggle
                mode={viewMode}
                onModeChange={setViewMode}
                chartAvailable={chartAvailable}
                chartType={chartRecommendation.chartType}
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
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {Object.keys(results[0]).map((column) => (
                      <th
                        key={column}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {results.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      {Object.values(row).map((value, colIndex) => (
                        <td
                          key={colIndex}
                          className="px-4 py-3 text-sm text-gray-900 font-mono"
                        >
                          {value === null ? (
                            <span className="text-gray-400 italic">null</span>
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
            </div>
          )}
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-500">
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
