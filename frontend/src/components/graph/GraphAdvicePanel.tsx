/**
 * Guru Advice panel — Phase 25.6.
 *
 * Displays rule-based + AI-enhanced modeling recommendations for
 * the selected Neo4j connection. Cards are sorted by severity (high first)
 * and can be dismissed per-session.
 */
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { graphAPI } from '../../services/graphApi';
import type {
  GraphAdvisorFinding,
  GraphModelingAdviceResponse,
} from '../../services/graphApi';

interface Props {
  connectionId: number | null;
}

const SEVERITY_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  high: {
    bg: 'bg-red-50 dark:bg-red-950/30',
    border: 'border-red-200 dark:border-red-800/50',
    text: 'text-red-800 dark:text-red-300',
    badge: 'bg-red-600 text-white',
  },
  medium: {
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    border: 'border-amber-200 dark:border-amber-800/50',
    text: 'text-amber-800 dark:text-amber-300',
    badge: 'bg-amber-600 text-white',
  },
  low: {
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    border: 'border-blue-200 dark:border-blue-800/50',
    text: 'text-blue-800 dark:text-blue-300',
    badge: 'bg-blue-600 text-white',
  },
  info: {
    bg: 'bg-gray-50 dark:bg-gray-900/30',
    border: 'border-gray-200 dark:border-gray-700/50',
    text: 'text-gray-700 dark:text-gray-300',
    badge: 'bg-gray-500 text-white',
  },
};

function getSeverityStyle(severity: string) {
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
}

function FindingCard({
  finding,
  onDismiss,
}: {
  finding: GraphAdvisorFinding;
  onDismiss: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const style = getSeverityStyle(finding.severity);

  return (
    <div className={`rounded-xl border ${style.border} ${style.bg} p-4 transition-all`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${style.badge}`}>
              {finding.severity}
            </span>
            {finding.entity_name && (
              <span className="text-[10px] font-mono text-gray-500 dark:text-gray-400 truncate">
                {finding.entity_type === 'RELATIONSHIP' ? `[:${finding.entity_name}]` : `(:${finding.entity_name})`}
              </span>
            )}
          </div>
          <h4 className={`text-sm font-semibold ${style.text}`}>
            {finding.title}
          </h4>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            {finding.description}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-xs px-2 py-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 text-gray-500 dark:text-gray-400"
          >
            {expanded ? 'Less' : 'More'}
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="text-xs px-1.5 py-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 text-gray-400"
            title="Dismiss"
          >
            &times;
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-black/5 dark:border-white/5 space-y-2">
          <div>
            <span className="text-[10px] font-bold uppercase text-gray-500 dark:text-gray-400">
              Why this matters
            </span>
            <p className="text-xs text-gray-700 dark:text-gray-300 mt-0.5">
              {finding.why}
            </p>
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase text-gray-500 dark:text-gray-400">
              Suggested fix
            </span>
            <pre className="text-xs text-gray-700 dark:text-gray-300 mt-0.5 bg-black/5 dark:bg-white/5 rounded-lg p-2 overflow-x-auto whitespace-pre-wrap font-mono">
              {finding.suggested_fix}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default function GraphAdvicePanel({ connectionId }: Props) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const mutation = useMutation<GraphModelingAdviceResponse, unknown, void>({
    mutationFn: () => {
      if (!connectionId) throw new Error('No connection selected');
      return graphAPI.getModelingAdvice(connectionId);
    },
  });

  const run = () => mutation.mutate();

  if (!connectionId) {
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-8 text-center">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Select a Neo4j connection to get modeling advice.
        </p>
      </div>
    );
  }

  if (!mutation.data && !mutation.isPending && !mutation.error) {
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-8 text-center">
        <div className="text-4xl mb-4">💡</div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">
          Graph Modeling Advisor
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          Analyze your graph schema for missing indexes, overloaded labels,
          heavy relationships, orphan nodes, and other modeling issues.
        </p>
        <button
          type="button"
          onClick={run}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 transition-all"
        >
          Run Analysis
        </button>
      </div>
    );
  }

  if (mutation.isPending) {
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-8 text-center">
        <div className="animate-spin text-4xl mb-4">⚙️</div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Analyzing graph schema...
        </p>
      </div>
    );
  }

  if (mutation.error) {
    const err = mutation.error;
    const msg =
      (err as any)?.response?.data?.detail || (err as Error).message;
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-8 text-center">
        <p className="text-sm text-red-600 dark:text-red-400 mb-4">{msg}</p>
        <button
          type="button"
          onClick={run}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-all"
        >
          Retry
        </button>
      </div>
    );
  }

  const data = mutation.data;
  const visibleFindings = (data?.findings || []).filter(
    (f) => !dismissed.has(`${f.rule_id}:${f.entity_name}`),
  );

  const severityCounts = (data?.findings || []).reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            Modeling Advice
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {data?.finding_count ?? 0} finding{(data?.finding_count ?? 0) !== 1 ? 's' : ''} detected
            {Object.entries(severityCounts).length > 0 && (
              <span className="ml-2">
                ({Object.entries(severityCounts)
                  .sort(([a], [b]) => {
                    const order = ['high', 'medium', 'low', 'info'];
                    return order.indexOf(a) - order.indexOf(b);
                  })
                  .map(([sev, count]) => `${count} ${sev}`)
                  .join(', ')})
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setDismissed(new Set());
            run();
          }}
          className="px-4 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/30 rounded-xl transition-all"
        >
          Re-analyze
        </button>
      </div>

      {/* AI Summary */}
      {data?.ai_summary && (
        <div className="glass-panel rounded-xl p-4 border border-purple-200/50 dark:border-purple-800/30 bg-purple-50/50 dark:bg-purple-950/20">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-bold uppercase text-purple-600 dark:text-purple-400">
              AI Summary
            </span>
            {data.model && (
              <span className="text-[10px] text-gray-400 dark:text-gray-500">
                via {data.model}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
            {data.ai_summary}
          </p>
        </div>
      )}

      {/* Findings */}
      {visibleFindings.length === 0 ? (
        <div className="glass-panel rounded-2xl p-8 text-center">
          <div className="text-3xl mb-3">✅</div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {(data?.finding_count ?? 0) === 0
              ? 'No modeling issues detected — your graph schema looks good!'
              : 'All findings dismissed.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visibleFindings.map((finding) => {
            const key = `${finding.rule_id}:${finding.entity_name}`;
            return (
              <FindingCard
                key={key}
                finding={finding}
                onDismiss={() =>
                  setDismissed((prev) => new Set([...prev, key]))
                }
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
