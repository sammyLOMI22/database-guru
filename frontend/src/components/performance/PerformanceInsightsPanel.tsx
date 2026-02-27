// Phase 22: Performance Insights Panel
import { useState } from 'react';
import { AlertTriangle, CheckCircle2, XCircle, Copy, Check, ChevronDown, ChevronRight, Lightbulb, Database, FileCode2 } from 'lucide-react';
import type { PerformanceInsights } from '../../types/performance';

interface PerformanceInsightsPanelProps {
  insights: PerformanceInsights;
}

const SEVERITY_CONFIG = {
  good: { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800', label: 'Good' },
  warning: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800', label: 'Needs Attention' },
  critical: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800', label: 'Critical' },
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

export function PerformanceInsightsPanel({ insights }: PerformanceInsightsPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['bottlenecks', 'index_suggestions'])
  );

  const toggleSection = (id: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const severity = SEVERITY_CONFIG[insights.overall_severity] || SEVERITY_CONFIG.warning;
  const SeverityIcon = severity.icon;

  return (
    <div className="space-y-4">
      {/* Summary Banner */}
      <div className={`p-4 rounded-xl border ${severity.bg} ${severity.border}`}>
        <div className="flex items-start gap-3">
          <SeverityIcon className={`w-5 h-5 ${severity.color} flex-shrink-0 mt-0.5`} />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-sm font-bold ${severity.color}`}>{severity.label}</span>
              <span className="text-xs text-gray-400">
                Confidence: {Math.round(insights.confidence * 100)}%
              </span>
              {!insights.llm_used && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                  Deterministic Only
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300">{insights.summary}</p>
          </div>
        </div>
      </div>

      {/* Before/After Estimate */}
      {insights.before_after_estimate && (
        <div className="p-3 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20">
          <div className="flex items-center gap-2 text-sm">
            <Lightbulb className="w-4 h-4 text-blue-500" />
            <span className="font-semibold text-blue-700 dark:text-blue-300">Estimated Impact:</span>
            <span className="text-blue-600 dark:text-blue-400">{insights.before_after_estimate}</span>
          </div>
        </div>
      )}

      {/* Bottlenecks */}
      {insights.bottlenecks.length > 0 && (
        <Section
          id="bottlenecks"
          title="Bottlenecks"
          count={insights.bottlenecks.length}
          icon={<AlertTriangle className="w-4 h-4 text-amber-500" />}
          expanded={expandedSections.has('bottlenecks')}
          onToggle={() => toggleSection('bottlenecks')}
        >
          <div className="space-y-2">
            {insights.bottlenecks.map((b, i) => (
              <div key={i} className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50">
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={b.severity} />
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{b.node_type}</span>
                  {b.table_or_index && (
                    <span className="text-xs text-gray-400">on {b.table_or_index}</span>
                  )}
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{b.description}</p>
                {b.impact_estimate && (
                  <p className="text-xs text-gray-400 mt-1">Impact: {b.impact_estimate}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Index Suggestions */}
      {insights.index_suggestions.length > 0 && (
        <Section
          id="index_suggestions"
          title="Index Suggestions"
          count={insights.index_suggestions.length}
          icon={<Database className="w-4 h-4 text-green-500" />}
          expanded={expandedSections.has('index_suggestions')}
          onToggle={() => toggleSection('index_suggestions')}
        >
          <div className="space-y-2">
            {insights.index_suggestions.map((s, i) => (
              <div key={i} className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    {s.table} ({s.columns.join(', ')})
                  </span>
                  <span className="text-xs text-green-600 dark:text-green-400">{s.estimated_speedup}</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{s.reason}</p>
                <div className="flex items-center gap-2 bg-gray-50 dark:bg-gray-900 p-2 rounded-lg">
                  <code className="text-xs font-mono text-gray-700 dark:text-gray-300 flex-1 break-all">
                    {s.create_sql}
                  </code>
                  <CopyButton text={s.create_sql} />
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Query Rewrites */}
      {insights.query_rewrites.length > 0 && (
        <Section
          id="query_rewrites"
          title="Query Rewrites"
          count={insights.query_rewrites.length}
          icon={<FileCode2 className="w-4 h-4 text-purple-500" />}
          expanded={expandedSections.has('query_rewrites')}
          onToggle={() => toggleSection('query_rewrites')}
        >
          <div className="space-y-2">
            {insights.query_rewrites.map((r, i) => (
              <div key={i} className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  {r.reason} ({r.expected_improvement})
                </p>
                <div className="flex items-center gap-2 bg-gray-50 dark:bg-gray-900 p-2 rounded-lg">
                  <code className="text-xs font-mono text-gray-700 dark:text-gray-300 flex-1 break-all whitespace-pre-wrap">
                    {r.rewritten_sql}
                  </code>
                  <CopyButton text={r.rewritten_sql} />
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* General Recommendations */}
      {insights.general_recommendations.length > 0 && (
        <Section
          id="recommendations"
          title="Recommendations"
          count={insights.general_recommendations.length}
          icon={<Lightbulb className="w-4 h-4 text-blue-500" />}
          expanded={expandedSections.has('recommendations')}
          onToggle={() => toggleSection('recommendations')}
        >
          <ul className="space-y-1.5">
            {insights.general_recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span className="text-blue-400 mt-1">-</span>
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function Section({ id: _id, title, count, icon, expanded, onToggle, children }: {
  id: string;
  title: string;
  count: number;
  icon: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors text-left"
      >
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        {icon}
        <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{title}</span>
        <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
          {count}
        </span>
      </button>
      {expanded && (
        <div className="p-3">
          {children}
        </div>
      )}
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const config: Record<string, string> = {
    low: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
    medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-bold uppercase ${config[severity] || config.medium}`}>
      {severity}
    </span>
  );
}
