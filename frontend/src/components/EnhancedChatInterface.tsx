import { useState, useRef, useEffect } from 'react';
import QueryInput from './QueryInput';
import ChatSessionSelector from './ChatSessionSelector';
import Sidebar from './Sidebar';
import MultiDatabaseResults from './MultiDatabaseResults';
import ConversationContextPanel from './ConversationContextPanel';
import SchemaGlance from './SchemaGlance';
import { useMultiQuery } from '../hooks/useMultiQuery';
import { useModels } from '../hooks/useModels';
import { connectionsAPI } from '../services/api';
import type { ChatSession, MultiDatabaseQueryResponse, DatabaseConnection } from '../types/api';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  multiQueryResponse?: MultiDatabaseQueryResponse;
}

interface PerTaskModelSettings {
  model_sql_generation: string | null;
  model_narratives: string | null;
  model_query_planning: string | null;
  model_error_correction: string | null;
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
  const [showContextPanel, setShowContextPanel] = useState(true);
  const [hasContext, setHasContext] = useState(false);
  const [forceSchemaRefresh, setForceSchemaRefresh] = useState(false);
  const [perTaskModels, setPerTaskModels] = useState<PerTaskModelSettings | null>(null);
  const [activeConnection, setActiveConnection] = useState<DatabaseConnection | null>(null);
  const [enableNarratives, setEnableNarratives] = useState<boolean>(() => {
    // Load from localStorage, default to true
    const stored = localStorage.getItem('enableNarratives');
    return stored !== null ? JSON.parse(stored) : true;
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { loading, executeQuery } = useMultiQuery();
  const { data: modelsData } = useModels();

  // Set default model when models load
  useEffect(() => {
    if (modelsData && !selectedModel) {
      setSelectedModel(modelsData.default_model);
    }
  }, [modelsData, selectedModel]);

  // Fetch active connection for default mode (no session selected)
  const fetchActiveConnection = async () => {
    try {
      const data = await connectionsAPI.listConnections();
      const active = data.connections.find((c: DatabaseConnection) => c.is_active);
      setActiveConnection(active || null);
    } catch (error) {
      console.error('Failed to fetch connections:', error);
    }
  };

  useEffect(() => {
    fetchActiveConnection();
  }, []);

  // Fetch per-task model settings on mount
  useEffect(() => {
    const fetchPerTaskModels = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/settings/');
        if (response.ok) {
          const settings = await response.json();
          setPerTaskModels({
            model_sql_generation: settings.model_sql_generation,
            model_narratives: settings.model_narratives,
            model_query_planning: settings.model_query_planning,
            model_error_correction: settings.model_error_correction,
          });
        }
      } catch (error) {
        console.error('Failed to fetch per-task model settings:', error);
      }
    };
    fetchPerTaskModels();
  }, []);

  // Save narratives preference to localStorage
  useEffect(() => {
    localStorage.setItem('enableNarratives', JSON.stringify(enableNarratives));
  }, [enableNarratives]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (question: string, rowLimit: number = 100) => {
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
        force_schema_refresh: forceSchemaRefresh,
        enable_narratives: enableNarratives,
        row_limit: rowLimit,
      });

      // Reset force refresh after query
      setForceSchemaRefresh(false);

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
      console.log('DEBUG: Response from multi-query:', response);
      console.log('DEBUG: Combined analysis:', response.combined_analysis);
      console.log('DEBUG: DB results[0].result_analysis:', response.database_results[0]?.result_analysis);
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
          onConnectionSelect={() => fetchActiveConnection()}
        />
      )}

      {/* Session Selector Sidebar */}
      {showSessionSelector && (
        <div className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto flex-shrink-0 transition-colors">
          <ChatSessionSelector
            currentSession={currentSession}
            onSessionChange={setCurrentSession}
          />
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {/* Toggle connections sidebar button */}
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                title="Toggle database connections"
              >
                <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
              </button>

              {/* Toggle sessions sidebar button */}
              <button
                onClick={() => setShowSessionSelector(!showSessionSelector)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                title="Toggle sessions panel"
              >
                <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </button>

              {/* Current session info */}
              <div>
                {currentSession ? (
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{currentSession.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {currentSession.connections.length} database{currentSession.connections.length !== 1 ? 's' : ''} connected
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">Default Mode</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Single database queries</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Model selector */}
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-600 dark:text-gray-400">Model:</span>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {modelsData?.models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                      {model === modelsData.default_model && ' (default)'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Force schema refresh checkbox */}
              <div className="flex items-center space-x-2 px-3 py-1 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 transition-colors">
                <input
                  type="checkbox"
                  id="force-schema-refresh"
                  checked={forceSchemaRefresh}
                  onChange={(e) => setForceSchemaRefresh(e.target.checked)}
                  className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500 bg-white dark:bg-gray-800"
                />
                <label
                  htmlFor="force-schema-refresh"
                  className="text-xs text-gray-700 dark:text-gray-300 cursor-pointer select-none"
                  title="Force re-introspection of database schema on next query (bypasses 30-min cache)"
                >
                  Force Schema Refresh
                </label>
              </div>

              {/* Narratives Toggle */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <button
                  onClick={() => setEnableNarratives(!enableNarratives)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enableNarratives ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  title={enableNarratives ? 'Disable AI Narratives' : 'Enable AI Narratives'}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${enableNarratives ? 'translate-x-6' : 'translate-x-1'
                      }`}
                  />
                </button>
                <span className="text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap">
                  {enableNarratives ? '✨ Narratives' : '📊 Data Only'}
                </span>
              </label>

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

          {/* Schema at a Glance - show for session connections OR active connection in default mode */}
          {currentSession && currentSession.connections.length > 0 ? (
            <div className="mt-2">
              <SchemaGlance
                connectionIds={currentSession.connections.map(c => c.id)}
                connectionNames={Object.fromEntries(currentSession.connections.map(c => [c.id, c.name]))}
              />
            </div>
          ) : !currentSession && activeConnection ? (
            <div className="mt-2">
              <SchemaGlance
                connectionIds={[activeConnection.id]}
                connectionNames={{ [activeConnection.id]: activeConnection.name }}
              />
            </div>
          ) : null}

          {/* Context awareness indicator */}
          {hasContext && (
            <div className="mt-2 flex items-center justify-between text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded border border-blue-100 dark:border-blue-800 transition-colors">
              <div className="flex items-center">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <span>Conversational memory active</span>
              </div>
              <button
                onClick={() => setShowContextPanel(!showContextPanel)}
                className="ml-2 px-2 py-0.5 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800 rounded transition-colors"
              >
                {showContextPanel ? 'Hide' : 'Show'} context
              </button>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {/* Conversation Context Panel */}
          {currentSession && showContextPanel && (
            <div className="mb-4">
              <ConversationContextPanel
                sessionId={currentSession?.id || null}
                onContextUpdate={setHasContext}
              />
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className="flex items-start space-x-3">
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.type === 'user'
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
                <div className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm transition-colors">
                  <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{message.content}</p>
                </div>

                {/* Multi-database results */}
                {message.multiQueryResponse && (
                  <div className="mt-3">
                    <MultiDatabaseResults
                      results={message.multiQueryResponse.database_results}
                      totalRows={message.multiQueryResponse.total_rows}
                      totalExecutionTime={message.multiQueryResponse.total_execution_time_ms}
                      question={message.multiQueryResponse.question}
                      cacheInfo={message.multiQueryResponse.cache_info}
                      combinedAnalysis={message.multiQueryResponse.combined_analysis}
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
                <div className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
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
          perTaskModels={perTaskModels ? {
            sql: perTaskModels.model_sql_generation,
            narratives: perTaskModels.model_narratives,
            planning: perTaskModels.model_query_planning,
            correction: perTaskModels.model_error_correction,
          } : null}
          connectionIds={currentSession?.connections.map(c => c.id)}
        />
      </div>
    </div>
  );
}
