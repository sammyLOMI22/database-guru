import { useState } from 'react';
import { Loader2, TestTube, Eye, EyeOff } from 'lucide-react';
import { llmProviderApi, type ProviderTestResult } from '../services/llmProviderApi';

interface ProviderCardProps {
  name: string;
  displayName: string;
  dataLocality: 'local' | 'cloud_private' | 'cloud_public';
  enabled: boolean;
  hasApiKey: boolean;
  apiKeyMasked: string | null;
  endpoint: string | null;
  defaultModel: string | null;
  registered: boolean;
  healthy?: boolean;
  onConfigure: (name: string) => void;
}

const LOCALITY_BADGES: Record<string, { label: string; color: string }> = {
  local: { label: 'LOCAL', color: 'text-emerald-600 bg-emerald-500/10 border-emerald-500/20' },
  cloud_private: { label: 'PRIVATE CLOUD', color: 'text-blue-600 bg-blue-500/10 border-blue-500/20' },
  cloud_public: { label: 'FRONTIER', color: 'text-amber-600 bg-amber-500/10 border-amber-500/20' },
};

export function ProviderCard({
  name,
  displayName,
  dataLocality,
  enabled,
  hasApiKey,
  apiKeyMasked,
  endpoint,
  defaultModel,
  registered,
  healthy,
  onConfigure,
}: ProviderCardProps) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ProviderTestResult | null>(null);
  const [showKey, setShowKey] = useState(false);

  const badge = LOCALITY_BADGES[dataLocality] || LOCALITY_BADGES.local;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await llmProviderApi.testProvider(name);
      setTestResult(result);
    } catch {
      setTestResult({ provider: name, healthy: false, message: 'Connection failed', data_locality: dataLocality });
    } finally {
      setTesting(false);
    }
  };

  const isHealthy = testResult ? testResult.healthy : healthy;
  const statusDot = !registered
    ? 'bg-gray-400 dark:bg-white/20'
    : isHealthy === true
      ? 'bg-emerald-500'
      : isHealthy === false
        ? 'bg-red-500'
        : 'bg-gray-400 dark:bg-white/20';

  const statusText = !registered
    ? 'Not registered'
    : isHealthy === true
      ? 'Connected'
      : isHealthy === false
        ? 'Unreachable'
        : 'Unknown';

  return (
    <div className={`p-6 glass-panel rounded-[1.5rem] transition-all ${enabled ? 'border-white/10' : 'opacity-60 border-white/5'}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h4 className="text-sm font-bold text-gray-900 dark:text-white">{displayName}</h4>
          <span className={`text-[9px] font-black uppercase tracking-[0.15em] px-2 py-0.5 rounded-full border ${badge.color}`}>
            {badge.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${statusDot}`} />
          <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">
            {statusText}
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-2 mb-4">
        {hasApiKey && (
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="font-semibold w-16">API Key:</span>
            <span className="font-mono text-[11px]">
              {showKey && apiKeyMasked ? apiKeyMasked : '••••••••••••'}
            </span>
            <button onClick={() => setShowKey(!showKey)} className="p-0.5 hover:text-gray-300 transition-colors">
              {showKey ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
            </button>
          </div>
        )}
        {defaultModel && (
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="font-semibold w-16">Model:</span>
            <span className="font-mono text-[11px]">{defaultModel}</span>
          </div>
        )}
        {endpoint && (
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="font-semibold w-16">Endpoint:</span>
            <span className="font-mono text-[11px] truncate max-w-[200px]">{endpoint}</span>
          </div>
        )}
      </div>

      {/* Test result message */}
      {testResult && (
        <div className={`mb-3 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest ${
          testResult.healthy
            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            : 'bg-red-500/10 text-red-600 dark:text-red-400'
        }`}>
          {testResult.message}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleTest}
          disabled={testing || !registered}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.15em] glass-panel rounded-lg hover:scale-105 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <TestTube className="w-3 h-3" />}
          Test
        </button>
        <button
          onClick={() => onConfigure(name)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.15em] glass-panel rounded-lg hover:scale-105 active:scale-95 transition-all text-blue-600 dark:text-blue-400"
        >
          Configure
        </button>
      </div>
    </div>
  );
}
