import { useState, useRef, useEffect } from 'react';
import Message from './Message';
import QueryInput from './QueryInput';
import { useQuerySubmit } from '../hooks/useQuerySubmit';
import { useModels } from '../hooks/useModels';
import type { QueryResponse } from '../types/api';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  queryResponse?: QueryResponse;
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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryMutation = useQuerySubmit();
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
      const response = await queryMutation.mutateAsync({
        question,
        model: selectedModel || undefined,
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
      {/* Model selector header */}
      <div className="px-6 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
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

        <div className="text-xs text-gray-500">
          {messages.length - 1} {messages.length === 2 ? 'query' : 'queries'}
        </div>
      </div>

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
      />
    </div>
  );
}
