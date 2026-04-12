import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { llmProviderApi, type TaskRoutingRule, type RegistryProvider } from '../services/llmProviderApi';

const TASK_TYPES = [
  { value: 'sql_generation', label: 'SQL Generation' },
  { value: 'narratives', label: 'Data Narratives' },
  { value: 'query_planning', label: 'Query Planning' },
  { value: 'error_correction', label: 'Error Correction' },
  { value: 'lineage_narrative', label: 'Lineage Narrative' },
  { value: 'impact_analysis', label: 'Impact Analysis' },
  { value: 'schema_health', label: 'Schema Health' },
  { value: 'lineage_conversation', label: 'Lineage Q&A' },
  { value: 'pattern_intelligence', label: 'Pattern Intelligence' },
  { value: 'migration_planner', label: 'Migration Planner' },
  { value: 'explain_analysis', label: 'EXPLAIN Analysis' },
];

interface TaskRoutingConfigProps {
  providers: RegistryProvider[];
}

export function TaskRoutingConfig({ providers }: TaskRoutingConfigProps) {
  const [expanded, setExpanded] = useState(false);
  const [routes, setRoutes] = useState<TaskRoutingRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (expanded && routes.length === 0) {
      loadRoutes();
    }
  }, [expanded]);

  const loadRoutes = async () => {
    setLoading(true);
    try {
      const data = await llmProviderApi.listRouting();
      setRoutes(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const getRouteForTask = (taskType: string) => {
    return routes.find((r) => r.task_type === taskType);
  };

  const handleProviderChange = async (taskType: string, providerName: string) => {
    setSaving(taskType);
    try {
      if (providerName === 'default') {
        await llmProviderApi.deleteRouting(taskType);
        setRoutes((prev) => prev.filter((r) => r.task_type !== taskType));
      } else {
        const result = await llmProviderApi.upsertRouting({
          task_type: taskType,
          primary_provider: providerName,
        });
        setRoutes((prev) => {
          const existing = prev.findIndex((r) => r.task_type === taskType);
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = result;
            return updated;
          }
          return [...prev, result];
        });
      }
    } catch {
      // silent
    } finally {
      setSaving(null);
    }
  };

  const isFrontier = (providerName: string) => {
    const p = providers.find((pr) => pr.name === providerName);
    return p && p.data_locality !== 'local';
  };

  return (
    <div className="glass-panel rounded-[1.5rem] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-300">
          Advanced: Per-Task Provider Routing
        </h4>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="px-6 pb-6">
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-gray-400 py-4">
              <Loader2 className="w-3 h-3 animate-spin" />
              Loading routing rules...
            </div>
          ) : (
            <div className="space-y-1">
              {/* Header */}
              <div className="grid grid-cols-[1fr_180px] gap-4 px-3 py-2">
                <span className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-500">Task</span>
                <span className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-500">Provider</span>
              </div>

              {/* Rows */}
              {TASK_TYPES.map((task) => {
                const route = getRouteForTask(task.value);
                const currentProvider = route?.primary_provider || 'default';
                const frontier = currentProvider !== 'default' && isFrontier(currentProvider);

                return (
                  <div
                    key={task.value}
                    className={`grid grid-cols-[1fr_180px] gap-4 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors ${
                      frontier ? 'border-l-2 border-amber-500' : 'border-l-2 border-transparent'
                    }`}
                  >
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 flex items-center">
                      {task.label}
                      {saving === task.value && <Loader2 className="w-3 h-3 animate-spin ml-2 text-blue-400" />}
                    </span>
                    <select
                      value={currentProvider}
                      onChange={(e) => handleProviderChange(task.value, e.target.value)}
                      className="text-xs bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-gray-700 dark:text-gray-300 focus:outline-none focus:border-blue-500/50"
                    >
                      <option value="default">Default (Ollama)</option>
                      {providers.map((p) => (
                        <option key={p.name} value={p.name}>
                          {p.name} {p.data_locality !== 'local' ? '⚡' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          )}

          <p className="mt-4 text-[10px] text-gray-500 dark:text-gray-500 italic">
            Tasks routed to frontier providers are marked with an amber border.
            Default uses your active local provider.
          </p>
        </div>
      )}
    </div>
  );
}
