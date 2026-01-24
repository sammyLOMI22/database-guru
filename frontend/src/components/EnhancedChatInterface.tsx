import { useState, useRef, useEffect, useCallback } from 'react';
import QueryInput from './QueryInput';
import ChatSessionSelector from './ChatSessionSelector';
import Sidebar from './Sidebar';
import Message from './Message';
import ConversationContextPanel from './ConversationContextPanel';
import SchemaGlance from './SchemaGlance';
import { useMultiQuery } from '../hooks/useMultiQuery';
import { useModels } from '../hooks/useModels';
import { connectionsAPI, settingsAPI } from '../services/api';
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
  // Reasoning module flags
  enable_intent_classification: boolean;
  enable_dynamic_examples: boolean;
  enable_semantic_validation: boolean;
  enable_prompt_optimization: boolean;
}

interface EnhancedChatInterfaceProps {
  onViewLineage?: (sql: string) => void;
  onLastSqlChange?: (sql: string) => void;
}

export default function EnhancedChatInterface({ onViewLineage, onLastSqlChange }: EnhancedChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: "👋 Hello! I'm your Database Guru! Ask me to help you fetch some data!",
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

  // Fetch per-task model settings
  const fetchPerTaskModels = useCallback(async () => {
    try {
      const settings = await settingsAPI.getSettings();
      setPerTaskModels({
        model_sql_generation: settings.model_sql_generation,
        model_narratives: settings.model_narratives,
        model_query_planning: settings.model_query_planning,
        model_error_correction: settings.model_error_correction,
        enable_intent_classification: settings.enable_intent_classification,
        enable_dynamic_examples: settings.enable_dynamic_examples,
        enable_semantic_validation: settings.enable_semantic_validation,
        enable_prompt_optimization: settings.enable_prompt_optimization,
      });
    } catch (error) {
      console.error('Failed to fetch per-task model settings:', error);
    }
  }, []);

  useEffect(() => {
    // Initial fetch on mount
    fetchPerTaskModels();

    // Listener for immediate updates from SettingsPanel
    window.addEventListener('settingsUpdated', fetchPerTaskModels);

    return () => {
      window.removeEventListener('settingsUpdated', fetchPerTaskModels);
    };
  }, [fetchPerTaskModels]);

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

      // Track last executed SQL for ER diagram query path overlay
      const firstSuccessful = response.database_results.find((r) => r.success && r.sql);
      if (firstSuccessful?.sql) {
        onLastSqlChange?.(firstSuccessful.sql);
      }
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
    <div className={`flex h-full w-full ${!showSidebar && !showSessionSelector ? 'justify-center' : ''}`}>
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
        <div className="w-[450px] glass-panel border-r border-white/10 overflow-y-auto flex-shrink-0 transition-all duration-500 animate-slideInLeft relative z-30">
          <ChatSessionSelector
            currentSession={currentSession}
            onSessionChange={setCurrentSession}
          />
        </div>
      )}

      {/* Main Chat Area */}
      <div className={
        !showSidebar && !showSessionSelector
          ? 'flex-none mx-auto max-w-[1600px] bg-transparent relative z-10 flex flex-col min-w-0'
          : 'flex-1 flex flex-col min-w-0 bg-transparent relative z-10'
      }>
        {/* Header - Sub Header for Chat Info */}
        {/* Floating Header Card */}
        <div className="px-4 pt-4 pb-2 transition-all duration-300">
          <div className="max-w-[1600px] mx-auto">
            <div className="px-6 py-4 glass-card rounded-[2rem] shadow-2xl border-white/20 dark:border-white/10 backdrop-blur-3xl relative z-40">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {/* Toggle connections sidebar button */}
                  <button
                    onClick={() => setShowSidebar(!showSidebar)}
                    className="p-2 glass-panel rounded-xl hover:scale-110 active:scale-95 transition-all text-gray-600 dark:text-gray-400 group"
                    title="Toggle database connections"
                  >
                    <svg className="w-5 h-5 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                    </svg>
                  </button>

                  {/* Toggle sessions sidebar button */}
                  <button
                    onClick={() => setShowSessionSelector(!showSessionSelector)}
                    className="p-2 glass-panel rounded-xl hover:scale-110 active:scale-95 transition-all text-gray-600 dark:text-gray-400 group"
                    title="Toggle sessions panel"
                  >
                    <svg className="w-5 h-5 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enableNarratives ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
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
                <div className="mt-3 flex flex-wrap gap-2">
                  {currentSession.connections.map((conn) => (
                    <span
                      key={conn.id}
                      className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-widest bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 transition-all border border-blue-200/50 dark:border-blue-400/10"
                    >
                      <span className="w-1.5 h-1.5 bg-blue-500 dark:bg-blue-400 rounded-full mr-2 animate-pulse"></span>
                      {conn.name}
                    </span>
                  ))}
                </div>
              )}

              {/* Schema at a Glance - show for session connections OR active connection in default mode */}
              {currentSession && currentSession.connections.length > 0 ? (
                <div className="mt-3">
                  <SchemaGlance
                    connectionIds={currentSession.connections.map(c => c.id)}
                    connectionNames={Object.fromEntries(currentSession.connections.map(c => [c.id, c.name]))}
                  />
                </div>
              ) : !currentSession && activeConnection ? (
                <div className="mt-3">
                  <SchemaGlance
                    connectionIds={[activeConnection.id]}
                    connectionNames={{ [activeConnection.id]: activeConnection.name }}
                  />
                </div>
              ) : null}

              {/* Context awareness indicator */}
              {hasContext && (
                <div className="mt-3 flex items-center justify-between text-[11px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-900/20 px-4 py-2 rounded-xl border border-blue-100/50 dark:border-blue-800/30 backdrop-blur-md transition-all">
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-2 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <span>Conversational memory active</span>
                  </div>
                  <button
                    onClick={() => setShowContextPanel(!showContextPanel)}
                    className="px-3 py-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-lg transition-all border border-blue-500/10"
                  >
                    {showContextPanel ? 'Hide' : 'Show'} details
                  </button>
                </div>
              )}
            </div>
          </div>
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
            <div key={message.id} className="flex items-start gap-4 animate-fadeIn">
              <Message
                type={message.type}
                content={message.content}
                multiQueryResponse={message.multiQueryResponse}
                onViewLineage={onViewLineage}
              />
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-start gap-4 animate-fadeIn">
              <div className="w-10 h-10 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center shadow-lg transition-transform duration-300 hover:scale-110">
                <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <div className="flex-1">
                <div className="px-6 py-4 glass-card rounded-2xl shadow-2xl border-white/10">
                  <div className="flex items-center space-x-3">
                    <p className="text-sm font-bold text-blue-600 dark:text-blue-400 tracking-tight">
                      {currentSession && currentSession.connections.length > 1
                        ? `CONSULTING ${currentSession.connections.length} DATABASES...`
                        : 'SNIFFING OUT DATA...'}
                    </p>
                    <div className="flex space-x-1">
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                    </div>
                  </div>
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
            intentGuard: perTaskModels.enable_intent_classification,
            dynamicExamples: perTaskModels.enable_dynamic_examples,
            semanticCheck: perTaskModels.enable_semantic_validation,
            promptTuning: perTaskModels.enable_prompt_optimization,
          } : null}
          connectionIds={currentSession?.connections.map(c => c.id)}
        />
      </div>
    </div>
  );
}
