/**
 * SchemaHealthDashboard - Phase 12.3
 *
 * Displays comprehensive database design health analysis:
 * - Health grade (A-F) with visual score indicator
 * - Index suggestions with CREATE SQL
 * - Normalization issues
 * - Anti-patterns detected
 * - Per-table health summaries
 */
import { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Code,
  Copy,
  Check,
  Database,
  Key,
  Layers,
  Lightbulb,
  XCircle,
  Table2,
  TrendingUp,
} from 'lucide-react';
import { lineageAPI } from '../../services/lineageApi';
import type {
  SchemaHealthReport,
  IndexSuggestion,
  SchemaIssue,
  NormalizationIssue,
  TableHealthSummary,
  HealthGrade,
} from '../../types/lineage';

interface SchemaHealthDashboardProps {
  connectionId: number;
  databaseName?: string;
}

export function SchemaHealthDashboard({ connectionId, databaseName }: SchemaHealthDashboardProps) {
  const [report, setReport] = useState<SchemaHealthReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('indexes');
  const [copiedSql, setCopiedSql] = useState<string | null>(null);

  useEffect(() => {
    if (connectionId > 0) {
      loadHealthReport();
    }
  }, [connectionId]);

  const loadHealthReport = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await lineageAPI.getSchemaHealth(connectionId, true);
      setReport(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to analyze schema health');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopySql = async (sql: string, key: string) => {
    await navigator.clipboard.writeText(sql);
    setCopiedSql(key);
    setTimeout(() => setCopiedSql(null), 2000);
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (isLoading) {
    return (
      <div className="bg-teal-50 dark:bg-teal-900/20 rounded-xl p-6 border border-teal-200 dark:border-teal-800">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin" />
          <div className="text-center">
            <span className="text-sm font-medium text-teal-600 dark:text-teal-400 block">
              Analyzing schema health...
            </span>
            <span className="text-xs text-teal-500 dark:text-teal-500 mt-1">
              This may take a moment for large schemas
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-4 border border-red-200 dark:border-red-800">
        <div className="flex items-center gap-3">
          <XCircle className="w-5 h-5 text-red-500" />
          <div>
            <span className="text-sm font-medium text-red-600 dark:text-red-400 block">
              Failed to analyze schema
            </span>
            <span className="text-xs text-red-500 dark:text-red-500">{error}</span>
          </div>
        </div>
        <button
          onClick={loadHealthReport}
          className="mt-3 px-3 py-1.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 border border-gray-200 dark:border-gray-700 text-center">
        <Activity className="w-8 h-8 text-gray-400 mx-auto mb-3" />
        <span className="text-sm text-gray-500 dark:text-gray-400 block">
          Select a connection to analyze schema health
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Grade */}
      <div className="bg-gradient-to-r from-teal-50 to-cyan-50 dark:from-teal-900/30 dark:to-cyan-900/30 rounded-xl border border-teal-200 dark:border-teal-800 overflow-hidden">
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <GradeCircle grade={report.grade} score={report.score} />
              <div>
                <h3 className="text-lg font-bold text-gray-800 dark:text-gray-200">
                  {databaseName || report.database_name}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {report.table_count} tables analyzed
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Issue Counts */}
              <div className="flex items-center gap-3">
                {report.critical_issues > 0 && (
                  <div className="flex items-center gap-1 px-2 py-1 bg-red-100 dark:bg-red-900/30 rounded-lg">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                    <span className="text-xs font-bold text-red-600 dark:text-red-400">
                      {report.critical_issues} critical
                    </span>
                  </div>
                )}
                <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                    {report.total_issues} total issues
                  </span>
                </div>
              </div>

              {/* LLM Badge */}
              {report.llm_used && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-600 dark:text-teal-400 font-bold uppercase tracking-widest">
                  AI Enhanced
                </span>
              )}
            </div>
          </div>

          {/* Summary */}
          {report.summary && (
            <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
              {report.summary}
            </p>
          )}

          {/* Recommendations */}
          {report.recommendations.length > 0 && (
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-blue-500" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600 dark:text-blue-400">
                  Top Recommendations
                </span>
              </div>
              <ul className="space-y-1">
                {report.recommendations.slice(0, 3).map((rec, i) => (
                  <li key={i} className="text-xs text-blue-700 dark:text-blue-400 flex items-start gap-2">
                    <span className="text-blue-400">•</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Index Suggestions */}
      {report.index_suggestions.length > 0 && (
        <CollapsibleSection
          title="Index Suggestions"
          icon={<TrendingUp className="w-4 h-4 text-emerald-500" />}
          count={report.index_suggestions.length}
          color="emerald"
          isExpanded={expandedSection === 'indexes'}
          onToggle={() => toggleSection('indexes')}
        >
          <div className="space-y-3">
            {report.index_suggestions.map((suggestion, i) => (
              <IndexSuggestionCard
                key={i}
                suggestion={suggestion}
                onCopy={(sql) => handleCopySql(sql, `index-${i}`)}
                isCopied={copiedSql === `index-${i}`}
              />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Normalization Issues */}
      {report.normalization_issues.length > 0 && (
        <CollapsibleSection
          title="Normalization Issues"
          icon={<Layers className="w-4 h-4 text-amber-500" />}
          count={report.normalization_issues.length}
          color="amber"
          isExpanded={expandedSection === 'normalization'}
          onToggle={() => toggleSection('normalization')}
        >
          <div className="space-y-3">
            {report.normalization_issues.map((issue, i) => (
              <NormalizationIssueCard key={i} issue={issue} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Anti-Patterns */}
      {report.anti_patterns.length > 0 && (
        <CollapsibleSection
          title="Design Anti-Patterns"
          icon={<AlertTriangle className="w-4 h-4 text-red-500" />}
          count={report.anti_patterns.length}
          color="red"
          isExpanded={expandedSection === 'antipatterns'}
          onToggle={() => toggleSection('antipatterns')}
        >
          <div className="space-y-3">
            {report.anti_patterns.map((issue, i) => (
              <SchemaIssueCard
                key={i}
                issue={issue}
                onCopy={issue.fix_sql ? (sql) => handleCopySql(sql, `fix-${i}`) : undefined}
                isCopied={copiedSql === `fix-${i}`}
              />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Table Summaries */}
      {report.table_summaries.length > 0 && (
        <CollapsibleSection
          title="Table Health"
          icon={<Table2 className="w-4 h-4 text-indigo-500" />}
          count={report.table_summaries.length}
          color="indigo"
          isExpanded={expandedSection === 'tables'}
          onToggle={() => toggleSection('tables')}
        >
          <div className="space-y-2">
            {report.table_summaries.map((table, i) => (
              <TableSummaryCard key={i} table={table} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Analysis Timestamp */}
      {report.analyzed_at && (
        <div className="text-center">
          <span className="text-[10px] text-gray-400 dark:text-gray-500">
            Analyzed {new Date(report.analyzed_at).toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
}

// Grade Circle Component
function GradeCircle({ grade, score }: { grade: HealthGrade; score: number }) {
  const getGradeColor = () => {
    switch (grade) {
      case 'A':
        return { bg: 'bg-emerald-500', text: 'text-emerald-600', ring: 'ring-emerald-200' };
      case 'B':
        return { bg: 'bg-teal-500', text: 'text-teal-600', ring: 'ring-teal-200' };
      case 'C':
        return { bg: 'bg-amber-500', text: 'text-amber-600', ring: 'ring-amber-200' };
      case 'D':
        return { bg: 'bg-orange-500', text: 'text-orange-600', ring: 'ring-orange-200' };
      case 'F':
        return { bg: 'bg-red-500', text: 'text-red-600', ring: 'ring-red-200' };
      default:
        return { bg: 'bg-gray-500', text: 'text-gray-600', ring: 'ring-gray-200' };
    }
  };

  const colors = getGradeColor();
  const circumference = 2 * Math.PI * 28; // radius = 28
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative w-16 h-16">
      <svg className="w-16 h-16 transform -rotate-90">
        <circle
          cx="32"
          cy="32"
          r="28"
          stroke="currentColor"
          strokeWidth="4"
          fill="transparent"
          className="text-gray-200 dark:text-gray-700"
        />
        <circle
          cx="32"
          cy="32"
          r="28"
          stroke="currentColor"
          strokeWidth="4"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={colors.text}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-black ${colors.text}`}>{grade}</span>
        <span className="text-[10px] text-gray-500 dark:text-gray-400">{score}%</span>
      </div>
    </div>
  );
}

// Collapsible Section Component
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  count: number;
  color: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  icon,
  count,
  color,
  isExpanded,
  onToggle,
  children,
}: CollapsibleSectionProps) {
  const colorClasses: Record<string, { bg: string; border: string; hover: string }> = {
    emerald: {
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
      border: 'border-emerald-200 dark:border-emerald-800',
      hover: 'hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30',
    },
    amber: {
      bg: 'bg-amber-50 dark:bg-amber-900/20',
      border: 'border-amber-200 dark:border-amber-800',
      hover: 'hover:bg-amber-100/50 dark:hover:bg-amber-900/30',
    },
    red: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      hover: 'hover:bg-red-100/50 dark:hover:bg-red-900/30',
    },
    indigo: {
      bg: 'bg-indigo-50 dark:bg-indigo-900/20',
      border: 'border-indigo-200 dark:border-indigo-800',
      hover: 'hover:bg-indigo-100/50 dark:hover:bg-indigo-900/30',
    },
  };

  const classes = colorClasses[color] || colorClasses.indigo;

  return (
    <div className={`${classes.bg} rounded-xl border ${classes.border} overflow-hidden`}>
      <button
        onClick={onToggle}
        className={`w-full px-4 py-3 flex items-center justify-between ${classes.hover} transition-colors`}
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">
            {title}
          </span>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">({count})</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>
      {isExpanded && <div className="p-4 bg-white/50 dark:bg-gray-800/50">{children}</div>}
    </div>
  );
}

// Index Suggestion Card
function IndexSuggestionCard({
  suggestion,
  onCopy,
  isCopied,
}: {
  suggestion: IndexSuggestion;
  onCopy: (sql: string) => void;
  isCopied: boolean;
}) {
  const [showSql, setShowSql] = useState(false);

  return (
    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-emerald-100 dark:border-emerald-900">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300">
              {suggestion.table_name}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 font-medium">
              {suggestion.index_type}
            </span>
          </div>

          <div className="flex items-center gap-2 mb-2">
            <Key className="w-3 h-3 text-gray-400" />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {suggestion.columns.join(', ')}
            </span>
          </div>

          <p className="text-xs text-gray-600 dark:text-gray-400">{suggestion.reason}</p>

          <div className="mt-2 flex items-center gap-3">
            <span className="text-[10px] text-gray-500 dark:text-gray-400">
              Impact: <strong className="text-emerald-600 dark:text-emerald-400">{suggestion.estimated_impact}</strong>
            </span>
            <span className="text-[10px] text-gray-500 dark:text-gray-400">
              Benefits {suggestion.query_count_benefiting} queries
            </span>
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={() => setShowSql(!showSql)}
          className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1"
        >
          <Code className="w-3 h-3" />
          {showSql ? 'Hide SQL' : 'Show CREATE INDEX'}
        </button>
        {showSql && (
          <button
            onClick={() => onCopy(suggestion.create_sql)}
            className="text-xs text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 flex items-center gap-1"
          >
            {isCopied ? (
              <>
                <Check className="w-3 h-3" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copy
              </>
            )}
          </button>
        )}
      </div>

      {showSql && (
        <pre className="mt-2 text-xs p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 overflow-x-auto text-gray-700 dark:text-gray-300">
          {suggestion.create_sql}
        </pre>
      )}
    </div>
  );
}

// Normalization Issue Card
function NormalizationIssueCard({ issue }: { issue: NormalizationIssue }) {
  return (
    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-amber-100 dark:border-amber-900">
      <div className="flex items-center gap-2 mb-1">
        <Table2 className="w-3.5 h-3.5 text-amber-500" />
        <span className="text-xs font-bold text-amber-700 dark:text-amber-300">
          {issue.table_name}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 font-medium uppercase">
          {issue.issue_type}
        </span>
      </div>

      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{issue.description}</p>

      {issue.affected_columns.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {issue.affected_columns.map((col, i) => (
            <span
              key={i}
              className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
            >
              {col}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-start gap-2 p-2 bg-amber-50 dark:bg-amber-900/20 rounded">
        <Lightbulb className="w-3 h-3 text-amber-500 mt-0.5 flex-shrink-0" />
        <span className="text-xs text-amber-700 dark:text-amber-400">{issue.recommendation}</span>
      </div>
    </div>
  );
}

// Schema Issue Card (for anti-patterns)
function SchemaIssueCard({
  issue,
  onCopy,
  isCopied,
}: {
  issue: SchemaIssue;
  onCopy?: (sql: string) => void;
  isCopied?: boolean;
}) {
  const [showSql, setShowSql] = useState(false);

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400';
      case 'error':
        return 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400';
      case 'warning':
        return 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400';
      default:
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'error':
        return <XCircle className="w-3 h-3" />;
      case 'warning':
        return <AlertTriangle className="w-3 h-3" />;
      default:
        return <Lightbulb className="w-3 h-3" />;
    }
  };

  return (
    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-red-100 dark:border-red-900">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase flex items-center gap-1 ${getSeverityColor(issue.severity)}`}>
            {getSeverityIcon(issue.severity)}
            {issue.severity}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 font-medium">
            {issue.category}
          </span>
        </div>
      </div>

      <h4 className="text-xs font-bold text-gray-800 dark:text-gray-200 mb-1">{issue.title}</h4>
      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{issue.description}</p>

      {issue.affected_objects.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {issue.affected_objects.map((obj, i) => (
            <span
              key={i}
              className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400"
            >
              {obj}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-start gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
        <CheckCircle className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
        <span className="text-xs text-blue-700 dark:text-blue-400">{issue.recommendation}</span>
      </div>

      {issue.fix_sql && onCopy && (
        <>
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={() => setShowSql(!showSql)}
              className="text-xs text-red-600 dark:text-red-400 hover:underline flex items-center gap-1"
            >
              <Code className="w-3 h-3" />
              {showSql ? 'Hide Fix SQL' : 'Show Fix SQL'}
            </button>
            {showSql && (
              <button
                onClick={() => onCopy(issue.fix_sql!)}
                className="text-xs text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 flex items-center gap-1"
              >
                {isCopied ? (
                  <>
                    <Check className="w-3 h-3" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copy
                  </>
                )}
              </button>
            )}
          </div>

          {showSql && (
            <pre className="mt-2 text-xs p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 overflow-x-auto text-gray-700 dark:text-gray-300">
              {issue.fix_sql}
            </pre>
          )}
        </>
      )}
    </div>
  );
}

// Table Summary Card
function TableSummaryCard({ table }: { table: TableHealthSummary }) {
  const [expanded, setExpanded] = useState(false);
  const hasIssues = table.issues.length > 0 || table.suggestions.length > 0;

  return (
    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-indigo-100 dark:border-indigo-900">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Table2 className="w-4 h-4 text-indigo-500" />
          <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300">
            {table.table_name}
          </span>

          {/* Quick stats */}
          <div className="flex items-center gap-2 text-[10px] text-gray-500 dark:text-gray-400">
            <span>{table.column_count} cols</span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>{table.index_count} indexes</span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>{table.foreign_key_count} FKs</span>
          </div>

          {/* Status icons */}
          <div className="flex items-center gap-1">
            {table.has_primary_key ? (
              <span title="Has primary key">
                <Key className="w-3 h-3 text-emerald-500" />
              </span>
            ) : (
              <span title="Missing primary key">
                <Key className="w-3 h-3 text-red-400" />
              </span>
            )}
          </div>
        </div>

        {hasIssues && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400"
          >
            <span>
              {table.issues.length + table.suggestions.length} items
            </span>
            {expanded ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </button>
        )}
      </div>

      {expanded && hasIssues && (
        <div className="mt-3 pt-3 border-t border-indigo-100 dark:border-indigo-900 space-y-2">
          {table.issues.map((issue, i) => (
            <div
              key={i}
              className="text-xs p-2 bg-red-50 dark:bg-red-900/20 rounded flex items-start gap-2"
            >
              <AlertTriangle className="w-3 h-3 text-red-500 mt-0.5 flex-shrink-0" />
              <span className="text-red-700 dark:text-red-400">{issue.title}</span>
            </div>
          ))}
          {table.suggestions.map((suggestion, i) => (
            <div
              key={i}
              className="text-xs p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded flex items-start gap-2"
            >
              <TrendingUp className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />
              <span className="text-emerald-700 dark:text-emerald-400">
                Add index on {suggestion.columns.join(', ')}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SchemaHealthDashboard;
