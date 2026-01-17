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
    <div className="glass-card rounded-xl overflow-hidden mt-4 shadow-lg border border-white/10 dark:border-white/5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-5 py-4 hover:bg-white/5 transition-all group"
        aria-expanded={expanded}
        aria-label="Toggle agent execution trace"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center group-hover:scale-110 transition-transform">
            <span className="text-xl" role="img" aria-label="Trace">📊</span>
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-gray-100 text-base">
              Agent Execution Trace
            </h3>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {steps.length} steps • <span className="font-mono">{totalElapsedMs.toFixed(0)}ms</span>
            </p>
          </div>
        </div>
        <div className={`p-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 transition-all ${expanded ? 'rotate-180 bg-blue-500/10 text-blue-500' : 'text-gray-500'}`}>
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2.5}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-5 py-6 bg-white/30 dark:bg-black/20 backdrop-blur-sm border-t border-white/10 dark:border-white/5">
          <div className="relative space-y-6 ml-4">
            {/* Vertical Flow Line */}
            <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-gradient-to-b from-blue-500/50 via-purple-500/50 to-blue-500/50 dark:from-blue-500/30 dark:via-purple-500/30 dark:to-blue-500/30 rounded-full" />

            {steps.map((step, idx) => {
              // Defensive: ensure step has required properties
              const stepType = step?.type || 'unknown';
              const stepMessage = step?.message || 'No message';
              const stepElapsedMs = step?.elapsed_ms ?? 0;
              const stepMetadata = step?.metadata || {};
              const stepIcon = step?.icon || getStepIcon(stepType) || '•';

              const staggerClass = idx < 8 ? `delay-${idx * 100}` : 'delay-700';

              return (
                <div
                  key={idx}
                  className={`relative flex items-start gap-5 animate-fadeIn ${staggerClass} opacity-0 fill-mode-forwards`}
                >
                  {/* Step Connector Node */}
                  <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm border-2 ${getStepBorderColor(stepType)} ${getStepColor(stepType)}`}>
                    <span className="text-sm" role="img" aria-label={stepType}>
                      {stepIcon}
                    </span>
                  </div>

                  {/* Content Card */}
                  <div className="flex-1 min-w-0 glass-card p-3.5 rounded-xl border-white/5 hover:border-white/20 transition-all group/step">
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-semibold text-sm text-gray-800 dark:text-gray-200 leading-snug">
                        {stepMessage}
                      </p>
                      <span className="text-[10px] font-bold font-mono text-gray-400 dark:text-gray-500 tracking-tighter bg-gray-100 dark:bg-gray-800/50 px-1.5 py-0.5 rounded">
                        +{stepElapsedMs.toFixed(0)}ms
                      </span>
                    </div>

                    {/* Step Type Badge */}
                    <div className="mt-2 flex items-center gap-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase ${getStepColor(stepType)} bg-opacity-10 dark:bg-opacity-20`}>
                        {stepType.replace('_', ' ')}
                      </span>
                    </div>

                    {/* Metadata (expandable) */}
                    {stepMetadata && typeof stepMetadata === 'object' && Object.keys(stepMetadata).length > 0 && (
                      <details className="mt-2.5 group">
                        <summary className="text-[11px] font-bold text-gray-500 dark:text-gray-400 cursor-pointer hover:text-blue-500 transition-colors list-none flex items-center gap-1">
                          <svg className="w-3 h-3 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
                          </svg>
                          TECHNICAL DETAILS
                        </summary>
                        <div className="mt-2 overflow-hidden rounded-lg border border-white/5">
                          <pre className="text-[10px] font-mono bg-black/40 text-blue-300 p-3 overflow-x-auto scrollbar-thin">
                            {JSON.stringify(stepMetadata, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary Footer */}
          <div className="mt-8 pt-4 border-t border-white/10 dark:border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Process completed successfully
            </div>
            <p className="text-xs font-bold text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-3 py-1.5 rounded-lg">
              Total Time: <span className="font-mono text-blue-500">{totalElapsedMs.toFixed(2)}ms</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
