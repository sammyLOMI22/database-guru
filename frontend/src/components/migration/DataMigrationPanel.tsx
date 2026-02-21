import { useState, useEffect } from 'react';
import { Loader2, ChevronDown, ChevronUp, Copy, Check, AlertTriangle } from 'lucide-react';
import { migrationAPI } from '../../services/migrationApi';
import type { MigrationProjectDetail, DataMigrationPlanResponse, TableDataMigration } from '../../types/migration';

interface Props {
  project: MigrationProjectDetail;
  onRefresh: () => void;
}

export function DataMigrationPanel({ project, onRefresh }: Props) {
  const [plan, setPlan] = useState<DataMigrationPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [batchSize, setBatchSize] = useState(1000);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (project.data_migration_plan) {
      migrationAPI.getDataMigration(project.id).then(setPlan).catch(() => {});
    }
  }, [project.id, project.data_migration_plan]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await migrationAPI.generateDataMigration(project.id, batchSize);
      setPlan(result);
      onRefresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Data migration generation failed');
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
      {/* Controls */}
      <div className="flex items-end gap-3">
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 block mb-1">
            Batch Size
          </label>
          <input
            type="number"
            value={batchSize}
            onChange={(e) => setBatchSize(Math.max(1, Number(e.target.value)))}
            min={1}
            className="w-32 px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-xs font-bold uppercase tracking-wide transition-all shadow-lg"
          data-testid="generate-data-migration-button"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : plan ? 'Regenerate' : 'Generate Data Migration'}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {plan && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">Tables</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-1">{plan.total_tables_with_data}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">Batch Size</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-1">{plan.batch_size.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">LLM Used</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-1">{plan.llm_used ? 'Yes' : 'No'}</p>
              </div>
            </div>
            {plan.recommended_order.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500 mb-1">Recommended Order</p>
                <p className="text-xs text-gray-700 dark:text-gray-300 font-mono">
                  {plan.recommended_order.join(' → ')}
                </p>
              </div>
            )}
          </div>

          {/* Table migrations */}
          {plan.table_migrations.map((tm) => (
            <TableMigrationCard
              key={tm.source_table}
              migration={tm}
              expanded={expandedTables.has(tm.source_table)}
              onToggle={() => toggleTable(tm.source_table)}
            />
          ))}

          {plan.table_migrations.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">
              No tables require data migration (only added/removed tables in diff).
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function TableMigrationCard({ migration, expanded, onToggle }: {
  migration: TableDataMigration;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-900 dark:text-white font-mono">{migration.source_table}</span>
          <span className="text-[10px] text-gray-400">
            {migration.column_mappings.length} mapping{migration.column_mappings.length !== 1 ? 's' : ''}
          </span>
          {migration.warnings.length > 0 && (
            <AlertTriangle className="w-3 h-3 text-amber-500" />
          )}
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 space-y-3">
          {/* Column mappings */}
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900/50">
                <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Source</th>
                <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Target</th>
                <th className="px-4 py-2 text-left font-bold text-gray-500 uppercase tracking-wide">Transform</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {migration.column_mappings.map((cm, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-4 py-2 font-mono text-gray-900 dark:text-white">{cm.source_col || '(new)'}</td>
                  <td className="px-4 py-2 font-mono text-gray-900 dark:text-white">{cm.target_col}</td>
                  <td className="px-4 py-2 font-mono text-gray-600 dark:text-gray-400">{cm.transform_expression}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* SQL blocks */}
          <div className="px-4 pb-4 space-y-3">
            <SqlBlock label="Insert SQL" sql={migration.insert_sql} />
            <SqlBlock label="Batched Insert SQL" sql={migration.batched_insert_sql} />
            <SqlBlock label="Verification SQL" sql={migration.count_verify_sql} />
          </div>

          {/* Warnings */}
          {migration.warnings.length > 0 && (
            <div className="px-4 pb-4">
              {migration.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400 py-0.5">
                  <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SqlBlock({ label, sql }: { label: string; sql: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-bold uppercase tracking-wide text-gray-500">{label}</p>
        <button
          onClick={copy}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="text-xs bg-gray-900 text-green-300 p-3 rounded-lg overflow-x-auto font-mono leading-relaxed">
        {sql || '-- N/A'}
      </pre>
    </div>
  );
}
