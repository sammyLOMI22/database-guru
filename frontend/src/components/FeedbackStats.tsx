import React, { useEffect, useState } from 'react';
import { feedbackAPI, FeedbackStatsResponse, FeedbackResponse } from '../services/api';
import { CheckCircle, Clock, TrendingUp, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react';

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
      return { tier: 1, label: 'Tier 1', color: 'from-emerald-500/20 to-green-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30', emoji: '🚀', description: 'Auto-applied (STRICT)' };
    } else if (confidence >= 0.80) {
      return { tier: 2, label: 'Tier 2', color: 'from-blue-500/20 to-cyan-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30', emoji: '⚡', description: 'Auto-applied (MODERATE)' };
    } else if (confidence >= 0.70) {
      return { tier: 3, label: 'Tier 3', color: 'from-amber-500/20 to-yellow-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30', emoji: '📋', description: 'Queued for batch' };
    } else {
      return { tier: 0, label: 'Manual', color: 'from-gray-500/20 to-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/30', emoji: '👁️', description: 'Manual review' };
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
      <div className="animate-pulse space-y-6">
        <div className="h-16 glass-panel rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 glass-panel rounded-2xl" />
          ))}
        </div>
        <div className="h-48 glass-panel rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="glass-panel rounded-2xl p-8 max-w-md mx-auto">
          <div className="text-red-500 mb-4 text-sm font-bold uppercase tracking-widest">Error: {error}</div>
          <button
            onClick={() => loadStats()}
            className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-indigo-500/20"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const feedbackTypes = [
    { key: 'sql_correction', label: 'SQL Corrections', gradient: 'from-blue-500 to-cyan-500' },
    { key: 'column_name', label: 'Column Names', gradient: 'from-emerald-500 to-green-500' },
    { key: 'table_name', label: 'Table Names', gradient: 'from-amber-500 to-yellow-500' },
    { key: 'result_issue', label: 'Result Issues', gradient: 'from-red-500 to-rose-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl glass-card flex items-center justify-center text-indigo-500 shadow-xl shadow-indigo-500/10">
              <MessageSquare className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-2xl font-black uppercase tracking-tight text-gray-900 dark:text-white">Feedback Dashboard</h2>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                User corrections and continuous learning
              </p>
            </div>
          </div>
          <label className="flex items-center gap-3 cursor-pointer glass-card px-4 py-2.5 rounded-xl transition-all hover:scale-105">
            <Clock className={`w-4 h-4 ${autoRefresh ? 'text-indigo-500 animate-pulse' : 'text-gray-400'}`} />
            <span className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">Auto-Refresh</span>
            <input
              type="checkbox"
              className="sr-only"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <div className={`w-10 h-5 rounded-full transition-all relative ${autoRefresh ? 'bg-gradient-to-r from-indigo-500 to-purple-500' : 'bg-gray-300 dark:bg-gray-600'}`}>
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${autoRefresh ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
          </label>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Feedback */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-blue-500/10 via-transparent to-blue-500/5 hover:border-blue-500/30 transition-all duration-300 group">
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Total Feedback</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">{stats.total_feedback}</p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform">
              <TrendingUp className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[11px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            All submitted corrections
          </p>
        </div>

        {/* Applied to Learning */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-emerald-500/10 via-transparent to-emerald-500/5 hover:border-emerald-500/30 transition-all duration-300 group">
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Applied to Learning</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">{stats.applied_to_learning}</p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-emerald-500 group-hover:scale-110 transition-transform">
              <CheckCircle className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[11px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            Learned from feedback
          </p>
        </div>

        {/* Pending Review */}
        <div className="glass-card rounded-2xl p-5 border-white/10 bg-gradient-to-br from-amber-500/10 via-transparent to-amber-500/5 hover:border-amber-500/30 transition-all duration-300 group">
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Pending Review</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-black text-gray-900 dark:text-white">{stats.pending}</p>
            <div className="w-12 h-12 rounded-xl glass-panel flex items-center justify-center text-amber-500 group-hover:scale-110 transition-transform">
              <Clock className="w-6 h-6" />
            </div>
          </div>
          <p className="text-[11px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
            Awaiting approval
          </p>
        </div>
      </div>

      {/* Tier Distribution */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-purple-500" />
          Auto-Approval Tiers (Phase 1)
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="glass-card rounded-xl p-4 bg-gradient-to-br from-emerald-500/10 via-transparent to-green-500/5 border-emerald-500/20 hover:border-emerald-500/40 transition-all">
            <div className="text-[11px] font-black uppercase tracking-widest text-emerald-600 dark:text-emerald-400 mb-2">🚀 Tier 1 (≥90%)</div>
            <div className="text-3xl font-black text-emerald-600 dark:text-emerald-400">
              {recentFeedback.filter(f => f.user_confidence >= 0.90).length}
            </div>
            <div className="text-[11px] font-bold text-emerald-500/70 mt-2 uppercase tracking-widest">Auto-apply (STRICT)</div>
          </div>
          <div className="glass-card rounded-xl p-4 bg-gradient-to-br from-blue-500/10 via-transparent to-cyan-500/5 border-blue-500/20 hover:border-blue-500/40 transition-all">
            <div className="text-[11px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 mb-2">⚡ Tier 2 (≥80%)</div>
            <div className="text-3xl font-black text-blue-600 dark:text-blue-400">
              {recentFeedback.filter(f => f.user_confidence >= 0.80 && f.user_confidence < 0.90).length}
            </div>
            <div className="text-[11px] font-bold text-blue-500/70 mt-2 uppercase tracking-widest">Auto-apply (MODERATE)</div>
          </div>
          <div className="glass-card rounded-xl p-4 bg-gradient-to-br from-amber-500/10 via-transparent to-yellow-500/5 border-amber-500/20 hover:border-amber-500/40 transition-all">
            <div className="text-[11px] font-black uppercase tracking-widest text-amber-600 dark:text-amber-400 mb-2">📋 Tier 3 (≥70%)</div>
            <div className="text-3xl font-black text-amber-600 dark:text-amber-400">
              {recentFeedback.filter(f => f.user_confidence >= 0.70 && f.user_confidence < 0.80).length}
            </div>
            <div className="text-[11px] font-bold text-amber-500/70 mt-2 uppercase tracking-widest">Batch queue</div>
          </div>
          <div className="glass-card rounded-xl p-4 bg-gradient-to-br from-gray-500/10 via-transparent to-gray-500/5 border-gray-500/20 hover:border-gray-500/40 transition-all">
            <div className="text-[11px] font-black uppercase tracking-widest text-gray-600 dark:text-gray-400 mb-2">👁 Manual (&lt;70%)</div>
            <div className="text-3xl font-black text-gray-600 dark:text-gray-300">
              {recentFeedback.filter(f => f.user_confidence < 0.70).length}
            </div>
            <div className="text-[11px] font-bold text-gray-500/70 mt-2 uppercase tracking-widest">Manual review</div>
          </div>
        </div>
      </div>

      {/* Feedback by Type */}
      <div className="glass-panel rounded-2xl p-6 border-white/10">
        <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white mb-5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
          Feedback by Type
        </h3>
        <div className="space-y-4">
          {feedbackTypes.map(({ key, label, gradient }) => {
            const count = stats.by_type[key] || 0;
            const percentage = stats.total_feedback > 0
              ? (count / stats.total_feedback) * 100
              : 0;

            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">{label}</span>
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">{count} ({percentage.toFixed(0)}%)</span>
                </div>
                <div className="w-full bg-black/5 dark:bg-white/5 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${gradient}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Feedback */}
      <div className="glass-panel rounded-2xl overflow-hidden border-white/10">
        <div className="px-6 py-5 border-b border-white/10 bg-black/5 dark:bg-white/5">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Recent Feedback
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex p-1 glass-panel rounded-xl border-white/10 bg-black/5 dark:bg-white/5">
                {[
                  { key: 'all', label: 'All' },
                  { key: 'pending', label: 'Pending' },
                  { key: 'applied', label: 'Applied' },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => { setFilterMode(key as typeof filterMode); setCurrentPage(0); }}
                    className={`px-4 py-2 text-[11px] font-black uppercase tracking-widest rounded-lg transition-all duration-300 ${
                      filterMode === key
                        ? key === 'pending'
                          ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white shadow-lg shadow-amber-500/20'
                          : key === 'applied'
                          ? 'bg-gradient-to-r from-emerald-500 to-green-500 text-white shadow-lg shadow-emerald-500/20'
                          : 'bg-gradient-to-r from-gray-700 to-gray-800 text-white shadow-lg'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/10'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <span className="text-[11px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest glass-panel px-3 py-1.5 rounded-lg">
                Page {currentPage + 1}
              </span>
            </div>
          </div>
        </div>
        <div className="divide-y divide-white/10 overflow-x-hidden">
          {recentFeedback.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-16 h-16 rounded-2xl glass-card flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
                {filterMode === 'pending' ? 'No pending feedback' :
                  filterMode === 'applied' ? 'No applied feedback yet' :
                    'No feedback submitted yet'}
              </p>
            </div>
          ) : (
            recentFeedback.map((feedback) => (
              <div key={feedback.id} className="p-5 hover:bg-white/5 dark:hover:bg-white/5 transition-colors overflow-x-hidden">
                <div className="flex flex-col sm:flex-row items-start gap-4">
                  <div className="flex-1 min-w-0 overflow-hidden" style={{ maxWidth: "calc(100% - 100px)" }}>

                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className={`px-2.5 py-1 text-[11px] font-black uppercase tracking-widest rounded-lg bg-gradient-to-r border ${
                        feedback.feedback_type === 'sql_correction' ? 'from-blue-500/20 to-cyan-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30' :
                        feedback.feedback_type === 'column_name' ? 'from-emerald-500/20 to-green-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' :
                        feedback.feedback_type === 'table_name' ? 'from-amber-500/20 to-yellow-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30' :
                        'from-red-500/20 to-rose-500/20 text-red-600 dark:text-red-400 border-red-500/30'
                      }`}>
                        {feedback.feedback_type.replace('_', ' ')}
                      </span>
                      {(() => {
                        const tierInfo = getTierInfo(feedback.user_confidence);
                        return (
                          <span className={`px-2.5 py-1 text-[11px] font-black uppercase tracking-widest rounded-lg bg-gradient-to-r border ${tierInfo.color}`} title={tierInfo.description}>
                            {tierInfo.emoji} {tierInfo.label}
                          </span>
                        );
                      })()}
                      {feedback.applied_successfully && (
                        <span className="px-2.5 py-1 text-[11px] font-black uppercase tracking-widest rounded-lg bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                          ✓ Applied
                        </span>
                      )}
                      {feedback.learned_correction_id && (
                        <span className="px-2.5 py-1 text-[11px] font-black uppercase tracking-widest rounded-lg bg-gradient-to-r from-purple-500/20 to-indigo-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30" title="Learned Correction ID">
                          🧠 LC-{feedback.learned_correction_id}
                        </span>
                      )}
                      <span className="text-[11px] font-bold text-gray-500 uppercase tracking-widest">
                        {Math.round(feedback.user_confidence * 100)}% conf
                      </span>
                    </div>

                    {feedback.correction_description && (
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 break-all overflow-hidden">
                        {feedback.correction_description}
                      </p>
                    )}

                    {/* Show validation rejection message if present */}
                    {feedback.user_notes && feedback.user_notes.includes('[AUTO-APPLY REJECTED]') && (
                      <div className="text-xs glass-panel bg-gradient-to-r from-red-500/10 to-rose-500/10 border border-red-500/30 rounded-xl p-3 mb-3 overflow-hidden">
                        <span className="font-black text-red-600 dark:text-red-400">⚠️ Validation Rejected: </span>
                        <span className="font-medium text-red-700 dark:text-red-300">{feedback.user_notes.replace('[AUTO-APPLY REJECTED]', '').trim()}</span>
                      </div>
                    )}

                    {/* Show correction details for table_name/column_name feedback */}
                    {feedback.correction_details && (feedback.feedback_type === 'table_name' || feedback.feedback_type === 'column_name') && (
                      <div className="text-xs glass-panel bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/30 rounded-xl p-3 mb-3 overflow-hidden">
                        <span className="font-black text-blue-600 dark:text-blue-400">Correction: </span>
                        <span className="text-red-600 dark:text-red-400 line-through font-medium">{feedback.correction_details.from || 'N/A'}</span>
                        {' → '}
                        <span className="text-emerald-600 dark:text-emerald-400 font-black">{feedback.correction_details.to || 'N/A'}</span>
                      </div>
                    )}

                    {/* Show user notes if available and no description */}
                    {!feedback.correction_description && feedback.user_notes && (
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 italic mb-2 break-all overflow-hidden">
                        Note: {feedback.user_notes}
                      </p>
                    )}

                    {/* Show placeholder if no meaningful content */}
                    {!feedback.correction_description && !feedback.user_notes && !feedback.correction_details && !feedback.corrected_sql && (
                      <p className="text-xs font-medium text-gray-400 dark:text-gray-500 italic mb-2">
                        No detailed information provided for this feedback.
                      </p>
                    )}

                    {/* Show SQL comparison if available */}
                    {feedback.corrected_sql && (
                      <div className="mt-3 overflow-hidden">
                        <button
                          onClick={() => toggleSqlExpanded(feedback.id)}
                          className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 transition-colors glass-panel px-3 py-1.5 rounded-lg"
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
                          <div className="mt-3 space-y-3 max-w-full animate-fadeIn">
                            <div className="glass-panel bg-gradient-to-r from-red-500/10 to-rose-500/10 border border-red-500/30 rounded-xl p-4 overflow-hidden">
                              <p className="text-[11px] font-black uppercase tracking-widest text-red-600 dark:text-red-400 mb-2">Original SQL:</p>
                              <div className="max-w-full overflow-hidden">
                                <pre className="text-xs text-gray-800 dark:text-gray-300 whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto w-full">
                                  {feedback.original_sql}
                                </pre>
                              </div>
                            </div>
                            <div className="glass-panel bg-gradient-to-r from-emerald-500/10 to-green-500/10 border border-emerald-500/30 rounded-xl p-4 overflow-hidden">
                              <p className="text-[11px] font-black uppercase tracking-widest text-emerald-600 dark:text-emerald-400 mb-2">Corrected SQL:</p>
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

                    <p className="text-[11px] font-bold text-gray-400 mt-3 uppercase tracking-widest">
                      {new Date(feedback.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex-shrink-0 flex flex-row sm:flex-col gap-2 w-full sm:w-auto">
                    {!feedback.applied_successfully ? (
                      <>
                        {feedback.corrected_sql ? (
                          <button
                            onClick={() => handleApplyFeedback(feedback.id)}
                            className="flex-1 sm:flex-initial px-4 py-2 text-[11px] font-black uppercase tracking-widest bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl hover:scale-105 active:scale-95 transition-all shadow-lg shadow-indigo-500/20"
                          >
                            Apply
                          </button>
                        ) : (
                          <div className="flex-1 sm:flex-initial px-4 py-2 text-[11px] font-black uppercase tracking-widest glass-panel text-gray-500 dark:text-gray-400 rounded-xl text-center">
                            Info Only
                          </div>
                        )}
                        <button
                          onClick={() => handleRejectFeedback(feedback.id)}
                          className="flex-1 sm:flex-initial px-4 py-2 text-[11px] font-black uppercase tracking-widest bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-xl hover:scale-105 active:scale-95 transition-all shadow-lg shadow-red-500/20"
                        >
                          {feedback.corrected_sql ? 'Reject' : 'Dismiss'}
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleRejectFeedback(feedback.id)}
                        className="flex-1 sm:flex-initial px-4 py-2 text-[11px] font-black uppercase tracking-widest glass-panel text-gray-600 dark:text-gray-400 rounded-xl hover:scale-105 active:scale-95 transition-all hover:bg-gray-500/10"
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
          <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between bg-black/5 dark:bg-white/5">
            <button
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="px-5 py-2.5 text-[11px] font-black uppercase tracking-widest glass-card rounded-xl text-gray-700 dark:text-gray-300 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all"
            >
              Previous
            </button>

            <div className="text-[11px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
              Showing {recentFeedback.length} items on page {currentPage + 1}
              {stats && (
                <span className="ml-2 text-gray-400">
                  ({filterMode === 'pending' ? `${stats.pending} total pending` :
                    filterMode === 'applied' ? `${stats.applied_to_learning} total applied` :
                      `${stats.total_feedback} total`})
                </span>
              )}
            </div>

            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={recentFeedback.length < pageSize}
              className="px-5 py-2.5 text-[11px] font-black uppercase tracking-widest glass-card rounded-xl text-gray-700 dark:text-gray-300 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
