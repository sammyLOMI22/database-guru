import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface QueryInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  selectedModel?: string;
}

export default function QueryInput({ onSubmit, isLoading, selectedModel }: QueryInputProps) {
  const [question, setQuestion] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [question]);

  const handleSubmit = () => {
    if (question.trim() && !isLoading) {
      onSubmit(question.trim());
      setQuestion('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

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
