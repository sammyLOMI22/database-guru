import React, { useState } from 'react';
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
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Provide Feedback
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Feedback Type */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              What type of feedback are you providing?
            </label>
            <select
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="sql_correction">SQL Correction</option>
              <option value="column_name">Column Name Issue</option>
              <option value="table_name">Table Name Issue</option>
              <option value="result_issue">Result Issue</option>
            </select>
            <p className="text-sm text-gray-500 mt-1">
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
            <label className="block font-semibold text-gray-900 mb-2">
              What's wrong? / What should change? *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="E.g., Should use 'category_name' instead of 'category' in the WHERE clause"
            />
          </div>

          {/* Additional Notes */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              Additional Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 min-h-[80px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Any additional context or information..."
            />
          </div>

          {/* Confidence Slider */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              How confident are you in this correction?
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={confidence}
                onChange={(e) => setConfidence(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-lg font-semibold text-gray-900 w-16 text-right">
                {Math.round(confidence * 100)}%
              </span>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Not sure</span>
              <span>Very confident</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
