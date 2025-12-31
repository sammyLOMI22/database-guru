/**
 * ModelConfigPanel - Per-Task Model Configuration UI
 *
 * Allows users to configure different LLM models for different tasks:
 * - SQL Generation: Use specialized SQL models (duckdb-nsql, sqlcoder)
 * - Narratives: Use general-purpose models (llama3.2, gemma)
 * - Query Planning: Use reasoning-capable models
 * - Error Correction: Use code-focused models
 *
 * Part of: Small Model Optimization Phase
 */
import { useState, useEffect } from 'react';
import { Cpu, Clock, Zap, MessageSquare, GitBranch, AlertTriangle, Info, RefreshCw } from 'lucide-react';

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
      const response = await fetch('http://localhost:8000/api/models/');
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

  const handleTimeoutChange = (key: keyof ModelConfig, value: number) => {
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
    const colors: Record<string, { bg: string; border: string; text: string; icon: string }> = {
      blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: 'text-blue-500' },
      green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: 'text-green-500' },
      purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', icon: 'text-purple-500' },
      orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', icon: 'text-orange-500' },
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <Cpu className="w-5 h-5" />
            <span>Per-Task Model Configuration</span>
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Assign different models to different tasks for optimal performance
          </p>
        </div>
        <button
          onClick={fetchAvailableModels}
          disabled={loadingModels || disabled}
          className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
          <span>Refresh Models</span>
        </button>
      </div>

      {/* Models error message */}
      {modelsError && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          <AlertTriangle className="w-4 h-4 inline mr-2" />
          Could not load available models. Make sure Ollama is running.
        </div>
      )}

      {/* Per-Task Model Configuration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TASK_CONFIGS.map((task) => {
          const colors = getColorClasses(task.color);
          const Icon = task.icon;
          const currentModel = config[task.modelKey];
          const currentTimeout = config[task.timeoutKey];

          return (
            <div
              key={task.key}
              className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}
            >
              {/* Task Header */}
              <div className="flex items-center space-x-2 mb-3">
                <Icon className={`w-5 h-5 ${colors.icon}`} />
                <span className={`font-semibold ${colors.text}`}>{task.label}</span>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-600 mb-3">{task.description}</p>

              {/* Model Selection */}
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model
                </label>
                <select
                  value={currentModel || ''}
                  onChange={(e) => handleModelChange(task.modelKey, e.target.value)}
                  disabled={disabled || loadingModels}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                >
                  <option value="">Default (use system model)</option>
                  {availableModels.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">{task.hint}</p>
              </div>

              {/* Timeout Configuration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Clock className="w-3 h-3 inline mr-1" />
                  Timeout: {currentTimeout}s
                </label>
                <input
                  type="range"
                  min="5"
                  max="120"
                  step="5"
                  value={currentTimeout}
                  onChange={(e) => handleTimeoutChange(task.timeoutKey, parseInt(e.target.value))}
                  disabled={disabled}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>5s</span>
                  <span>Default: {task.defaultTimeout}s</span>
                  <span>120s</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Optimization Features */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-md font-semibold text-gray-900 flex items-center space-x-2 mb-4">
          <Zap className="w-5 h-5 text-yellow-500" />
          <span>Optimization Features</span>
        </h4>
        <p className="text-sm text-gray-600 mb-4">
          Features that improve response time and accuracy for smaller models
        </p>

        {/* Query Templates Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg mb-3">
          <div className="flex-1">
            <label className="font-semibold text-gray-900">Query Templates</label>
            <p className="text-sm text-gray-600 mt-1">
              Bypass LLM for simple patterns like "show all customers" or "count products"
            </p>
          </div>
          <button
            onClick={() => handleToggleChange('enable_query_templates', !config.enable_query_templates)}
            disabled={disabled}
            className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors disabled:opacity-50 ${
              config.enable_query_templates ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                config.enable_query_templates ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Location Preprocessing Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex-1">
            <label className="font-semibold text-gray-900">Location Preprocessing</label>
            <p className="text-sm text-gray-600 mt-1">
              Automatically normalize locations (California → CA) based on database format
            </p>
          </div>
          <button
            onClick={() => handleToggleChange('enable_location_preprocessing', !config.enable_location_preprocessing)}
            disabled={disabled}
            className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors disabled:opacity-50 ${
              config.enable_location_preprocessing ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                config.enable_location_preprocessing ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Info Section */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm">
        <Info className="w-4 h-4 inline mr-2 text-blue-500" />
        <span className="text-blue-800">
          <strong>Tip:</strong> Use specialized models (like duckdb-nsql) for SQL generation and
          general-purpose models (like llama3.2) for narratives to get the best of both worlds.
          Leave fields empty to use the default system model.
        </span>
      </div>
    </div>
  );
}
