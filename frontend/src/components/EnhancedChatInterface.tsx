import { useState, useRef, useEffect } from 'react';
import Message from './Message';
import QueryInput from './QueryInput';
import ChatSessionSelector from './ChatSessionSelector';
import Sidebar from './Sidebar';
import MultiDatabaseResults from './MultiDatabaseResults';
import { useMultiQuery } from '../hooks/useMultiQuery';
import { useModels } from '../hooks/useModels';
import type { ChatSession, MultiDatabaseQueryResponse } from '../types/api';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  multiQueryResponse?: MultiDatabaseQueryResponse;
}

export default function EnhancedChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: "👋 Hello! I'm Database Guru with multi-database support! Ask me about one or multiple databases at once!",
    },
  ]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [showSessionSelector, setShowSessionSelector] = useState(true);
  const [showSidebar, setShowSidebar] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { loading, executeQuery } = useMultiQuery();
  const { data: modelsData } = useModels();

  // Set default model when models load
  useEffect(() => {
    if (modelsData && !selectedModel) {
      setSelectedModel(modelsData.default_model);
    }
  }, [modelsData, selectedModel]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (question: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: question,
    };
    setMessages((prev) => [...prev, userMessage]);

    // Submit query
    try {
      const response = await executeQuery(question, currentSession, {
        model: selectedModel || undefined,
      });

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.database_results.length > 1
          ? `I queried ${response.database_results.length} databases and found ${response.total_rows} total rows:`
          : response.database_results[0]?.success
          ? `Here's what I found in ${response.database_results[0].connection_name}:`
          : 'Query executed.',
        multiQueryResponse: response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      // Add error message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error.response?.data?.detail || error.message}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <div className="flex h-full">
      {/* Left Sidebar - Connections/Schema/History */}
      {showSidebar && (
        <Sidebar
          onClose={() => setShowSidebar(false)}
          onSelectQuery={(question) => handleSubmit(question)}
        />
      )}

      {/* Session Selector Sidebar */}
      {showSessionSelector && (
        <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0">
          <ChatSessionSelector
            currentSession={currentSession}
            onSessionChange={setCurrentSession}
          />
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-6 py-3 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {/* Toggle connections sidebar button */}
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-1 hover:bg-gray-100 rounded"
                title="Toggle database connections"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
              </button>

              {/* Toggle sessions sidebar button */}
              <button
                onClick={() => setShowSessionSelector(!showSessionSelector)}
                className="p-1 hover:bg-gray-100 rounded"
                title="Toggle sessions panel"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </button>

              {/* Current session info */}
              <div>
                {currentSession ? (
                  <div>
                    <p className="text-sm font-medium text-gray-900">{currentSession.name}</p>
                    <p className="text-xs text-gray-500">
                      {currentSession.connections.length} database{currentSession.connections.length !== 1 ? 's' : ''} connected
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium text-gray-900">Default Mode</p>
                    <p className="text-xs text-gray-500">Single database queries</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Model selector */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-600">Model:</span>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {modelsData?.models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                      {model === modelsData.default_model && ' (default)'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Query count */}
              <div className="text-xs text-gray-500">
                {messages.length - 1} {messages.length === 2 ? 'query' : 'queries'}
              </div>
            </div>
          </div>

          {/* Connected databases pills */}
          {currentSession && currentSession.connections.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {currentSession.connections.map((conn) => (
                <span
                  key={conn.id}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-700"
                >
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-1.5"></span>
                  {conn.name}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.map((message) => (
            <div key={message.id} className="flex items-start space-x-3">
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.type === 'user'
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {message.type === 'user' ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                ) : (
                  <span className="text-lg">🧙‍♂️</span>
                )}
              </div>

              {/* Message content */}
              <div className="flex-1 min-w-0">
                <div className="px-4 py-3 bg-white border border-gray-200 rounded-lg">
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{message.content}</p>
                </div>

                {/* Multi-database results */}
                {message.multiQueryResponse && (
                  <div className="mt-3">
                    <MultiDatabaseResults
                      results={message.multiQueryResponse.database_results}
                      totalRows={message.multiQueryResponse.total_rows}
                      totalExecutionTime={message.multiQueryResponse.total_execution_time_ms}
                      question={message.multiQueryResponse.question}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-gray-600 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <div className="flex-1">
                <div className="px-4 py-3 bg-white border border-gray-200 rounded-lg">
                  <p className="text-sm text-gray-600">
                    {currentSession && currentSession.connections.length > 1
                      ? `Querying ${currentSession.connections.length} databases...`
                      : 'Thinking...'}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <QueryInput
          onSubmit={handleSubmit}
          isLoading={loading}
          selectedModel={selectedModel}
        />
      </div>
    </div>
  );
}
