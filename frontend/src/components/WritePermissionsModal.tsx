import { useState, useEffect, useCallback, useRef } from 'react';
import { X, Loader2, Shield, ShieldCheck } from 'lucide-react';
import { dmlAPI } from '../services/dmlApi';
import type { WritePermission, WritePermissionRequest } from '../types/dml';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  connectionId: number;
  connectionName: string;
}

const labelClass = "text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400";
const toggleBase = "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50";

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`${toggleBase} ${checked ? 'bg-blue-600' : 'bg-gray-600'} ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}

export default function WritePermissionsModal({ isOpen, onClose, connectionId, connectionName }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [allowInsert, setAllowInsert] = useState(false);
  const [allowUpdate, setAllowUpdate] = useState(false);
  const [allowDelete, setAllowDelete] = useState(false);
  const [requireWhere, setRequireWhere] = useState(true);
  const [maxRows, setMaxRows] = useState(100);
  const [allowedTables, setAllowedTables] = useState<string[] | null>(null);

  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) onClose();
    },
    [onClose, saving]
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener('keydown', handleKeyDown);
    // Focus the panel for keyboard accessibility
    panelRef.current?.focus();
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleKeyDown]);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setSuccess(false);
    setLoading(true);

    dmlAPI.getPermissions(connectionId)
      .then((perms: WritePermission) => {
        setAllowInsert(perms.allow_insert);
        setAllowUpdate(perms.allow_update);
        setAllowDelete(perms.allow_delete);
        setRequireWhere(perms.require_where_clause);
        setMaxRows(perms.max_rows_per_operation);
        setAllowedTables(perms.allowed_tables);
      })
      .catch(() => {
        // No permissions yet — defaults are fine
      })
      .finally(() => setLoading(false));
  }, [isOpen, connectionId]);

  if (!isOpen) return null;

  const hasAnyWrite = allowInsert || allowUpdate || allowDelete;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const request: WritePermissionRequest = {
        allow_insert: allowInsert,
        allow_update: allowUpdate,
        allow_delete: allowDelete,
        require_where_clause: requireWhere,
        max_rows_per_operation: maxRows,
        allowed_tables: allowedTables,
      };
      await dmlAPI.updatePermissions(connectionId, request);
      setSuccess(true);
      setTimeout(() => onClose(), 800);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to save permissions';
      setError(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] backdrop-blur-xl animate-fadeIn p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !saving) onClose(); }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="glass-panel bg-white/5 dark:bg-black/40 rounded-[2rem] shadow-2xl border-white/10 max-w-lg w-full overflow-hidden relative shadow-[0_30px_100px_rgba(0,0,0,0.5)] outline-none"
      >
        {/* Glow */}
        <div className="absolute top-0 left-0 w-48 h-48 bg-emerald-500/5 blur-[80px] -ml-24 -mt-24 pointer-events-none" />

        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5 bg-white/5 dark:bg-black/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl glass-panel text-emerald-500 shadow-lg shadow-emerald-500/10">
              {hasAnyWrite ? <ShieldCheck className="w-5 h-5" /> : <Shield className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Write Permissions</h3>
              <p className="text-sm font-bold text-gray-900 dark:text-white truncate max-w-[280px]">{connectionName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-200 glass-panel rounded-xl hover:scale-110 active:scale-95 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : (
            <>
              {/* Operation Toggles */}
              <div className="space-y-4">
                <label className={labelClass}>Allowed Operations</label>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 glass-panel rounded-xl">
                    <div>
                      <span className="text-sm font-bold text-gray-900 dark:text-white">Insert</span>
                      <p className="text-[11px] text-gray-500">Allow adding new rows</p>
                    </div>
                    <Toggle checked={allowInsert} onChange={setAllowInsert} />
                  </div>
                  <div className="flex items-center justify-between p-3 glass-panel rounded-xl">
                    <div>
                      <span className="text-sm font-bold text-gray-900 dark:text-white">Update</span>
                      <p className="text-[11px] text-gray-500">Allow editing existing rows</p>
                    </div>
                    <Toggle checked={allowUpdate} onChange={setAllowUpdate} />
                  </div>
                  <div className="flex items-center justify-between p-3 glass-panel rounded-xl">
                    <div>
                      <span className="text-sm font-bold text-gray-900 dark:text-white">Delete</span>
                      <p className="text-[11px] text-gray-500">Allow removing rows</p>
                    </div>
                    <Toggle checked={allowDelete} onChange={setAllowDelete} />
                  </div>
                </div>
              </div>

              {/* Safety Settings */}
              {hasAnyWrite && (
                <div className="space-y-4 border-t border-white/5 pt-5">
                  <label className={labelClass}>Safety Guards</label>
                  <div className="flex items-center justify-between p-3 glass-panel rounded-xl">
                    <div>
                      <span className="text-sm font-bold text-gray-900 dark:text-white">Require WHERE clause</span>
                      <p className="text-[11px] text-gray-500">Prevent unscoped updates/deletes</p>
                    </div>
                    <Toggle checked={requireWhere} onChange={setRequireWhere} />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-gray-900 dark:text-white">Max rows per operation</span>
                      <input
                        type="number"
                        min={1}
                        max={10000}
                        value={maxRows}
                        onChange={(e) => setMaxRows(Math.max(1, Math.min(10000, parseInt(e.target.value) || 100)))}
                        className="w-24 px-3 py-2 glass-panel bg-white/5 dark:bg-black/10 border-white/5 rounded-xl text-gray-900 dark:text-white text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-bold"
                      />
                    </div>
                    <p className="text-[11px] text-gray-500">Limit how many rows can be affected in a single operation (1–10,000)</p>
                  </div>
                </div>
              )}

              {/* Status Messages */}
              {error && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-bold">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold">
                  Permissions saved successfully
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {!loading && (
          <div className="flex items-center justify-end gap-3 p-6 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 text-[11px] font-black uppercase tracking-widest text-gray-500 hover:text-gray-300 transition-all"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2.5 bg-blue-600 text-white text-[11px] font-black uppercase tracking-widest rounded-xl hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/20 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {saving ? 'Saving...' : 'Save Permissions'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
