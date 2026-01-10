import React, { useState } from 'react';
import { AgentTrace as AgentTraceType } from '../types/api';

interface AgentTraceProps {
  trace: AgentTraceType;
}

export const AgentTrace: React.FC<AgentTraceProps> = ({ trace }) => {
  const [expanded, setExpanded] = useState(false);

  // Defensive: ensure trace has required properties
  const steps = trace?.steps || [];
  const totalElapsedMs = trace?.total_elapsed_ms ?? trace?.total_duration_ms ?? 0;

  // Don't render if no valid trace data
  if (!trace || !Array.isArray(steps)) {
    return null;
  }

  const getStepColor = (type: string): string => {
    if (type.includes('success')) return 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/40';
    if (type.includes('error')) return 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/40';
    if (type.includes('warning')) return 'text-yellow-700 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-900/40';
    if (type.includes('verification')) return 'text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/40';
    if (type.includes('tool')) return 'text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-900/40';
    if (type.includes('cache_hit') || type.includes('semantic_cache_hit')) return 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/40';
    if (type.includes('cache_miss')) return 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/40';
    if (type.includes('cache_store')) return 'text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/40';
    if (type.includes('cache')) return 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/40';
    if (type.includes('fix') || type.includes('learning')) return 'text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-900/40';
    return 'text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800';
  };

  const getStepBorderColor = (type: string): string => {
    if (type.includes('success')) return 'border-green-200 dark:border-green-800/50';
    if (type.includes('error')) return 'border-red-200 dark:border-red-800/50';
    if (type.includes('warning')) return 'border-yellow-200 dark:border-yellow-800/50';
    if (type.includes('verification')) return 'border-blue-200 dark:border-blue-800/50';
    if (type.includes('tool')) return 'border-orange-200 dark:border-orange-800/50';
    if (type.includes('cache_hit') || type.includes('semantic_cache_hit')) return 'border-amber-200 dark:border-amber-800/50';
    if (type.includes('cache_miss')) return 'border-slate-200 dark:border-slate-800/50';
    if (type.includes('cache_store')) return 'border-teal-200 dark:border-teal-800/50';
    if (type.includes('cache')) return 'border-amber-200 dark:border-amber-800/50';
    if (type.includes('fix') || type.includes('learning')) return 'border-purple-200 dark:border-purple-800/50';
    return 'border-gray-200 dark:border-gray-700';
  };

  const getStepIcon = (type: string): string => {
    if (type.includes('cache_hit') || type.includes('semantic_cache_hit')) return '⚡';  // Lightning for cache hit
    if (type.includes('cache_miss')) return '🔍';  // Search for cache miss
    if (type.includes('cache_store')) return '💾';  // Disk for cache store
    if (type.includes('cache_lookup') || type.includes('cache_summary')) return '🗄️';  // File cabinet for cache lookup
    return '';
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-900/30 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden mt-4 shadow-sm transition-colors">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        aria-expanded={expanded}
        aria-label="Toggle agent execution trace"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl" role="img" aria-label="Trace">📊</span>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              Agent Execution Trace
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {steps.length} steps • {totalElapsedMs.toFixed(0)}ms
            </p>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''
            }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="space-y-3">
            {steps.map((step, idx) => {
              // Defensive: ensure step has required properties
              const stepType = step?.type || 'unknown';
              const stepMessage = step?.message || 'No message';
              const stepElapsedMs = step?.elapsed_ms ?? 0;
              const stepMetadata = step?.metadata || {};
              const stepIcon = step?.icon || getStepIcon(stepType) || '•';

              return (
                <div
                  key={idx}
                  className={`flex items-start gap-3 p-3 rounded-lg border ${getStepColor(stepType)} ${getStepBorderColor(stepType)}`}
                >
                  {/* Icon */}
                  <span className="text-2xl flex-shrink-0" role="img" aria-label={stepType}>
                    {stepIcon}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium text-sm flex-1">
                        {stepMessage}
                      </p>
                      <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                        +{stepElapsedMs.toFixed(0)}ms
                      </span>
                    </div>

                    {/* Step Type Badge */}
                    <div className="mt-1">
                      <span className="inline-block text-xs px-2 py-0.5 rounded bg-white dark:bg-black/20 bg-opacity-50">
                        {stepType}
                      </span>
                    </div>

                    {/* Metadata (expandable) */}
                    {stepMetadata && typeof stepMetadata === 'object' && Object.keys(stepMetadata).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-gray-200">
                          Show details
                        </summary>
                        <pre className="text-xs bg-white dark:bg-gray-900/50 p-2 rounded mt-1 overflow-x-auto border border-gray-100 dark:border-gray-800">
                          {JSON.stringify(stepMetadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary */}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              <strong>Total execution time:</strong> {totalElapsedMs.toFixed(2)}ms
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
