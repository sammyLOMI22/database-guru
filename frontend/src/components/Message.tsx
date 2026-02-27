import { useMemo } from 'react';
import { User } from 'lucide-react';
import mascot from '../assets/boxer_mascot.png';
import MultiDatabaseResults from './MultiDatabaseResults';
import type { MultiDatabaseQueryResponse, QueryResponse } from '../types/api';

interface MessageProps {
  type: 'user' | 'assistant';
  content: string;
  queryResponse?: QueryResponse;  // Legacy single-database response
  multiQueryResponse?: MultiDatabaseQueryResponse;  // Multi-database response
  onViewLineage?: (sql: string) => void;
  onAnalyzePerformance?: (sql: string, connectionId?: number) => void;
}

export default function Message({ type, content, queryResponse, multiQueryResponse, onViewLineage, onAnalyzePerformance }: MessageProps) {
  // Convert legacy single-database response to multi-database format for unified rendering
  const effectiveMultiResponse = useMemo(() => {
    if (multiQueryResponse) return multiQueryResponse;
    if (!queryResponse) return undefined;

    // Convert single QueryResponse to MultiDatabaseQueryResponse format
    return {
      question: queryResponse.question || '',
      database_results: [{
        connection_id: 0,
        connection_name: 'Database',
        database_type: 'unknown',
        success: queryResponse.is_valid,
        sql: queryResponse.sql || '',
        results: queryResponse.results || [],
        row_count: queryResponse.row_count || 0,
        execution_time_ms: queryResponse.execution_time_ms || 0,
        error: queryResponse.warnings?.join(', ') || undefined,
        result_analysis: queryResponse.result_analysis,
      }],
      total_rows: queryResponse.row_count || 0,
      total_execution_time_ms: queryResponse.execution_time_ms || 0,
      cache_info: queryResponse.cached ? { hit: true, type: 'exact' as const } : undefined,
    } as MultiDatabaseQueryResponse;
  }, [queryResponse, multiQueryResponse]);
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
          <img
            src={mascot}
            alt="Assistant Mascot"
            className="w-7 h-7 object-contain drop-shadow-sm transition-transform group-hover:scale-110"
          />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 min-w-0 ${isUser ? 'flex justify-end' : ''}`}>
        <div className={`max-w-[1100px] w-full group ${isUser ? 'ml-auto' : ''}`}>
          {/* Text content */}
          <div className={`px-6 py-4 shadow-2xl transition-all duration-300 ${isUser
            ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-2xl rounded-tr-none border-b-2 border-indigo-800/50'
            : 'glass-card rounded-2xl rounded-tl-none border-white/10 dark:border-white/5'
            }`}>
            <p className={`text-[15px] leading-relaxed tracking-tight ${isUser ? 'text-white/90 font-medium' : 'text-gray-900 dark:text-gray-100'}`}>
              {content}
            </p>
          </div>

          {/* Query results (only for assistant messages with actual data) */}
          {!isUser && effectiveMultiResponse && effectiveMultiResponse.database_results?.some(
            (r) => (r.results && r.results.length > 0) || r.sql || r.error
          ) && (
            <div className="mt-4 animate-scaleUp fill-mode-forwards opacity-0">
              <MultiDatabaseResults
                results={effectiveMultiResponse.database_results}
                totalRows={effectiveMultiResponse.total_rows}
                totalExecutionTime={effectiveMultiResponse.total_execution_time_ms}
                question={effectiveMultiResponse.question}
                cacheInfo={effectiveMultiResponse.cache_info}
                combinedAnalysis={effectiveMultiResponse.combined_analysis}
                onViewLineage={onViewLineage}
                onAnalyzePerformance={onAnalyzePerformance}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
