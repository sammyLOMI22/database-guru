import { useState, useEffect } from 'react';
import { MessageSquare, ChevronRight, RefreshCw, Trash2, Info, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
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
      <div className="glass-panel rounded-xl p-4 border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg glass-card flex items-center justify-center text-gray-400">
            <MessageSquare className="w-4 h-4" />
          </div>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Select or create a chat session to enable conversational memory
          </p>
        </div>
      </div>
    );
  }

  if (loading && !context) {
    return (
      <div className="glass-panel rounded-xl p-4 border-white/10">
        <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
          <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
          <span className="text-xs font-medium">Loading conversation context...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-red-500/10 via-transparent to-rose-500/5 border-red-500/20">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center text-red-500">
            <AlertCircle className="w-4 h-4" />
          </div>
          <span className="text-xs font-bold text-red-600 dark:text-red-400">{error}</span>
        </div>
        <button
          onClick={loadContext}
          className="px-4 py-2 glass-panel rounded-lg text-[10px] font-black uppercase tracking-widest text-red-600 dark:text-red-400 hover:scale-105 active:scale-95 transition-all"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!context || !context.has_context) {
    return (
      <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-blue-500/10 via-transparent to-cyan-500/5 border-blue-500/20">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-500 flex-shrink-0">
            <Info className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <h3 className="text-xs font-black uppercase tracking-widest text-blue-600 dark:text-blue-400">
              No conversation history
            </h3>
            <p className="mt-1 text-[10px] font-medium text-blue-700/70 dark:text-blue-300/70">
              Start asking questions! I'll remember your queries to help with follow-ups like "filter that" or "sort by price".
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-xl border-white/10 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center flex-1 text-left gap-2"
        >
          <ChevronRight
            className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          />
          <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-500">
            <MessageSquare className="w-3 h-3" />
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">
            Context ({context.window_size})
          </span>
        </button>

        <div className="flex items-center gap-1">
          <button
            onClick={loadContext}
            disabled={loading}
            className="w-7 h-7 rounded-lg glass-card flex items-center justify-center text-gray-400 hover:text-blue-500 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
            title="Refresh context"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleClearContext}
            disabled={loading}
            className="w-7 h-7 rounded-lg glass-card flex items-center justify-center text-gray-400 hover:text-red-500 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
            title="Clear context"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Context Messages */}
      {isExpanded && (
        <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
          {context.messages.map((msg, index) => (
            <div
              key={index}
              className="glass-card rounded-lg p-3 border-l-2 border-blue-500/50"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <span className="text-blue-500 font-bold mr-1">{index + 1}.</span>
                    {msg.question}
                  </div>
                  <div className="text-[10px] font-mono text-gray-500 dark:text-gray-400 glass-panel rounded-lg px-2 py-1.5 overflow-x-auto border-white/10">
                    {msg.sql}
                  </div>
                </div>
                <div className="flex-shrink-0">
                  {msg.success ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-bold uppercase tracking-widest bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                      <CheckCircle className="w-3 h-3" />
                      OK
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-bold uppercase tracking-widest bg-red-500/20 text-red-600 dark:text-red-400">
                      <XCircle className="w-3 h-3" />
                      Err
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}

          <div className="pt-3 border-t border-white/10">
            <p className="text-[10px] font-medium text-gray-400 flex items-center gap-2">
              <Info className="w-3 h-3" />
              I'll use this context for follow-up questions like "filter that" or "sort by price"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
