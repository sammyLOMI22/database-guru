import { useState, useEffect, useCallback } from 'react';
import {
  Cpu, Cloud, Shield, AlertTriangle, Loader2, RefreshCw,
  X, Save, Eye, EyeOff, Info,
} from 'lucide-react';
import { ProviderCard } from './ProviderCard';
import { TaskRoutingConfig } from './TaskRoutingConfig';
import {
  llmProviderApi,
  type ProviderConfig,
  type RegistryInfo,
  type ProviderHealthResult,
  type ProviderConfigRequest,
} from '../services/llmProviderApi';

type LLMMode = 'local' | 'frontier';

// Provider metadata for display
const PROVIDER_META: Record<string, { displayName: string; locality: 'local' | 'cloud_private' | 'cloud_public' }> = {
  ollama: { displayName: 'Ollama', locality: 'local' },
  lm_studio: { displayName: 'LM Studio', locality: 'local' },
  vllm: { displayName: 'vLLM', locality: 'local' },
  openai: { displayName: 'OpenAI', locality: 'cloud_public' },
  anthropic: { displayName: 'Anthropic', locality: 'cloud_public' },
  azure_openai: { displayName: 'Azure OpenAI', locality: 'cloud_private' },
  google_vertex: { displayName: 'Google Vertex AI', locality: 'cloud_private' },
  aws_bedrock: { displayName: 'AWS Bedrock', locality: 'cloud_private' },
};

export function LLMProviderSettings() {
  const [mode, setMode] = useState<LLMMode>('local');
  const [registry, setRegistry] = useState<RegistryInfo | null>(null);
  const [configs, setConfigs] = useState<ProviderConfig[]>([]);
  const [healthResults, setHealthResults] = useState<ProviderHealthResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [configModalProvider, setConfigModalProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [registryData, configsData] = await Promise.all([
        llmProviderApi.getRegistry(),
        llmProviderApi.listConfigs(),
      ]);
      setRegistry(registryData);
      setConfigs(configsData);

      // Determine mode from registry
      const hasFrontier = registryData.providers.some((p) => p.data_locality !== 'local' && p.allowed);
      setMode(hasFrontier && registryData.security_level !== 'local_only' ? 'frontier' : 'local');

      setError(null);
    } catch (err) {
      setError('Failed to load provider data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleModeSwitch = (newMode: LLMMode) => {
    if (newMode === 'frontier' && mode === 'local') {
      setShowConfirmDialog(true);
    } else {
      setMode(newMode);
    }
  };

  const confirmFrontierMode = () => {
    setMode('frontier');
    setShowConfirmDialog(false);
  };

  const handleConfigure = (providerName: string) => {
    setConfigModalProvider(providerName);
  };

  const handleRunHealthChecks = async () => {
    try {
      const results = await llmProviderApi.healthCheckAll();
      setHealthResults(results);
    } catch {
      // silent
    }
  };

  const getHealthForProvider = (name: string): boolean | undefined => {
    const result = healthResults.find((r) => r.provider === name);
    return result?.healthy;
  };

  const localProviders = registry?.providers.filter((p) => p.data_locality === 'local') || [];
  const frontierProviders = registry?.providers.filter((p) => p.data_locality !== 'local') || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        <span className="ml-2 text-xs font-bold uppercase tracking-widest text-gray-400">
          Loading providers...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 glass-panel bg-red-500/5 border-red-500/10 rounded-[1.5rem] text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Mode Toggle */}
      <div className="p-6 glass-panel rounded-[1.5rem]">
        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-300 mb-4 flex items-center gap-3">
          <div className="p-1 glass-panel bg-blue-500/10 rounded-lg">
            <Shield className="w-4 h-4 text-blue-500" />
          </div>
          LLM Provider Mode
        </h4>

        <div className="flex gap-3 mb-4">
          {/* Local toggle */}
          <button
            onClick={() => handleModeSwitch('local')}
            className={`flex-1 p-4 rounded-xl border-2 transition-all hover:scale-[1.02] active:scale-[0.98] ${
              mode === 'local'
                ? 'border-emerald-500/40 bg-emerald-500/10'
                : 'border-white/10 bg-white/5 hover:border-white/20'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <Cpu className={`w-5 h-5 ${mode === 'local' ? 'text-emerald-500' : 'text-gray-400'}`} />
              <span className={`text-sm font-bold ${mode === 'local' ? 'text-emerald-500' : 'text-gray-400'}`}>
                Local
              </span>
              {mode === 'local' && (
                <span className="text-[9px] font-black uppercase tracking-widest text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                  Active
                </span>
              )}
            </div>
            <p className="text-[10px] text-gray-500 dark:text-gray-400 text-left">
              Your data stays on this machine. Powered by Ollama, LM Studio, or vLLM.
            </p>
          </button>

          {/* Frontier toggle */}
          <button
            onClick={() => handleModeSwitch('frontier')}
            className={`flex-1 p-4 rounded-xl border-2 transition-all hover:scale-[1.02] active:scale-[0.98] ${
              mode === 'frontier'
                ? 'border-blue-500/40 bg-gradient-to-r from-blue-600/10 to-indigo-600/10'
                : 'border-white/10 bg-white/5 hover:border-white/20'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <Cloud className={`w-5 h-5 ${mode === 'frontier' ? 'text-blue-500' : 'text-gray-400'}`} />
              <span className={`text-sm font-bold ${mode === 'frontier' ? 'text-blue-500' : 'text-gray-400'}`}>
                Frontier
              </span>
              {mode === 'frontier' && (
                <span className="text-[9px] font-black uppercase tracking-widest text-blue-500 bg-blue-500/10 px-2 py-0.5 rounded-full">
                  Active
                </span>
              )}
            </div>
            <p className="text-[10px] text-gray-500 dark:text-gray-400 text-left">
              Use cloud LLMs (OpenAI, Anthropic, Azure, Vertex, Bedrock) for higher accuracy.
            </p>
          </button>
        </div>

        {/* Security info box */}
        {mode === 'local' ? (
          <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
            <div className="flex items-start gap-2">
              <Shield className="w-3.5 h-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                Your database schemas, query data, and results never leave this machine.
                All LLM processing runs locally.
              </p>
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/10">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
                Queries and schema data will be sent to cloud providers.
                Ensure this complies with your organization's data policies.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Provider Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-300 flex items-center gap-3">
            <div className="p-1 glass-panel bg-emerald-500/10 rounded-lg">
              <Cpu className="w-4 h-4 text-emerald-500" />
            </div>
            {mode === 'local' ? 'Local Providers' : 'All Providers'}
          </h4>
          <button
            onClick={handleRunHealthChecks}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.15em] glass-panel rounded-lg hover:scale-105 active:scale-95 transition-all"
          >
            <RefreshCw className="w-3 h-3" />
            Health Check
          </button>
        </div>

        {/* Local providers always shown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {localProviders.map((p) => {
            const meta = PROVIDER_META[p.name];
            const config = configs.find((c) => c.provider_name === p.name);
            return (
              <ProviderCard
                key={p.name}
                name={p.name}
                displayName={meta?.displayName || p.name}
                dataLocality={meta?.locality || 'local'}
                enabled={config?.enabled ?? true}
                hasApiKey={config?.has_api_key ?? false}
                apiKeyMasked={config?.api_key_masked ?? null}
                endpoint={config?.endpoint ?? null}
                defaultModel={p.default_model}
                registered={true}
                healthy={getHealthForProvider(p.name)}
                onConfigure={handleConfigure}
              />
            );
          })}
        </div>

        {/* Frontier providers (only in frontier mode) */}
        {mode === 'frontier' && (
          <>
            <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-600 dark:text-gray-300 flex items-center gap-3 mt-6">
              <div className="p-1 glass-panel bg-amber-500/10 rounded-lg">
                <Cloud className="w-4 h-4 text-amber-500" />
              </div>
              Frontier Providers
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Show registered frontier providers */}
              {frontierProviders.map((p) => {
                const meta = PROVIDER_META[p.name];
                const config = configs.find((c) => c.provider_name === p.name);
                return (
                  <ProviderCard
                    key={p.name}
                    name={p.name}
                    displayName={meta?.displayName || p.name}
                    dataLocality={meta?.locality || 'cloud_public'}
                    enabled={config?.enabled ?? true}
                    hasApiKey={config?.has_api_key ?? false}
                    apiKeyMasked={config?.api_key_masked ?? null}
                    endpoint={config?.endpoint ?? null}
                    defaultModel={p.default_model}
                    registered={true}
                    healthy={getHealthForProvider(p.name)}
                    onConfigure={handleConfigure}
                  />
                );
              })}

              {/* Show unregistered frontier providers as placeholders */}
              {Object.entries(PROVIDER_META)
                .filter(([, meta]) => meta.locality !== 'local')
                .filter(([name]) => !frontierProviders.some((p) => p.name === name))
                .map(([name, meta]) => {
                  const config = configs.find((c) => c.provider_name === name);
                  return (
                    <ProviderCard
                      key={name}
                      name={name}
                      displayName={meta.displayName}
                      dataLocality={meta.locality}
                      enabled={false}
                      hasApiKey={config?.has_api_key ?? false}
                      apiKeyMasked={config?.api_key_masked ?? null}
                      endpoint={config?.endpoint ?? null}
                      defaultModel={config?.default_model ?? null}
                      registered={false}
                      onConfigure={handleConfigure}
                    />
                  );
                })}
            </div>
          </>
        )}
      </div>

      {/* Task Routing (advanced) */}
      {registry && <TaskRoutingConfig providers={registry.providers} />}

      {/* Security level info */}
      <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-[1.5rem]">
        <div className="flex items-start gap-3">
          <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <div className="text-[10px] text-gray-500 dark:text-gray-400 space-y-1">
            <p>
              <span className="font-bold text-gray-600 dark:text-gray-300">Security Level:</span>{' '}
              <span className="font-mono">{registry?.security_level || 'local_only'}</span>
            </p>
            <p>
              Set <span className="font-mono">DATA_SECURITY_LEVEL</span> in your <span className="font-mono">.env</span> to control
              which provider tiers are allowed: <span className="font-mono">local_only</span> (default),{' '}
              <span className="font-mono">cloud_private</span>, or <span className="font-mono">unrestricted</span>.
            </p>
          </div>
        </div>
      </div>

      {/* Frontier Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xl flex items-center justify-center z-50">
          <div className="glass-panel rounded-[1.5rem] p-8 max-w-md mx-4 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-xl">
                <AlertTriangle className="w-6 h-6 text-amber-500" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">Enable Cloud LLM?</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Database schemas and query data will be sent to external cloud providers.
              Schema names, table structures, and query results will leave your network.
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Ensure this complies with your organization's data policies before proceeding.
            </p>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowConfirmDialog(false)}
                className="flex-1 px-4 py-2 text-xs font-black uppercase tracking-[0.15em] glass-panel rounded-xl hover:scale-105 active:scale-95 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={confirmFrontierMode}
                className="flex-1 px-4 py-2 text-xs font-black uppercase tracking-[0.15em] bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:scale-105 active:scale-95 transition-all"
              >
                Enable Frontier
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provider Configuration Modal */}
      {configModalProvider && (
        <ProviderConfigModal
          providerName={configModalProvider}
          onClose={() => {
            setConfigModalProvider(null);
            loadData();
          }}
        />
      )}
    </div>
  );
}

// --- Inline Configuration Modal ---

function ProviderConfigModal({ providerName, onClose }: { providerName: string; onClose: () => void }) {
  const meta = PROVIDER_META[providerName];
  const [enabled, setEnabled] = useState(true);
  const [apiKey, setApiKey] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [defaultModel, setDefaultModel] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing config
  useEffect(() => {
    (async () => {
      try {
        const config = await llmProviderApi.getConfig(providerName);
        setEnabled(config.enabled);
        setEndpoint(config.endpoint || '');
        setDefaultModel(config.default_model || '');
      } catch {
        // New config — defaults are fine
      }
    })();
  }, [providerName]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const req: ProviderConfigRequest = {
        enabled,
        data_locality: meta?.locality || 'local',
        endpoint: endpoint || undefined,
        default_model: defaultModel || undefined,
      };
      if (apiKey) {
        req.api_key = apiKey;
      }
      await llmProviderApi.upsertConfig(providerName, req);
      onClose();
    } catch (err) {
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await llmProviderApi.deleteConfig(providerName);
      onClose();
    } catch {
      // silent
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xl flex items-center justify-center z-50">
      <div className="glass-panel rounded-[1.5rem] p-8 max-w-lg mx-4 w-full space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-gray-900 dark:text-white">
            Configure {meta?.displayName || providerName}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 text-xs text-red-400 font-semibold">{error}</div>
        )}

        <div className="space-y-4">
          {/* Enabled toggle */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="w-4 h-4 accent-blue-500 rounded"
            />
            <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-widest">
              Enabled
            </span>
          </label>

          {/* API Key */}
          {meta?.locality !== 'local' && (
            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-1.5">
                API Key
              </label>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter API key (leave empty to keep existing)"
                  className="w-full px-3 py-2 text-xs bg-white/5 border border-white/10 rounded-lg text-gray-700 dark:text-gray-300 focus:outline-none focus:border-blue-500/50 font-mono pr-8"
                />
                <button
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-300"
                >
                  {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          )}

          {/* Endpoint */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-1.5">
              Endpoint URL
            </label>
            <input
              type="text"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="Default endpoint"
              className="w-full px-3 py-2 text-xs bg-white/5 border border-white/10 rounded-lg text-gray-700 dark:text-gray-300 focus:outline-none focus:border-blue-500/50 font-mono"
            />
          </div>

          {/* Default Model */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-1.5">
              Default Model
            </label>
            <input
              type="text"
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              placeholder="Provider default"
              className="w-full px-3 py-2 text-xs bg-white/5 border border-white/10 rounded-lg text-gray-700 dark:text-gray-300 focus:outline-none focus:border-blue-500/50 font-mono"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-4 py-2 text-xs font-black uppercase tracking-[0.15em] glass-panel rounded-xl hover:scale-105 active:scale-95 transition-all text-red-500 hover:bg-red-500/10 disabled:opacity-40"
          >
            {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Delete'}
          </button>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-black uppercase tracking-[0.15em] glass-panel rounded-xl hover:scale-105 active:scale-95 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-xs font-black uppercase tracking-[0.15em] bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:scale-105 active:scale-95 transition-all disabled:opacity-40 flex items-center gap-1.5"
          >
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
