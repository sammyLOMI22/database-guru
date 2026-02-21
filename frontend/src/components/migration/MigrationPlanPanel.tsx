import { useState, useEffect } from 'react';
import { Loader2, AlertTriangle, CheckCircle, Clock, Lock, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { migrationAPI } from '../../services/migrationApi';
import type { MigrationProjectDetail, MigrationPlanResponse, MigrationStep } from '../../types/migration';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  critical: 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-200',
};

interface Props {
  project: MigrationProjectDetail;
  onRefresh: () => void;
}

export function MigrationPlanPanel({ project, onRefresh }: Props) {
  const [plan, setPlan] = useState<MigrationPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [checkedPre, setCheckedPre] = useState<Set<number>>(new Set());
  const [checkedPost, setCheckedPost] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (project.migration_plan) {
      migrationAPI.getPlan(project.id).then(setPlan).catch(() => {});
    }
  }, [project.id, project.migration_plan]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await migrationAPI.generatePlan(project.id);
      setPlan(result);
      onRefresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Plan generation failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleStep = (n: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  };

  const togglePre = (i: number) => {
    setCheckedPre((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const togglePost = (i: number) => {
    setCheckedPost((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          Migration Plan
        </h3>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-xs font-bold uppercase tracking-wide transition-all shadow-lg"
          data-testid="generate-plan-button"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : plan ? 'Regenerate Plan' : 'Generate Plan'}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {plan && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">Complexity</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-1">{plan.overall_complexity}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">Est. Downtime</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-1">{plan.total_estimated_downtime}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">Maintenance Window</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-1">
                  {plan.recommended_maintenance_window ? 'Recommended' : 'Not Required'}
                </p>
              </div>
            </div>
            {plan.rollback_strategy && (
              <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 mb-1">Rollback Strategy</p>
                <p className="text-xs text-gray-700 dark:text-gray-300">{plan.rollback_strategy}</p>
              </div>
            )}
          </div>

          {/* Pre-migration checklist */}
          {plan.pre_migration_checklist.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
              <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700 dark:text-amber-400 mb-2">
                Pre-Migration Checklist
              </p>
              {plan.pre_migration_checklist.map((item, i) => (
                <label key={i} className="flex items-center gap-2 py-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checkedPre.has(i)}
                    onChange={() => togglePre(i)}
                    className="rounded border-amber-300"
                  />
                  <span className={`text-xs ${checkedPre.has(i) ? 'line-through text-gray-400' : 'text-gray-700 dark:text-gray-300'}`}>
                    {item}
                  </span>
                </label>
              ))}
            </div>
          )}

          {/* Steps */}
          <div className="space-y-2">
            {plan.steps.map((step) => (
              <StepCard
                key={step.step_number}
                step={step}
                expanded={expandedSteps.has(step.step_number)}
                onToggle={() => toggleStep(step.step_number)}
              />
            ))}
          </div>

          {/* Post-migration checklist */}
          {plan.post_migration_checklist.length > 0 && (
            <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
              <p className="text-[10px] font-bold uppercase tracking-wide text-green-700 dark:text-green-400 mb-2">
                Post-Migration Checklist
              </p>
              {plan.post_migration_checklist.map((item, i) => (
                <label key={i} className="flex items-center gap-2 py-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checkedPost.has(i)}
                    onChange={() => togglePost(i)}
                    className="rounded border-green-300"
                  />
                  <span className={`text-xs ${checkedPost.has(i) ? 'line-through text-gray-400' : 'text-gray-700 dark:text-gray-300'}`}>
                    {item}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StepCard({ step, expanded, onToggle }: { step: MigrationStep; expanded: boolean; onToggle: () => void }) {
  const [copied, setCopied] = useState(false);

  const copyHint = () => {
    if (step.sql_hint) {
      navigator.clipboard.writeText(step.sql_hint);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-bold flex items-center justify-center">
            {step.step_number}
          </span>
          <span className="text-sm font-bold text-gray-900 dark:text-white">{step.action}</span>
          {step.table_name && <span className="text-xs text-gray-500 font-mono">{step.table_name}</span>}
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK_COLORS[step.risk_level] || RISK_COLORS.low}`}>
            {step.risk_level}
          </span>
          {step.lock_type !== 'none' && (
            <span className="flex items-center gap-1 text-[10px] text-gray-400">
              <Lock className="w-3 h-3" /> {step.lock_type}
            </span>
          )}
          <span className="flex items-center gap-1 text-[10px] text-gray-400">
            <Clock className="w-3 h-3" /> {step.estimated_duration}
          </span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3 space-y-3">
          <p className="text-xs text-gray-700 dark:text-gray-300">{step.description}</p>

          {step.sql_hint && (
            <div className="relative">
              <pre className="text-xs bg-gray-900 text-green-300 p-3 rounded-lg overflow-x-auto font-mono">
                {step.sql_hint}
              </pre>
              <button
                onClick={copyHint}
                className="absolute top-2 right-2 p-1 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
                title="Copy SQL"
              >
                {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3 text-gray-400" />}
              </button>
            </div>
          )}

          {step.warnings.length > 0 && (
            <div className="space-y-1">
              {step.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-4 text-[10px] text-gray-400">
            {step.is_reversible && (
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3 text-green-500" /> Reversible
              </span>
            )}
            {step.depends_on.length > 0 && (
              <span>Depends on: {step.depends_on.map((d) => `#${d}`).join(', ')}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
