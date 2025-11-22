import React from 'react';
import { ParallelExecutionMetrics, ParallelCorrectionMetrics } from '../types/api';

interface ParallelExecutionMetricsProps {
  metrics: ParallelExecutionMetrics;
  title?: string;
}

interface ParallelCorrectionMetricsProps {
  metrics: ParallelCorrectionMetrics;
  title?: string;
}

/**
 * Display metrics for parallel multi-database execution
 * Shows speedup, concurrency, success rates, and timing
 */
export const ParallelDatabaseMetrics: React.FC<ParallelExecutionMetricsProps> = ({
  metrics,
  title = "Parallel Execution Metrics"
}) => {
  const hasSpeedup = metrics.speedup && metrics.speedup > 1;
  const successRate = metrics.total_queries > 0
    ? Math.round((metrics.successful_queries / metrics.total_queries) * 100)
    : 0;

  return (
    <div className="bg-gradient-to-r from-orange-50 to-yellow-50 border-2 border-orange-200 rounded-lg p-4 mt-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        </div>
        {hasSpeedup && (
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-bold rounded-full border border-green-300">
              ⚡ {metrics.speedup!.toFixed(1)}x faster
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        {/* Total Queries */}
        <div className="bg-white rounded-lg p-3 border border-orange-100">
          <div className="text-xs text-gray-500 mb-1">Total Queries</div>
          <div className="text-lg font-bold text-gray-800">{metrics.total_queries}</div>
        </div>

        {/* Concurrency */}
        <div className="bg-white rounded-lg p-3 border border-orange-100">
          <div className="text-xs text-gray-500 mb-1">Concurrent</div>
          <div className="text-lg font-bold text-orange-600">
            {metrics.actual_concurrent}/{metrics.max_concurrent}
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-white rounded-lg p-3 border border-orange-100">
          <div className="text-xs text-gray-500 mb-1">Success Rate</div>
          <div className={`text-lg font-bold ${successRate === 100 ? 'text-green-600' : 'text-yellow-600'}`}>
            {successRate}%
          </div>
          <div className="text-xs text-gray-500">
            {metrics.successful_queries}/{metrics.total_queries} OK
          </div>
        </div>

        {/* Execution Time */}
        <div className="bg-white rounded-lg p-3 border border-orange-100">
          <div className="text-xs text-gray-500 mb-1">Execution Time</div>
          <div className="text-lg font-bold text-blue-600">{metrics.elapsed_ms.toFixed(0)}ms</div>
          <div className="text-xs text-gray-500">
            avg: {metrics.average_query_time_ms.toFixed(0)}ms
          </div>
        </div>
      </div>

      {/* Speedup Comparison */}
      {hasSpeedup && metrics.estimated_sequential_ms && (
        <div className="mt-3 bg-white rounded-lg p-3 border border-green-200">
          <div className="flex items-center justify-between text-sm">
            <div>
              <span className="text-gray-500">Sequential would take:</span>
              <span className="ml-2 font-semibold text-gray-700">
                {metrics.estimated_sequential_ms.toFixed(0)}ms
              </span>
            </div>
            <div>
              <span className="text-gray-500">Parallel execution:</span>
              <span className="ml-2 font-semibold text-green-600">
                {metrics.elapsed_ms.toFixed(0)}ms
              </span>
            </div>
            <div>
              <span className="text-green-700 font-bold">
                ⚡ {metrics.speedup!.toFixed(1)}x speedup!
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-3 text-xs text-gray-500 italic">
        💡 Queries executed in parallel across {metrics.actual_concurrent} databases simultaneously
        {metrics.max_concurrent < metrics.total_queries &&
          ` (throttled to ${metrics.max_concurrent} max concurrent)`
        }
      </div>
    </div>
  );
};

/**
 * Display metrics for parallel correction attempts
 * Shows winning strategy, timing, and timeout information
 */
export const ParallelCorrectionsMetrics: React.FC<ParallelCorrectionMetricsProps> = ({
  metrics,
  title = "Parallel Correction Metrics"
}) => {
  const strategyDisplayName = (strategy: string | null): string => {
    if (!strategy) return 'None';
    const names: Record<string, string> = {
      'quick_fix': 'Quick Fix',
      'learned': 'Learned Pattern',
      'llm': 'LLM Correction',
      'tool_using': 'Tool-Assisted Fix',
      'llm_fallback': 'LLM Fallback',
      'llm_fallback_timeout': 'LLM Fallback (Timeout)'
    };
    return names[strategy] || strategy;
  };

  const strategyIcon = (strategy: string | null): string => {
    if (!strategy) return '❓';
    const icons: Record<string, string> = {
      'quick_fix': '⚡',
      'learned': '🧠',
      'llm': '🤖',
      'tool_using': '🔧',
      'llm_fallback': '🔄',
      'llm_fallback_timeout': '⏱️'
    };
    return icons[strategy] || '🔧';
  };

  return (
    <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-lg p-4 mt-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🏆</span>
          <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        </div>
        {metrics.timed_out && (
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-yellow-100 text-yellow-700 text-sm font-bold rounded-full border border-yellow-300">
              ⚠️ Timed out
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm mb-3">
        {/* Winning Strategy */}
        <div className="bg-white rounded-lg p-3 border border-purple-100 md:col-span-2">
          <div className="text-xs text-gray-500 mb-1">Winning Strategy</div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">{strategyIcon(metrics.winning_strategy)}</span>
            <div>
              <div className="text-lg font-bold text-purple-600">
                {strategyDisplayName(metrics.winning_strategy)}
              </div>
              <div className="text-xs text-gray-500">
                in {metrics.elapsed_ms.toFixed(0)}ms
              </div>
            </div>
          </div>
        </div>

        {/* Execution Time */}
        <div className="bg-white rounded-lg p-3 border border-purple-100">
          <div className="text-xs text-gray-500 mb-1">Total Time</div>
          <div className="text-lg font-bold text-blue-600">{metrics.elapsed_ms.toFixed(0)}ms</div>
        </div>
      </div>

      {/* Strategy Results */}
      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="bg-white rounded-lg p-2 border border-gray-200 text-center">
          <div className="text-xs text-gray-500">Attempted</div>
          <div className="text-base font-bold text-gray-700">{metrics.strategies_attempted}</div>
        </div>
        <div className="bg-white rounded-lg p-2 border border-green-200 text-center">
          <div className="text-xs text-gray-500">Succeeded</div>
          <div className="text-base font-bold text-green-600">{metrics.strategies_succeeded}</div>
        </div>
        <div className="bg-white rounded-lg p-2 border border-red-200 text-center">
          <div className="text-xs text-gray-500">Failed</div>
          <div className="text-base font-bold text-red-600">{metrics.strategies_failed}</div>
        </div>
      </div>

      {/* Timeout Warning */}
      {metrics.timed_out && (
        <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-start gap-2 text-sm">
            <span className="text-yellow-600">⚠️</span>
            <div>
              <div className="font-semibold text-yellow-800">Timeout Protection Triggered</div>
              <div className="text-xs text-yellow-700 mt-1">
                {metrics.strategies_timed_out} {metrics.strategies_timed_out === 1 ? 'strategy' : 'strategies'} timed out.
                Fallback LLM correction was used to prevent indefinite hanging.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="mt-3 text-xs text-gray-500 italic">
        💡 {metrics.strategies_attempted} correction strategies executed in parallel
        {metrics.timed_out ? ' with timeout protection' : '. First successful strategy wins!'}
      </div>
    </div>
  );
};

export default ParallelDatabaseMetrics;
