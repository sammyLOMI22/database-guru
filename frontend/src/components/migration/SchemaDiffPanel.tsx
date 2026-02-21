import { useState, useEffect } from 'react';
import { Loader2, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { migrationAPI } from '../../services/migrationApi';
import { connectionsAPI } from '../../services/api';
import { SchemaObjectToggles } from './SchemaObjectToggles';
import type { SchemaDiffResponse, TableDiff, SchemaObjectFlags } from '../../types/migration';
import type { DatabaseConnection } from '../../types/api';

const RISK_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  critical: 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-200',
};

const DIFF_TYPE_COLORS: Record<string, string> = {
  added: 'text-green-600 dark:text-green-400',
  removed: 'text-red-600 dark:text-red-400',
  modified: 'text-amber-600 dark:text-amber-400',
  type_changed: 'text-blue-600 dark:text-blue-400',
  nullability_changed: 'text-purple-600 dark:text-purple-400',
  default_changed: 'text-gray-600 dark:text-gray-400',
};

interface Props {
  onProjectCreated: (projectId: number) => void;
}

export function SchemaDiffPanel({ onProjectCreated }: Props) {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [sourceId, setSourceId] = useState<number | ''>('');
  const [targetId, setTargetId] = useState<number | ''>('');
  const [projectName, setProjectName] = useState('');
  const [loading, setLoading] = useState(false);
  const [diff, setDiff] = useState<SchemaDiffResponse | null>(null);
  const [error, setError] = useState('');
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [flags, setFlags] = useState<SchemaObjectFlags>({});

  useEffect(() => {
    connectionsAPI.listConnections().then((res) => {
      setConnections(res.connections);
    }).catch(() => {});
  }, []);

  const handleCompare = async (save = false) => {
    if (sourceId === '' || targetId === '') return;
    setLoading(true);
    setError('');
    setDiff(null);
    try {
      const result = await migrationAPI.compareDatabases(
        sourceId as number,
        targetId as number,
        save,
        save ? (projectName || undefined) : undefined,
        flags,
      );
      setDiff(result);
      if (save && result.project_id) {
        onProjectCreated(result.project_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleTable = (name: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {/* Connection selectors */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Source Connection
          </label>
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value ? Number(e.target.value) : '')}
            className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
            data-testid="source-connection-select"
          >
            <option value="">Select source...</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.database_type})</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Target Connection
          </label>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : '')}
            className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
            data-testid="target-connection-select"
          >
            <option value="">Select target...</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.database_type})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Extended object toggles */}
      <SchemaObjectToggles flags={flags} onChange={setFlags} />

      {/* Project name + actions */}
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Project Name (optional)
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="e.g., Staging to Production"
            className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <button
          onClick={() => handleCompare(false)}
          disabled={loading || sourceId === '' || targetId === ''}
          className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-xs font-bold uppercase tracking-wide transition-all shadow-lg"
          data-testid="compare-button"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Compare'}
        </button>
        <button
          onClick={() => handleCompare(true)}
          disabled={loading || sourceId === '' || targetId === ''}
          className="px-5 py-2 rounded-xl bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-xs font-bold uppercase tracking-wide transition-all shadow-lg"
          data-testid="compare-save-button"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Compare & Save'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Results */}
      {diff && (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-white">{diff.diff_summary}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {diff.total_breaking_changes} breaking, {diff.total_safe_changes} safe changes
                </p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${RISK_COLORS[diff.overall_risk] || RISK_COLORS.low}`}>
                {diff.overall_risk} risk
              </span>
            </div>
          </div>

          {/* Table diffs */}
          {diff.table_diffs.map((td) => (
            <TableDiffCard
              key={td.table_name}
              tableDiff={td}
              expanded={expandedTables.has(td.table_name)}
              onToggle={() => toggleTable(td.table_name)}
            />
          ))}

          {/* Extended object diffs */}
          <ExtendedDiffSection label="Views" diffs={diff.view_diffs} nameKey="view_name" />
          <ExtendedDiffSection label="Sequences" diffs={diff.sequence_diffs} nameKey="sequence_name" />
          <ExtendedDiffSection label="Check Constraints" diffs={diff.check_constraint_diffs} nameKey="constraint_name" />
          <ExtendedDiffSection label="Routines" diffs={diff.routine_diffs} nameKey="routine_name" />
          <ExtendedDiffSection label="Triggers" diffs={diff.trigger_diffs} nameKey="trigger_name" />
          <ExtendedDiffSection label="Enums" diffs={diff.enum_diffs} nameKey="enum_name" />
        </div>
      )}
    </div>
  );
}

function TableDiffCard({ tableDiff, expanded, onToggle }: {
  tableDiff: TableDiff;
  expanded: boolean;
  onToggle: () => void;
}) {
  const diffIcon = tableDiff.diff_type === 'added' ? '+' : tableDiff.diff_type === 'removed' ? '-' : '~';

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className={`font-mono text-sm font-bold ${DIFF_TYPE_COLORS[tableDiff.diff_type]}`}>
            {diffIcon}
          </span>
          <span className="text-sm font-bold text-gray-900 dark:text-white">{tableDiff.table_name}</span>
          <span className="text-xs text-gray-500">({tableDiff.diff_type})</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK_COLORS[tableDiff.risk_level]}`}>
            {tableDiff.risk_level}
          </span>
          <span className="text-[10px] text-gray-400">
            {tableDiff.column_diffs.length} column change{tableDiff.column_diffs.length !== 1 ? 's' : ''}
          </span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          {tableDiff.column_diffs.length > 0 && (
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-900/50">
                  <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Column</th>
                  <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Change</th>
                  <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Source</th>
                  <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Target</th>
                  <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {tableDiff.column_diffs.map((cd, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-4 py-2 font-mono font-bold text-gray-900 dark:text-white">{cd.column_name}</td>
                    <td className={`px-4 py-2 font-bold ${DIFF_TYPE_COLORS[cd.diff_type]}`}>{cd.diff_type}</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400 font-mono">
                      {cd.source_state ? `${cd.source_state.type || ''}${cd.source_state.nullable ? ' NULL' : ' NOT NULL'}` : '-'}
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400 font-mono">
                      {cd.target_state ? `${cd.target_state.type || ''}${cd.target_state.nullable ? ' NULL' : ' NOT NULL'}` : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK_COLORS[cd.risk_level]}`}>
                        {cd.risk_level}
                      </span>
                      {cd.is_breaking && <AlertTriangle className="w-3 h-3 text-red-500 inline ml-1" />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {tableDiff.constraint_diffs.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700">
              <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 mb-2">Constraint Changes</p>
              {tableDiff.constraint_diffs.map((cd, i) => (
                <div key={i} className="text-xs text-gray-600 dark:text-gray-400 py-1">
                  <span className={`font-bold ${DIFF_TYPE_COLORS[cd.diff_type]}`}>{cd.diff_type}</span>{' '}
                  {cd.constraint_type}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ExtendedDiffSection({ label, diffs, nameKey }: {
  label: string;
  diffs: Array<Record<string, any>>;
  nameKey: string;
}) {
  if (!diffs || diffs.length === 0) return null;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <div className="px-4 py-3">
        <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">{label}</p>
        {diffs.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-xs py-1">
            <span className={`font-bold ${DIFF_TYPE_COLORS[d.diff_type] || 'text-gray-600'}`}>
              {d.diff_type}
            </span>
            <span className="font-mono text-gray-900 dark:text-white">{d[nameKey] || '?'}</span>
            {d.table_name && <span className="text-gray-400">on {d.table_name}</span>}
            <span className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${RISK_COLORS[d.risk_level] || RISK_COLORS.low}`}>
              {d.risk_level}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
