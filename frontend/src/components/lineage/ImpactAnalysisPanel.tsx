import { useState, useEffect, useCallback } from 'react';
import { lineageAPI } from '../../services/lineageApi';
import { ImpactedQueryCard } from './ImpactedQueryCard';
import type { ImpactAnalysisResponse } from '../../types/lineage';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

interface ImpactAnalysisPanelProps {
  tableName: string;
  columnName?: string;
  autoAnalyze?: boolean;
}

export function ImpactAnalysisPanel({ tableName, columnName, autoAnalyze = false }: ImpactAnalysisPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImpactAnalysisResponse | null>(null);

  const analyze = useCallback(async () => {
    if (!tableName.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await lineageAPI.analyzeImpact(
        tableName.trim(),
        columnName?.trim() || undefined
      );
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Impact analysis failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [tableName, columnName]);

  useEffect(() => {
    if (autoAnalyze && tableName.trim()) {
      analyze();
    }
  }, [autoAnalyze, analyze]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
          <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium">Analyzing impact...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold text-gray-900 dark:text-white">
            Impact: {result.changed_object}
          </h3>
          <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${RISK_COLORS[result.risk_level]}`}>
            {result.risk_level.toUpperCase()}
          </span>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">{result.summary}</p>
        <div className="flex gap-4 mt-3 text-xs">
          <span className="text-green-600 dark:text-green-400">Low: {result.risk_counts.low}</span>
          <span className="text-yellow-600 dark:text-yellow-400">Medium: {result.risk_counts.medium}</span>
          <span className="text-red-600 dark:text-red-400">High: {result.risk_counts.high}</span>
        </div>
      </div>

      {/* Affected Queries */}
      {result.impacted_queries.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Affected Queries ({result.total_affected})
          </h4>
          {result.impacted_queries.map((q) => (
            <ImpactedQueryCard key={q.query_id} query={q} />
          ))}
        </div>
      )}
    </div>
  );
}
