import React, { useEffect, useState } from 'react';
import { feedbackAPI, FeedbackStatsResponse, FeedbackResponse } from '../services/api';
import { CheckCircle, Clock, TrendingUp } from 'lucide-react';

export const FeedbackStats: React.FC = () => {
  const [stats, setStats] = useState<FeedbackStatsResponse | null>(null);
  const [recentFeedback, setRecentFeedback] = useState<FeedbackResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, recentData] = await Promise.all([
        feedbackAPI.getStats(),
        feedbackAPI.getRecentFeedback(5, 0),
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
      await feedbackAPI.applyFeedback(feedbackId, true);
      // Reload stats after applying
      await loadStats();
    } catch (err: any) {
      alert(`Failed to apply feedback: ${err.message}`);
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
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Recent Feedback</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {recentFeedback.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No feedback submitted yet
            </div>
          ) : (
            recentFeedback.map((feedback) => (
              <div key={feedback.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        feedback.feedback_type === 'sql_correction' ? 'bg-blue-100 text-blue-800' :
                        feedback.feedback_type === 'column_name' ? 'bg-green-100 text-green-800' :
                        feedback.feedback_type === 'table_name' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {feedback.feedback_type.replace('_', ' ').toUpperCase()}
                      </span>
                      {feedback.applied_successfully && (
                        <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                          ✓ Applied
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        Confidence: {Math.round(feedback.user_confidence * 100)}%
                      </span>
                    </div>

                    {feedback.correction_description && (
                      <p className="text-sm text-gray-700 mb-2">
                        {feedback.correction_description}
                      </p>
                    )}

                    <p className="text-xs text-gray-500">
                      {new Date(feedback.created_at).toLocaleString()}
                    </p>
                  </div>

                  {!feedback.applied_successfully && (
                    <button
                      onClick={() => handleApplyFeedback(feedback.id)}
                      className="ml-4 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                    >
                      Apply to Learning
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
