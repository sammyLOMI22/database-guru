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
    <div className="max-w-4xl mx-auto p-6 min-h-full transition-colors">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <SettingsIcon className="w-6 h-6 text-gray-700 dark:text-gray-300" />
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">System Settings</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">Configure auto-learning and feedback behavior</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={resetSettings}
                disabled={saving}
                className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg disabled:opacity-50 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Reset to Defaults</span>
              </button>
              <button
                onClick={saveSettings}
                disabled={saving}
                className="flex items-center space-x-2 px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
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
        <div className="p-6 space-y-8">
          {/* Query Quality Section */}
          <div className="space-y-4 pb-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <span>🎯 Query Quality</span>
            </h3>

            <div className="p-4 bg-gradient-to-r from-green-50 via-blue-50 to-purple-50 dark:from-green-900/10 dark:via-blue-900/10 dark:to-purple-900/10 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <label className="block font-semibold text-gray-900 dark:text-white mb-2">
                Quality Level: {settings.query_quality_level}%
              </label>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Balance between query speed and accuracy
              </p>

              <div className="flex items-center space-x-4">
                <span className="text-xs font-medium text-green-600">Fast</span>
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
                  className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <span className="text-xs font-medium text-purple-600">Thorough</span>
              </div>

              {/* Mode Description */}
              <div className="mt-4 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-sm transition-colors">
                {settings.query_quality_level <= 30 && (
                  <div className="text-green-700 dark:text-green-400">
                    <strong className="block">Fast Mode (0-30%)</strong>
                    <ul className="mt-1 ml-4 list-disc text-xs">
                      <li>Minimal query planning</li>
                      <li>Basic prompts, 1 retry max</li>
                      <li>Best for simple queries</li>
                    </ul>
                  </div>
                )}
                {settings.query_quality_level > 30 && settings.query_quality_level <= 70 && (
                  <div className="text-blue-700 dark:text-blue-400">
                    <strong className="block">Balanced Mode (31-70%) - Recommended</strong>
                    <ul className="mt-1 ml-4 list-disc text-xs">
                      <li>Smart query planning for complex queries</li>
                      <li>Location-aware hints (NY, CA, etc.)</li>
                      <li>Result verification, 3 retries</li>
                    </ul>
                  </div>
                )}
                {settings.query_quality_level > 70 && (
                  <div className="text-purple-700 dark:text-purple-400">
                    <strong className="block">Thorough Mode (71-100%)</strong>
                    <ul className="mt-1 ml-4 list-disc text-xs">
                      <li>Full planning for all queries</li>
                      <li>Rich context, tool exploration</li>
                      <li>Maximum retries, best accuracy</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SQL Generation Intelligence Section */}
          <div className="space-y-4 pb-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <span>🧠 SQL Generation Intelligence</span>
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Advanced features that improve SQL generation accuracy. Disable for faster responses.
            </p>

            {/* Toggle components (Generic styling for all blue toggles in this section) */}
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <div className="flex-1">
                <label className="font-semibold text-gray-900 dark:text-white">Intent Classification</label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Detect impossible queries before SQL generation (e.g., "Show me data we don't have")
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, enable_intent_classification: !settings.enable_intent_classification })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${settings.enable_intent_classification ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${settings.enable_intent_classification ? 'translate-x-7' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>

            {/* Dynamic Examples Toggle */}
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <div className="flex-1">
                <label className="font-semibold text-gray-900 dark:text-white">Dynamic Examples</label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Generate schema-specific few-shot examples for better SQL accuracy
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, enable_dynamic_examples: !settings.enable_dynamic_examples })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${settings.enable_dynamic_examples ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${settings.enable_dynamic_examples ? 'translate-x-7' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>

            {/* Semantic Validation Toggle */}
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <div className="flex-1">
                <label className="font-semibold text-gray-900 dark:text-white">Semantic Validation</label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Validate that generated SQL matches your question's intent before execution
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, enable_semantic_validation: !settings.enable_semantic_validation })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${settings.enable_semantic_validation ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${settings.enable_semantic_validation ? 'translate-x-7' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>

            {/* Info box */}
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm transition-colors">
              <Info className="w-4 h-4 inline mr-2 text-blue-500 dark:text-blue-400" />
              <span className="text-blue-800 dark:text-blue-300">
                These features are automatically enabled for Balanced and Thorough quality levels.
                Override here to customize behavior.
              </span>
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
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <span>🤖 Smart Auto-Learning (Option 3)</span>
            </h3>

            {/* Master Toggle */}
            <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg transition-colors">
              <div className="flex-1">
                <label className="font-semibold text-gray-900 dark:text-white">Enable Auto-Learning</label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Automatically apply high-confidence user feedback to the learning system
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, auto_learning_enabled: !settings.auto_learning_enabled })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${settings.auto_learning_enabled ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${settings.auto_learning_enabled ? 'translate-x-7' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>

            {/* Confidence Threshold Slider */}
            <div className="p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <label className="block font-semibold text-gray-900 dark:text-white mb-2">
                Confidence Threshold: {(settings.confidence_threshold * 100).toFixed(0)}%
              </label>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Minimum confidence required for auto-application (50-100%)
              </p>
              <div className="flex items-center space-x-4">
                <span className="text-xs text-gray-500">50%</span>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={settings.confidence_threshold}
                  onChange={(e) => setSettings({ ...settings, confidence_threshold: parseFloat(e.target.value) })}
                  className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  disabled={!settings.auto_learning_enabled}
                />
                <span className="text-xs text-gray-500 dark:text-gray-400">100%</span>
              </div>
              <div className="mt-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-sm transition-colors">
                <Info className="w-4 h-4 inline mr-2 text-blue-500 dark:text-blue-400" />
                <strong className="text-gray-900 dark:text-white">Auto-Learning Rules:</strong>
                <ul className="mt-2 ml-6 list-disc space-y-1 text-gray-700 dark:text-gray-300">
                  <li>High confidence (≥90%): Auto-apply immediately</li>
                  <li>Medium confidence (70-89%): Queue for batch (deferred mode)</li>
                  <li>Low confidence (&lt;70%): Manual review required</li>
                </ul>
              </div>
            </div>

            {/* Apply Mode */}
            <div className="p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <label className="block font-semibold text-gray-900 dark:text-white mb-2">Apply Mode</label>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                How to handle medium-confidence feedback (70-89%)
              </p>
              <div className="flex space-x-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="apply_mode"
                    value="immediate"
                    checked={settings.apply_mode === 'immediate'}
                    onChange={(e) => setSettings({ ...settings, apply_mode: e.target.value as 'immediate' | 'deferred' })}
                    className="w-4 h-4 text-blue-600"
                    disabled={!settings.auto_learning_enabled}
                  />
                  <span className="text-sm">
                    <strong>Immediate</strong> - Manual review only
                  </span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="apply_mode"
                    value="deferred"
                    checked={settings.apply_mode === 'deferred'}
                    onChange={(e) => setSettings({ ...settings, apply_mode: e.target.value as 'immediate' | 'deferred' })}
                    className="w-4 h-4 text-blue-600"
                    disabled={!settings.auto_learning_enabled}
                  />
                  <span className="text-sm text-gray-800 dark:text-gray-200">
                    <strong>Deferred</strong> - Queue for batch processing
                  </span>
                </label>
              </div>
            </div>

            {/* Test Before Learning */}
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <div className="flex-1">
                <label className="font-semibold text-gray-900 dark:text-white">Test Before Learning</label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Execute corrected SQL to verify it works before adding to learning system
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, test_before_learning: !settings.test_before_learning })}
                disabled={!settings.auto_learning_enabled}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors disabled:opacity-50 ${settings.test_before_learning ? 'bg-green-600' : 'bg-gray-300'
                  }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${settings.test_before_learning ? 'translate-x-7' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>
          </div>

          {/* Audit Settings Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">📋 Audit & Logging</h3>

            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <div className="flex-1">
                <label className="font-semibold text-gray-900 dark:text-white">Enable Audit Log</label>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Track all auto-applied feedback for review and rollback
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, enable_audit_log: !settings.enable_audit_log })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${settings.enable_audit_log ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${settings.enable_audit_log ? 'translate-x-7' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>

            <div className="p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors">
              <label className="block font-semibold text-gray-900 dark:text-white mb-2">
                Audit Log Retention: {settings.max_audit_log_days} days
              </label>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                How long to keep audit logs (1-365 days)
              </p>
              <div className="flex items-center space-x-4">
                <span className="text-xs text-gray-500">1 day</span>
                <input
                  type="range"
                  min="1"
                  max="365"
                  step="1"
                  value={settings.max_audit_log_days}
                  onChange={(e) => setSettings({ ...settings, max_audit_log_days: parseInt(e.target.value) })}
                  className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  disabled={!settings.enable_audit_log}
                />
                <span className="text-xs text-gray-500 dark:text-gray-400">365 days</span>
              </div>
            </div>
          </div>

          {/* Info Section */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg transition-colors">
              <h4 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">ℹ️ How Auto-Learning Works</h4>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-2 ml-4 list-disc">
                <li>When users submit feedback with high confidence (≥90%), the system automatically applies it</li>
                <li>The corrected SQL is tested before learning (if enabled) to ensure it works</li>
                <li>Future similar errors will automatically use the learned correction</li>
                <li>All auto-applied feedback is logged for audit and can be reviewed in the dashboard</li>
                <li>You can always manually review and apply medium/low confidence feedback</li>
              </ul>
            </div>
          </div>

          {/* Metadata */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
            <p>Last updated: {new Date(settings.updated_at).toLocaleString()}</p>
            <p>Created: {new Date(settings.created_at).toLocaleString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
