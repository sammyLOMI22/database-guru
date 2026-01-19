import React, { useEffect, useState } from 'react';
import { Trash2, AlertCircle, ThumbsUp, TrendingUp, Filter } from 'lucide-react';
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

  const getPatternTypeStyle = (type: string) => {
    switch (type) {
      case 'empty_result':
        return 'bg-red-500/10 text-red-600 dark:text-red-400';
      case 'missing_data':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400';
      case 'suspicious_values':
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400';
      default:
        return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
    }
  };

  const getActionStyle = (action: string) => {
    switch (action) {
      case 'warn_user':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400';
      case 'suggest_fix':
        return 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
      case 'block':
        return 'bg-red-500/10 text-red-600 dark:text-red-400';
      default:
        return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-10 glass-panel rounded-2xl"></div>
        <div className="h-32 glass-panel rounded-2xl"></div>
        <div className="h-32 glass-panel rounded-2xl"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card rounded-2xl p-4 bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/5 border-red-500/20">
        <p className="text-xs font-black uppercase tracking-[0.15em] text-red-600 dark:text-red-400">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="w-full glass-panel rounded-xl pl-10 pr-4 py-2.5 text-xs font-medium text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 border-white/5 bg-transparent appearance-none cursor-pointer transition-all"
          >
            <option value="" className="bg-gray-800 text-white">All pattern types</option>
            <option value="empty_result" className="bg-gray-800 text-white">Empty Result</option>
            <option value="missing_data" className="bg-gray-800 text-white">Missing Data</option>
            <option value="suspicious_values" className="bg-gray-800 text-white">Suspicious Values</option>
          </select>
        </div>
        <div className="flex-1 relative">
          <AlertCircle className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="w-full glass-panel rounded-xl pl-10 pr-4 py-2.5 text-xs font-medium text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 border-white/5 bg-transparent appearance-none cursor-pointer transition-all"
          >
            <option value="" className="bg-gray-800 text-white">All actions</option>
            <option value="warn_user" className="bg-gray-800 text-white">Warn User</option>
            <option value="suggest_fix" className="bg-gray-800 text-white">Suggest Fix</option>
            <option value="block" className="bg-gray-800 text-white">Block</option>
          </select>
        </div>
      </div>

      {/* Patterns List */}
      {patterns.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-2xl border-white/10">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl glass-panel flex items-center justify-center text-gray-400">
            <AlertCircle className="w-7 h-7" />
          </div>
          <p className="text-xs font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">No validation patterns</p>
          <p className="text-[10px] font-medium text-gray-400 mt-2">
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
                className="glass-card rounded-2xl p-4 hover:scale-[1.005] transition-all border-white/10 hover:border-purple-500/20"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className={`px-2 py-1 text-[9px] font-black uppercase tracking-[0.15em] rounded-lg ${getPatternTypeStyle(pattern.pattern_type)}`}>
                        {pattern.pattern_type.replace('_', ' ')}
                      </span>
                      <span className={`px-2 py-1 text-[9px] font-black uppercase tracking-[0.15em] rounded-lg ${getActionStyle(pattern.action)}`}>
                        {pattern.action.replace('_', ' ')}
                      </span>
                      {pattern.times_triggered > 0 && (
                        <span className="px-2 py-1 text-[9px] font-black uppercase tracking-[0.15em] rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center gap-1">
                          <TrendingUp className="w-3 h-3" />
                          {pattern.times_triggered}x
                        </span>
                      )}
                      {pattern.times_helpful > 0 && (
                        <span className="px-2 py-1 text-[9px] font-black uppercase tracking-[0.15em] rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                          <ThumbsUp className="w-3 h-3" />
                          {pattern.times_helpful}x ({Math.round(helpfulnessRate)}%)
                        </span>
                      )}
                      <span className={`px-2 py-1 text-[9px] font-black uppercase tracking-[0.15em] rounded-lg ${
                        pattern.confidence_score >= 0.8 ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
                        pattern.confidence_score >= 0.5 ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
                        'bg-red-500/10 text-red-600 dark:text-red-400'
                      }`}>
                        {Math.round(pattern.confidence_score * 100)}%
                      </span>
                    </div>

                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">{pattern.pattern_description}</p>

                    {/* Matching Criteria */}
                    <div className="glass-panel rounded-xl p-3 mb-3 border-white/5">
                      <p className="text-[9px] font-black uppercase tracking-[0.15em] text-gray-500 dark:text-gray-400 mb-2">Matching Criteria</p>
                      <pre className="text-[10px] font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-x-auto">
                        {JSON.stringify(pattern.matching_criteria, null, 2)}
                      </pre>
                    </div>

                    {pattern.suggestion && (
                      <div className="glass-card rounded-xl p-3 bg-gradient-to-r from-blue-500/10 via-transparent to-cyan-500/5 border-blue-500/20">
                        <p className="text-[9px] font-black uppercase tracking-[0.15em] text-blue-600 dark:text-blue-400 mb-1">Suggestion</p>
                        <p className="text-[10px] font-medium text-blue-700 dark:text-blue-300">{pattern.suggestion}</p>
                      </div>
                    )}
                  </div>

                  <div className="flex-shrink-0 flex flex-col gap-2">
                    <button
                      onClick={() => handleMarkHelpful(pattern.id)}
                      className="w-9 h-9 rounded-xl glass-panel flex items-center justify-center text-gray-400 hover:text-emerald-500 hover:scale-105 active:scale-95 transition-all"
                      title="Mark as helpful"
                    >
                      <ThumbsUp className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(pattern.id)}
                      className="w-9 h-9 rounded-xl glass-panel flex items-center justify-center text-gray-400 hover:text-red-500 hover:scale-105 active:scale-95 transition-all"
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
        <div className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 text-center pt-4 border-t border-white/5">
          {patterns.length} pattern{patterns.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};
