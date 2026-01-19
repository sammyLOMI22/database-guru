import { Sparkles, TrendingUp, AlertCircle, CheckCircle, ChevronDown } from 'lucide-react';
import { ResultAnalysis } from '../types/api';

interface ResultSummaryProps {
  analysis: ResultAnalysis;
  rowCount?: number;
  executionTime?: number;
}

export function ResultSummary({ analysis, rowCount, executionTime }: ResultSummaryProps) {
  // Determine confidence badge styling
  const getConfidenceBadgeStyle = (confidence: number) => {
    if (confidence >= 0.85) return 'from-emerald-500/20 to-green-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
    if (confidence >= 0.7) return 'from-amber-500/20 to-yellow-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30';
    return 'from-red-500/20 to-rose-500/20 text-red-600 dark:text-red-400 border-red-500/30';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.85) return 'High';
    if (confidence >= 0.7) return 'Good';
    if (confidence >= 0.5) return 'Moderate';
    return 'Low';
  };

  return (
    <div className="glass-card rounded-2xl p-6 border-white/10 bg-gradient-to-br from-blue-500/5 via-transparent to-indigo-500/5 space-y-4">
      {/* Header with confidence badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-blue-500">
            <Sparkles className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white">Data Insights</h3>
        </div>
        <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg border bg-gradient-to-r ${getConfidenceBadgeStyle(analysis.confidence)}`}>
          {getConfidenceLabel(analysis.confidence)} ({(analysis.confidence * 100).toFixed(0)}%)
        </span>
      </div>

      {/* Direct Answer (if available) */}
      {analysis.direct_answer && (
        <div className="glass-panel rounded-xl p-4 border-l-4 border-blue-500 bg-gradient-to-r from-blue-500/10 via-transparent to-transparent">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400 mb-1">Answer</p>
          <p className="text-xl font-black text-gray-900 dark:text-white">{analysis.direct_answer}</p>
        </div>
      )}

      {/* Summary */}
      <div className="glass-panel rounded-xl p-4">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 leading-relaxed">{analysis.summary}</p>
      </div>

      {/* Key Insights */}
      {analysis.key_insights && analysis.key_insights.length > 0 && (
        <div className="glass-panel rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-blue-500" />
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400">Key Insights</p>
          </div>
          <ul className="space-y-2">
            {analysis.key_insights.map((insight, index) => (
              <li key={index} className="flex gap-3 text-sm text-gray-700 dark:text-gray-300">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
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
            <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/5 border-red-500/20">
              <p className="text-xs font-black uppercase tracking-widest text-red-600 dark:text-red-400 flex items-center gap-2 mb-3">
                <AlertCircle className="w-4 h-4" />
                Anomalies Detected
              </p>
              <ul className="space-y-1.5">
                {analysis.statistics.anomalies?.patterns?.map((pattern: string, idx: number) => (
                  <li key={idx} className="text-xs text-red-700 dark:text-red-300 flex items-start gap-2">
                    <span className="w-1 h-1 rounded-full bg-red-500 mt-1.5 flex-shrink-0" />
                    {pattern}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trends Alert */}
          {analysis.statistics.trends?.found && (
            <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-blue-500/10 via-transparent to-cyan-500/5 border-blue-500/20">
              <p className="text-xs font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4" />
                Trends Detected
              </p>
              <ul className="space-y-1.5">
                {analysis.statistics.trends?.detected_trends?.map((trend: any, idx: number) => (
                  <li key={idx} className="text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
                    <span className="w-1 h-1 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                    {trend.insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Correlations Alert */}
          {analysis.statistics.correlations?.found && (
            <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-purple-500/10 via-transparent to-indigo-500/5 border-purple-500/20">
              <p className="text-xs font-black uppercase tracking-widest text-purple-600 dark:text-purple-400 flex items-center gap-2 mb-3">
                <CheckCircle className="w-4 h-4" />
                Correlations Found
              </p>
              <ul className="space-y-1.5">
                {analysis.statistics.correlations?.significant_correlations?.map((corr: any, idx: number) => (
                  <li key={idx} className="text-xs text-purple-700 dark:text-purple-300 flex items-start gap-2">
                    <span className="w-1 h-1 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                    {corr.insight}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Statistics (Expandable) */}
      {analysis.statistics && Object.keys(analysis.statistics).length > 0 && (
        <details className="glass-panel rounded-xl overflow-hidden group">
          <summary className="flex items-center gap-3 px-4 py-3 cursor-pointer select-none hover:bg-white/5 transition-colors">
            <CheckCircle className="w-4 h-4 text-blue-500" />
            <span className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">
              Detailed Statistics
            </span>
            <ChevronDown className="ml-auto w-4 h-4 text-gray-400 group-open:rotate-180 transition-transform" />
          </summary>
          <div className="px-4 pb-4 pt-2 border-t border-white/5 space-y-2">
            {Object.entries(analysis.statistics)
              .filter(([key]) => !['anomalies', 'trends', 'correlations'].includes(key))
              .map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="font-mono text-xs font-bold text-gray-900 dark:text-gray-100">
                    {typeof value === 'object'
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            {rowCount !== undefined && executionTime !== undefined && (
              <>
                <div className="flex justify-between text-sm pt-2 border-t border-white/5">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">Row count</span>
                  <span className="font-mono text-xs font-bold text-gray-900 dark:text-gray-100">{rowCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">Execution time</span>
                  <span className="font-mono text-xs font-bold text-gray-900 dark:text-gray-100">{executionTime.toFixed(2)} ms</span>
                </div>
              </>
            )}
          </div>
        </details>
      )}

      {/* Generated timestamp */}
      <div className="flex justify-end pt-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500">
          Generated {new Date(analysis.generated_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
