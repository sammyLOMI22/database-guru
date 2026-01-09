import React, { useState } from 'react';
import type { QueryCapability, DatabaseAssessmentResponse } from '../types/api';

interface QueryFeasibilityBadgeProps {
  assessment: DatabaseAssessmentResponse;
  compact?: boolean;
}

export const QueryFeasibilityBadge: React.FC<QueryFeasibilityBadgeProps> = ({
  assessment,
  compact = false,
}) => {
  const [expanded, setExpanded] = useState(false);

  // Color schemes for each capability level
  const capabilityStyles: Record<QueryCapability, {
    bg: string;
    text: string;
    border: string;
    icon: string;
    label: string;
  }> = {
    full: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      border: 'border-green-300',
      icon: '✓',
      label: 'Full Capability',
    },
    partial: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-800',
      border: 'border-yellow-300',
      icon: '⚡',
      label: 'Partial Capability',
    },
    cannot: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      border: 'border-red-300',
      icon: '✗',
      label: 'Cannot Execute',
    },
  };

  const style = capabilityStyles[assessment.capability];

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text} ${style.border} border`}
        title={assessment.reason}
      >
        <span>{style.icon}</span>
        <span className="capitalize">{assessment.capability}</span>
      </span>
    );
  }

  return (
    <div className="inline-block">
      {/* Main Badge */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${style.bg} ${style.text} ${style.border} cursor-pointer hover:opacity-80 transition-opacity`}
        aria-label={`${style.label}: ${assessment.connection_name}`}
        aria-expanded={expanded}
      >
        <span className="font-semibold">{style.icon}</span>
        <span className="text-sm font-medium capitalize">
          {assessment.capability}
        </span>
        <span className="text-xs opacity-75">
          {Math.round(assessment.confidence * 100)}%
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
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

      {/* Expanded Details */}
      {expanded && (
        <div className={`mt-2 p-3 rounded-lg border ${style.bg} ${style.border} max-w-md`}>
          {/* Database Info */}
          <div className="mb-3">
            <p className={`text-xs font-semibold ${style.text} mb-1`}>
              Database:
            </p>
            <p className="text-sm text-gray-700">
              {assessment.connection_name} ({assessment.database_type})
            </p>
          </div>

          {/* Reason */}
          <div className="mb-3">
            <p className={`text-xs font-semibold ${style.text} mb-1`}>
              Assessment:
            </p>
            <p className="text-sm text-gray-700">
              {assessment.reason}
            </p>
          </div>

          {/* Missing Tables */}
          {assessment.missing_tables.length > 0 && (
            <div className="mb-3">
              <p className={`text-xs font-semibold ${style.text} mb-1`}>
                Missing Tables:
              </p>
              <div className="flex flex-wrap gap-1">
                {assessment.missing_tables.map((table) => (
                  <span
                    key={table}
                    className="px-2 py-0.5 bg-red-200 text-red-800 text-xs rounded"
                  >
                    {table}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Missing Columns */}
          {Object.keys(assessment.missing_columns).length > 0 && (
            <div className="mb-3">
              <p className={`text-xs font-semibold ${style.text} mb-1`}>
                Missing Columns:
              </p>
              {Object.entries(assessment.missing_columns).map(([table, columns]) => (
                <div key={table} className="mb-1">
                  <span className="text-xs text-gray-600">{table}:</span>
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {columns.map((col) => (
                      <span
                        key={col}
                        className="px-2 py-0.5 bg-orange-200 text-orange-800 text-xs rounded"
                      >
                        {col}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Available Alternatives */}
          {Object.keys(assessment.available_alternatives).length > 0 && (
            <div className="mb-3">
              <p className={`text-xs font-semibold ${style.text} mb-1`}>
                Available Alternatives:
              </p>
              <div className="space-y-1">
                {Object.entries(assessment.available_alternatives).map(([missing, alternative]) => (
                  <div key={missing} className="text-xs flex items-center gap-2">
                    <span className="text-gray-600">{missing}</span>
                    <span className="text-gray-400">→</span>
                    <span className="px-2 py-0.5 bg-green-200 text-green-800 rounded">
                      {alternative}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested SQL */}
          {assessment.suggested_sql && (
            <div>
              <p className={`text-xs font-semibold ${style.text} mb-1`}>
                Suggested SQL:
              </p>
              <pre className="text-xs bg-gray-800 text-green-400 p-2 rounded overflow-x-auto">
                {assessment.suggested_sql}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
