import { User } from 'lucide-react';
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
    <div className={`flex items-start space-x-4 animate-fadeIn transition-all duration-500 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-sm border transition-transform duration-300 hover:scale-110 ${isUser
        ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white border-blue-400/50'
        : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-700'
        }`}>
        {isUser ? (
          <User className="w-5 h-5" />
        ) : (
          <span className="text-xl">🧙‍♂️</span>
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
        <div className={`max-w-3xl group ${isUser ? 'ml-auto' : ''}`}>
          {/* Text content */}
          <div className={`px-5 py-3.5 shadow-xl transition-all duration-300 ${isUser
            ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-t-[20px] rounded-bl-[20px] rounded-br-[4px] glow-primary'
            : 'glass-node rounded-t-[20px] rounded-br-[20px] rounded-bl-[4px]'
            }`}>
            <p className={`text-sm leading-relaxed ${isUser ? 'text-white font-medium' : 'text-gray-900 dark:text-gray-100'}`}>
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
                // Option 2: Observability props
                agentTrace={queryResponse.agent_trace}
                queryPlan={queryResponse.query_plan}
                attempts={queryResponse.attempts}
                selfCorrected={queryResponse.self_corrected}
                totalAttempts={queryResponse.total_attempts}
                verificationWarnings={queryResponse.verification_warnings}
                usedPlanning={queryResponse.used_planning}
                // Parallel Execution Metrics
                parallelExecutionMetrics={queryResponse.parallelExecutionMetrics}
                parallelCorrectionMetrics={queryResponse.parallelCorrectionMetrics}
                // Cache Information
                cacheType={queryResponse.cache_type}
                semanticSimilarity={queryResponse.semantic_similarity}
                matchedQuestion={queryResponse.matched_question}
                // Intelligent Data Narratives
                resultAnalysis={queryResponse.result_analysis}
                // Chart Intent (Phase 8: Chart Intelligence)
                preferredChartType={queryResponse.preferred_chart_type}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
