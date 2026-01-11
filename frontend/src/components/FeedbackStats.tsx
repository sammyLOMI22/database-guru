import React, { useEffect, useState } from 'react';
import { feedbackAPI, FeedbackStatsResponse, FeedbackResponse } from '../services/api';
import { CheckCircle, Clock, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';

export const FeedbackStats: React.FC = () => {
  const [stats, setStats] = useState<FeedbackStatsResponse | null>(null);
  const [recentFeedback, setRecentFeedback] = useState<FeedbackResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [filterMode, setFilterMode] = useState<'all' | 'pending' | 'applied'>('pending');
  const [expandedSql, setExpandedSql] = useState<Set<number>>(new Set());
  const [autoRefresh, setAutoRefresh] = useState(false);
  const pageSize = 20;

  const toggleSqlExpanded = (feedbackId: number) => {
    setExpandedSql(prev => {
      const newSet = new Set(prev);
      if (newSet.has(feedbackId)) {
        newSet.delete(feedbackId);
      } else {
        newSet.add(feedbackId);
      }
      return newSet;
    });
  };

  useEffect(() => {
    loadStats();
  }, [currentPage, filterMode]);

  // Auto-refresh every 10 seconds when enabled
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadStats();
    }, 10000); // 10 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, currentPage, filterMode]);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      // Use server-side filtering - backend will filter by applied status
      const [statsData, recentData] = await Promise.all([
        feedbackAPI.getStats(),
        feedbackAPI.getRecentFeedback(pageSize, currentPage * pageSize, filterMode),
      ]);
      setStats(statsData);
      setRecentFeedback(recentData);
    } catch (err: any) {
      setError(err.message || 'Failed to load feedback statistics');
    } finally {
      setLoading(false);
    }
  };

  // Get tier information based on confidence
  const getTierInfo = (confidence: number) => {
    if (confidence >= 0.90) {
      return { tier: 1, label: 'Tier 1', color: 'bg-green-100 text-green-800', emoji: '🚀', description: 'Auto-applied (STRICT)' };
    } else if (confidence >= 0.80) {
      return { tier: 2, label: 'Tier 2', color: 'bg-blue-100 text-blue-800', emoji: '⚡', description: 'Auto-applied (MODERATE)' };
    } else if (confidence >= 0.70) {
      return { tier: 3, label: 'Tier 3', color: 'bg-yellow-100 text-yellow-800', emoji: '📋', description: 'Queued for batch' };
    } else {
      return { tier: 0, label: 'Manual', color: 'bg-gray-100 text-gray-800', emoji: '👁️', description: 'Manual review' };
    }
  };

  const handleApplyFeedback = async (feedbackId: number) => {
    try {
      // First try with testing enabled
      await feedbackAPI.applyFeedback(feedbackId, true);
      // Reload stats after applying
      setCurrentPage(0); // Reset to first page
      await loadStats();
    } catch (err: any) {
      // If testing failed, ask user if they want to skip testing
      const errorMessage = err.response?.data?.detail || err.message;

      if (errorMessage.includes('failed to execute')) {
        const skipTesting = window.confirm(
          `The corrected SQL failed validation:\n\n${errorMessage}\n\n` +
          `This might happen for schema changes or queries with dependencies.\n\n` +
          `Do you want to apply this correction WITHOUT testing?\n\n` +
          `⚠️ Warning: Skipping testing means the SQL won't be validated before learning.`
        );

        if (skipTesting) {
          try {
            await feedbackAPI.applyFeedback(feedbackId, false);
            setCurrentPage(0); // Reset to first page
            await loadStats();
          } catch (retryErr: any) {
            alert(`Failed to apply feedback: ${retryErr.response?.data?.detail || retryErr.message}`);
          }
        }
      } else {
        alert(`Failed to apply feedback: ${errorMessage}`);
      }
    }
  };

  const handleRejectFeedback = async (feedbackId: number) => {
    const confirmed = window.confirm(
      `Are you sure you want to reject and delete this feedback?\n\n` +
      `This action cannot be undone.`
    );

    if (confirmed) {
      try {
        await feedbackAPI.deleteFeedback(feedbackId);
        // Reload stats after deleting
        setCurrentPage(0); // Reset to first page
        await loadStats();
      } catch (err: any) {
        alert(`Failed to reject feedback: ${err.response?.data?.detail || err.message}`);
      }
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="text-red-600 dark:text-red-400">Error: {error}</div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const feedbackTypes = [
    { key: 'sql_correction', label: 'SQL Corrections', color: 'blue' },
    { key: 'column_name', label: 'Column Names', color: 'green' },
    { key: 'table_name', label: 'Table Names', color: 'yellow' },
    { key: 'result_issue', label: 'Result Issues', color: 'red' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Feedback Dashboard</h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">User corrections and continuous learning insights</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-3 py-1.5 rounded-lg text-sm transition-colors">
            <Clock className={`w-4 h-4 ${autoRefresh ? 'text-blue-500 animate-pulse' : 'text-gray-400'}`} />
            <span className="text-gray-700 dark:text-gray-300 font-medium">Auto-Refresh</span>
            <input
              type="checkbox"
              className="sr-only"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <div className={`w-8 h-4 rounded-full transition-colors relative ${autoRefresh ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}`}>
              <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-transform ${autoRefresh ? 'translate-x-4' : 'translate-x-0.5'}`} />
            </div>
          </label>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Feedback */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border-l-4 border-blue-500 overflow-hidden border border-gray-100 dark:border-gray-700 transition-colors">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Feedback</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{stats.total_feedback}</p>
            </div>
            <TrendingUp className="w-10 h-10 text-blue-500 opacity-50 dark:opacity-30" />
          </div>
        </div>

        {/* Applied to Learning */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border-l-4 border-green-500 overflow-hidden border border-gray-100 dark:border-gray-700 transition-colors">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Applied to Learning</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{stats.applied_to_learning}</p>
            </div>
            <CheckCircle className="w-10 h-10 text-green-500 opacity-50 dark:opacity-30" />
          </div>
        </div>

        {/* Pending Review */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border-l-4 border-yellow-500 overflow-hidden border border-gray-100 dark:border-gray-700 transition-colors">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Pending Review</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{stats.pending}</p>
            </div>
            <Clock className="w-10 h-10 text-yellow-500 opacity-50 dark:opacity-30" />
          </div>
        </div>
      </div>

      {/* Tier Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Auto-Approval Tiers (Phase 1)</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded-lg p-3">
            <div className="text-xs text-green-600 dark:text-green-400 font-medium mb-1">🚀 Tier 1 (≥90%)</div>
            <div className="text-lg font-bold text-green-700 dark:text-green-300">
              {recentFeedback.filter(f => f.user_confidence >= 0.90).length}
            </div>
            <div className="text-xs text-green-600 dark:text-green-500 mt-1">Auto-apply (STRICT)</div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded-lg p-3">
            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium mb-1">⚡ Tier 2 (≥80%)</div>
            <div className="text-lg font-bold text-blue-700 dark:text-blue-300">
              {recentFeedback.filter(f => f.user_confidence >= 0.80 && f.user_confidence < 0.90).length}
            </div>
            <div className="text-xs text-blue-600 dark:text-blue-500 mt-1">Auto-apply (MODERATE)</div>
          </div>
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800/50 rounded-lg p-3">
            <div className="text-xs text-yellow-600 dark:text-yellow-400 font-medium mb-1">📋 Tier 3 (≥70%)</div>
            <div className="text-lg font-bold text-yellow-700 dark:text-yellow-300">
              {recentFeedback.filter(f => f.user_confidence >= 0.70 && f.user_confidence < 0.80).length}
            </div>
            <div className="text-xs text-yellow-600 dark:text-yellow-500 mt-1">Batch queue</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700/30 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
            <div className="text-xs text-gray-600 dark:text-gray-400 font-medium mb-1">👁 Manual (&lt;70%)</div>
            <div className="text-lg font-bold text-gray-700 dark:text-gray-200">
              {recentFeedback.filter(f => f.user_confidence < 0.70).length}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-500 mt-1">Manual review</div>
          </div>
        </div>
      </div>

      {/* Feedback by Type */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Feedback by Type</h3>
        <div className="space-y-3">
          {feedbackTypes.map(({ key, label, color }) => {
            const count = stats.by_type[key] || 0;
            const percentage = stats.total_feedback > 0
              ? (count / stats.total_feedback) * 100
              : 0;

            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">{count}</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                  <div
                    className={`bg-${color}-500 dark:bg-${color}-400 h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Feedback */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Feedback
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => { setFilterMode('all'); setCurrentPage(0); }}
                  className={`px-3 py-1 text-xs rounded font-medium transition-all ${filterMode === 'all'
                    ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow-sm'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                >
                  All
                </button>
                <button
                  onClick={() => { setFilterMode('pending'); setCurrentPage(0); }}
                  className={`px-3 py-1 text-xs rounded font-medium transition-all ${filterMode === 'pending'
                    ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 shadow-sm'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                >
                  Pending
                </button>
                <button
                  onClick={() => { setFilterMode('applied'); setCurrentPage(0); }}
                  className={`px-3 py-1 text-xs rounded font-medium transition-all ${filterMode === 'applied'
                    ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800 shadow-sm'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                >
                  Applied
                </button>
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Page {currentPage + 1}
              </div>
            </div>
          </div>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700 overflow-x-hidden">
          {recentFeedback.length === 0 ? (
            <div className="p-6 text-center text-gray-500 dark:text-gray-400">
              {filterMode === 'pending' ? 'No pending feedback' :
                filterMode === 'applied' ? 'No applied feedback yet' :
                  'No feedback submitted yet'}
            </div>
          ) : (
            recentFeedback.map((feedback) => (
              <div key={feedback.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors overflow-x-hidden">
                <div className="flex flex-col sm:flex-row items-start gap-3">
                  <div className="flex-1 min-w-0 overflow-hidden" style={{ maxWidth: "calc(100% - 100px)" }}>

                    <div className="flex flex-wrap items-center gap-1.5 mb-2">
                      <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${feedback.feedback_type === 'sql_correction' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' :
                        feedback.feedback_type === 'column_name' ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300' :
                          feedback.feedback_type === 'table_name' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300' :
                            'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                        }`}>
                        {feedback.feedback_type.replace('_', ' ').toUpperCase()}
                      </span>
                      {(() => {
                        const tierInfo = getTierInfo(feedback.user_confidence);
                        const darkColor = feedback.user_confidence >= 0.90 ? 'dark:bg-green-900/40 dark:text-green-300' :
                          feedback.user_confidence >= 0.80 ? 'dark:bg-blue-900/40 dark:text-blue-300' :
                            feedback.user_confidence >= 0.70 ? 'dark:bg-yellow-900/40 dark:text-yellow-300' :
                              'dark:bg-gray-800 dark:text-gray-300';
                        return (
                          <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${tierInfo.color} ${darkColor}`} title={tierInfo.description}>
                            {tierInfo.emoji} {tierInfo.label}
                          </span>
                        );
                      })()}
                      {feedback.applied_successfully && (
                        <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300">
                          ✓ Applied
                        </span>
                      )}
                      {feedback.learned_correction_id && (
                        <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300" title="Learned Correction ID">
                          🧠 LC-{feedback.learned_correction_id}
                        </span>
                      )}
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {Math.round(feedback.user_confidence * 100)}% conf
                      </span>
                    </div>

                    {feedback.correction_description && (
                      <p className="text-xs text-gray-700 dark:text-gray-300 mb-1.5 break-all overflow-hidden">
                        {feedback.correction_description}
                      </p>
                    )}

                    {/* Show validation rejection message if present */}
                    {feedback.user_notes && feedback.user_notes.includes('[AUTO-APPLY REJECTED]') && (
                      <div className="text-xs bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 rounded p-2 mb-2 overflow-hidden">
                        <span className="font-semibold text-red-900 dark:text-red-200">⚠️ Validation Rejected: </span>
                        <span className="text-red-700 dark:text-red-300">{feedback.user_notes.replace('[AUTO-APPLY REJECTED]', '').trim()}</span>
                      </div>
                    )}

                    {/* Show correction details for table_name/column_name feedback */}
                    {feedback.correction_details && (feedback.feedback_type === 'table_name' || feedback.feedback_type === 'column_name') && (
                      <div className="text-xs bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded p-2 mb-2 overflow-hidden">
                        <span className="font-semibold text-blue-900 dark:text-blue-200">Correction: </span>
                        <span className="text-red-700 dark:text-red-400 line-through">{feedback.correction_details.from || 'N/A'}</span>
                        {' → '}
                        <span className="text-green-700 dark:text-green-400 font-medium">{feedback.correction_details.to || 'N/A'}</span>
                      </div>
                    )}

                    {/* Show user notes if available and no description */}
                    {!feedback.correction_description && feedback.user_notes && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 italic mb-1.5 break-all overflow-hidden">
                        Note: {feedback.user_notes}
                      </p>
                    )}

                    {/* Show placeholder if no meaningful content */}
                    {!feedback.correction_description && !feedback.user_notes && !feedback.correction_details && !feedback.corrected_sql && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 italic mb-1.5">
                        No detailed information provided for this feedback.
                      </p>
                    )}

                    {/* Show SQL comparison if available */}
                    {feedback.corrected_sql && (
                      <div className="mt-2 overflow-hidden">
                        <button
                          onClick={() => toggleSqlExpanded(feedback.id)}
                          className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium transition-colors"
                        >
                          {expandedSql.has(feedback.id) ? (
                            <>
                              <ChevronUp className="w-4 h-4" />
                              Hide SQL
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-4 h-4" />
                              Show SQL
                            </>
                          )}
                        </button>

                        {expandedSql.has(feedback.id) && (
                          <div className="mt-2 space-y-2 max-w-full">
                            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 rounded p-2 overflow-hidden">
                              <p className="text-xs font-semibold text-red-700 dark:text-red-400 mb-1">Original SQL:</p>
                              <div className="max-w-full overflow-hidden">
                                <pre className="text-xs text-gray-800 dark:text-gray-300 whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto w-full">
                                  {feedback.original_sql}
                                </pre>
                              </div>
                            </div>
                            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded p-2 overflow-hidden">
                              <p className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1">Corrected SQL:</p>
                              <div className="max-w-full overflow-hidden">
                                <pre className="text-xs text-gray-800 dark:text-gray-300 whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto w-full">
                                  {feedback.corrected_sql}
                                </pre>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                      {new Date(feedback.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex-shrink-0 flex flex-row sm:flex-col gap-2 w-full sm:w-auto">
                    {!feedback.applied_successfully ? (
                      <>
                        {feedback.corrected_sql ? (
                          <button
                            onClick={() => handleApplyFeedback(feedback.id)}
                            className="flex-1 sm:flex-initial px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors whitespace-nowrap"
                          >
                            Apply
                          </button>
                        ) : (
                          <div className="flex-1 sm:flex-initial px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded text-center whitespace-nowrap">
                            Info Only
                          </div>
                        )}
                        <button
                          onClick={() => handleRejectFeedback(feedback.id)}
                          className="flex-1 sm:flex-initial px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors whitespace-nowrap"
                        >
                          {feedback.corrected_sql ? 'Reject' : 'Dismiss'}
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleRejectFeedback(feedback.id)}
                        className="flex-1 sm:flex-initial px-3 py-1.5 text-xs bg-gray-600 dark:bg-gray-700 text-white rounded hover:bg-gray-700 dark:hover:bg-gray-600 transition-colors whitespace-nowrap"
                        title="Delete this feedback record"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination Controls */}
        {recentFeedback.length > 0 && (
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <button
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>

            <div className="text-sm text-gray-600 dark:text-gray-400">
              Showing {recentFeedback.length} items on page {currentPage + 1}
              {stats && (
                <span className="ml-2 text-gray-500 dark:text-gray-500">
                  ({filterMode === 'pending' ? `${stats.pending} total pending` :
                    filterMode === 'applied' ? `${stats.applied_to_learning} total applied` :
                      `${stats.total_feedback} total`})
                </span>
              )}
            </div>

            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={recentFeedback.length < pageSize}
              className="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
