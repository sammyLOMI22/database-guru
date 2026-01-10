import { useState, useEffect } from 'react';
import { chatAPI } from '../services/api';
import type { ConversationContext } from '../types/api';

interface ConversationContextPanelProps {
  sessionId: string | null;
  onContextUpdate?: (hasContext: boolean) => void;
}

export default function ConversationContextPanel({
  sessionId,
  onContextUpdate,
}: ConversationContextPanelProps) {
  const [context, setContext] = useState<ConversationContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  // Fetch context when session changes
  useEffect(() => {
    if (sessionId) {
      loadContext();
    } else {
      setContext(null);
      if (onContextUpdate) {
        onContextUpdate(false);
      }
    }
  }, [sessionId]);

  const loadContext = async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await chatAPI.getContext(sessionId);
      setContext(response.context);

      if (onContextUpdate) {
        onContextUpdate(response.context.has_context);
      }
    } catch (err: any) {
      console.error('Failed to load conversation context:', err);
      setError(err.response?.data?.detail || 'Failed to load context');
      setContext(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClearContext = async () => {
    if (!sessionId) return;

    if (!confirm('Are you sure you want to clear the conversation context? This will start fresh.')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await chatAPI.clearContext(sessionId);
      setContext(null);

      if (onContextUpdate) {
        onContextUpdate(false);
      }

      // Reload to confirm
      await loadContext();
    } catch (err: any) {
      console.error('Failed to clear context:', err);
      setError(err.response?.data?.detail || 'Failed to clear context');
    } finally {
      setLoading(false);
    }
  };

  if (!sessionId) {
    return (
      <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 text-sm text-gray-500 dark:text-gray-400 border border-gray-100 dark:border-gray-800">
        💬 Select or create a chat session to enable conversational memory
      </div>
    );
  }

  if (loading && !context) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center text-gray-500">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
          Loading conversation context...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-900/50 p-4">
        <div className="text-red-700 dark:text-red-400 text-sm">
          ⚠️ {error}
        </div>
        <button
          onClick={loadContext}
          className="mt-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!context || !context.has_context) {
    return (
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-900/50 p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300">
              No conversation history yet
            </h3>
            <p className="mt-1 text-sm text-blue-700 dark:text-blue-400">
              Start asking questions! I'll remember your queries to help with follow-ups like "filter that" or "sort by price".
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center flex-1 text-left"
        >
          <svg
            className={`h-4 w-4 text-gray-500 transition-transform ${isExpanded ? 'transform rotate-90' : ''}`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
          <span className="ml-2 text-sm font-medium text-gray-900 dark:text-white">
            💬 Conversation Context ({context.window_size})
          </span>
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={loadContext}
            disabled={loading}
            className="p-1 text-gray-400 hover:text-gray-600 rounded disabled:opacity-50"
            title="Refresh context"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>

          <button
            onClick={handleClearContext}
            disabled={loading}
            className="p-1 text-gray-400 hover:text-red-600 rounded disabled:opacity-50"
            title="Clear context (fresh start)"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Context Messages */}
      {isExpanded && (
        <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
          {context.messages.map((msg, index) => (
            <div
              key={index}
              className="text-sm border-l-2 border-blue-300 dark:border-blue-700 pl-3 py-2 bg-gray-50 dark:bg-gray-900/50 rounded-r"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-gray-700 dark:text-gray-300 font-medium mb-1">
                    {index + 1}. {msg.question}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 font-mono bg-gray-100 dark:bg-gray-900 px-2 py-1 rounded mb-1 overflow-x-auto border border-gray-200 dark:border-gray-800">
                    {msg.sql}
                  </div>
                </div>
                <div className="ml-2">
                  {msg.success ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      ✓ Success
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      ✗ Error
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}

          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 italic">
              💡 I'll use this context when you ask follow-up questions like "filter that" or "sort by price"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
