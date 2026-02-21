import { useState, useEffect } from 'react';
import { Loader2, Copy, Check, Download, AlertTriangle } from 'lucide-react';
import { migrationAPI } from '../../services/migrationApi';
import type { MigrationProjectDetail, GeneratedScriptsResponse } from '../../types/migration';

const DIALECTS = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'sqlite', label: 'SQLite' },
];

type ScriptTab = 'up' | 'down' | 'verify';

interface Props {
  project: MigrationProjectDetail;
  onRefresh: () => void;
}

export function ScriptGeneratorPanel({ project, onRefresh }: Props) {
  const [scripts, setScripts] = useState<GeneratedScriptsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dialect, setDialect] = useState(project.target_dialect || 'postgresql');
  const [activeScript, setActiveScript] = useState<ScriptTab>('up');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (project.up_sql) {
      migrationAPI.getScripts(project.id).then(setScripts).catch(() => {});
    }
  }, [project.id, project.up_sql]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await migrationAPI.generateScripts(project.id, dialect);
      setScripts(result);
      onRefresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Script generation failed');
    } finally {
      setLoading(false);
    }
  };

  const currentSql = scripts
    ? activeScript === 'up' ? scripts.up_sql
      : activeScript === 'down' ? scripts.down_sql
      : scripts.verify_sql
    : '';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(currentSql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadScript = () => {
    const blob = new Blob([currentSql], { type: 'text/sql' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeScript}.sql`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-end gap-3">
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Target Dialect
          </label>
          <select
            value={dialect}
            onChange={(e) => setDialect(e.target.value)}
            className="px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
          >
            {DIALECTS.map((d) => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-xs font-bold uppercase tracking-wide transition-all shadow-lg"
          data-testid="generate-scripts-button"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : scripts ? 'Regenerate' : 'Generate Scripts'}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {scripts && (
        <div className="space-y-3">
          {/* Warnings */}
          {scripts.warnings.length > 0 && (
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
              <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700 dark:text-amber-400 mb-2">Warnings</p>
              {scripts.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400 py-0.5">
                  <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Script tabs */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
            <div className="flex border-b border-gray-200 dark:border-gray-700">
              {(['up', 'down', 'verify'] as ScriptTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveScript(tab)}
                  className={`flex-1 px-4 py-2.5 text-xs font-bold uppercase tracking-wide transition-colors ${
                    activeScript === tab
                      ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 border-b-2 border-indigo-500'
                      : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  {tab}.sql
                </button>
              ))}
            </div>

            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
              <span className="text-[10px] text-gray-500 uppercase tracking-wide">
                {scripts.target_dialect} &middot; {scripts.llm_used ? 'LLM Enhanced' : 'Deterministic'}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={copyToClipboard}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold uppercase rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <button
                  onClick={downloadScript}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold uppercase rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  <Download className="w-3 h-3" />
                  Download
                </button>
              </div>
            </div>

            {/* Code */}
            <pre className="p-4 text-xs bg-gray-900 text-green-300 overflow-auto max-h-[500px] font-mono leading-relaxed">
              {currentSql || '-- No script generated yet'}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
