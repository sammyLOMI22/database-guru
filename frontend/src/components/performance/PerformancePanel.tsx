// Phase 22: Performance Guru Panel
import { useState, useEffect } from 'react';
import { Loader2, AlertTriangle, Zap } from 'lucide-react';
import { performanceAPI } from '../../services/performanceApi';
import { connectionsAPI } from '../../services/api';
import { ExecutionPlanTree } from './ExecutionPlanTree';
import { PerformanceInsightsPanel } from './PerformanceInsightsPanel';
import type { PerformanceAnalysisResponse } from '../../types/performance';

interface PerformancePanelProps {
  initialSql?: string;
  initialConnectionId?: number;
}

interface ConnectionOption {
  id: number;
  name: string;
  database_type: string;
}

export function PerformancePanel({ initialSql, initialConnectionId }: PerformancePanelProps) {
  const [connections, setConnections] = useState<ConnectionOption[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(initialConnectionId || null);
  const [sql, setSql] = useState(initialSql || '');
  const [runAnalyze, setRunAnalyze] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PerformanceAnalysisResponse | null>(null);

  // Load connections on mount
  useEffect(() => {
    connectionsAPI.listConnections().then((data: any) => {
      const conns = (data.connections || data || []).map((c: any) => ({
        id: c.id,
        name: c.name,
        database_type: c.database_type,
      }));
      setConnections(conns);
      if (conns.length > 0) {
        setSelectedConnectionId(prev => prev ?? conns[0].id);
      }
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update from initial props (cross-tab navigation)
  useEffect(() => {
    if (initialSql) setSql(initialSql);
    if (initialConnectionId) setSelectedConnectionId(initialConnectionId);
  }, [initialSql, initialConnectionId]);

  const handleAnalyze = async () => {
    if (!selectedConnectionId || !sql.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await performanceAPI.analyzeQuery({
        sql: sql.trim(),
        connection_id: selectedConnectionId,
        run_analyze: runAnalyze,
        include_schema_context: true,
      });
      setResult(response);
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Analysis failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <Zap className="w-5 h-5 text-amber-500" />
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-200">Performance Guru</h2>
          <span className="text-xs text-gray-400">EXPLAIN Analysis with AI Insights</span>
        </div>

        {/* Controls */}
        <div className="space-y-3">
          {/* Connection selector */}
          <div className="flex items-center gap-3">
            <label className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide w-24">
              Connection
            </label>
            <select
              value={selectedConnectionId || ''}
              onChange={(e) => setSelectedConnectionId(Number(e.target.value))}
              className="flex-1 px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="" disabled>Select a connection...</option>
              {connections.map(c => (
                <option key={c.id} value={c.id}>{c.name} ({c.database_type})</option>
              ))}
            </select>
          </div>

          {/* SQL input */}
          <div className="flex items-start gap-3">
            <label className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide w-24 pt-2">
              SQL
            </label>
            <textarea
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              placeholder="SELECT * FROM orders WHERE status = 'pending'..."
              className="flex-1 px-3 py-2 text-sm font-mono rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y min-h-[80px]"
              rows={3}
            />
          </div>

          {/* Actions row */}
          <div className="flex items-center gap-4 pl-27">
            {/* EXPLAIN ANALYZE toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={runAnalyze}
                onChange={(e) => setRunAnalyze(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">EXPLAIN ANALYZE</span>
              {runAnalyze && (
                <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="w-3 h-3" />
                  Executes query
                </span>
              )}
            </label>

            <div className="flex-1" />

            <button
              onClick={handleAnalyze}
              disabled={loading || !selectedConnectionId || !sql.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-bold transition-all shadow-lg disabled:shadow-none"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Analyze
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results area */}
      <div className="flex-1 overflow-auto px-6 py-4 space-y-6">
        {/* Error */}
        {error && (
          <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
            </div>
          </div>
        )}

        {/* No results yet */}
        {!result && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Zap className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-4" />
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
              Enter a SQL query and select a connection to analyze performance.
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              The analyzer will run EXPLAIN and provide actionable optimization suggestions.
            </p>
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Meta info */}
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span>Dialect: <span className="font-semibold text-gray-600 dark:text-gray-300">{result.dialect}</span></span>
              <span>Mode: <span className="font-semibold text-gray-600 dark:text-gray-300">{result.analyzed ? 'EXPLAIN ANALYZE' : 'EXPLAIN'}</span></span>
              {result.plan.node_count > 0 && (
                <span>Nodes: <span className="font-semibold text-gray-600 dark:text-gray-300">{result.plan.node_count}</span></span>
              )}
            </div>

            {/* Execution Plan Tree */}
            <ExecutionPlanTree
              rootNode={result.plan.root_node}
              allNodes={result.plan.all_nodes}
              rawPlan={result.plan.raw_plan}

            />

            {/* Performance Insights */}
            <div>
              <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3">
                AI Insights
              </h3>
              <PerformanceInsightsPanel insights={result.insights} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
