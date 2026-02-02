/**
 * Lineage Chat Component - Phase 12.5
 *
 * Natural language Q&A interface for lineage, schema, and pattern questions.
 * Supports multi-turn conversations with context.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Loader2,
  MessageSquare,
  Sparkles,
  ChevronRight,
  Database,
  GitBranch,
  AlertTriangle,
  LayoutGrid,
  Lightbulb,
  HelpCircle,
} from 'lucide-react';
import lineageAPI from '../../services/lineageApi';
import type { LineageAnswer, QuestionType } from '../../types/lineage';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  answer?: LineageAnswer;
}

interface LineageChatProps {
  connectionId: number;
  connectionName?: string;
  onTableClick?: (tableName: string) => void;
}

const QUESTION_TYPE_ICONS: Record<QuestionType, React.ReactNode> = {
  lineage: <GitBranch className="w-4 h-4" />,
  impact: <AlertTriangle className="w-4 h-4" />,
  pattern: <LayoutGrid className="w-4 h-4" />,
  schema: <Database className="w-4 h-4" />,
  recommendation: <Lightbulb className="w-4 h-4" />,
  general: <HelpCircle className="w-4 h-4" />,
};

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  lineage: 'Lineage',
  impact: 'Impact',
  pattern: 'Pattern',
  schema: 'Schema',
  recommendation: 'Recommendation',
  general: 'General',
};

const QUESTION_TYPE_COLORS: Record<QuestionType, string> = {
  lineage: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  impact: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  pattern: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  schema: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  recommendation: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  general: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
};

const SUGGESTED_QUESTIONS = [
  "What are the most used tables?",
  "Show me the schema overview",
  "Are there any bottlenecks?",
  "What tables are available?",
  "How can I optimize my queries?",
];

export const LineageChat: React.FC<LineageChatProps> = ({
  connectionId,
  connectionName,
  onTableClick,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = async (question: string) => {
    if (!question.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: question.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const answer = await lineageAPI.askLineageQuestion(
        question.trim(),
        connectionId,
        sessionId
      );

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: answer.answer,
        timestamp: new Date(),
        answer,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to get answer:', error);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: 'Sorry, I encountered an error while processing your question. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(input);
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    handleSubmit(question);
  };

  const handleFollowUp = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  const renderTableLinks = (tables: string[]) => {
    if (!tables || tables.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-1 mt-2">
        {tables.slice(0, 5).map((table) => (
          <button
            key={table}
            onClick={() => onTableClick?.(table)}
            className="px-2 py-0.5 text-xs rounded bg-gray-100 dark:bg-gray-700
                       text-gray-600 dark:text-gray-300 hover:bg-gray-200
                       dark:hover:bg-gray-600 transition-colors"
          >
            {table}
          </button>
        ))}
        {tables.length > 5 && (
          <span className="px-2 py-0.5 text-xs text-gray-500">
            +{tables.length - 5} more
          </span>
        )}
      </div>
    );
  };

  const renderMessage = (message: Message) => {
    const isUser = message.type === 'user';

    return (
      <div
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div
          className={`max-w-[85%] rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
          }`}
        >
          {/* Question type badge for assistant messages */}
          {!isUser && message.answer && (
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${
                  QUESTION_TYPE_COLORS[message.answer.question_type as QuestionType]
                }`}
              >
                {QUESTION_TYPE_ICONS[message.answer.question_type as QuestionType]}
                {QUESTION_TYPE_LABELS[message.answer.question_type as QuestionType]}
              </span>
              {message.answer.llm_used && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                  <Sparkles className="w-3 h-3" />
                  AI Enhanced
                </span>
              )}
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {Math.round(message.answer.confidence * 100)}% confidence
              </span>
            </div>
          )}

          {/* Message content */}
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>

          {/* Related tables */}
          {!isUser && message.answer?.related_tables && (
            renderTableLinks(message.answer.related_tables)
          )}

          {/* Follow-up suggestions */}
          {!isUser && message.answer?.follow_up_suggestions && message.answer.follow_up_suggestions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Follow-up questions:
              </p>
              <div className="flex flex-wrap gap-2">
                {message.answer.follow_up_suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleFollowUp(suggestion)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md
                               bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600
                               text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600
                               transition-colors"
                  >
                    <ChevronRight className="w-3 h-3" />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Timestamp */}
          <p
            className={`text-xs mt-2 ${
              isUser ? 'text-indigo-200' : 'text-gray-400 dark:text-gray-500'
            }`}
          >
            {message.timestamp.toLocaleTimeString()}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <MessageSquare className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        <h3 className="font-medium text-gray-900 dark:text-gray-100">
          Lineage Chat
        </h3>
        {connectionName && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            - {connectionName}
          </span>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 min-h-[300px]">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <Sparkles className="w-12 h-12 text-indigo-300 dark:text-indigo-600 mx-auto mb-4" />
            <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              Ask about your data
            </h4>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Ask questions about lineage, impact, patterns, schema, or get recommendations.
            </p>

            {/* Suggested questions */}
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestedQuestion(question)}
                  className="px-3 py-1.5 text-sm rounded-full border border-gray-200
                             dark:border-gray-700 text-gray-600 dark:text-gray-300
                             hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(renderMessage)}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about lineage, impact, patterns..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={() => handleSubmit(input)}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white
                       hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span className="sr-only">Send</span>
          </button>
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
          Try: "What feeds into orders?" or "What breaks if I rename customer_id?"
        </p>
      </div>
    </div>
  );
};

export default LineageChat;
