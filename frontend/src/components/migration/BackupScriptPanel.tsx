import { useState, useEffect } from 'react';
import { Loader2, Copy, Check, Download, AlertTriangle, Archive } from 'lucide-react';
import { migrationAPI } from '../../services/migrationApi';
import { connectionsAPI } from '../../services/api';
import { SchemaObjectToggles } from './SchemaObjectToggles';
import type { BackupScriptsResponse, SchemaObjectFlags } from '../../types/migration';
import type { DatabaseConnection } from '../../types/api';

const DIALECTS = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'sqlite', label: 'SQLite' },
  { value: 'mssql', label: 'SQL Server' },
  { value: 'oracle', label: 'Oracle' },
];

type ScriptTab = 'backup' | 'restore' | 'verify';

const SCRIPT_LABELS: Record<ScriptTab, { file: string; description: string }> = {
  backup: { file: 'backup.sql', description: 'CREATE TABLE statements to recreate the schema' },
  restore: { file: 'restore.sql', description: 'DROP TABLE statements to wipe the schema before a restore' },
  verify: { file: 'verify.sql', description: 'Column-count checks to confirm the schema is intact' },
};

export function BackupScriptPanel() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [connectionId, setConnectionId] = useState<number | ''>('');
  const [dialect, setDialect] = useState('');
  const [scripts, setScripts] = useState<BackupScriptsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<ScriptTab>('backup');
  const [copied, setCopied] = useState(false);
  const [flags, setFlags] = useState<SchemaObjectFlags>({});

  useEffect(() => {
    connectionsAPI.listConnections().then((res) => {
      setConnections(res.connections);
    }).catch(() => {});
  }, []);

  // When connection changes, pre-select its dialect
  const handleConnectionChange = (id: number | '') => {
    setConnectionId(id);
    if (id !== '') {
      const conn = connections.find((c) => c.id === id);
      if (conn) setDialect(conn.database_type || 'postgresql');
    }
    setScripts(null);
    setError('');
  };

  const handleGenerate = async () => {
    if (connectionId === '') return;
    setLoading(true);
    setError('');
    try {
      const result = await migrationAPI.generateBackupScripts(
        connectionId as number,
        dialect || undefined,
        flags,
      );
      setScripts(result);
      setActiveTab('backup');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Backup generation failed');
    } finally {
      setLoading(false);
    }
  };

  const currentSql = scripts
    ? activeTab === 'backup' ? scripts.backup_sql
      : activeTab === 'restore' ? scripts.restore_sql
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
    a.download = SCRIPT_LABELS[activeTab].file;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800">
        <Archive className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-sm font-bold text-blue-700 dark:text-blue-300">Schema Backup Scripts</p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
            Generate <strong>backup.sql</strong> (schema DDL), <strong>restore.sql</strong> (pre-restore cleanup),
            and <strong>verify.sql</strong> (integrity checks) for any connected database.
            Data is not included — these are schema-only scripts.
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Database
          </label>
          <select
            value={connectionId}
            onChange={(e) => handleConnectionChange(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select a database...</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.database_type})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Dialect
          </label>
          <select
            value={dialect}
            onChange={(e) => setDialect(e.target.value)}
            className="px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Auto-detect</option>
            {DIALECTS.map((d) => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || connectionId === ''}
          className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-xs font-bold uppercase tracking-wide transition-all shadow-lg"
        >
          {loading
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : scripts ? 'Regenerate' : 'Generate Scripts'}
        </button>
      </div>

      {/* Extended object toggles */}
      <SchemaObjectToggles flags={flags} onChange={setFlags} dialect={dialect || undefined} />

      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {scripts && (
        <div className="space-y-3">
          {/* Summary */}
          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span className="font-bold text-gray-700 dark:text-gray-300">{scripts.connection_name}</span>
            <span>&middot;</span>
            <span>{scripts.dialect}</span>
            <span>&middot;</span>
            <span>{scripts.table_count} table{scripts.table_count !== 1 ? 's' : ''}</span>
          </div>

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

          {/* Script tabs + code */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
            <div className="flex border-b border-gray-200 dark:border-gray-700">
              {(['backup', 'restore', 'verify'] as ScriptTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 px-4 py-2.5 text-xs font-bold uppercase tracking-wide transition-colors ${
                    activeTab === tab
                      ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 border-b-2 border-indigo-500'
                      : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                  title={SCRIPT_LABELS[tab].description}
                >
                  {SCRIPT_LABELS[tab].file}
                </button>
              ))}
            </div>

            {/* Tab description + toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
              <span className="text-[10px] text-gray-500 dark:text-gray-400">
                {SCRIPT_LABELS[activeTab].description}
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

            <pre className="p-4 text-xs bg-gray-900 text-green-300 overflow-auto max-h-[500px] font-mono leading-relaxed">
              {currentSql || '-- No script generated yet'}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
