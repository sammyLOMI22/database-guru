import React, { useState } from 'react';
import { MessageSquarePlus, X, AlertCircle, ChevronRight } from 'lucide-react';
import { SQLEditor } from './SQLEditor';

interface FeedbackModalProps {
  queryId: number;
  originalSQL: string;
  onSubmit: (feedback: FeedbackData) => Promise<void>;
  onClose: () => void;
}

export interface FeedbackData {
  query_id: number;
  feedback_type: string;
  corrected_sql?: string;
  correction_description?: string;
  correction_details?: any;
  user_notes?: string;
  user_confidence: number;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  queryId,
  originalSQL,
  onSubmit,
  onClose
}) => {
  const [feedbackType, setFeedbackType] = useState('sql_correction');
  const [correctedSQL, setCorrectedSQL] = useState(originalSQL);
  const [description, setDescription] = useState('');
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState(1.0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    // Validation
    if (!description.trim()) {
      setError('Please provide a description of what needs to be corrected');
      return;
    }

    if (feedbackType === 'sql_correction' && correctedSQL === originalSQL) {
      setError('Corrected SQL is the same as original SQL');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await onSubmit({
        query_id: queryId,
        feedback_type: feedbackType,
        corrected_sql: feedbackType === 'sql_correction' ? correctedSQL : undefined,
        correction_description: description,
        user_notes: notes || undefined,
        user_confidence: confidence
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="glass-card rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border-white/20 bg-gradient-to-br from-blue-500/5 via-transparent to-indigo-500/5">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-blue-500">
                <MessageSquarePlus className="w-5 h-5" />
              </div>
              <h2 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white">
                Provide Feedback
              </h2>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg glass-panel flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:scale-105 active:scale-95 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 glass-card rounded-xl p-4 bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/5 border-red-500/30 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center text-red-500">
                  <AlertCircle className="w-4 h-4" />
                </div>
                <p className="text-xs font-bold text-red-600 dark:text-red-400">{error}</p>
              </div>
            </div>
          )}

          {/* Feedback Type */}
          <div className="mb-6">
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400 mb-2">
              Feedback Type
            </label>
            <select
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
              className="w-full glass-panel rounded-xl px-4 py-3 text-sm font-medium text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 border-white/10 bg-transparent appearance-none cursor-pointer"
            >
              <option value="sql_correction" className="bg-gray-800 text-white">SQL Correction</option>
              <option value="column_name" className="bg-gray-800 text-white">Column Name Issue</option>
              <option value="table_name" className="bg-gray-800 text-white">Table Name Issue</option>
              <option value="result_issue" className="bg-gray-800 text-white">Result Issue</option>
            </select>
            <p className="text-[10px] font-medium text-gray-400 mt-2 flex items-center gap-1">
              <ChevronRight className="w-3 h-3" />
              {feedbackType === 'sql_correction' && 'Provide a corrected version of the SQL query'}
              {feedbackType === 'column_name' && 'Report an incorrect column name'}
              {feedbackType === 'table_name' && 'Report an incorrect table name'}
              {feedbackType === 'result_issue' && 'Report an issue with the query results'}
            </p>
          </div>

          {/* Original SQL (read-only) */}
          <div className="mb-6">
            <SQLEditor
              initialSQL={originalSQL}
              readOnly={true}
              label="Original SQL"
            />
          </div>

          {/* Corrected SQL (if correction type) */}
          {feedbackType === 'sql_correction' && (
            <div className="mb-6">
              <SQLEditor
                initialSQL={correctedSQL}
                onChange={setCorrectedSQL}
                label="Corrected SQL *"
              />
            </div>
          )}

          {/* Description */}
          <div className="mb-6">
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400 mb-2">
              What's Wrong? <span className="text-red-500">*</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                if (error && e.target.value.trim()) {
                  setError(null);
                }
              }}
              className={`w-full glass-panel rounded-xl px-4 py-3 min-h-[100px] text-sm font-medium text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                !description.trim() && error ? 'border-red-500/50 bg-red-500/5' : 'border-white/10'
              }`}
              placeholder="E.g., Should use 'category_name' instead of 'category' in the WHERE clause"
              required
            />
            {!description.trim() && (
              <p className="text-[10px] font-bold text-red-500 mt-2 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Required field
              </p>
            )}
          </div>

          {/* Additional Notes */}
          <div className="mb-6">
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400 mb-2">
              Additional Notes
              <span className="text-gray-400 font-medium normal-case tracking-normal ml-2">(optional)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full glass-panel rounded-xl px-4 py-3 min-h-[80px] text-sm font-medium text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 border-white/10 transition-all"
              placeholder="Any additional context or information..."
            />
          </div>

          {/* Confidence Slider */}
          <div className="mb-6">
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400 mb-3">
              Confidence Level
            </label>
            <div className="glass-panel rounded-xl p-4 border-white/10">
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={confidence}
                  onChange={(e) => setConfidence(parseFloat(e.target.value))}
                  className="flex-1 h-2 rounded-full appearance-none bg-gradient-to-r from-gray-300 to-blue-500 cursor-pointer"
                />
                <span className={`text-xl font-black w-16 text-right ${
                  confidence >= 0.8 ? 'text-emerald-500' :
                  confidence >= 0.5 ? 'text-blue-500' :
                  'text-amber-500'
                }`}>
                  {Math.round(confidence * 100)}%
                </span>
              </div>
              <div className="flex justify-between text-[9px] font-bold uppercase tracking-widest text-gray-400 mt-2">
                <span>Not sure</span>
                <span>Very confident</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-6 border-t border-white/10">
            <button
              onClick={onClose}
              className="px-6 py-2.5 glass-panel rounded-xl text-xs font-black uppercase tracking-widest text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="px-6 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
