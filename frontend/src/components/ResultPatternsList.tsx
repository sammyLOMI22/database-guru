import React, { useEffect, useState } from 'react';
import { Trash2, AlertCircle, ThumbsUp, TrendingUp } from 'lucide-react';
import { mappingsAPI } from '../services/mappingsApi';
import type { ResultPattern } from '../types/api';

export const ResultPatternsList: React.FC = () => {
  const [patterns, setPatterns] = useState<ResultPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState('');
  const [filterAction, setFilterAction] = useState('');

  useEffect(() => {
    loadPatterns();
  }, [filterType, filterAction]);

  const loadPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mappingsAPI.getResultPatterns({
        pattern_type: filterType || undefined,
        action: filterAction || undefined,
        limit: 100,
      });
      setPatterns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load result patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkHelpful = async (patternId: number) => {
    try {
      await mappingsAPI.markPatternHelpful(patternId);
      await loadPatterns();
    } catch (err: any) {
      alert(`Failed to mark pattern as helpful: ${err.message}`);
    }
  };

  const handleDelete = async (patternId: number) => {
    if (!confirm('Are you sure you want to delete this validation pattern?')) {
      return;
    }

    try {
      await mappingsAPI.deleteResultPattern(patternId);
      await loadPatterns();
    } catch (err: any) {
      alert(`Failed to delete pattern: ${err.message}`);
    }
  };

  const getPatternTypeColor = (type: string) => {
    switch (type) {
      case 'empty_result':
        return 'bg-red-100 text-red-700';
      case 'missing_data':
        return 'bg-yellow-100 text-yellow-700';
      case 'suspicious_values':
        return 'bg-orange-100 text-orange-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'warn_user':
        return 'bg-yellow-100 text-yellow-700';
      case 'suggest_fix':
        return 'bg-blue-100 text-blue-700';
      case 'block':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 rounded w-1/3"></div>
        <div className="h-20 bg-gray-200 rounded"></div>
        <div className="h-20 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (error) {
    return <div className="text-red-600">Error: {error}</div>;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All pattern types</option>
          <option value="empty_result">Empty Result</option>
          <option value="missing_data">Missing Data</option>
          <option value="suspicious_values">Suspicious Values</option>
        </select>
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All actions</option>
          <option value="warn_user">Warn User</option>
          <option value="suggest_fix">Suggest Fix</option>
          <option value="block">Block</option>
        </select>
      </div>

      {/* Patterns List */}
      {patterns.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No validation patterns learned yet</p>
          <p className="text-sm mt-1">
            Submit result issue feedback to start learning validation patterns
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {patterns.map((pattern) => {
            const helpfulnessRate =
              pattern.times_triggered > 0
                ? (pattern.times_helpful / pattern.times_triggered) * 100
                : 0;

            return (
              <div
                key={pattern.id}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className={`px-2 py-1 text-xs rounded font-medium ${getPatternTypeColor(pattern.pattern_type)}`}>
                        {pattern.pattern_type.replace('_', ' ')}
                      </span>
                      <span className={`px-2 py-1 text-xs rounded font-medium ${getActionColor(pattern.action)}`}>
                        Action: {pattern.action.replace('_', ' ')}
                      </span>
                      {pattern.times_triggered > 0 && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded flex items-center gap-1">
                          <TrendingUp className="w-3 h-3" />
                          Triggered {pattern.times_triggered}x
                        </span>
                      )}
                      {pattern.times_helpful > 0 && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded flex items-center gap-1">
                          <ThumbsUp className="w-3 h-3" />
                          Helpful {pattern.times_helpful}x ({Math.round(helpfulnessRate)}%)
                        </span>
                      )}
                      <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded">
                        {Math.round(pattern.confidence_score * 100)}% confidence
                      </span>
                    </div>

                    <p className="text-sm text-gray-900 mb-2">{pattern.pattern_description}</p>

                    {/* Matching Criteria */}
                    <div className="bg-white border border-gray-200 rounded p-3 mb-2">
                      <p className="text-xs font-semibold text-gray-700 mb-1">Matching Criteria:</p>
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono">
                        {JSON.stringify(pattern.matching_criteria, null, 2)}
                      </pre>
                    </div>

                    {pattern.suggestion && (
                      <div className="bg-blue-50 border border-blue-200 rounded p-2">
                        <p className="text-xs font-semibold text-blue-700 mb-1">Suggestion:</p>
                        <p className="text-xs text-blue-900">{pattern.suggestion}</p>
                      </div>
                    )}
                  </div>

                  <div className="flex-shrink-0 flex flex-col gap-2">
                    <button
                      onClick={() => handleMarkHelpful(pattern.id)}
                      className="p-2 text-green-600 hover:bg-green-50 rounded transition-colors"
                      title="Mark as helpful"
                    >
                      <ThumbsUp className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(pattern.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="Delete pattern"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Summary */}
      {patterns.length > 0 && (
        <div className="text-sm text-gray-600 text-center pt-4 border-t border-gray-200">
          Showing {patterns.length} validation pattern{patterns.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};
