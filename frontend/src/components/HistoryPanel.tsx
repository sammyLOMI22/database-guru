import { Clock, CheckCircle, XCircle } from 'lucide-react';
import { useHistory } from '../hooks/useHistory';

interface HistoryPanelProps {
  onSelectQuery: (question: string) => void;
}

export default function HistoryPanel({ onSelectQuery }: HistoryPanelProps) {
  const { data: history, isLoading } = useHistory(20);

  if (isLoading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-spin w-6 h-6 border-2 border-primary-600 dark:border-primary-400 border-t-transparent rounded-full mx-auto"></div>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading history...</p>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-500 mt-10">
        <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No history yet</p>
        <p className="text-xs mt-1">Your queries will appear here</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4 space-y-3">
      {history.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelectQuery(item.natural_language_query)}
          className="text-left p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary-300 dark:hover:border-primary-500 hover:shadow-sm transition-all duration-200"
        >
          {/* Query text */}
          <p className="text-sm text-gray-900 dark:text-gray-100 line-clamp-2 mb-2 font-medium">
            {item.natural_language_query}
          </p>

          {/* SQL preview */}
          <p className="text-xs font-mono text-gray-500 dark:text-gray-400 line-clamp-1 mb-2 bg-gray-50 dark:bg-gray-900/50 p-1.5 rounded">
            {item.generated_sql}
          </p>

          {/* Metadata */}
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center space-x-2">
              {item.executed ? (
                <CheckCircle className="w-3.5 h-3.5 text-green-500 dark:text-green-400" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-red-500 dark:text-red-400" />
              )}
              {item.execution_time_ms !== null && (
                <span className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{item.execution_time_ms.toFixed(2)}ms</span>
              )}
              {item.result_count !== null && (
                <span className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{item.result_count} rows</span>
              )}
            </div>
            {item.model_used && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded transition-colors">
                {item.model_used}
              </span>
            )}
          </div>

          {/* Timestamp */}
          <div className="mt-2 text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">
            {new Date(item.created_at).toLocaleString()}
          </div>
        </button>
      ))}
    </div>
  );
}
