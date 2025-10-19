import React, { useState } from 'react';
import { AgentTrace as AgentTraceType } from '../types/api';

interface AgentTraceProps {
  trace: AgentTraceType;
}

export const AgentTrace: React.FC<AgentTraceProps> = ({ trace }) => {
  const [expanded, setExpanded] = useState(false);

  const getStepColor = (type: string): string => {
    if (type.includes('success')) return 'text-green-700 bg-green-50';
    if (type.includes('error')) return 'text-red-700 bg-red-50';
    if (type.includes('warning')) return 'text-yellow-700 bg-yellow-50';
    if (type.includes('verification')) return 'text-blue-700 bg-blue-50';
    if (type.includes('fix') || type.includes('learning')) return 'text-purple-700 bg-purple-50';
    return 'text-gray-700 bg-gray-50';
  };

  const getStepBorderColor = (type: string): string => {
    if (type.includes('success')) return 'border-green-200';
    if (type.includes('error')) return 'border-red-200';
    if (type.includes('warning')) return 'border-yellow-200';
    if (type.includes('verification')) return 'border-blue-200';
    if (type.includes('fix') || type.includes('learning')) return 'border-purple-200';
    return 'border-gray-200';
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
              {trace.steps.length} steps • {trace.total_elapsed_ms.toFixed(0)}ms
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
            {trace.steps.map((step, idx) => (
              <div
                key={idx}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getStepColor(step.type)} ${getStepBorderColor(step.type)}`}
              >
                {/* Icon */}
                <span className="text-2xl flex-shrink-0" role="img" aria-label={step.type}>
                  {step.icon || '•'}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-sm flex-1">
                      {step.message}
                    </p>
                    <span className="text-xs text-gray-500 flex-shrink-0">
                      +{step.elapsed_ms.toFixed(0)}ms
                    </span>
                  </div>

                  {/* Step Type Badge */}
                  <div className="mt-1">
                    <span className="inline-block text-xs px-2 py-0.5 rounded bg-white bg-opacity-50">
                      {step.type}
                    </span>
                  </div>

                  {/* Metadata (expandable) */}
                  {Object.keys(step.metadata).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                        Show details
                      </summary>
                      <pre className="text-xs bg-white p-2 rounded mt-1 overflow-x-auto border">
                        {JSON.stringify(step.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              <strong>Total execution time:</strong> {trace.total_elapsed_ms.toFixed(2)}ms
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
