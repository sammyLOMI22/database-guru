import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, RotateCcw, Info } from 'lucide-react';
import { ModelConfigPanel } from './ModelConfigPanel';

interface SystemSettings {
  id: number;
  auto_learning_enabled: boolean;
  confidence_threshold: number;
  apply_mode: 'immediate' | 'deferred';
  test_before_learning: boolean;
  enable_audit_log: boolean;
  max_audit_log_days: number;
  query_quality_level: number;  // 0-100 scale
  // Semantic Understanding Settings (Phase 1, 2, 3)
  enable_intent_classification: boolean;  // Phase 1: Detect impossible queries
  enable_dynamic_examples: boolean;       // Phase 2: Schema-specific examples
  enable_semantic_validation: boolean;    // Phase 3: Post-generation validation
  // Per-Task Model Configuration (Small Model Optimization)
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
  prompt_model_size: string;
  enable_schema_compression: boolean;
  max_schema_tables: number;
  enable_example_selection: boolean;
  max_few_shot_examples: number;
  created_at: string;
  updated_at: string;
}

export function SettingsPanel() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch settings on mount
  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/settings/');
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    if (!settings) return;

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      const response = await fetch('http://localhost:8000/api/settings/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          auto_learning_enabled: settings.auto_learning_enabled,
          confidence_threshold: settings.confidence_threshold,
          apply_mode: settings.apply_mode,
          test_before_learning: settings.test_before_learning,
          enable_audit_log: settings.enable_audit_log,
          max_audit_log_days: settings.max_audit_log_days,
          query_quality_level: settings.query_quality_level,
          // Semantic Understanding Settings
          enable_intent_classification: settings.enable_intent_classification,
          enable_dynamic_examples: settings.enable_dynamic_examples,
          enable_semantic_validation: settings.enable_semantic_validation,
          // Per-Task Model Configuration
          model_sql_generation: settings.model_sql_generation,
          model_narratives: settings.model_narratives,
          model_query_planning: settings.model_query_planning,
          model_error_correction: settings.model_error_correction,
          timeout_sql_generation: settings.timeout_sql_generation,
          timeout_narratives: settings.timeout_narratives,
          timeout_query_planning: settings.timeout_query_planning,
          timeout_error_correction: settings.timeout_error_correction,
          enable_query_templates: settings.enable_query_templates,
          enable_location_preprocessing: settings.enable_location_preprocessing,
          // Prompt Optimization (Phase 2.2)
          enable_prompt_optimization: settings.enable_prompt_optimization,
          prompt_model_size: settings.prompt_model_size,
          enable_schema_compression: settings.enable_schema_compression,
          max_schema_tables: settings.max_schema_tables,
          enable_example_selection: settings.enable_example_selection,
          max_few_shot_examples: settings.max_few_shot_examples,
        }),
      });

      if (!response.ok) throw new Error('Failed to save settings');

      const updatedSettings = await response.json();
      setSettings(updatedSettings);
      setSuccessMessage('Settings saved successfully!');

      // Notify other components (like EnhancedChatInterface) to refresh
      window.dispatchEvent(new CustomEvent('settingsUpdated'));

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const resetSettings = async () => {
    if (!confirm('Are you sure you want to reset all settings to defaults?')) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      const response = await fetch('http://localhost:8000/api/settings/reset', {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Failed to reset settings');

      const resetSettings = await response.json();
      setSettings(resetSettings);
      setSuccessMessage('Settings reset to defaults!');

      // Notify other components (like EnhancedChatInterface) to refresh
      window.dispatchEvent(new CustomEvent('settingsUpdated'));

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="p-8 text-center text-red-600">
        Failed to load settings. Please try again.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 min-h-full transition-colors animate-fadeIn">
      <div className="glass-panel rounded-[2rem] shadow-2xl border-white/10 overflow-hidden">
        {/* Header */}
        <div className="border-b border-white/5 px-8 py-6 bg-white/5 dark:bg-black/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-2xl glass-panel flex items-center justify-center text-blue-500 shadow-lg shadow-blue-500/10">
                <SettingsIcon className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-black uppercase tracking-tight text-gray-900 dark:text-white">System Settings</h2>
                <p className="text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">Configure engine behavior and intelligence</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={resetSettings}
                disabled={saving}
                className="flex items-center space-x-2 px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 glass-panel rounded-xl disabled:opacity-50 transition-all hover:scale-105 active:scale-95"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Reset</span>
              </button>
              <button
                onClick={saveSettings}
                disabled={saving}
                className="flex items-center space-x-2 px-6 py-2.5 text-[10px] font-black uppercase tracking-widest text-white bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl disabled:opacity-50 shadow-xl shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all"
              >
                <Save className="w-4 h-4" />
                <span>{saving ? 'Saving...' : 'Save Changes'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="mx-6 mt-4 p-4 bg-red-100 dark:bg-red-900/30 border-2 border-red-500 dark:border-red-800 rounded-lg">
            <p className="text-red-900 dark:text-red-200 font-semibold">⚠️ {error}</p>
          </div>
        )}
        {successMessage && (
          <div className="mx-6 mt-4 p-4 bg-green-100 dark:bg-green-900/30 border-2 border-green-500 dark:border-green-800 rounded-lg">
            <p className="text-green-900 dark:text-green-200 font-semibold">✅ {successMessage}</p>
          </div>
        )}

        {/* Settings Form */}
        <div className="p-8 space-y-10">
          {/* Query Quality Section */}
          <div className="space-y-6">
            <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              Query Intelligence
            </h3>

            <div className="p-6 glass-panel bg-gradient-to-br from-blue-500/5 via-transparent to-indigo-500/5 border-white/10 rounded-2xl transition-all">
              <div className="flex justify-between mb-4">
                <label className="text-xs font-black uppercase tracking-wider text-gray-900 dark:text-white">
                  Target Quality Level
                </label>
                <span className="text-lg font-black text-blue-600 dark:text-blue-400">{settings.query_quality_level}%</span>
              </div>
              <p className="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-6">
                Optimizes for speed at lower levels and precision at higher levels
              </p>

              <div className="flex items-center space-x-4 mb-8">
                <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500">Fast</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={settings.query_quality_level}
                  onChange={(e) => setSettings({
                    ...settings,
                    query_quality_level: parseInt(e.target.value)
                  })}
                  className="flex-1 h-1.5 bg-gray-200 dark:bg-white/10 rounded-full appearance-none cursor-pointer accent-blue-600 focus:outline-none"
                />
                <span className="text-[10px] font-black uppercase tracking-widest text-indigo-500">Thorough</span>
              </div>

              {/* Mode Description */}
              <div className="p-4 glass-panel bg-white/5 dark:bg-black/20 rounded-xl border-white/5 transition-all">
                {settings.query_quality_level <= 30 && (
                  <div className="animate-fadeIn">
                    <strong className="text-[10px] font-black uppercase tracking-widest text-emerald-500 block mb-2">Performance Focus</strong>
                    <ul className="grid grid-cols-2 gap-2 text-[10px] font-bold text-gray-600 dark:text-gray-400">
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-emerald-500" /> Minimal planning</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-emerald-500" /> Max 1 retry</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-emerald-500" /> Basic prompting</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-emerald-500" /> Low latency</li>
                    </ul>
                  </div>
                )}
                {settings.query_quality_level > 30 && settings.query_quality_level <= 70 && (
                  <div className="animate-fadeIn">
                    <strong className="text-[10px] font-black uppercase tracking-widest text-blue-500 block mb-2">Balanced Engine (Optimal)</strong>
                    <ul className="grid grid-cols-2 gap-2 text-[10px] font-bold text-gray-600 dark:text-gray-400">
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-blue-500" /> Multi-step planning</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-blue-500" /> Up to 3 retries</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-blue-500" /> Semantic verification</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-blue-500" /> Dynamic examples</li>
                    </ul>
                  </div>
                )}
                {settings.query_quality_level > 70 && (
                  <div className="animate-fadeIn">
                    <strong className="text-[10px] font-black uppercase tracking-widest text-indigo-500 block mb-2">Deep Intelligence</strong>
                    <ul className="grid grid-cols-2 gap-2 text-[10px] font-bold text-gray-600 dark:text-gray-400">
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-indigo-500" /> Full schema exploration</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-indigo-500" /> Tool-augmented reasoning</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-indigo-500" /> Parallel correction paths</li>
                      <li className="flex items-center gap-2"><div className="w-1 h-1 rounded-full bg-indigo-500" /> Highest accuracy</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SQL Generation Intelligence Section */}
          <div className="space-y-6">
            <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Reasoning Modules
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  key: 'enable_intent_classification',
                  label: 'Intent Guard',
                  desc: 'Auto-detect impossible or malformed queries',
                  icon: '🛡️'
                },
                {
                  key: 'enable_dynamic_examples',
                  label: 'Dynamic Few-shot',
                  desc: 'Fetch schema-specific examples for accuracy',
                  icon: '📚'
                },
                {
                  key: 'enable_semantic_validation',
                  label: 'Semantic Check',
                  desc: 'Final pass to verify SQL against natural intent',
                  icon: '⚖️'
                },
                {
                  key: 'enable_prompt_optimization',
                  label: 'Prompt Tuning',
                  desc: 'Compress schema and optimize instructions',
                  icon: '⚡'
                }
              ].map((mod) => (
                <div
                  key={mod.key}
                  className="p-5 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-2xl flex items-center justify-between group hover:border-blue-500/30 transition-all duration-300"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-lg shadow-sm">
                      {mod.icon}
                    </div>
                    <div>
                      <h4 className="text-xs font-black uppercase tracking-wider text-gray-900 dark:text-white">{mod.label}</h4>
                      <p className="text-[10px] font-bold text-gray-500 dark:text-gray-500 uppercase tracking-widest mt-0.5">{mod.desc}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setSettings({ ...settings, [mod.key]: !settings[mod.key as keyof SystemSettings] })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-500 ${settings[mod.key as keyof SystemSettings] ? 'bg-blue-600 shadow-lg shadow-blue-500/20' : 'bg-gray-300 dark:bg-white/10'}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-500 ${settings[mod.key as keyof SystemSettings] ? 'translate-x-6' : 'translate-x-1'}`}
                    />
                  </button>
                </div>
              ))}
            </div>

            {/* Info box */}
            <div className="p-4 glass-panel bg-blue-500/5 border-blue-500/10 rounded-2xl flex items-start gap-3 transition-colors">
              <Info className="w-4 h-4 text-blue-500 mt-0.5" />
              <p className="text-[10px] font-bold text-blue-600/80 dark:text-blue-400/80 uppercase tracking-widest leading-relaxed">
                Note: Reasoning modules are calibrated automatically based on your Query Quality setting, but can be manually overridden here for specific workload requirements.
              </p>
            </div>
          </div>

          {/* Per-Task Model Configuration Section */}
          <div className="space-y-4 pb-6 border-b border-gray-200 dark:border-gray-700">
            <ModelConfigPanel
              config={{
                model_sql_generation: settings.model_sql_generation,
                model_narratives: settings.model_narratives,
                model_query_planning: settings.model_query_planning,
                model_error_correction: settings.model_error_correction,
                timeout_sql_generation: settings.timeout_sql_generation,
                timeout_narratives: settings.timeout_narratives,
                timeout_query_planning: settings.timeout_query_planning,
                timeout_error_correction: settings.timeout_error_correction,
                enable_query_templates: settings.enable_query_templates,
                enable_location_preprocessing: settings.enable_location_preprocessing,
                // Prompt Optimization (Phase 2.2)
                enable_prompt_optimization: settings.enable_prompt_optimization,
                prompt_model_size: settings.prompt_model_size,
                enable_schema_compression: settings.enable_schema_compression,
                max_schema_tables: settings.max_schema_tables,
                enable_example_selection: settings.enable_example_selection,
                max_few_shot_examples: settings.max_few_shot_examples,
              }}
              onChange={(modelConfig) => setSettings({ ...settings, ...modelConfig })}
              disabled={saving}
            />
          </div>

          {/* Auto-Learning Section */}
          <div className="space-y-6">
            <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Auto-Evolution Engine
            </h3>

            {/* Master Toggle */}
            <div className="p-6 glass-panel bg-emerald-500/5 border-emerald-500/10 rounded-2xl flex items-center justify-between transition-all">
              <div className="flex-1">
                <label className="text-xs font-black uppercase tracking-wider text-gray-900 dark:text-white">Active Learning</label>
                <p className="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mt-1">
                  Automatically integrate high-confidence feedback into core models
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, auto_learning_enabled: !settings.auto_learning_enabled })}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-500 ${settings.auto_learning_enabled ? 'bg-emerald-600 shadow-lg shadow-emerald-500/20' : 'bg-gray-300 dark:bg-white/10'}`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-all duration-500 ${settings.auto_learning_enabled ? 'translate-x-6' : 'translate-x-1'}`}
                />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Confidence Threshold Slider */}
              <div className="p-6 glass-panel bg-white/5 border-white/5 rounded-2xl transition-all">
                <div className="flex justify-between mb-4">
                  <label className="text-[10px] font-black uppercase tracking-widest text-gray-900 dark:text-white">
                    Confidence Floor
                  </label>
                  <span className="text-xs font-black text-emerald-600">{(settings.confidence_threshold * 100).toFixed(0)}%</span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-[10px] font-bold text-gray-400">50%</span>
                  <input
                    type="range"
                    min="0.5"
                    max="1.0"
                    step="0.05"
                    value={settings.confidence_threshold}
                    onChange={(e) => setSettings({ ...settings, confidence_threshold: parseFloat(e.target.value) })}
                    className="flex-1 h-1 bg-gray-200 dark:bg-white/10 rounded-full appearance-none cursor-pointer accent-emerald-600 focus:outline-none"
                    disabled={!settings.auto_learning_enabled}
                  />
                  <span className="text-[10px] font-bold text-gray-400">100%</span>
                </div>
              </div>

              {/* Apply Mode */}
              <div className="p-6 glass-panel bg-white/5 border-white/5 rounded-2xl transition-all">
                <label className="text-[10px] font-black uppercase tracking-widest text-gray-900 dark:text-white block mb-4">Strategy</label>
                <div className="flex gap-4">
                  {['immediate', 'deferred'].map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setSettings({ ...settings, apply_mode: mode as 'immediate' | 'deferred' })}
                      disabled={!settings.auto_learning_enabled}
                      className={`flex-1 py-2 text-[10px] font-black uppercase tracking-widest border rounded-xl transition-all ${settings.apply_mode === mode
                        ? 'bg-emerald-600/10 border-emerald-500/30 text-emerald-600 font-black shadow-sm'
                        : 'border-white/5 text-gray-500 hover:bg-white/5'}`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Test Before Learning Toggle */}
            <div className="p-5 glass-panel bg-white/5 border-white/5 rounded-2xl flex items-center justify-between group transition-all">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center text-lg shadow-sm">
                  🔬
                </div>
                <div>
                  <h4 className="text-xs font-black uppercase tracking-wider text-gray-900 dark:text-white">Pre-flight Validation</h4>
                  <p className="text-[10px] font-bold text-gray-500 dark:text-gray-500 uppercase tracking-widest mt-0.5">Test SQL execution before integrating knowledge</p>
                </div>
              </div>
              <button
                onClick={() => setSettings({ ...settings, test_before_learning: !settings.test_before_learning })}
                disabled={!settings.auto_learning_enabled}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-500 disabled:opacity-20 ${settings.test_before_learning ? 'bg-emerald-600 shadow-lg shadow-emerald-500/20' : 'bg-gray-300 dark:bg-white/10'}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-500 ${settings.test_before_learning ? 'translate-x-6' : 'translate-x-1'}`}
                />
              </button>
            </div>
          </div>

          {/* Audit Settings Section */}
          <div className="space-y-6 pt-4 border-t border-white/5">
            <h3 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
              Transparency & Logs
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-6 glass-panel bg-white/5 border-white/5 rounded-2xl flex items-center justify-between group transition-all">
                <div>
                  <h4 className="text-xs font-black uppercase tracking-wider text-gray-900 dark:text-white">Audit Trail</h4>
                  <p className="text-[10px] font-bold text-gray-500  uppercase tracking-widest mt-0.5">Log all auto-adjustments</p>
                </div>
                <button
                  onClick={() => setSettings({ ...settings, enable_audit_log: !settings.enable_audit_log })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-500 ${settings.enable_audit_log ? 'bg-blue-600 shadow-lg shadow-blue-500/20' : 'bg-gray-300 dark:bg-white/10'}`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-500 ${settings.enable_audit_log ? 'translate-x-6' : 'translate-x-1'}`}
                  />
                </button>
              </div>

              <div className="p-6 glass-panel bg-white/5 border-white/5 rounded-2xl transition-all">
                <div className="flex justify-between mb-4">
                  <label className="text-[10px] font-black uppercase tracking-widest text-gray-900 dark:text-white">Retention Policy</label>
                  <span className="text-xs font-black text-gray-500">{settings.max_audit_log_days} Days</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="365"
                  step="1"
                  value={settings.max_audit_log_days}
                  onChange={(e) => setSettings({ ...settings, max_audit_log_days: parseInt(e.target.value) })}
                  className="w-full h-1 bg-gray-200 dark:bg-white/10 rounded-full appearance-none cursor-pointer accent-gray-500 focus:outline-none"
                  disabled={!settings.enable_audit_log}
                />
              </div>
            </div>
          </div>

          {/* Info Section */}
          <div className="p-6 glass-panel bg-blue-500/5 border-blue-500/10 rounded-3xl transition-all">
            <h4 className="text-xs font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 mb-4 flex items-center gap-2">
              <Info className="w-4 h-4" />
              Evolution Protocol
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
              {[
                'High confidence (≥90%) auto-applies immediately.',
                'Medium confidence (70-89%) queues for batch review.',
                'Low confidence requires manual intervention.',
                'Rollback any change from the core audit dashboard.'
              ].map((text, idx) => (
                <div key={idx} className="flex gap-3 text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest leading-relaxed">
                  <div className="w-1 h-1 rounded-full bg-blue-500/50 mt-1.5 flex-shrink-0" />
                  {text}
                </div>
              ))}
            </div>
          </div>

          {/* Metadata */}
          <div className="pt-2 flex justify-between items-center text-[9px] font-black uppercase tracking-[0.2em] text-gray-400">
            <p>LAST_SYNC: {new Date(settings.updated_at).toLocaleTimeString()}</p>
            <p className="text-gray-300 dark:text-gray-600">ID: {settings.id.toString(16).toUpperCase()}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
