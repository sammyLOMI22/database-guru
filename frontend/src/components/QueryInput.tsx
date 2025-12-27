import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, ChevronDown } from 'lucide-react';

interface QueryInputProps {
  onSubmit: (question: string, rowLimit: number) => void;
  isLoading: boolean;
  selectedModel?: string;
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

export default function QueryInput({ onSubmit, isLoading, selectedModel }: QueryInputProps) {
  const [question, setQuestion] = useState('');
  const [rowLimit, setRowLimit] = useState(100);
  const [showLimitDropdown, setShowLimitDropdown] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="max-w-4xl mx-auto">
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
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none disabled:bg-gray-50 disabled:text-gray-500"
              style={{ maxHeight: '200px' }}
            />

            {/* Character count */}
            {question.length > 0 && (
              <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                {question.length}/500
              </div>
            )}
          </div>

          {/* Row Limit Selector */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowLimitDropdown(!showLimitDropdown)}
              disabled={isLoading}
              className="px-3 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors flex items-center space-x-1 text-sm text-gray-700"
              title="Maximum rows to return"
            >
              <span>{selectedOption.label}</span>
              <ChevronDown className="w-4 h-4" />
            </button>

            {showLimitDropdown && (
              <div className="absolute bottom-full mb-1 right-0 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-[120px]">
                {ROW_LIMIT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      setRowLimit(option.value);
                      setShowLimitDropdown(false);
                    }}
                    className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-100 ${
                      option.value === rowLimit ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-700'
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
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            title="Send (Ctrl+Enter)"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
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
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
          <span>Press Ctrl+Enter to send</span>
          {selectedModel && (
            <span>Using model: <strong>{selectedModel}</strong></span>
          )}
        </div>
      </div>
    </div>
  );
}
