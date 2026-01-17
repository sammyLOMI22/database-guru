import { User } from 'lucide-react';
import MultiDatabaseResults from './MultiDatabaseResults';
import type { MultiDatabaseQueryResponse } from '../types/api';

interface MessageProps {
  type: 'user' | 'assistant';
  content: string;
  multiQueryResponse?: MultiDatabaseQueryResponse;
}

export default function Message({ type, content, multiQueryResponse }: MessageProps) {
  const isUser = type === 'user';

  return (
    <div className={`flex items-start w-full gap-5 transition-all duration-500 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg border-2 transition-all duration-300 hover:scale-110 active:scale-95 ${isUser
        ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white border-blue-400/30'
        : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-white/10 shadow-blue-500/5'
        }`}>
        {isUser ? (
          <User className="w-5 h-5 shadow-sm" />
        ) : (
          <span className="text-xl drop-shadow-sm">🧙‍♂️</span>
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 min-w-0 ${isUser ? 'flex justify-end' : ''}`}>
        <div className={`max-w-[85%] group ${isUser ? 'ml-auto' : ''}`}>
          {/* Text content */}
          <div className={`px-6 py-4 shadow-2xl transition-all duration-300 ${isUser
            ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-2xl rounded-tr-none border-b-2 border-indigo-800/50'
            : 'glass-card rounded-2xl rounded-tl-none border-white/10 dark:border-white/5'
            }`}>
            <p className={`text-[15px] leading-relaxed tracking-tight ${isUser ? 'text-white/90 font-medium' : 'text-gray-900 dark:text-gray-100'}`}>
              {content}
            </p>
          </div>

          {/* Multi-database results (only for assistant messages) */}
          {!isUser && multiQueryResponse && (
            <div className="mt-4 animate-scaleUp fill-mode-forwards opacity-0">
              <MultiDatabaseResults
                results={multiQueryResponse.database_results}
                totalRows={multiQueryResponse.total_rows}
                totalExecutionTime={multiQueryResponse.total_execution_time_ms}
                question={multiQueryResponse.question}
                cacheInfo={multiQueryResponse.cache_info}
                combinedAnalysis={multiQueryResponse.combined_analysis}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
