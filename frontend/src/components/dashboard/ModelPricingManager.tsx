import React, { useState, useEffect } from 'react';
import { Settings, Plus, Trash2, AlertTriangle, DollarSign, Check, X } from 'lucide-react';
import { llmUsageApi, ModelConfig, UnpricedModel } from '../../services/llmUsageApi';

interface EditingRow {
  model_name: string;
  provider: string;
  display_name: string;
  cost_per_1m_input_tokens: string;
  cost_per_1m_output_tokens: string;
  isNew: boolean;
}

const formatProvider = (provider: string): string =>
  provider
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' ');

export const ModelPricingManager: React.FC = () => {
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [unpriced, setUnpriced] = useState<UnpricedModel[]>([]);
  const [editing, setEditing] = useState<EditingRow | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [configData, unpricedData] = await Promise.all([
        llmUsageApi.getModelConfigs(),
        llmUsageApi.getUnpricedModels(),
      ]);
      setConfigs(configData);
      setUnpriced(unpricedData);
    } catch (err) {
      setError('Failed to load pricing data');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSave = async () => {
    if (!editing) return;
    const trimmedName = editing.model_name.trim();
    const trimmedProvider = editing.provider.trim();
    if (!trimmedName || !trimmedProvider) {
      setError('Model name and provider are required');
      return;
    }
    const inputCost = parseFloat(editing.cost_per_1m_input_tokens);
    const outputCost = parseFloat(editing.cost_per_1m_output_tokens);
    if (isNaN(inputCost) || isNaN(outputCost) || inputCost < 0 || outputCost < 0) {
      setError('Costs must be valid non-negative numbers');
      return;
    }
    try {
      await llmUsageApi.upsertModelConfig({
        model_name: trimmedName,
        provider: trimmedProvider,
        cost_per_1m_input_tokens: inputCost,
        cost_per_1m_output_tokens: outputCost,
        display_name: editing.display_name.trim() || undefined,
      });
      setEditing(null);
      setError(null);
      await fetchData();
    } catch (err) {
      setError('Failed to save pricing config');
      console.error(err);
    }
  };

  const handleDelete = async (provider: string, modelName: string) => {
    const confirmed = window.confirm(
      `Delete pricing for "${modelName}" on ${formatProvider(provider)}?\n\n` +
      `Future usage for this model will be recorded without a cost until pricing is reconfigured.`
    );
    if (!confirmed) return;
    try {
      await llmUsageApi.deleteModelConfig(provider, modelName);
      await fetchData();
    } catch (err) {
      setError('Failed to delete pricing config');
      console.error(err);
    }
  };

  const startEditing = (config: ModelConfig) => {
    setEditing({
      model_name: config.model_name,
      provider: config.provider,
      display_name: config.display_name || '',
      cost_per_1m_input_tokens: (config.cost_per_1m_input_tokens ?? 0).toString(),
      cost_per_1m_output_tokens: (config.cost_per_1m_output_tokens ?? 0).toString(),
      isNew: false,
    });
  };

  const startNewFromUnpriced = (model: UnpricedModel) => {
    setEditing({
      model_name: model.model_name,
      provider: model.provider,
      display_name: '',
      cost_per_1m_input_tokens: '0',
      cost_per_1m_output_tokens: '0',
      isNew: true,
    });
  };

  const startNew = () => {
    setEditing({
      model_name: '',
      provider: '',
      display_name: '',
      cost_per_1m_input_tokens: '0',
      cost_per_1m_output_tokens: '0',
      isNew: true,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-slate-400" />
          Model Pricing Configuration
        </h3>
        <button
          onClick={startNew}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg hover:bg-blue-500/20 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Model
        </button>
      </div>

      {error && (
        <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
          {error}
        </div>
      )}

      {/* Unpriced Models Alert */}
      {unpriced.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-medium text-amber-300">
              {unpriced.length} model{unpriced.length > 1 ? 's' : ''} detected without pricing
            </span>
          </div>
          <div className="space-y-2">
            {unpriced.map((model) => (
              <div
                key={`${model.provider}-${model.model_name}`}
                className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm text-slate-200 font-mono">{model.model_name}</span>
                  <span className="text-xs text-slate-500">{formatProvider(model.provider)}</span>
                  <span className="text-xs text-slate-500">{model.call_count} calls</span>
                </div>
                <button
                  onClick={() => startNewFromUnpriced(model)}
                  className="text-xs text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1"
                >
                  <DollarSign className="w-3 h-3" />
                  Set Pricing
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Form */}
      {editing && (
        <div className="bg-slate-700/50 border border-slate-600/50 rounded-xl p-4">
          <h4 className="text-sm font-medium text-slate-300 mb-3">
            {editing.isNew ? 'Add Model Pricing' : `Edit: ${editing.model_name}`}
          </h4>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Model Name</label>
              <input
                type="text"
                value={editing.model_name}
                onChange={(e) => setEditing({ ...editing, model_name: e.target.value })}
                disabled={!editing.isNew}
                className="w-full bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-slate-200 disabled:opacity-50"
                placeholder="e.g. gpt-4o"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Provider</label>
              <input
                type="text"
                value={editing.provider}
                onChange={(e) => setEditing({ ...editing, provider: e.target.value })}
                disabled={!editing.isNew}
                className="w-full bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-slate-200 disabled:opacity-50"
                placeholder="e.g. openai"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Input $/1M tokens</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={editing.cost_per_1m_input_tokens}
                onChange={(e) => setEditing({ ...editing, cost_per_1m_input_tokens: e.target.value })}
                className="w-full bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Output $/1M tokens</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={editing.cost_per_1m_output_tokens}
                onChange={(e) => setEditing({ ...editing, cost_per_1m_output_tokens: e.target.value })}
                className="w-full bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-slate-200"
              />
            </div>
            <div className="flex items-end gap-2">
              <button
                onClick={handleSave}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md hover:bg-emerald-500/20 transition-colors"
              >
                <Check className="w-3.5 h-3.5" />
                Save
              </button>
              <button
                onClick={() => { setEditing(null); setError(null); }}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-400 bg-slate-600/30 border border-slate-600/50 rounded-md hover:bg-slate-600/50 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Configured Models Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : configs.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700/50">
                <th className="pb-2 pr-4 font-medium">Model</th>
                <th className="pb-2 pr-4 font-medium">Provider</th>
                <th className="pb-2 pr-4 font-medium text-right">Input $/1M</th>
                <th className="pb-2 pr-4 font-medium text-right">Output $/1M</th>
                <th className="pb-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {configs.map((config) => (
                <tr key={`${config.provider}-${config.model_name}`} className="text-slate-300 hover:bg-slate-700/20 transition-colors">
                  <td className="py-2.5 pr-4 font-mono text-sm">{config.model_name}</td>
                  <td className="py-2.5 pr-4 text-slate-400">{formatProvider(config.provider)}</td>
                  <td className="py-2.5 pr-4 text-right font-mono">
                    ${(config.cost_per_1m_input_tokens ?? 0).toFixed(2)}
                  </td>
                  <td className="py-2.5 pr-4 text-right font-mono">
                    ${(config.cost_per_1m_output_tokens ?? 0).toFixed(2)}
                  </td>
                  <td className="py-2.5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => startEditing(config)}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(config.provider, config.model_name)}
                        className="text-xs text-red-400 hover:text-red-300 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8 text-slate-500 italic text-sm">
          No model pricing configured yet. Add pricing for your models to track costs.
        </div>
      )}
    </div>
  );
};
