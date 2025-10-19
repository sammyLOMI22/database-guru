import React, { useState } from 'react';
import { CorrectionAttempt } from '../types/api';

interface CorrectionHistoryProps {
  attempts: CorrectionAttempt[];
  selfCorrected: boolean;
}

export const CorrectionHistory: React.FC<CorrectionHistoryProps> = ({
  attempts,
  selfCorrected
}) => {
  const [expanded, setExpanded] = useState(false);

  // Don't show if no corrections were made
  if (!selfCorrected || attempts.length <= 1) {
    return null;
  }

  const getFixMethodBadge = (method?: string | null) => {
    const badges: Record<string, { label: string; color: string }> = {
      'quick_fix': { label: 'Quick Fix', color: 'bg-purple-100 text-purple-800' },
      'learned': { label: 'Learned', color: 'bg-blue-100 text-blue-800' },
      'llm': { label: 'LLM', color: 'bg-orange-100 text-orange-800' }
    };

    if (!method || !badges[method]) {
      return null;
    }

    const badge = badges[method];
    return (
      <span className={`text-xs px-2 py-1 rounded ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg overflow-hidden mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-blue-100 transition-colors"
        aria-expanded={expanded}
        aria-label="Toggle correction history"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl" role="img" aria-label="Auto-corrected">✨</span>
          <div>
            <h3 className="font-semibold text-blue-900">
              Auto-Corrected Query
            </h3>
            <p className="text-sm text-blue-700">
              Fixed after {attempts.length - 1} attempt{attempts.length - 1 !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-blue-700 transition-transform ${
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
        <div className="border-t border-blue-200 p-4 bg-white">
          <div className="space-y-4">
            {attempts.map((attempt, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  attempt.success
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">
                      Attempt {attempt.attempt_number}
                    </span>
                    {attempt.fix_method && getFixMethodBadge(attempt.fix_method)}
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      attempt.success
                        ? 'bg-green-200 text-green-800'
                        : 'bg-red-200 text-red-800'
                    }`}
                  >
                    {attempt.success ? '✓ Success' : '✗ Failed'}
                  </span>
                </div>

                {/* SQL Query */}
                <div className="mb-2">
                  <p className="text-xs text-gray-600 mb-1">SQL:</p>
                  <pre className="text-xs bg-gray-900 text-gray-100 p-2 rounded overflow-x-auto">
                    {attempt.sql}
                  </pre>
                </div>

                {/* Error Message */}
                {attempt.error && (
                  <div className="mb-2">
                    <p className="text-xs text-gray-600 mb-1">Error:</p>
                    <p className="text-xs text-red-700 bg-red-100 p-2 rounded">
                      {attempt.error}
                    </p>
                    {attempt.error_type && (
                      <p className="text-xs text-gray-500 mt-1">
                        Type: {attempt.error_type}
                      </p>
                    )}
                  </div>
                )}

                {/* Execution Details */}
                {attempt.success && (
                  <div className="flex gap-4 text-xs text-gray-600">
                    {attempt.execution_time_ms !== null && attempt.execution_time_ms !== undefined && (
                      <span>⏱️ {attempt.execution_time_ms.toFixed(2)}ms</span>
                    )}
                    {attempt.row_count !== null && attempt.row_count !== undefined && (
                      <span>📊 {attempt.row_count} rows</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              <strong>Summary:</strong> Query succeeded after {attempts.length} attempt{attempts.length !== 1 ? 's' : ''}.
              {attempts.some(a => a.fix_method === 'quick_fix') && ' Quick schema-aware fix was applied.'}
              {attempts.some(a => a.fix_method === 'learned') && ' Used learned correction from previous queries.'}
              {attempts.some(a => a.fix_method === 'llm') && ' AI-generated fix was used.'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
