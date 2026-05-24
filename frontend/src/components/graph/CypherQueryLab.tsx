/**
 * Cypher Query Lab — Phase 25.3.
 *
 * MVP scope:
 *   - Cypher editor (textarea — Monaco intentionally deferred to keep the
 *     bundle small; the safety classifier already does the heavy lifting).
 *   - "Run" submits to /api/graph/connections/:id/query.
 *   - Three result tabs: Table / JSON / Graph (the Graph tab shows a
 *     placeholder for 25.3 — visual rendering lands in 25.5).
 *   - Blocked-by-safety responses surface inline with the reason and a
 *     plain-English explanation. Driver errors surface the
 *     classified category + hint.
 *   - History strip below the result lists the most recent runs for the
 *     connection and lets the user re-load any query into the editor.
 */
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import {
  graphAPI,
  type CypherExplainResponse,
  type CypherGenerateResponse,
  type GraphHistoryItem,
  type GraphQueryBlocked,
  type GraphQueryErrorPayload,
  type GraphQueryResult,
  type GraphQuerySafetyLevel,
} from '../../services/graphApi';

type ResultTab = 'table' | 'json' | 'graph';

interface Props {
  connectionId: number | null;
}

const DEFAULT_CYPHER =
  'MATCH (n)\nRETURN n\nLIMIT 25';

export default function CypherQueryLab({ connectionId }: Props) {
  const [cypher, setCypher] = useState<string>(DEFAULT_CYPHER);
  const [nlPrompt, setNlPrompt] = useState<string>('');
  const [activeResultTab, setActiveResultTab] = useState<ResultTab>('table');
  const [explanation, setExplanation] = useState<CypherExplainResponse | null>(null);
  const queryClient = useQueryClient();

  const runMutation = useMutation<
    GraphQueryResult,
    unknown,
    string
  >({
    mutationFn: (text: string) =>
      graphAPI.runQuery(connectionId as number, {
        cypher: text,
        source: 'manual',
      }),
    onSettled: () => {
      if (connectionId !== null) {
        queryClient.invalidateQueries({
          queryKey: ['graph', 'history', connectionId],
        });
      }
    },
  });

  const generateMutation = useMutation<
    CypherGenerateResponse,
    unknown,
    string
  >({
    mutationFn: (question: string) =>
      graphAPI.generateCypher(connectionId as number, { question }),
    onSuccess: (data) => {
      if (data.cypher) {
        setCypher(data.cypher);
      }
    },
  });

  const explainMutation = useMutation<
    CypherExplainResponse,
    unknown,
    string
  >({
    mutationFn: (text: string) =>
      graphAPI.explainCypher(connectionId as number, { cypher: text }),
    onSuccess: (data) => {
      setExplanation(data);
    },
  });

  const historyQuery = useQuery({
    queryKey: ['graph', 'history', connectionId],
    queryFn: () => graphAPI.listHistory(connectionId as number, { limit: 20 }),
    enabled: connectionId !== null,
    staleTime: 15 * 1000,
  });

  const blocked = useMemo<GraphQueryBlocked | null>(() => {
    const err = runMutation.error;
    if (
      err &&
      isAxiosError(err) &&
      err.response?.status === 400 &&
      err.response.data?.detail?.blocked_reason
    ) {
      return err.response.data.detail as GraphQueryBlocked;
    }
    return null;
  }, [runMutation.error]);

  const driverError = useMemo<GraphQueryErrorPayload | null>(() => {
    const err = runMutation.error;
    if (
      err &&
      isAxiosError(err) &&
      err.response?.status === 502 &&
      err.response.data?.detail?.error_category
    ) {
      return err.response.data.detail as GraphQueryErrorPayload;
    }
    return null;
  }, [runMutation.error]);

  const result: GraphQueryResult | undefined = runMutation.data;

  if (connectionId === null) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 p-8">
        Pick a Neo4j connection to start writing Cypher.
      </div>
    );
  }

  const onRun = () => {
    const trimmed = cypher.trim();
    if (!trimmed) return;
    runMutation.reset();
    setExplanation(null);
    runMutation.mutate(trimmed);
  };

  const onGenerate = () => {
    const trimmed = nlPrompt.trim();
    if (!trimmed) return;
    generateMutation.reset();
    generateMutation.mutate(trimmed);
  };

  const onExplain = () => {
    const trimmed = cypher.trim();
    if (!trimmed) return;
    explainMutation.reset();
    setExplanation(null);
    explainMutation.mutate(trimmed);
  };

  const onLoadFromHistory = (item: GraphHistoryItem) => {
    setCypher(item.cypher);
    setExplanation(null);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* NL prompt → Generate Cypher */}
      <div className="glass-panel rounded-2xl p-4">
        <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
          Ask in plain English
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={nlPrompt}
            onChange={(e) => setNlPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                onGenerate();
              }
            }}
            placeholder="e.g. Show users who purchased from the same category twice"
            className="flex-1 font-sans text-sm p-3 rounded-xl bg-black/40 text-gray-100 border border-white/10 focus:outline-none focus:border-purple-500/60 placeholder-gray-600"
          />
          <button
            type="button"
            onClick={onGenerate}
            disabled={generateMutation.isPending || !nlPrompt.trim()}
            className="px-4 py-2 rounded-xl bg-purple-600 text-white text-sm font-bold uppercase tracking-wider shadow-lg shadow-purple-500/30 disabled:opacity-50 whitespace-nowrap"
          >
            {generateMutation.isPending ? 'Generating…' : 'Generate'}
          </button>
        </div>
        {generateMutation.data?.unknown_labels && generateMutation.data.unknown_labels.length > 0 && (
          <p className="mt-2 text-xs text-amber-300">
            Warning: generated query references unknown labels:{' '}
            {generateMutation.data.unknown_labels.join(', ')}
          </p>
        )}
        {generateMutation.data?.error && (
          <p className="mt-2 text-xs text-red-300">
            {generateMutation.data.error}
          </p>
        )}
        {!!generateMutation.error && (
          <p className="mt-2 text-xs text-red-300">
            Failed to generate Cypher. Check your LLM provider configuration.
          </p>
        )}
      </div>

      {/* Cypher editor + Run/Explain buttons */}
      <div className="glass-panel rounded-2xl p-4">
        <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
          Cypher
        </label>
        <textarea
          value={cypher}
          onChange={(e) => { setCypher(e.target.value); setExplanation(null); }}
          spellCheck={false}
          className="w-full min-h-[140px] font-mono text-sm p-3 rounded-xl bg-black/40 text-gray-100 border border-white/10 focus:outline-none focus:border-blue-500/60 resize-y"
        />
        <div className="flex items-center justify-between mt-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Read-only queries only. Writes ({' '}
            <code className="px-1 rounded bg-black/30">CREATE</code> /{' '}
            <code className="px-1 rounded bg-black/30">MERGE</code> /{' '}
            <code className="px-1 rounded bg-black/30">DELETE</code> ) are
            blocked at the API.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onExplain}
              disabled={explainMutation.isPending || !cypher.trim()}
              className="px-4 py-2 rounded-xl bg-gray-600 text-white text-sm font-bold uppercase tracking-wider shadow-lg shadow-gray-500/20 disabled:opacity-50"
            >
              {explainMutation.isPending ? 'Explaining…' : 'Explain'}
            </button>
            <button
              type="button"
              onClick={onRun}
              disabled={runMutation.isPending || !cypher.trim()}
              className="px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-bold uppercase tracking-wider shadow-lg shadow-blue-500/30 disabled:opacity-50"
            >
              {runMutation.isPending ? 'Running…' : 'Run query'}
            </button>
          </div>
        </div>
      </div>

      {/* Explanation card */}
      {explanation && <ExplanationCard payload={explanation} />}
      {!!explainMutation.error && !explanation && (
        <div className="glass-panel rounded-2xl p-4 border border-red-500/30 bg-red-500/5">
          <p className="text-sm text-red-200">
            Failed to explain query. Check your LLM provider configuration.
          </p>
        </div>
      )}

      {/* Blocked / error / success cards */}
      {blocked && <BlockedCard payload={blocked} />}
      {driverError && <ErrorCard payload={driverError} />}
      {result && (
        <ResultPanel
          result={result}
          activeTab={activeResultTab}
          onChangeTab={setActiveResultTab}
        />
      )}

      {/* History */}
      <HistoryStrip
        loading={historyQuery.isLoading}
        items={historyQuery.data?.items ?? []}
        onLoad={onLoadFromHistory}
      />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function BlockedCard({ payload }: { payload: GraphQueryBlocked }) {
  return (
    <div className="glass-panel rounded-2xl p-4 border border-amber-500/30 bg-amber-500/5">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-amber-400">⛔</span>
        <h4 className="text-sm font-bold text-amber-200 uppercase tracking-wider">
          Blocked — {payload.safety_level.replace('_', ' ')}
        </h4>
      </div>
      <p className="text-sm text-gray-100">{payload.blocked_reason}</p>
      {payload.reasons.length > 0 && (
        <ul className="mt-2 text-xs text-gray-400 list-disc pl-5">
          {payload.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ErrorCard({ payload }: { payload: GraphQueryErrorPayload }) {
  return (
    <div className="glass-panel rounded-2xl p-4 border border-red-500/30 bg-red-500/5">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-red-400">⚠️</span>
        <h4 className="text-sm font-bold text-red-200 uppercase tracking-wider">
          {payload.error_category.replace('_', ' ')}
        </h4>
      </div>
      <p className="text-sm text-gray-100">{payload.error_message}</p>
      {payload.error_hint && (
        <p className="mt-2 text-xs text-gray-400">{payload.error_hint}</p>
      )}
      {payload.error_code && (
        <p className="mt-2 text-[11px] text-gray-500 font-mono">
          {payload.error_code}
        </p>
      )}
    </div>
  );
}

function ExplanationCard({ payload }: { payload: CypherExplainResponse }) {
  return (
    <div className="glass-panel rounded-2xl p-4 border border-purple-500/20 bg-purple-500/5">
      <div className="flex items-center gap-2 mb-2">
        <h4 className="text-sm font-bold text-purple-200 uppercase tracking-wider">
          Explanation
        </h4>
        {payload.used_fallback && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400 border border-gray-500/30">
            fallback
          </span>
        )}
        {payload.model && (
          <span className="text-[10px] text-gray-500 font-mono">
            {payload.provider}/{payload.model}
          </span>
        )}
      </div>
      <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
        {payload.explanation}
      </p>
    </div>
  );
}

function SafetyBadge({ level }: { level: GraphQuerySafetyLevel }) {
  const styles: Record<GraphQuerySafetyLevel, string> = {
    read_only: 'bg-green-500/15 text-green-300 border-green-500/30',
    write: 'bg-amber-500/15 text-amber-200 border-amber-500/30',
    admin: 'bg-purple-500/15 text-purple-200 border-purple-500/30',
    dangerous: 'bg-red-500/15 text-red-200 border-red-500/30',
    unknown: 'bg-gray-500/15 text-gray-300 border-gray-500/30',
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${styles[level]}`}
    >
      {level.replace('_', ' ')}
    </span>
  );
}

function ResultPanel({
  result,
  activeTab,
  onChangeTab,
}: {
  result: GraphQueryResult;
  activeTab: ResultTab;
  onChangeTab: (t: ResultTab) => void;
}) {
  return (
    <div className="glass-panel rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <SafetyBadge level={result.safety_level} />
          <span className="text-xs text-gray-400">
            {result.record_count} record{result.record_count === 1 ? '' : 's'} ·{' '}
            {result.execution_time_ms.toFixed(0)} ms
          </span>
        </div>
        <div className="flex gap-1 p-1 bg-black/30 rounded-xl border border-white/10">
          {(['table', 'json', 'graph'] as ResultTab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => onChangeTab(t)}
              className={`px-3 py-1 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all ${
                activeTab === t
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {result.truncated && (
        <p className="text-xs text-amber-300 mb-2">
          Result truncated. {result.warnings.join(' ')}
        </p>
      )}
      {result.server_warnings.length > 0 && (
        <ul className="mb-3 text-xs text-gray-400 list-disc pl-5">
          {result.server_warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}

      {activeTab === 'table' && <TableView result={result} />}
      {activeTab === 'json' && <JsonView result={result} />}
      {activeTab === 'graph' && <GraphPlaceholder result={result} />}
    </div>
  );
}

function TableView({ result }: { result: GraphQueryResult }) {
  const { columns, rows } = result.table;
  if (columns.length === 0) {
    return <p className="text-sm text-gray-400">No rows returned.</p>;
  }
  return (
    <div className="overflow-auto rounded-xl border border-white/5">
      <table className="min-w-full text-sm">
        <thead className="bg-black/40 text-gray-300">
          <tr>
            {columns.map((c) => (
              <th
                key={c}
                className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((row, ri) => (
            <tr key={ri} className="hover:bg-white/5">
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className="px-3 py-2 align-top font-mono text-xs text-gray-200 whitespace-pre-wrap"
                >
                  {renderCell(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderCell(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function JsonView({ result }: { result: GraphQueryResult }) {
  const records = result.table.rows.map((row) => {
    const obj: Record<string, unknown> = {};
    result.table.columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
  return (
    <pre className="text-xs font-mono text-gray-200 whitespace-pre-wrap bg-black/30 rounded-xl p-4 border border-white/5 overflow-auto max-h-[500px]">
      {JSON.stringify(records, null, 2)}
    </pre>
  );
}

function GraphPlaceholder({ result }: { result: GraphQueryResult }) {
  if (!result.graph_viz.has_graph) {
    return (
      <p className="text-sm text-gray-400 p-3">
        This result has no nodes or relationships to visualize. Try a query that
        returns node or relationship objects (e.g. <code>MATCH (n) RETURN n</code>).
      </p>
    );
  }
  return (
    <div className="text-sm text-gray-300 p-3 space-y-2">
      <p>
        Found <strong>{result.graph_viz.nodes.length}</strong> node(s) and{' '}
        <strong>{result.graph_viz.edges.length}</strong> relationship(s).
      </p>
      <p className="text-xs text-gray-500">
        Interactive Cytoscape visualization lands in Phase 25.5. For now the
        graph payload is captured server-side and is accessible via the JSON
        tab.
      </p>
    </div>
  );
}

function HistoryStrip({
  loading,
  items,
  onLoad,
}: {
  loading: boolean;
  items: GraphHistoryItem[];
  onLoad: (item: GraphHistoryItem) => void;
}) {
  if (loading) {
    return (
      <div className="glass-panel rounded-2xl p-4 text-xs text-gray-400">
        Loading history…
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-4 text-xs text-gray-400">
        No prior runs yet. Your queries will appear here.
      </div>
    );
  }
  return (
    <div className="glass-panel rounded-2xl p-4">
      <h5 className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
        Recent queries
      </h5>
      <ul className="divide-y divide-white/5">
        {items.map((item) => (
          <li
            key={item.id}
            className="py-2 flex items-start gap-3 hover:bg-white/[0.02] rounded-lg px-2 cursor-pointer"
            onClick={() => onLoad(item)}
          >
            <SafetyBadge level={item.safety_level} />
            <div className="flex-1 min-w-0">
              <pre className="text-xs font-mono text-gray-200 truncate">
                {item.cypher.replace(/\s+/g, ' ').slice(0, 120)}
              </pre>
              <p className="text-[11px] text-gray-500 mt-0.5">
                {item.success ? '✅' : '⛔'}{' '}
                {item.success
                  ? `${item.record_count ?? 0} records`
                  : item.blocked_reason ?? item.error_message ?? 'failed'}
                {' · '}
                {new Date(item.created_at).toLocaleTimeString()}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
