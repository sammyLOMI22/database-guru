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
    <div className="fixed bottom-0 left-0 right-0 z-40 px-4 pb-8 pt-4 transition-all duration-300">
      <div className="max-w-4xl mx-auto animate-fadeIn group">
        {/* Pre-flight validation indicator - Glass Panel */}
        {connectionIds && connectionIds.length >= 2 && (
          <div className="mb-3 px-4 py-2 glass-panel rounded-xl shadow-lg border-white/10 animate-slideInLeft">
            {validating ? (
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-600 dark:text-blue-400">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Synchronizing database schemas...</span>
              </div>
            ) : validation && summary ? (
              <div className="flex items-center gap-4 text-[11px] font-bold tracking-tight">
                {/* Full support */}
                {summary.full > 0 && (
                  <div className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>{summary.full} READY</span>
                  </div>
                )}
                {/* Partial support */}
                {summary.partial > 0 && (
                  <div className="flex items-center gap-1.5 text-amber-500 dark:text-amber-400">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{summary.partial} PARTIAL</span>
                  </div>
                )}
                {/* Cannot answer */}
                {summary.cannot > 0 && (
                  <div className="flex items-center gap-1.5 text-red-500 dark:text-red-400">
                    <XCircle className="w-3.5 h-3.5" />
                    <span>{summary.cannot} INCOMPATIBLE</span>
                  </div>
                )}

                <div className="h-3 w-[1px] bg-gray-300 dark:bg-gray-700 mx-1"></div>

                {/* Overall status message */}
                {!validation.can_execute_any ? (
                  <div className="text-red-600 dark:text-red-500 font-black animate-pulse">
                    EXECUTION BLOCKED
                  </div>
                ) : (
                  <div className="text-blue-600/70 dark:text-blue-400/70">
                    MULTI-DB OPTIMIZED
                  </div>
                )}
              </div>
            ) : question.trim() ? (
              <div className="text-[10px] uppercase tracking-widest text-gray-400 dark:text-gray-500 font-bold">
                Analyzing query intent...
              </div>
            ) : null}
          </div>
        )}

        {/* Input Area - Premium Glass Card */}
        <div className="glass-card rounded-[2.5rem] p-2 pr-4 pl-6 shadow-2xl flex items-end space-x-3 border-white/20 dark:border-white/10 group-focus-within:border-blue-500/50 group-focus-within:shadow-blue-500/10 transition-all duration-500">
          {/* Textarea */}
          <div className="flex-1 relative py-2">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Query the guru..."
              disabled={isLoading}
              rows={1}
              className="w-full px-0 py-2 border-none bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-0 resize-none font-medium text-lg transition-all"
              style={{ maxHeight: '200px' }}
            />

            {/* Character count */}
            {question.length > 0 && (
              <div className="absolute -top-1 right-0 text-[10px] font-bold text-blue-500/50 animate-fadeIn">
                {question.length} / 500
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2 pb-1.5">
            {/* Row Limit Selector */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setShowLimitDropdown(!showLimitDropdown)}
                disabled={isLoading}
                className="h-10 px-4 rounded-2xl glass-panel hover:bg-white/10 dark:hover:bg-gray-800/10 transition-all flex items-center space-x-2 text-xs font-black uppercase tracking-wider text-gray-600 dark:text-gray-400 border-white/10"
              >
                <span>{selectedOption.value} ROWS</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-300 ${showLimitDropdown ? 'rotate-180' : ''}`} />
              </button>

              {showLimitDropdown && (
                <div className="absolute bottom-full mb-4 right-0 glass-card rounded-2xl p-1 shadow-2xl z-50 min-w-[140px] animate-scaleUp">
                  {ROW_LIMIT_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setRowLimit(option.value);
                        setShowLimitDropdown(false);
                      }}
                      className={`w-full px-4 py-2 text-left text-xs font-bold rounded-xl transition-all ${option.value === rowLimit
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-white/10 dark:hover:bg-gray-800/20'
                        }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Send button - Pulsing Gradient */}
            <button
              onClick={handleSubmit}
              disabled={!question.trim() || isLoading}
              className={`
                h-10 px-6 rounded-2xl font-black text-xs uppercase tracking-widest transition-all duration-500 flex items-center space-x-2 shadow-xl
                ${!question.trim() || isLoading
                  ? 'bg-gray-200 dark:bg-gray-800 text-gray-400 dark:text-gray-600 opacity-50 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:scale-105 active:scale-95 shadow-blue-500/20 hover:shadow-blue-500/40'
                }
              `}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>THINKING...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>SEND</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Footer Hints */}
        <div className="mt-3 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4 opacity-50">
            <div className="flex items-center space-x-1.5">
              <span className="px-1.5 py-0.5 rounded border border-gray-400 dark:border-gray-600 text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase">Cmd</span>
              <span className="text-gray-400 dark:text-gray-600 text-[10px] font-bold">+</span>
              <span className="px-1.5 py-0.5 rounded border border-gray-400 dark:border-gray-600 text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase">Enter</span>
            </div>
            <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">to execute</span>
          </div>

          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest">
            {perTaskModels && (
              <span className="text-blue-600/60 dark:text-blue-400/60">
                AI ENGINE: <strong className="text-gray-900 dark:text-gray-200">{selectedModel}</strong>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
