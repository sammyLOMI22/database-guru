import React, { useState } from 'react';
import { ConfidencePrediction } from '../types/api';

interface ConfidenceBadgeProps {
  confidence: ConfidencePrediction;
  showDetails?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  showDetails = true
}) => {
  const [expanded, setExpanded] = useState(false);

  // Color schemes for each confidence level
  const levelStyles = {
    HIGH: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      border: 'border-green-300',
      icon: '🎯',
      label: 'High Confidence'
    },
    MEDIUM: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-800',
      border: 'border-yellow-300',
      icon: '⚡',
      label: 'Medium Confidence'
    },
    LOW: {
      bg: 'bg-orange-100',
      text: 'text-orange-800',
      border: 'border-orange-300',
      icon: '⚠️',
      label: 'Low Confidence'
    },
    VERY_LOW: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      border: 'border-red-300',
      icon: '🚫',
      label: 'Very Low Confidence'
    }
  };

  const style = levelStyles[confidence.level];

  // Validate confidence.overall to prevent NaN display
  const validOverall = (typeof confidence.overall === 'number' && !isNaN(confidence.overall))
    ? confidence.overall
    : 0.0; // Fallback to 0% for invalid data

  const percentage = (validOverall * 100).toFixed(1);

  // Format factor names for display
  const factorLabels: Record<string, string> = {
    error_type: 'Error Type Difficulty',
    schema_match: 'Schema Match',
    historical_success: 'Historical Success',
    correction_complexity: 'Correction Complexity',
    similarity: 'Similarity to Original'
  };

  return (
    <div className="inline-block">
      {/* Main Badge */}
      <button
        onClick={() => showDetails && setExpanded(!expanded)}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${style.bg} ${style.text} ${style.border} ${
          showDetails ? 'cursor-pointer hover:opacity-80' : 'cursor-default'
        } transition-opacity`}
        disabled={!showDetails}
        aria-label={`${style.label}: ${percentage}%`}
        aria-expanded={expanded}
      >
        <span role="img" aria-hidden="true">{style.icon}</span>
        <span className="font-semibold text-sm">
          {percentage}%
        </span>
        <span className="text-xs opacity-75">
          {confidence.level}
        </span>
        {showDetails && (
          <svg
            className={`w-4 h-4 transition-transform ${
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
        )}
      </button>

      {/* Expanded Details */}
      {expanded && showDetails && (
        <div className={`mt-2 p-3 rounded-lg border ${style.bg} ${style.border}`}>
          {/* Reasoning */}
          <div className="mb-3">
            <p className={`text-xs font-semibold ${style.text} mb-1`}>
              Analysis:
            </p>
            <p className="text-xs text-gray-700">
              {confidence.reasoning}
            </p>
          </div>

          {/* Recommendation */}
          <div className="mb-3">
            <p className={`text-xs font-semibold ${style.text} mb-1`}>
              Recommendation:
            </p>
            <p className="text-xs text-gray-700">
              {confidence.recommendation}
            </p>
          </div>

          {/* Factor Breakdown */}
          <div>
            <p className={`text-xs font-semibold ${style.text} mb-2`}>
              Contributing Factors:
            </p>
            <div className="space-y-1.5">
              {Object.entries(confidence.factors).map(([key, value]) => {
                // Validate factor value to prevent NaN
                const validValue = (typeof value === 'number' && !isNaN(value)) ? value : 0;
                const factorPercentage = (validValue * 100).toFixed(1);
                // Prevent division by zero - if overall is 0, show 0% for factors too
                const barWidth = validOverall > 0 ? (validValue / validOverall) * 100 : 0;

                return (
                  <div key={key} className="text-xs">
                    <div className="flex justify-between items-center mb-0.5">
                      <span className="text-gray-700">
                        {factorLabels[key] || key}
                      </span>
                      <span className={`font-mono ${style.text}`}>
                        {factorPercentage}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${style.bg.replace('100', '400')} transition-all`}
                        style={{ width: `${Math.min(barWidth, 100)}%` }}
                        role="progressbar"
                        aria-valuenow={validValue}
                        aria-valuemin={0}
                        aria-valuemax={1}
                        aria-label={`${factorLabels[key]}: ${factorPercentage}%`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Overall Score Bar */}
          <div className="mt-3 pt-3 border-t border-gray-300">
            <div className="flex justify-between items-center mb-1">
              <span className={`text-xs font-semibold ${style.text}`}>
                Overall Confidence
              </span>
              <span className={`text-xs font-mono font-bold ${style.text}`}>
                {percentage}%
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${style.bg.replace('100', '500')} transition-all`}
                style={{ width: `${validOverall * 100}%` }}
                role="progressbar"
                aria-valuenow={validOverall}
                aria-valuemin={0}
                aria-valuemax={1}
                aria-label={`Overall confidence: ${percentage}%`}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
