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
    if (confidence >= 0.85) return 'bg-green-100 text-green-800 border-green-300';
    if (confidence >= 0.7) return 'bg-amber-100 text-amber-800 border-amber-300';
    return 'bg-red-100 text-red-800 border-red-300';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.85) return 'High Confidence';
    if (confidence >= 0.7) return 'Good Confidence';
    if (confidence >= 0.5) return 'Moderate Confidence';
    return 'Low Confidence';
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-5 space-y-4">
      {/* Header with confidence badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-blue-900">Data Insights</h3>
        </div>
        <span className={`text-xs font-medium px-3 py-1 rounded-full border ${getConfidenceBadgeColor(analysis.confidence)}`}>
          {getConfidenceLabel(analysis.confidence)} ({(analysis.confidence * 100).toFixed(0)}%)
        </span>
      </div>

      {/* Direct Answer (if available) */}
      {analysis.direct_answer && (
        <div className="bg-white border-l-4 border-blue-500 px-4 py-3 rounded">
          <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Answer</p>
          <p className="text-lg font-semibold text-blue-900 mt-1">{analysis.direct_answer}</p>
        </div>
      )}

      {/* Summary */}
      <div className="bg-white px-4 py-3 rounded">
        <p className="text-sm text-gray-700 leading-relaxed">{analysis.summary}</p>
      </div>

      {/* Key Insights */}
      {analysis.key_insights && analysis.key_insights.length > 0 && (
        <div className="bg-white px-4 py-3 rounded">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Key Insights</p>
          </div>
          <ul className="space-y-1">
            {analysis.key_insights.map((insight, index) => (
              <li key={index} className="flex gap-2 text-sm text-gray-700">
                <span className="text-blue-600 font-bold">•</span>
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
            <div className="bg-red-50 border border-red-200 rounded px-4 py-3">
              <p className="text-sm font-semibold text-red-900 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Statistical Anomalies Detected
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.statistics.anomalies?.patterns?.map((pattern: string, idx: number) => (
                  <li key={idx} className="text-xs text-red-800 ml-6">
                    • {pattern}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trends Alert */}
          {analysis.statistics.trends?.found && (
            <div className="bg-blue-50 border border-blue-200 rounded px-4 py-3">
              <p className="text-sm font-semibold text-blue-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Temporal Trends Detected
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.statistics.trends?.detected_trends?.map((trend: any, idx: number) => (
                  <li key={idx} className="text-xs text-blue-800 ml-6">
                    • {trend.insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Correlations Alert */}
          {analysis.statistics.correlations?.found && (
            <div className="bg-purple-50 border border-purple-200 rounded px-4 py-3">
              <p className="text-sm font-semibold text-purple-900 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Column Correlations Found
              </p>
              <ul className="mt-2 space-y-1">
                {analysis.statistics.correlations?.significant_correlations?.map((corr: any, idx: number) => (
                  <li key={idx} className="text-xs text-purple-800 ml-6">
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
        <details className="bg-white px-4 py-3 rounded cursor-pointer group">
          <summary className="flex items-center gap-2 font-medium text-gray-700 text-sm select-none">
            <CheckCircle className="w-4 h-4 text-blue-600" />
            Detailed Statistics
            <span className="ml-auto text-gray-400 group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            {Object.entries(analysis.statistics)
              .filter(([key]) => !['anomalies', 'trends', 'correlations'].includes(key))
              .map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                  <span className="font-mono text-gray-900">
                    {typeof value === 'object'
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            {rowCount !== undefined && executionTime !== undefined && (
              <>
                <div className="flex justify-between text-sm pt-2 border-t border-gray-100">
                  <span className="text-gray-600">Row count:</span>
                  <span className="font-mono text-gray-900">{rowCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Execution time:</span>
                  <span className="font-mono text-gray-900">{executionTime.toFixed(2)} ms</span>
                </div>
              </>
            )}
          </div>
        </details>
      )}

      {/* Generated timestamp */}
      <div className="flex justify-end">
        <p className="text-xs text-gray-500">
          Generated at {new Date(analysis.generated_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
