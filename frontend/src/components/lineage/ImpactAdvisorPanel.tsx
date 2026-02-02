/**
 * ImpactAdvisorPanel - Phase 12.2
 *
 * Displays LLM-enhanced impact analysis with:
 * - Risk explanation (why change is risky)
 * - Migration plan (step-by-step guide)
 * - SQL patches (updated queries)
 */
import { useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  GitBranch,
  Lightbulb,
  Clock,
  Shield,
  Code,
  CheckCircle,
  XCircle,
  Copy,
  Check,
} from 'lucide-react';
import type { ImpactAdviceResponse, MigrationStep, SQLPatch } from '../../types/lineage';

interface ImpactAdvisorPanelProps {
  advice: ImpactAdviceResponse | null;
  isLoading?: boolean;
}

export function ImpactAdvisorPanel({ advice, isLoading = false }: ImpactAdvisorPanelProps) {
  const [showMigrationSteps, setShowMigrationSteps] = useState(false);
  const [showPatches, setShowPatches] = useState(false);
  const [copiedPatchId, setCopiedPatchId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-4 border border-indigo-200 dark:border-indigo-800">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
            Generating impact advice...
          </span>
        </div>
      </div>
    );
  }

  if (!advice) {
    return null;
  }

  const { risk_explanation, migration_plan, sql_patches } = advice;

  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'high':
        return 'text-red-600 dark:text-red-400';
      case 'medium':
        return 'text-amber-600 dark:text-amber-400';
      case 'low':
        return 'text-green-600 dark:text-green-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getRiskBg = (level: string) => {
    switch (level.toLowerCase()) {
      case 'high':
        return 'bg-red-100 dark:bg-red-900/30';
      case 'medium':
        return 'bg-amber-100 dark:bg-amber-900/30';
      case 'low':
        return 'bg-green-100 dark:bg-green-900/30';
      default:
        return 'bg-gray-100 dark:bg-gray-800';
    }
  };

  const handleCopyPatch = async (patch: SQLPatch) => {
    await navigator.clipboard.writeText(patch.patched_sql);
    setCopiedPatchId(patch.query_id);
    setTimeout(() => setCopiedPatchId(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* LLM Badge */}
      {advice.llm_used && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 font-bold uppercase tracking-widest">
            AI Enhanced
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Generated {advice.generated_at ? new Date(advice.generated_at).toLocaleString() : 'just now'}
          </span>
        </div>
      )}

      {/* Risk Explanation */}
      {risk_explanation && (
        <div className={`rounded-xl border overflow-hidden ${
          risk_explanation.risk_level === 'high'
            ? 'border-red-200 dark:border-red-800'
            : risk_explanation.risk_level === 'medium'
            ? 'border-amber-200 dark:border-amber-800'
            : 'border-green-200 dark:border-green-800'
        }`}>
          {/* Header */}
          <div className={`px-4 py-3 ${getRiskBg(risk_explanation.risk_level)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className={`w-4 h-4 ${getRiskColor(risk_explanation.risk_level)}`} />
                <span className={`text-xs font-black uppercase tracking-widest ${getRiskColor(risk_explanation.risk_level)}`}>
                  {risk_explanation.risk_level} Risk
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400">
                  {Math.round(risk_explanation.confidence * 100)}% Confidence
                </span>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-4 bg-white/50 dark:bg-gray-800/50">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
              {risk_explanation.summary}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              {risk_explanation.detailed_explanation}
            </p>

            {/* Affected Areas */}
            {risk_explanation.affected_areas.length > 0 && (
              <div className="mt-3">
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">
                  Affected Areas
                </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {risk_explanation.affected_areas.map((area, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                    >
                      {area}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {risk_explanation.recommendations.length > 0 && (
              <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="w-3.5 h-3.5 text-blue-500" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600 dark:text-blue-400">
                    Recommendations
                  </span>
                </div>
                <ul className="space-y-1">
                  {risk_explanation.recommendations.map((rec, i) => (
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
      )}

      {/* Migration Plan */}
      {migration_plan && (
        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-200 dark:border-purple-800 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-purple-100/50 dark:bg-purple-900/30 border-b border-purple-200 dark:border-purple-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-purple-500" />
                <span className="text-xs font-black uppercase tracking-widest text-purple-700 dark:text-purple-300">
                  Migration Plan
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-purple-500" />
                  <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400">
                    {migration_plan.estimated_downtime} downtime
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {migration_plan.rollback_possible ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500" />
                  )}
                  <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400">
                    {migration_plan.rollback_possible ? 'Reversible' : 'Irreversible'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Warnings */}
          {migration_plan.warnings.length > 0 && (
            <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
              {migration_plan.warnings.map((warning, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
                  <AlertTriangle className="w-3 h-3" />
                  {warning}
                </div>
              ))}
            </div>
          )}

          {/* Toggle Steps */}
          <button
            onClick={() => setShowMigrationSteps(!showMigrationSteps)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-purple-100/50 dark:hover:bg-purple-900/30 transition-colors"
          >
            <span className="text-xs font-medium text-purple-600 dark:text-purple-400">
              {migration_plan.steps.length} Steps
            </span>
            {showMigrationSteps ? (
              <ChevronUp className="w-4 h-4 text-purple-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-purple-500" />
            )}
          </button>

          {/* Steps */}
          {showMigrationSteps && (
            <div className="p-4 space-y-3 bg-white/50 dark:bg-gray-800/50">
              {migration_plan.steps.map((step) => (
                <MigrationStepCard key={step.step_number} step={step} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* SQL Patches */}
      {sql_patches.length > 0 && (
        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-200 dark:border-emerald-800 overflow-hidden">
          {/* Header */}
          <button
            onClick={() => setShowPatches(!showPatches)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4 text-emerald-500" />
              <span className="text-xs font-black uppercase tracking-widest text-emerald-700 dark:text-emerald-300">
                SQL Patches ({sql_patches.length})
              </span>
            </div>
            {showPatches ? (
              <ChevronUp className="w-4 h-4 text-emerald-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-emerald-500" />
            )}
          </button>

          {/* Patches */}
          {showPatches && (
            <div className="p-4 space-y-4 bg-white/50 dark:bg-gray-800/50">
              {sql_patches.map((patch) => (
                <div
                  key={patch.query_id}
                  className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-600 dark:text-gray-400">
                        Query #{patch.query_id}
                      </span>
                      {patch.requires_review && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 font-bold">
                          Review Required
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => handleCopyPatch(patch)}
                      className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300"
                    >
                      {copiedPatchId === patch.query_id ? (
                        <>
                          <Check className="w-3 h-3" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copy Patched
                        </>
                      )}
                    </button>
                  </div>

                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                    {patch.change_description}
                  </p>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-1 block">
                        Original
                      </span>
                      <pre className="text-xs p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800 overflow-x-auto text-red-700 dark:text-red-400">
                        {patch.original_sql}
                      </pre>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-1 block">
                        Patched
                      </span>
                      <pre className="text-xs p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded border border-emerald-200 dark:border-emerald-800 overflow-x-auto text-emerald-700 dark:text-emerald-400">
                        {patch.patched_sql}
                      </pre>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${patch.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-bold text-gray-500">
                      {Math.round(patch.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MigrationStepCard({ step }: { step: MigrationStep }) {
  const [expanded, setExpanded] = useState(false);

  const getRiskIcon = () => {
    switch (step.risk_level) {
      case 'high':
        return <Shield className="w-3 h-3 text-red-500" />;
      case 'medium':
        return <Shield className="w-3 h-3 text-amber-500" />;
      default:
        return <Shield className="w-3 h-3 text-green-500" />;
    }
  };

  return (
    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-purple-100 dark:border-purple-900">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs font-bold">
          {step.step_number}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-purple-700 dark:text-purple-300 uppercase">
              {step.action}
            </span>
            {getRiskIcon()}
            {!step.reversible && (
              <span className="text-[10px] px-1 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 font-bold">
                Irreversible
              </span>
            )}
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            {step.description}
          </p>

          {step.sql && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 text-xs text-purple-600 dark:text-purple-400 hover:underline flex items-center gap-1"
            >
              <Code className="w-3 h-3" />
              {expanded ? 'Hide SQL' : 'Show SQL'}
            </button>
          )}

          {expanded && step.sql && (
            <pre className="mt-2 text-xs p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 overflow-x-auto text-gray-700 dark:text-gray-300">
              {step.sql}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImpactAdvisorPanel;
