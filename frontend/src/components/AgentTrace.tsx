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
    if (type.includes('success')) return 'text-green-700 bg-green-50';
    if (type.includes('error')) return 'text-red-700 bg-red-50';
    if (type.includes('warning')) return 'text-yellow-700 bg-yellow-50';
    if (type.includes('verification')) return 'text-blue-700 bg-blue-50';
    if (type.includes('tool')) return 'text-orange-700 bg-orange-50';  // Tool-Using Agent
    if (type.includes('cache_hit') || type.includes('semantic_cache_hit')) return 'text-amber-700 bg-amber-50';  // Cache hit
    if (type.includes('cache_miss')) return 'text-slate-700 bg-slate-50';  // Cache miss
    if (type.includes('cache_store')) return 'text-teal-700 bg-teal-50';  // Cache store
    if (type.includes('cache')) return 'text-amber-700 bg-amber-50';  // General cache
    if (type.includes('fix') || type.includes('learning')) return 'text-purple-700 bg-purple-50';
    return 'text-gray-700 bg-gray-50';
  };

  const getStepBorderColor = (type: string): string => {
    if (type.includes('success')) return 'border-green-200';
    if (type.includes('error')) return 'border-red-200';
    if (type.includes('warning')) return 'border-yellow-200';
    if (type.includes('verification')) return 'border-blue-200';
    if (type.includes('tool')) return 'border-orange-200';  // Tool-Using Agent
    if (type.includes('cache_hit') || type.includes('semantic_cache_hit')) return 'border-amber-200';  // Cache hit
    if (type.includes('cache_miss')) return 'border-slate-200';  // Cache miss
    if (type.includes('cache_store')) return 'border-teal-200';  // Cache store
    if (type.includes('cache')) return 'border-amber-200';  // General cache
    if (type.includes('fix') || type.includes('learning')) return 'border-purple-200';
    return 'border-gray-200';
  };

  const getStepIcon = (type: string): string => {
    if (type.includes('cache_hit') || type.includes('semantic_cache_hit')) return '⚡';  // Lightning for cache hit
    if (type.includes('cache_miss')) return '🔍';  // Search for cache miss
    if (type.includes('cache_store')) return '💾';  // Disk for cache store
    if (type.includes('cache_lookup') || type.includes('cache_summary')) return '🗄️';  // File cabinet for cache lookup
    return '';
  };

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-gray-100 transition-colors"
        aria-expanded={expanded}
        aria-label="Toggle agent execution trace"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl" role="img" aria-label="Trace">📊</span>
          <div>
            <h3 className="font-semibold text-gray-900">
              Agent Execution Trace
            </h3>
            <p className="text-sm text-gray-500">
              {steps.length} steps • {totalElapsedMs.toFixed(0)}ms
            </p>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${
            expanded ? 'rotate-180' : ''
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
        <div className="border-t border-gray-200 p-4">
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
                      <span className="text-xs text-gray-500 flex-shrink-0">
                        +{stepElapsedMs.toFixed(0)}ms
                      </span>
                    </div>

                    {/* Step Type Badge */}
                    <div className="mt-1">
                      <span className="inline-block text-xs px-2 py-0.5 rounded bg-white bg-opacity-50">
                        {stepType}
                      </span>
                    </div>

                    {/* Metadata (expandable) */}
                    {stepMetadata && typeof stepMetadata === 'object' && Object.keys(stepMetadata).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                          Show details
                        </summary>
                        <pre className="text-xs bg-white p-2 rounded mt-1 overflow-x-auto border">
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
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              <strong>Total execution time:</strong> {totalElapsedMs.toFixed(2)}ms
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
