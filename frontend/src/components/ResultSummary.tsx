import { Sparkles, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';
import { ResultAnalysis } from '../types/api';

interface ResultSummaryProps {
  analysis: ResultAnalysis;
  rowCount?: number;
  executionTime?: number;
}

export function ResultSummary({ analysis, rowCount, executionTime }: ResultSummaryProps) {
  // Determine confidence badge color
  const getConfidenceBadgeColor = (confidence: number) => {
    if (confidence >= 0.85) return 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300 border-green-300 dark:border-green-800/50';
    if (confidence >= 0.7) return 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800/50';
    return 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-300 border-red-300 dark:border-red-800/50';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.85) return 'High Confidence';
    if (confidence >= 0.7) return 'Good Confidence';
    if (confidence >= 0.5) return 'Moderate Confidence';
    return 'Low Confidence';
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800/50 rounded-lg p-5 space-y-4">
      {/* Header with confidence badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="font-semibold text-blue-900 dark:text-blue-100">Data Insights</h3>
        </div>
        <span className={`text-xs font-medium px-3 py-1 rounded-full border ${getConfidenceBadgeColor(analysis.confidence)}`}>
          {getConfidenceLabel(analysis.confidence)} ({(analysis.confidence * 100).toFixed(0)}%)
        </span>
      </div>

      {/* Direct Answer (if available) */}
      {analysis.direct_answer && (
        <div className="bg-white dark:bg-gray-800 border-l-4 border-blue-500 px-4 py-3 rounded shadow-sm">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">Answer</p>
          <p className="text-lg font-semibold text-blue-900 dark:text-blue-300 mt-1">{analysis.direct_answer}</p>
        </div>
      )}

      {/* Summary */}
      <div className="bg-white dark:bg-gray-800 px-4 py-3 rounded shadow-sm">
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.summary}</p>
      </div>

      {/* Key Insights */}
      {analysis.key_insights && analysis.key_insights.length > 0 && (
        <div className="bg-white dark:bg-gray-800 px-4 py-3 rounded shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">Key Insights</p>
          </div>
          <ul className="space-y-1">
            {analysis.key_insights.map((insight, index) => (
              <li key={index} className="flex gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span className="text-blue-600 dark:text-blue-400 font-bold">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Advanced Analysis Section */}
      {analysis.statistics && (
        <>
          {/* Anomalies Alert */}
          {analysis.statistics.anomalies?.found && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 rounded px-4 py-3">
              <p className="text-sm font-semibold text-red-900 dark:text-red-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Statistical Anomalies Detected
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.statistics.anomalies?.patterns?.map((pattern: string, idx: number) => (
                  <li key={idx} className="text-xs text-red-800 dark:text-red-400 ml-6">
                    • {pattern}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trends Alert */}
          {analysis.statistics.trends?.found && (
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded px-4 py-3">
              <p className="text-sm font-semibold text-blue-900 dark:text-blue-300 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Temporal Trends Detected
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.statistics.trends?.detected_trends?.map((trend: any, idx: number) => (
                  <li key={idx} className="text-xs text-blue-800 dark:text-blue-400 ml-6">
                    • {trend.insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Correlations Alert */}
          {analysis.statistics.correlations?.found && (
            <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800/50 rounded px-4 py-3">
              <p className="text-sm font-semibold text-purple-900 dark:text-purple-300 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Column Correlations Found
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.statistics.correlations?.significant_correlations?.map((corr: any, idx: number) => (
                  <li key={idx} className="text-xs text-purple-800 dark:text-purple-400 ml-6">
                    • {corr.insight}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Statistics (Expandable) */}
      {analysis.statistics && Object.keys(analysis.statistics).length > 0 && (
        <details className="bg-white dark:bg-gray-800 px-4 py-3 rounded cursor-pointer group shadow-sm">
          <summary className="flex items-center gap-2 font-medium text-gray-700 dark:text-gray-300 text-sm select-none">
            <CheckCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            Detailed Statistics
            <span className="ml-auto text-gray-400 dark:text-gray-500 group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 space-y-2">
            {Object.entries(analysis.statistics)
              .filter(([key]) => !['anomalies', 'trends', 'correlations'].includes(key))
              .map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400 capitalize">{key.replace(/_/g, ' ')}:</span>
                  <span className="font-mono text-gray-900 dark:text-gray-100">
                    {typeof value === 'object'
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            {rowCount !== undefined && executionTime !== undefined && (
              <>
                <div className="flex justify-between text-sm pt-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400">Row count:</span>
                  <span className="font-mono text-gray-900 dark:text-gray-100">{rowCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Execution time:</span>
                  <span className="font-mono text-gray-900 dark:text-gray-100">{executionTime.toFixed(2)} ms</span>
                </div>
              </>
            )}
          </div>
        </details>
      )}

      {/* Generated timestamp */}
      <div className="flex justify-end">
        <p className="text-xs text-gray-500 dark:text-gray-500">
          Generated at {new Date(analysis.generated_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
