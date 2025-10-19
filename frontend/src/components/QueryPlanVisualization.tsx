import React, { useState } from 'react';
import { QueryPlan } from '../types/api';

interface QueryPlanVisualizationProps {
  plan: QueryPlan;
  usedPlanning: boolean;
}

export const QueryPlanVisualization: React.FC<QueryPlanVisualizationProps> = ({
  plan,
  usedPlanning
}) => {
  const [expanded, setExpanded] = useState(false);

  // Don't show if planning wasn't used
  if (!usedPlanning) {
    return null;
  }

  const getComplexityColor = (complexity: string): string => {
    switch (complexity.toLowerCase()) {
      case 'simple':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'complex':
        return 'bg-orange-100 text-orange-800';
      case 'very_complex':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-700';
    if (confidence >= 0.6) return 'text-yellow-700';
    return 'text-red-700';
  };

  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded-lg overflow-hidden mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-indigo-100 transition-colors"
        aria-expanded={expanded}
        aria-label="Toggle query plan"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl" role="img" aria-label="Query plan">📋</span>
          <div>
            <h3 className="font-semibold text-indigo-900">
              Query Plan
            </h3>
            <div className="flex items-center gap-2 text-sm">
              <span className={`px-2 py-0.5 rounded text-xs ${getComplexityColor(plan.complexity)}`}>
                {plan.complexity}
              </span>
              <span className={`text-xs ${getConfidenceColor(plan.confidence)}`}>
                {(plan.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-indigo-700 transition-transform ${
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
        <div className="border-t border-indigo-200 p-4 bg-white">
          {/* Intent */}
          {plan.intent && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-1">Intent</h4>
              <p className="text-sm text-gray-600">{plan.intent}</p>
            </div>
          )}

          {/* Reasoning */}
          {plan.reasoning && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-1">Reasoning</h4>
              <p className="text-sm text-gray-600">{plan.reasoning}</p>
            </div>
          )}

          {/* Stats Badges */}
          <div className="flex flex-wrap gap-2 mb-4">
            {plan.joins_count > 0 && (
              <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                {plan.joins_count} join{plan.joins_count !== 1 ? 's' : ''}
              </span>
            )}
            {plan.filters_count > 0 && (
              <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                {plan.filters_count} filter{plan.filters_count !== 1 ? 's' : ''}
              </span>
            )}
            {plan.aggregations_count > 0 && (
              <span className="px-3 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                {plan.aggregations_count} aggregation{plan.aggregations_count !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Tables */}
          {plan.tables && plan.tables.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Tables</h4>
              <div className="space-y-2">
                {plan.tables.map((table, idx) => (
                  <div key={idx} className="bg-gray-50 p-2 rounded border border-gray-200">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm text-gray-900">{table.name}</span>
                      {table.alias && (
                        <span className="text-xs text-gray-500">as {table.alias}</span>
                      )}
                    </div>
                    {table.purpose && (
                      <p className="text-xs text-gray-600 mt-1">{table.purpose}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Joins */}
          {plan.joins && plan.joins.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Joins</h4>
              <div className="space-y-2">
                {plan.joins.map((join, idx) => (
                  <div key={idx} className="bg-blue-50 p-2 rounded border border-blue-200">
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 bg-blue-200 text-blue-800 rounded">
                        {join.type}
                      </span>
                      <span className="font-mono text-sm text-gray-900">
                        {join.from} → {join.to}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">ON {join.on}</p>
                    {join.purpose && (
                      <p className="text-xs text-gray-500 mt-1">{join.purpose}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filters */}
          {plan.filters && plan.filters.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Filters</h4>
              <div className="space-y-2">
                {plan.filters.map((filter, idx) => (
                  <div key={idx} className="bg-purple-50 p-2 rounded border border-purple-200">
                    <div className="font-mono text-sm text-gray-900">
                      {filter.column} {filter.operator} {filter.value}
                    </div>
                    {filter.purpose && (
                      <p className="text-xs text-gray-600 mt-1">{filter.purpose}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Aggregations */}
          {plan.aggregations && plan.aggregations.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Aggregations</h4>
              <div className="space-y-2">
                {plan.aggregations.map((agg, idx) => (
                  <div key={idx} className="bg-green-50 p-2 rounded border border-green-200">
                    <div className="font-mono text-sm text-gray-900">
                      {agg.function}({agg.column}){agg.alias && ` AS ${agg.alias}`}
                    </div>
                    {agg.purpose && (
                      <p className="text-xs text-gray-600 mt-1">{agg.purpose}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Grouping */}
          {plan.grouping && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Grouping</h4>
              <div className="bg-gray-50 p-2 rounded border border-gray-200">
                <div className="font-mono text-sm text-gray-900">
                  GROUP BY {plan.grouping.columns.join(', ')}
                </div>
                {plan.grouping.purpose && (
                  <p className="text-xs text-gray-600 mt-1">{plan.grouping.purpose}</p>
                )}
              </div>
            </div>
          )}

          {/* Ordering */}
          {plan.ordering && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Ordering</h4>
              <div className="bg-gray-50 p-2 rounded border border-gray-200">
                <div className="font-mono text-sm text-gray-900">
                  ORDER BY {plan.ordering.column} {plan.ordering.direction}
                </div>
                {plan.ordering.purpose && (
                  <p className="text-xs text-gray-600 mt-1">{plan.ordering.purpose}</p>
                )}
              </div>
            </div>
          )}

          {/* Limit */}
          {plan.limit !== null && plan.limit !== undefined && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Limit</h4>
              <div className="bg-gray-50 p-2 rounded border border-gray-200">
                <div className="font-mono text-sm text-gray-900">
                  LIMIT {plan.limit}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
