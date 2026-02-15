import { useState, useRef, useEffect } from 'react';
import Message from './Message';
import QueryInput from './QueryInput';
import SchemaGlance from './SchemaGlance';
import { useQuerySubmit } from '../hooks/useQuerySubmit';
import { useModels } from '../hooks/useModels';
import { connectionsAPI } from '../services/api';
import { parseChartIntent, getChartIntentHint } from '../utils/chartIntentParser';
import type { QueryResponse, DatabaseConnection } from '../types/api';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  queryResponse?: QueryResponse;
}

interface PerTaskModelSettings {
  model_sql_generation: string | null;
  model_narratives: string | null;
  model_query_planning: string | null;
  model_error_correction: string | null;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: "👋 Hello! I'm Database Guru, your AI SQL assistant. Ask me anything about your database in plain English!",
    },
  ]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [perTaskModels, setPerTaskModels] = useState<PerTaskModelSettings | null>(null);
  const [activeConnection, setActiveConnection] = useState<DatabaseConnection | null>(null);
  const [enableNarratives, setEnableNarratives] = useState<boolean>(() => {
    // Load from localStorage, default to true
    const stored = localStorage.getItem('enableNarratives');
    return stored !== null ? JSON.parse(stored) : true;
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryMutation = useQuerySubmit();
  const { data: modelsData } = useModels();

  // Set default model when models load
  useEffect(() => {
    if (modelsData && !selectedModel) {
      setSelectedModel(modelsData.default_model);
    }
  }, [modelsData, selectedModel]);

  // Fetch active connection on mount
  useEffect(() => {
    const fetchActiveConnection = async () => {
      try {
        const data = await connectionsAPI.listConnections();
        const active = data.connections.find((c: DatabaseConnection) => c.is_active);
        setActiveConnection(active || null);
      } catch (error) {
        console.error('Failed to fetch connections:', error);
      }
    };
    fetchActiveConnection();
  }, []);

  // Fetch per-task model settings on mount
  useEffect(() => {
    const fetchPerTaskModels = async () => {
      try {
        const response = await fetch('/api/settings/');
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
    // Parse chart intent from the question
    const chartIntent = parseChartIntent(question);
    const chartHint = getChartIntentHint(chartIntent);

    // Add user message (show chart hint if detected)
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: chartHint ? `${question}\n\n_${chartHint}_` : question,
    };
    setMessages((prev) => [...prev, userMessage]);

    // Submit query with chart preference and row limit
    try {
      const response = await queryMutation.mutateAsync({
        question: chartIntent.cleanedQuestion || question,
        model: selectedModel || undefined,
        enable_narratives: enableNarratives,
        preferred_chart_type: chartIntent.chartType,
        row_limit: rowLimit,
      });

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.results && response.results.length > 0
          ? `Here's what I found:`
          : 'Query executed successfully.',
        queryResponse: response,
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
    <div className="flex flex-col h-full">
      {/* Model selector and options header */}
      <div className="px-6 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-600">Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {modelsData?.models.map((model) => (
                <option key={model} value={model}>
                  {model}
                  {model === modelsData.default_model && ' (default)'}
                </option>
              ))}
            </select>
          </div>

          {/* Narratives Toggle */}
          <label className="flex items-center space-x-2 cursor-pointer">
            <button
              onClick={() => setEnableNarratives(!enableNarratives)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                enableNarratives ? 'bg-blue-600' : 'bg-gray-300'
              }`}
              title={enableNarratives ? 'Disable AI Narratives' : 'Enable AI Narratives'}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  enableNarratives ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className="text-xs text-gray-600 whitespace-nowrap">
              {enableNarratives ? '✨ Narratives' : '📊 Data Only'}
            </span>
          </label>
        </div>

        <div className="text-xs text-gray-500">
          {messages.length - 1} {messages.length === 2 ? 'query' : 'queries'}
        </div>
      </div>

      {/* Schema at a Glance for active connection */}
      {activeConnection && (
        <div className="px-6 py-2 bg-gray-50 border-b border-gray-200">
          <SchemaGlance
            connectionIds={[activeConnection.id]}
            connectionNames={{ [activeConnection.id]: activeConnection.name }}
          />
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.map((message) => (
          <Message
            key={message.id}
            type={message.type}
            content={message.content}
            queryResponse={message.queryResponse}
          />
        ))}

        {/* Loading indicator */}
        {queryMutation.isPending && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
              <div className="w-5 h-5 border-2 border-gray-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div className="flex-1">
              <div className="px-4 py-3 bg-white border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-600">Thinking...</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <QueryInput
        onSubmit={handleSubmit}
        isLoading={queryMutation.isPending}
        selectedModel={selectedModel}
        perTaskModels={perTaskModels ? {
          sql: perTaskModels.model_sql_generation,
          narratives: perTaskModels.model_narratives,
          planning: perTaskModels.model_query_planning,
          correction: perTaskModels.model_error_correction,
        } : null}
      />
    </div>
  );
}
