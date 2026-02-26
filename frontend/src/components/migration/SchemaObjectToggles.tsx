import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { SchemaObjectFlags } from '../../types/migration';

const DIALECT_CAPABILITIES: Record<string, Record<string, boolean>> = {
  sqlite:     { views: true,  sequences: false, check_constraints: false, routines: false, triggers: true,  enums: false },
  postgresql: { views: true,  sequences: true,  check_constraints: true,  routines: true,  triggers: true,  enums: true  },
  mysql:      { views: true,  sequences: false, check_constraints: true,  routines: true,  triggers: true,  enums: false },
  mssql:      { views: true,  sequences: true,  check_constraints: true,  routines: true,  triggers: true,  enums: false },
  oracle:     { views: true,  sequences: true,  check_constraints: true,  routines: true,  triggers: true,  enums: false },
  duckdb:     { views: true,  sequences: true,  check_constraints: false, routines: false, triggers: false, enums: false },
};

const FLAG_LABELS: { key: keyof SchemaObjectFlags; label: string; field: string }[] = [
  { key: 'include_views',             label: 'Views',              field: 'views' },
  { key: 'include_sequences',         label: 'Sequences',          field: 'sequences' },
  { key: 'include_check_constraints', label: 'Check Constraints',  field: 'check_constraints' },
  { key: 'include_routines',          label: 'Procedures/Functions', field: 'routines' },
  { key: 'include_triggers',          label: 'Triggers',           field: 'triggers' },
  { key: 'include_enums',             label: 'Enums (PG only)',    field: 'enums' },
];

interface Props {
  flags: SchemaObjectFlags;
  onChange: (flags: SchemaObjectFlags) => void;
  dialect?: string;
}

export function SchemaObjectToggles({ flags, onChange, dialect }: Props) {
  const [expanded, setExpanded] = useState(false);
  const caps = dialect ? DIALECT_CAPABILITIES[dialect] || {} : {};
  const anyEnabled = Object.values(flags).some(Boolean);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wide text-gray-600 dark:text-gray-300">
            Extended Objects
          </span>
          {anyEnabled && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
              {Object.values(flags).filter(Boolean).length} enabled
            </span>
          )}
        </div>
        {expanded ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
      </button>

      {expanded && (
        <div className="px-4 pb-3 grid grid-cols-2 sm:grid-cols-3 gap-2 border-t border-gray-100 dark:border-gray-700 pt-3">
          {FLAG_LABELS.map(({ key, label, field }) => {
            const supported = !dialect || caps[field] !== false;
            return (
              <label
                key={key}
                className={`flex items-center gap-2 text-xs px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${
                  supported
                    ? 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    : 'opacity-40 cursor-not-allowed'
                }`}
                title={supported ? undefined : `Not supported by ${dialect}`}
              >
                <input
                  type="checkbox"
                  checked={!!flags[key]}
                  disabled={!supported}
                  onChange={(e) => onChange({ ...flags, [key]: e.target.checked })}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                />
                <span className="font-medium text-gray-700 dark:text-gray-300">{label}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
