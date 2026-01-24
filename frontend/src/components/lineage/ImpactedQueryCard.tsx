import { useState } from 'react';
import type { ImpactedQuery } from '../../types/lineage';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export function ImpactedQueryCard({ query }: { query: ImpactedQuery }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="p-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${RISK_COLORS[query.risk_level]}`}>
            {query.risk_level}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            {query.impact_type}
          </span>
          <span className="text-sm text-gray-900 dark:text-white truncate">
            {query.natural_language_query}
          </span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex-shrink-0 ml-2"
        >
          {expanded ? 'Hide SQL' : 'Show SQL'}
        </button>
      </div>
      {expanded && (
        <pre className="mt-2 p-2 text-xs font-mono bg-gray-50 dark:bg-gray-900 rounded-lg overflow-x-auto text-gray-700 dark:text-gray-300">
          {query.generated_sql}
        </pre>
      )}
    </div>
  );
}
