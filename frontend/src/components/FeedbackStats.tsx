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
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">Error: {error}</div>
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
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Feedback Dashboard</h2>
        <p className="text-gray-600 mt-1">User corrections and continuous learning insights</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Feedback */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Feedback</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.total_feedback}</p>
            </div>
            <TrendingUp className="w-10 h-10 text-blue-500 opacity-50" />
          </div>
        </div>

        {/* Applied to Learning */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Applied to Learning</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.applied_to_learning}</p>
            </div>
            <CheckCircle className="w-10 h-10 text-green-500 opacity-50" />
          </div>
        </div>

        {/* Pending */}
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Pending Review</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.pending}</p>
            </div>
            <Clock className="w-10 h-10 text-yellow-500 opacity-50" />
          </div>
        </div>
      </div>

      {/* Feedback by Type */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Feedback by Type</h3>
        <div className="space-y-3">
          {feedbackTypes.map(({ key, label, color }) => {
            const count = stats.by_type[key] || 0;
            const percentage = stats.total_feedback > 0
              ? (count / stats.total_feedback) * 100
              : 0;

            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">{label}</span>
                  <span className="text-sm text-gray-600">{count}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`bg-${color}-500 h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Feedback */}
      <div className="bg-white rounded-lg shadow overflow-hidden max-w-full">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Recent Feedback
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3 text-sm">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="feedbackFilter"
                    value="all"
                    checked={filterMode === 'all'}
                    onChange={() => {
                      setFilterMode('all');
                      setCurrentPage(0);
                    }}
                    className="cursor-pointer"
                  />
                  <span className="text-gray-700">All</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="feedbackFilter"
                    value="pending"
                    checked={filterMode === 'pending'}
                    onChange={() => {
                      setFilterMode('pending');
                      setCurrentPage(0);
                    }}
                    className="cursor-pointer"
                  />
                  <span className="text-gray-700">Pending</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="feedbackFilter"
                    value="applied"
                    checked={filterMode === 'applied'}
                    onChange={() => {
                      setFilterMode('applied');
                      setCurrentPage(0);
                    }}
                    className="cursor-pointer"
                  />
                  <span className="text-gray-700">Applied</span>
                </label>
              </div>
              <div className="text-sm text-gray-600">
                Page {currentPage + 1}
              </div>
            </div>
          </div>
        </div>
        <div className="divide-y divide-gray-200 overflow-x-hidden">
          {recentFeedback.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              {filterMode === 'pending' ? 'No pending feedback' :
               filterMode === 'applied' ? 'No applied feedback yet' :
               'No feedback submitted yet'}
            </div>
          ) : (
            recentFeedback.map((feedback) => (
              <div key={feedback.id} className="p-4 hover:bg-gray-50 transition-colors overflow-x-hidden">
                <div className="flex flex-col sm:flex-row items-start gap-3">
                  <div className="flex-1 min-w-0 overflow-hidden" style={{maxWidth: "calc(100% - 100px)"}}>

                    <div className="flex flex-wrap items-center gap-1.5 mb-2">
                      <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                        feedback.feedback_type === 'sql_correction' ? 'bg-blue-100 text-blue-800' :
                        feedback.feedback_type === 'column_name' ? 'bg-green-100 text-green-800' :
                        feedback.feedback_type === 'table_name' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {feedback.feedback_type.replace('_', ' ').toUpperCase()}
                      </span>
                      {feedback.applied_successfully && (
                        <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-green-100 text-green-800">
                          ✓ Applied
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        {Math.round(feedback.user_confidence * 100)}% conf
                      </span>
                    </div>

                    {feedback.correction_description && (
                      <p className="text-xs text-gray-700 mb-1.5 break-all overflow-hidden">
                        {feedback.correction_description}
                      </p>
                    )}

                    {/* Show correction details for table_name/column_name feedback */}
                    {feedback.correction_details && (feedback.feedback_type === 'table_name' || feedback.feedback_type === 'column_name') && (
                      <div className="text-xs bg-blue-50 border border-blue-200 rounded p-2 mb-2 overflow-hidden">
                        <span className="font-semibold text-blue-900">Correction: </span>
                        <span className="text-red-700 line-through">{feedback.correction_details.from || 'N/A'}</span>
                        {' → '}
                        <span className="text-green-700 font-medium">{feedback.correction_details.to || 'N/A'}</span>
                      </div>
                    )}

                    {/* Show user notes if available and no description */}
                    {!feedback.correction_description && feedback.user_notes && (
                      <p className="text-xs text-gray-600 italic mb-1.5 break-all overflow-hidden">
                        Note: {feedback.user_notes}
                      </p>
                    )}

                    {/* Show placeholder if no meaningful content */}
                    {!feedback.correction_description && !feedback.user_notes && !feedback.correction_details && !feedback.corrected_sql && (
                      <p className="text-xs text-gray-500 italic mb-1.5">
                        No detailed information provided for this feedback.
                      </p>
                    )}

                    {/* Show SQL comparison if available */}
                    {feedback.corrected_sql && (
                      <div className="mt-2 overflow-hidden">
                        <button
                          onClick={() => toggleSqlExpanded(feedback.id)}
                          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
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
                            <div className="bg-red-50 border border-red-200 rounded p-2 overflow-hidden">
                              <p className="text-xs font-semibold text-red-700 mb-1">Original SQL:</p>
                              <div className="max-w-full overflow-hidden">
                                <pre className="text-xs text-gray-800 whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto w-full">
{feedback.original_sql}
                                </pre>
                              </div>
                            </div>
                            <div className="bg-green-50 border border-green-200 rounded p-2 overflow-hidden">
                              <p className="text-xs font-semibold text-green-700 mb-1">Corrected SQL:</p>
                              <div className="max-w-full overflow-hidden">
                                <pre className="text-xs text-gray-800 whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto w-full">
{feedback.corrected_sql}
                                </pre>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-gray-500 mt-2">
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
                          <div className="flex-1 sm:flex-initial px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded text-center whitespace-nowrap">
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
                        className="flex-1 sm:flex-initial px-3 py-1.5 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors whitespace-nowrap"
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
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <button
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>

            <div className="text-sm text-gray-600">
              Showing {recentFeedback.length} items on page {currentPage + 1}
              {stats && (
                <span className="ml-2 text-gray-500">
                  ({filterMode === 'pending' ? `${stats.pending} total pending` :
                    filterMode === 'applied' ? `${stats.applied_to_learning} total applied` :
                    `${stats.total_feedback} total`})
                </span>
              )}
            </div>

            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={recentFeedback.length < pageSize}
              className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
