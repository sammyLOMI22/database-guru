import { User, Bot } from 'lucide-react';
import QueryResults from './QueryResults';
import type { QueryResponse } from '../types/api';

interface MessageProps {
  type: 'user' | 'assistant';
  content: string;
  queryResponse?: QueryResponse;
}

export default function Message({ type, content, queryResponse }: MessageProps) {
  const isUser = type === 'user';

  return (
    <div className={`flex items-start space-x-3 animate-fadeIn ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary-100' : 'bg-gray-100'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-primary-600" />
        ) : (
          <Bot className="w-5 h-5 text-gray-600" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
        <div className={`max-w-3xl ${isUser ? 'ml-auto' : ''}`}>
          {/* Text content */}
          <div className={`px-4 py-3 rounded-lg ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-gray-200'
          }`}>
            <p className={`text-sm ${isUser ? 'text-white' : 'text-gray-900'}`}>
              {content}
            </p>
          </div>

          {/* Query response (only for assistant messages) */}
          {!isUser && queryResponse && (
            <div className="mt-4">
              <QueryResults
                sql={queryResponse.sql}
                results={queryResponse.results}
                rowCount={queryResponse.row_count}
                executionTime={queryResponse.execution_time_ms}
                isValid={queryResponse.is_valid}
                warnings={queryResponse.warnings}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
