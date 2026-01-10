import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react';
import { Send, ChevronDown, CheckCircle, AlertCircle, XCircle, Loader2 } from 'lucide-react';
import { multiQueryAPI } from '../services/api';
import type { ValidateMultiDBResponse } from '../types/api';

interface PerTaskModels {
  sql: string | null;
  narratives: string | null;
  planning: string | null;
  correction: string | null;
}

interface QueryInputProps {
  onSubmit: (question: string, rowLimit: number) => void;
  isLoading: boolean;
  selectedModel?: string;
  perTaskModels?: PerTaskModels | null;  // All per-task models from Settings
  connectionIds?: number[];  // For pre-flight validation
}

const ROW_LIMIT_OPTIONS = [
  { value: 10, label: '10 rows' },
  { value: 25, label: '25 rows' },
  { value: 50, label: '50 rows' },
  { value: 100, label: '100 rows' },
  { value: 250, label: '250 rows' },
  { value: 500, label: '500 rows' },
  { value: 1000, label: '1,000 rows' },
  { value: 5000, label: '5,000 rows' },
  { value: 10000, label: '10,000 rows' },
];

export default function QueryInput({ onSubmit, isLoading, selectedModel, perTaskModels, connectionIds }: QueryInputProps) {
  const [question, setQuestion] = useState('');
  const [rowLimit, setRowLimit] = useState(100);
  const [showLimitDropdown, setShowLimitDropdown] = useState(false);
  const [validation, setValidation] = useState<ValidateMultiDBResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const validationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [question]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowLimitDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced pre-flight validation for multi-database queries
  const validateQuery = useCallback(async (q: string, connIds: number[]) => {
    if (!q.trim() || connIds.length < 2) {
      setValidation(null);
      return;
    }

    setValidating(true);
    try {
      const result = await multiQueryAPI.validateQuery({
        question: q,
        connection_ids: connIds,
      });
      setValidation(result);
    } catch (error) {
      console.error('Pre-flight validation error:', error);
      setValidation(null);
    } finally {
      setValidating(false);
    }
  }, []);

  // Trigger validation on question or connection change (debounced)
  useEffect(() => {
    // Clear any pending validation
    if (validationTimeoutRef.current) {
      clearTimeout(validationTimeoutRef.current);
    }

    // Only validate if we have connections and a question
    if (!connectionIds || connectionIds.length < 2 || !question.trim()) {
      setValidation(null);
      return;
    }

    // Debounce validation by 500ms
    validationTimeoutRef.current = setTimeout(() => {
      validateQuery(question, connectionIds);
    }, 500);

    return () => {
      if (validationTimeoutRef.current) {
        clearTimeout(validationTimeoutRef.current);
      }
    };
  }, [question, connectionIds, validateQuery]);

  const handleSubmit = () => {
    if (question.trim() && !isLoading) {
      onSubmit(question.trim(), rowLimit);
      setQuestion('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const selectedOption = ROW_LIMIT_OPTIONS.find(o => o.value === rowLimit) || ROW_LIMIT_OPTIONS[3];

  // Get validation status summary
  const getValidationSummary = () => {
    if (!validation) return null;

    const full = validation.assessments.filter(a => a.capability === 'full').length;
    const partial = validation.assessments.filter(a => a.capability === 'partial').length;
    const cannot = validation.assessments.filter(a => a.capability === 'cannot').length;
    const total = validation.assessments.length;

    return { full, partial, cannot, total };
  };

  const summary = getValidationSummary();

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 transition-colors">
      <div className="max-w-4xl mx-auto">
        {/* Pre-flight validation indicator */}
        {connectionIds && connectionIds.length >= 2 && (
          <div className="mb-3">
            {validating ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Checking database compatibility...</span>
              </div>
            ) : validation && summary ? (
              <div className="flex items-center gap-3 text-sm">
                {/* Full support */}
                {summary.full > 0 && (
                  <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span>{summary.full} can answer</span>
                  </div>
                )}
                {/* Partial support */}
                {summary.partial > 0 && (
                  <div className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
                    <AlertCircle className="w-4 h-4" />
                    <span>{summary.partial} partial</span>
                  </div>
                )}
                {/* Cannot answer */}
                {summary.cannot > 0 && (
                  <div className="flex items-center gap-1 text-red-600 dark:text-red-400">
                    <XCircle className="w-4 h-4" />
                    <span>{summary.cannot} cannot answer</span>
                  </div>
                )}
                {/* Warnings */}
                {validation.warnings.length > 0 && (
                  <div className="text-xs text-amber-600 dark:text-amber-400 ml-2" title={validation.warnings.join('\n')}>
                    ⚠️ {validation.warnings.length} warning{validation.warnings.length !== 1 ? 's' : ''}
                  </div>
                )}
                {/* Overall status message */}
                {!validation.can_execute_any && (
                  <div className="text-xs text-red-600 dark:text-red-500 font-medium ml-2">
                    Query cannot be executed on any selected database
                  </div>
                )}
              </div>
            ) : question.trim() ? (
              <div className="text-xs text-gray-400 dark:text-gray-500">
                Type more to check database compatibility...
              </div>
            ) : null}
          </div>
        )}

        <div className="flex items-end space-x-3">
          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your database..."
              disabled={isLoading}
              rows={1}
              className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 disabled:bg-gray-50 dark:disabled:bg-gray-800 disabled:text-gray-500 transition-colors"
              style={{ maxHeight: '200px' }}
            />

            {/* Character count */}
            {question.length > 0 && (
              <div className="absolute bottom-2 right-2 text-xs text-gray-400 dark:text-gray-500">
                {question.length}/500
              </div>
            )}
          </div>

          {/* Row Limit Selector */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowLimitDropdown(!showLimitDropdown)}
              disabled={isLoading}
              className="px-3 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-400 dark:disabled:text-gray-600 disabled:cursor-not-allowed transition-colors flex items-center space-x-1 text-sm text-gray-700 dark:text-gray-300"
              title="Maximum rows to return"
            >
              <span>{selectedOption.label}</span>
              <ChevronDown className="w-4 h-4" />
            </button>

            {showLimitDropdown && (
              <div className="absolute bottom-full mb-1 right-0 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 z-50 min-w-[120px]">
                {ROW_LIMIT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      setRowLimit(option.value);
                      setShowLimitDropdown(false);
                    }}
                    className={`w-full px-3 py-2 text-left text-sm transition-colors ${option.value === rowLimit
                        ? 'bg-primary-50 dark:bg-primary-900/40 text-primary-700 dark:text-primary-400 font-medium'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={!question.trim() || isLoading}
            className="px-6 py-3 bg-primary-600 dark:bg-primary-700 text-white rounded-lg hover:bg-primary-700 dark:hover:bg-primary-600 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:text-gray-500 dark:disabled:text-gray-500 disabled:cursor-not-allowed transition-colors flex items-center space-x-2 shadow-sm"
            title="Send (Ctrl+Enter)"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Thinking...</span>
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                <span>Send</span>
              </>
            )}
          </button>
        </div>

        {/* Hints */}
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Press Ctrl+Enter to send</span>
          <div className="flex items-center gap-1 flex-wrap justify-end">
            {(() => {
              // Build list of per-task overrides (only those different from main model)
              const overrides: { label: string; model: string }[] = [];
              if (perTaskModels?.sql && perTaskModels.sql !== selectedModel) {
                overrides.push({ label: 'SQL', model: perTaskModels.sql });
              }
              if (perTaskModels?.narratives && perTaskModels.narratives !== selectedModel) {
                overrides.push({ label: 'Narratives', model: perTaskModels.narratives });
              }
              if (perTaskModels?.planning && perTaskModels.planning !== selectedModel) {
                overrides.push({ label: 'Planning', model: perTaskModels.planning });
              }
              if (perTaskModels?.correction && perTaskModels.correction !== selectedModel) {
                overrides.push({ label: 'Correction', model: perTaskModels.correction });
              }

              const hasOverrides = overrides.length > 0;
              const label = hasOverrides ? 'Models:' : 'Model:';

              return (
                <>
                  <span>{label} <strong>{selectedModel}</strong></span>
                  {overrides.map((o) => (
                    <span key={o.label} className="text-blue-600 dark:text-blue-400">
                      | {o.label} → <strong>{o.model}</strong>
                    </span>
                  ))}
                </>
              );
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}
