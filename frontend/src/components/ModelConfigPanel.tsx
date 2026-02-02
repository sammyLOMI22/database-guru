/**
 * ModelConfigPanel - Per-Task Model Configuration UI
 *
 * Allows users to configure different LLM models for different tasks:
 * - SQL Generation: Use specialized SQL models (duckdb-nsql, sqlcoder)
 * - Narratives: Use general-purpose models (llama3.2, gemma)
 * - Query Planning: Use reasoning-capable models
 * - Error Correction: Use code-focused models
 */
import { useState, useEffect } from 'react';
import { Cpu, Clock, Zap, MessageSquare, GitBranch, AlertTriangle, Info, RefreshCw, FileText, Activity, MessageCircle } from 'lucide-react';

interface ModelConfig {
  model_sql_generation: string | null;
  model_narratives: string | null;
  model_query_planning: string | null;
  model_error_correction: string | null;
  timeout_sql_generation: number;
  timeout_narratives: number;
  timeout_query_planning: number;
  timeout_error_correction: number;
  enable_query_templates: boolean;
  enable_location_preprocessing: boolean;
  // Prompt Optimization (Phase 2.2)
  enable_prompt_optimization: boolean;
  prompt_model_size: string; // auto|small|medium|large
  enable_schema_compression: boolean;
  max_schema_tables: number;
  enable_example_selection: boolean;
  max_few_shot_examples: number;
  // Phase 12: Lineage Intelligence
  model_lineage_narrative: string | null;
  model_impact_analysis: string | null;
  model_schema_health: string | null;
  model_lineage_conversation: string | null;
  timeout_lineage_narrative: number;
  timeout_impact_analysis: number;
  timeout_schema_health: number;
  timeout_lineage_conversation: number;
}

interface AvailableModel {
  name: string;
  modified_at: string;
  size: number;
}

interface ModelConfigPanelProps {
  config: ModelConfig;
  onChange: (config: ModelConfig) => void;
  disabled?: boolean;
}

// Task type configuration with icons and descriptions
const TASK_CONFIGS = [
  {
    key: 'sql_generation',
    label: 'SQL Generation',
    icon: Cpu,
    description: 'Model for generating SQL queries from natural language',
    hint: 'Recommended: duckdb-nsql, sqlcoder, or any code-focused model',
    defaultTimeout: 30,
    modelKey: 'model_sql_generation' as const,
    timeoutKey: 'timeout_sql_generation' as const,
    color: 'blue',
  },
  {
    key: 'narratives',
    label: 'Result Narratives',
    icon: MessageSquare,
    description: 'Model for generating human-readable summaries of query results',
    hint: 'Recommended: llama3.2, gemma, or any general-purpose model',
    defaultTimeout: 15,
    modelKey: 'model_narratives' as const,
    timeoutKey: 'timeout_narratives' as const,
    color: 'green',
  },
  {
    key: 'query_planning',
    label: 'Query Planning',
    icon: GitBranch,
    description: 'Model for planning complex multi-table queries',
    hint: 'Recommended: Models with good reasoning ability',
    defaultTimeout: 20,
    modelKey: 'model_query_planning' as const,
    timeoutKey: 'timeout_query_planning' as const,
    color: 'purple',
  },
  {
    key: 'error_correction',
    label: 'Error Correction',
    icon: AlertTriangle,
    description: 'Model for analyzing and fixing SQL errors',
    hint: 'Recommended: Code-focused models for error analysis',
    defaultTimeout: 15,
    modelKey: 'model_error_correction' as const,
    timeoutKey: 'timeout_error_correction' as const,
    color: 'orange',
  },
  // Phase 12: Lineage Intelligence
  {
    key: 'lineage_narrative',
    label: 'Lineage Narrative',
    icon: FileText,
    description: 'Model for explaining data lineage in business terms',
    hint: 'Recommended: General-purpose models with good reasoning',
    defaultTimeout: 15,
    modelKey: 'model_lineage_narrative' as const,
    timeoutKey: 'timeout_lineage_narrative' as const,
    color: 'indigo',
  },
  {
    key: 'impact_analysis',
    label: 'Impact Advisor',
    icon: AlertTriangle,
    description: 'Model for generating migration plans and risk explanations',
    hint: 'Recommended: Models with SQL and reasoning ability',
    defaultTimeout: 20,
    modelKey: 'model_impact_analysis' as const,
    timeoutKey: 'timeout_impact_analysis' as const,
    color: 'red',
  },
  {
    key: 'schema_health',
    label: 'Schema Health',
    icon: Activity,
    description: 'Model for analyzing database design and suggesting improvements',
    hint: 'Recommended: Models familiar with database best practices',
    defaultTimeout: 30,
    modelKey: 'model_schema_health' as const,
    timeoutKey: 'timeout_schema_health' as const,
    color: 'teal',
  },
  {
    key: 'lineage_conversation',
    label: 'Lineage Chat',
    icon: MessageCircle,
    description: 'Model for answering natural language questions about schema',
    hint: 'Recommended: Conversational models with good context handling',
    defaultTimeout: 15,
    modelKey: 'model_lineage_conversation' as const,
    timeoutKey: 'timeout_lineage_conversation' as const,
    color: 'cyan',
  },
];

export function ModelConfigPanel({ config, onChange, disabled = false }: ModelConfigPanelProps) {
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // Fetch available models from Ollama
  useEffect(() => {
    fetchAvailableModels();
  }, []);

  const fetchAvailableModels = async () => {
    try {
      setLoadingModels(true);
      setModelsError(null);
      const baseURL = (import.meta as any).env?.VITE_API_URL || '';
      const response = await fetch(`${baseURL}/api/models/details`);
      if (!response.ok) throw new Error('Failed to fetch models');
      const data = await response.json();
      setAvailableModels(data.models || []);
    } catch (err) {
      setModelsError(err instanceof Error ? err.message : 'Failed to load models');
      setAvailableModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleModelChange = (key: keyof ModelConfig, value: string | null) => {
    onChange({
      ...config,
      [key]: value === '' ? null : value,
    });
  };

  const handleNumberChange = (key: keyof ModelConfig, value: number) => {
    onChange({
      ...config,
      [key]: Math.max(1, Math.min(300, value)),
    });
  };

  const handleToggleChange = (key: keyof ModelConfig, value: boolean) => {
    onChange({
      ...config,
      [key]: value,
    });
  };

  const getColorClasses = (color: string) => {
    const colors: Record<string, { gradient: string; border: string; text: string; iconBg: string; icon: string }> = {
      blue: {
        gradient: 'bg-gradient-to-br from-blue-500/10 via-transparent to-cyan-500/5',
        border: 'border-blue-500/20',
        text: 'text-blue-600 dark:text-blue-400',
        iconBg: 'bg-blue-500/20',
        icon: 'text-blue-500',
      },
      green: {
        gradient: 'bg-gradient-to-br from-emerald-500/10 via-transparent to-green-500/5',
        border: 'border-emerald-500/20',
        text: 'text-emerald-600 dark:text-emerald-400',
        iconBg: 'bg-emerald-500/20',
        icon: 'text-emerald-500',
      },
      purple: {
        gradient: 'bg-gradient-to-br from-purple-500/10 via-transparent to-indigo-500/5',
        border: 'border-purple-500/20',
        text: 'text-purple-600 dark:text-purple-400',
        iconBg: 'bg-purple-500/20',
        icon: 'text-purple-500',
      },
      orange: {
        gradient: 'bg-gradient-to-br from-orange-500/10 via-transparent to-amber-500/5',
        border: 'border-orange-500/20',
        text: 'text-orange-600 dark:text-orange-400',
        iconBg: 'bg-orange-500/20',
        icon: 'text-orange-500',
      },
      // Phase 12: Lineage Intelligence colors
      indigo: {
        gradient: 'bg-gradient-to-br from-indigo-500/10 via-transparent to-violet-500/5',
        border: 'border-indigo-500/20',
        text: 'text-indigo-600 dark:text-indigo-400',
        iconBg: 'bg-indigo-500/20',
        icon: 'text-indigo-500',
      },
      red: {
        gradient: 'bg-gradient-to-br from-red-500/10 via-transparent to-rose-500/5',
        border: 'border-red-500/20',
        text: 'text-red-600 dark:text-red-400',
        iconBg: 'bg-red-500/20',
        icon: 'text-red-500',
      },
      teal: {
        gradient: 'bg-gradient-to-br from-teal-500/10 via-transparent to-emerald-500/5',
        border: 'border-teal-500/20',
        text: 'text-teal-600 dark:text-teal-400',
        iconBg: 'bg-teal-500/20',
        icon: 'text-teal-500',
      },
      cyan: {
        gradient: 'bg-gradient-to-br from-cyan-500/10 via-transparent to-sky-500/5',
        border: 'border-cyan-500/20',
        text: 'text-cyan-600 dark:text-cyan-400',
        iconBg: 'bg-cyan-500/20',
        icon: 'text-cyan-500',
      },
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-blue-500">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white">
              Model Configuration
            </h3>
            <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">
              Assign different models for optimal performance
            </p>
          </div>
        </div>
        <button
          onClick={fetchAvailableModels}
          disabled={loadingModels || disabled}
          className="flex items-center gap-2 px-3 py-2 glass-card rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-600 dark:text-gray-400 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loadingModels ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Models error message */}
      {modelsError && (
        <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-amber-500/10 via-transparent to-yellow-500/5 border-amber-500/20">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-600 dark:text-amber-400">
            <AlertTriangle className="w-4 h-4" />
            Could not load available models. Make sure Ollama is running.
          </div>
        </div>
      )}

      {/* Per-Task Model Configuration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TASK_CONFIGS.map((task) => {
          const classes = getColorClasses(task.color);
          const Icon = task.icon;
          const currentModel = config[task.modelKey];
          const currentTimeout = config[task.timeoutKey];

          return (
            <div
              key={task.key}
              className={`glass-card rounded-xl p-4 ${classes.gradient} ${classes.border}`}
            >
              {/* Task Header */}
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-8 h-8 rounded-lg ${classes.iconBg} flex items-center justify-center ${classes.icon}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className={`text-xs font-black uppercase tracking-widest ${classes.text}`}>{task.label}</span>
              </div>

              {/* Description */}
              <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mb-4">{task.description}</p>

              {/* Model Selection */}
              <div className="mb-4">
                <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400 mb-2">
                  Model
                </label>
                <select
                  value={currentModel || ''}
                  onChange={(e) => handleModelChange(task.modelKey, e.target.value)}
                  disabled={disabled || loadingModels}
                  className="w-full glass-panel rounded-lg px-3 py-2 text-xs font-medium text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 border-white/10 bg-transparent appearance-none cursor-pointer disabled:opacity-50"
                >
                  <option value="">Default (system model)</option>
                  {availableModels.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] font-medium text-gray-400 mt-1">{task.hint}</p>
              </div>

              {/* Timeout Configuration */}
              <div className="glass-panel rounded-lg p-3 border-white/10">
                <label className="flex items-center gap-1 text-[11px] font-black uppercase tracking-widest text-gray-600 dark:text-gray-400 mb-2">
                  <Clock className="w-3 h-3" />
                  Timeout: {currentTimeout}s
                </label>
                <input
                  type="range"
                  min="5"
                  max="120"
                  step="5"
                  value={currentTimeout}
                  onChange={(e) => handleNumberChange(task.timeoutKey, parseInt(e.target.value))}
                  disabled={disabled}
                  className="w-full h-1.5 rounded-full appearance-none bg-gradient-to-r from-gray-300 to-blue-500 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] font-bold text-gray-400 mt-1">
                  <span>5s</span>
                  <span className="text-blue-500">Default: {task.defaultTimeout}s</span>
                  <span>120s</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Optimization Features */}
      <div className="mt-6 pt-6 border-t border-white/10">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-500">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-black uppercase tracking-widest text-gray-900 dark:text-white">
              Optimization Features
            </h4>
            <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">
              Improve response time and accuracy for smaller models
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {/* Query Templates Toggle */}
          <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-blue-500/5 via-transparent to-cyan-500/5 border-blue-500/10">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">Query Templates</label>
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-1">
                  Bypass LLM for simple patterns like "show all customers"
                </p>
              </div>
              <button
                onClick={() => handleToggleChange('enable_query_templates', !config.enable_query_templates)}
                disabled={disabled}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all disabled:opacity-50 ${config.enable_query_templates ? 'bg-gradient-to-r from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/20' : 'bg-gray-300 dark:bg-gray-600'
                  }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${config.enable_query_templates ? 'translate-x-6' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>
          </div>

          {/* Location Preprocessing Toggle */}
          <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-emerald-500/5 via-transparent to-green-500/5 border-emerald-500/10">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">Location Preprocessing</label>
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-1">
                  Normalize locations (California → CA) based on database format
                </p>
              </div>
              <button
                onClick={() => handleToggleChange('enable_location_preprocessing', !config.enable_location_preprocessing)}
                disabled={disabled}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all disabled:opacity-50 ${config.enable_location_preprocessing ? 'bg-gradient-to-r from-emerald-500 to-green-500 shadow-lg shadow-emerald-500/20' : 'bg-gray-300 dark:bg-gray-600'
                  }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${config.enable_location_preprocessing ? 'translate-x-6' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Prompt Optimization Toggle */}
        <div className="glass-card rounded-xl p-4 mt-3 bg-gradient-to-r from-purple-500/10 via-transparent to-indigo-500/5 border-purple-500/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <label className="text-xs font-black uppercase tracking-widest text-gray-700 dark:text-gray-300">
                  Prompt Optimization
                </label>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 font-bold uppercase tracking-widest">
                  Phase 2.2
                </span>
              </div>
              <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-1">
                Compress prompts for faster responses (~40% token reduction)
              </p>
            </div>
            <button
              onClick={() => handleToggleChange('enable_prompt_optimization', !config.enable_prompt_optimization)}
              disabled={disabled}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all disabled:opacity-50 ${config.enable_prompt_optimization ? 'bg-gradient-to-r from-purple-500 to-indigo-500 shadow-lg shadow-purple-500/20' : 'bg-gray-300 dark:bg-gray-600'
                }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${config.enable_prompt_optimization ? 'translate-x-6' : 'translate-x-1'
                  }`}
              />
            </button>
          </div>

          {/* Advanced Settings (shown when enabled) */}
          {config.enable_prompt_optimization && (
            <div className="mt-4 pt-4 border-t border-purple-500/20 space-y-4">
              {/* Model Size Selection */}
              <div>
                <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400 mb-2">
                  Model Size Detection
                </label>
                <select
                  value={config.prompt_model_size || 'auto'}
                  onChange={(e) => handleModelChange('prompt_model_size' as keyof ModelConfig, e.target.value)}
                  disabled={disabled}
                  className="w-full glass-panel rounded-lg px-3 py-2 text-xs font-medium text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 border-white/10 bg-transparent appearance-none cursor-pointer disabled:opacity-50"
                >
                  <option value="auto">Auto-detect from model name</option>
                  <option value="small">Small (&lt;7B params, 2K context)</option>
                  <option value="medium">Medium (7-13B params, 4K context)</option>
                  <option value="large">Large (13B+ params, 8K+ context)</option>
                </select>
                <p className="text-[11px] font-medium text-gray-400 mt-1">
                  Controls token budget allocation for prompts
                </p>
              </div>

              {/* Schema Compression Toggle */}
              <div className="flex items-center justify-between glass-panel rounded-lg p-3 border-white/10">
                <div>
                  <label className="text-[11px] font-bold uppercase tracking-widest text-gray-700 dark:text-gray-300">Schema Compression</label>
                  <p className="text-[11px] font-medium text-gray-400 mt-0.5">
                    Include only relevant tables in prompts
                  </p>
                </div>
                <button
                  onClick={() => handleToggleChange('enable_schema_compression', !config.enable_schema_compression)}
                  disabled={disabled}
                  className={`relative inline-flex h-6 w-10 items-center rounded-full transition-all disabled:opacity-50 ${config.enable_schema_compression ? 'bg-purple-500 shadow-lg shadow-purple-500/20' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${config.enable_schema_compression ? 'translate-x-5' : 'translate-x-1'
                      }`}
                  />
                </button>
              </div>

              {/* Max Schema Tables */}
              {config.enable_schema_compression && (
                <div className="ml-4 glass-panel rounded-lg p-3 border-white/10">
                  <label className="block text-[11px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-2">
                    Max Tables: <span className="text-purple-500">{config.max_schema_tables || 10}</span>
                  </label>
                  <input
                    type="range"
                    min="3"
                    max="20"
                    step="1"
                    value={config.max_schema_tables || 10}
                    onChange={(e) => handleNumberChange('max_schema_tables' as keyof ModelConfig, parseInt(e.target.value))}
                    disabled={disabled}
                    className="w-full h-1.5 rounded-full appearance-none bg-gradient-to-r from-gray-300 to-purple-500 cursor-pointer"
                  />
                </div>
              )}

              {/* Example Selection Toggle */}
              <div className="flex items-center justify-between glass-panel rounded-lg p-3 border-white/10">
                <div>
                  <label className="text-[11px] font-bold uppercase tracking-widest text-gray-700 dark:text-gray-300">Smart Example Selection</label>
                  <p className="text-[11px] font-medium text-gray-400 mt-0.5">
                    Choose relevant few-shot examples based on query
                  </p>
                </div>
                <button
                  onClick={() => handleToggleChange('enable_example_selection', !config.enable_example_selection)}
                  disabled={disabled}
                  className={`relative inline-flex h-6 w-10 items-center rounded-full transition-all disabled:opacity-50 ${config.enable_example_selection ? 'bg-purple-500 shadow-lg shadow-purple-500/20' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${config.enable_example_selection ? 'translate-x-5' : 'translate-x-1'
                      }`}
                  />
                </button>
              </div>

              {/* Max Few-Shot Examples */}
              {config.enable_example_selection && (
                <div className="ml-4 glass-panel rounded-lg p-3 border-white/10">
                  <label className="block text-[11px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-2">
                    Max Examples: <span className="text-purple-500">{config.max_few_shot_examples || 3}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="5"
                    step="1"
                    value={config.max_few_shot_examples || 3}
                    onChange={(e) => handleNumberChange('max_few_shot_examples' as keyof ModelConfig, parseInt(e.target.value))}
                    disabled={disabled}
                    className="w-full h-1.5 rounded-full appearance-none bg-gradient-to-r from-gray-300 to-purple-500 cursor-pointer"
                  />
                  <p className="text-[11px] font-medium text-gray-400 mt-1">
                    0 = zero-shot (best for small models)
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Info Section */}
      <div className="glass-card rounded-xl p-4 bg-gradient-to-r from-blue-500/10 via-transparent to-cyan-500/5 border-blue-500/20">
        <div className="flex items-start gap-3">
          <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-500 flex-shrink-0 mt-0.5">
            <Info className="w-3.5 h-3.5" />
          </div>
          <p className="text-[11px] font-medium text-gray-600 dark:text-gray-400">
            <span className="font-bold text-blue-600 dark:text-blue-400">Tip:</span> Use specialized models (like duckdb-nsql) for SQL generation and
            general-purpose models (like llama3.2) for narratives. Leave fields empty to use the default system model.
          </p>
        </div>
      </div>
    </div>
  );
}
