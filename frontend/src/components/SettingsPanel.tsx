import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, RotateCcw, Info } from 'lucide-react';

interface SystemSettings {
  id: number;
  auto_learning_enabled: boolean;
  confidence_threshold: number;
  apply_mode: 'immediate' | 'deferred';
  test_before_learning: boolean;
  enable_audit_log: boolean;
  max_audit_log_days: number;
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
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <SettingsIcon className="w-6 h-6 text-gray-700" />
              <div>
                <h2 className="text-2xl font-bold text-gray-900">System Settings</h2>
                <p className="text-sm text-gray-600">Configure auto-learning and feedback behavior</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={resetSettings}
                disabled={saving}
                className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50"
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
          <div className="mx-6 mt-4 p-4 bg-red-100 border-2 border-red-500 rounded-lg">
            <p className="text-red-900 font-semibold">⚠️ {error}</p>
          </div>
        )}
        {successMessage && (
          <div className="mx-6 mt-4 p-4 bg-green-100 border-2 border-green-500 rounded-lg">
            <p className="text-green-900 font-semibold">✅ {successMessage}</p>
          </div>
        )}

        {/* Settings Form */}
        <div className="p-6 space-y-8">
          {/* Auto-Learning Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
              <span>🤖 Smart Auto-Learning (Option 3)</span>
            </h3>

            {/* Master Toggle */}
            <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex-1">
                <label className="font-semibold text-gray-900">Enable Auto-Learning</label>
                <p className="text-sm text-gray-600 mt-1">
                  Automatically apply high-confidence user feedback to the learning system
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, auto_learning_enabled: !settings.auto_learning_enabled })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                  settings.auto_learning_enabled ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    settings.auto_learning_enabled ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Confidence Threshold Slider */}
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <label className="block font-semibold text-gray-900 mb-2">
                Confidence Threshold: {(settings.confidence_threshold * 100).toFixed(0)}%
              </label>
              <p className="text-sm text-gray-600 mb-4">
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
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  disabled={!settings.auto_learning_enabled}
                />
                <span className="text-xs text-gray-500">100%</span>
              </div>
              <div className="mt-3 p-3 bg-white border border-gray-200 rounded text-sm">
                <Info className="w-4 h-4 inline mr-2 text-blue-500" />
                <strong>Auto-Learning Rules:</strong>
                <ul className="mt-2 ml-6 list-disc space-y-1 text-gray-700">
                  <li>High confidence (≥90%): Auto-apply immediately</li>
                  <li>Medium confidence (70-89%): Queue for batch (deferred mode)</li>
                  <li>Low confidence (&lt;70%): Manual review required</li>
                </ul>
              </div>
            </div>

            {/* Apply Mode */}
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <label className="block font-semibold text-gray-900 mb-2">Apply Mode</label>
              <p className="text-sm text-gray-600 mb-3">
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
                  <span className="text-sm">
                    <strong>Deferred</strong> - Queue for batch processing
                  </span>
                </label>
              </div>
            </div>

            {/* Test Before Learning */}
            <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex-1">
                <label className="font-semibold text-gray-900">Test Before Learning</label>
                <p className="text-sm text-gray-600 mt-1">
                  Execute corrected SQL to verify it works before adding to learning system
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, test_before_learning: !settings.test_before_learning })}
                disabled={!settings.auto_learning_enabled}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors disabled:opacity-50 ${
                  settings.test_before_learning ? 'bg-green-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    settings.test_before_learning ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Audit Settings Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">📋 Audit & Logging</h3>

            <div className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex-1">
                <label className="font-semibold text-gray-900">Enable Audit Log</label>
                <p className="text-sm text-gray-600 mt-1">
                  Track all auto-applied feedback for review and rollback
                </p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, enable_audit_log: !settings.enable_audit_log })}
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                  settings.enable_audit_log ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    settings.enable_audit_log ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <label className="block font-semibold text-gray-900 mb-2">
                Audit Log Retention: {settings.max_audit_log_days} days
              </label>
              <p className="text-sm text-gray-600 mb-3">
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
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  disabled={!settings.enable_audit_log}
                />
                <span className="text-xs text-gray-500">365 days</span>
              </div>
            </div>
          </div>

          {/* Info Section */}
          <div className="pt-6 border-t border-gray-200">
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">ℹ️ How Auto-Learning Works</h4>
              <ul className="text-sm text-blue-800 space-y-2 ml-4 list-disc">
                <li>When users submit feedback with high confidence (≥90%), the system automatically applies it</li>
                <li>The corrected SQL is tested before learning (if enabled) to ensure it works</li>
                <li>Future similar errors will automatically use the learned correction</li>
                <li>All auto-applied feedback is logged for audit and can be reviewed in the dashboard</li>
                <li>You can always manually review and apply medium/low confidence feedback</li>
              </ul>
            </div>
          </div>

          {/* Metadata */}
          <div className="pt-4 border-t border-gray-200 text-xs text-gray-500">
            <p>Last updated: {new Date(settings.updated_at).toLocaleString()}</p>
            <p>Created: {new Date(settings.created_at).toLocaleString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
