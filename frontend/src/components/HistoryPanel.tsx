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
        <div className="animate-spin w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full mx-auto"></div>
        <p className="mt-2 text-sm text-gray-500">Loading history...</p>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
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
          className="text-left p-3 bg-white border border-gray-200 rounded-lg hover:border-primary-300 hover:shadow-sm transition-all"
        >
          {/* Query text */}
          <p className="text-sm text-gray-900 line-clamp-2 mb-2">
            {item.natural_language_query}
          </p>

          {/* SQL preview */}
          <p className="text-xs font-mono text-gray-500 line-clamp-1 mb-2">
            {item.generated_sql}
          </p>

          {/* Metadata */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center space-x-2">
              {item.executed ? (
                <CheckCircle className="w-3 h-3 text-green-500" />
              ) : (
                <XCircle className="w-3 h-3 text-red-500" />
              )}
              {item.execution_time_ms !== null && (
                <span>{item.execution_time_ms.toFixed(2)}ms</span>
              )}
              {item.result_count !== null && (
                <span>{item.result_count} rows</span>
              )}
            </div>
            {item.model_used && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded">
                {item.model_used}
              </span>
            )}
          </div>

          {/* Timestamp */}
          <div className="mt-1 text-xs text-gray-400">
            {new Date(item.created_at).toLocaleString()}
          </div>
        </button>
      ))}
    </div>
  );
}
