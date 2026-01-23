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
          className="text-left p-4 glass-card bg-white/5 dark:bg-white/5 border-white/5 rounded-2xl hover:border-blue-500/30 hover:bg-white/10 transition-all duration-300 group relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-16 h-16 bg-blue-500/5 blur-2xl -mr-8 -mt-8 opacity-0 group-hover:opacity-100 transition-opacity" />

          {/* Query text */}
          <p className="text-xs font-black uppercase tracking-tight text-gray-900 dark:text-white line-clamp-2 mb-3 leading-relaxed">
            {item.natural_language_query}
          </p>

          {/* SQL preview */}
          <div className="relative mb-3">
            <p className="text-[11px] font-mono text-blue-500 dark:text-blue-400 line-clamp-1 bg-black/20 dark:bg-black/40 p-2 rounded-lg border border-white/5">
              {item.generated_sql}
            </p>
          </div>

          {/* Metadata */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-1 rounded-md ${item.executed ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                {item.executed ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
              </div>
              <div className="flex items-center gap-1.5">
                {item.execution_time_ms !== null && (
                  <span className="text-[10pt] font-black uppercase tracking-widest text-gray-500 bg-black/10 dark:bg-white/5 px-1.5 py-0.5 rounded-md">
                    {item.execution_time_ms.toFixed(0)}MS
                  </span>
                )}
                {item.result_count !== null && (
                  <span className="text-[10pt] font-black uppercase tracking-widest text-gray-500 bg-black/10 dark:bg-white/5 px-1.5 py-0.5 rounded-md">
                    {item.result_count}R
                  </span>
                )}
              </div>
            </div>
            {item.model_used && (
              <span className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-400 dark:text-gray-500">
                {item.model_used.split(':')[0]}
              </span>
            )}
          </div>

          {/* Timestamp */}
          <div className="mt-3 text-[11px] font-black uppercase tracking-[0.2em] text-gray-400 dark:text-gray-600 border-t border-white/5 pt-2">
            {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </button>
      ))}
    </div>
  );
}
