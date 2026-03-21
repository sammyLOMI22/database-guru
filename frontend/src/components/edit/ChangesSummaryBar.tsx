// Pending changes summary bar — Phase 18
import { useState } from 'react';
import { Eye, X, Save, Loader2 } from 'lucide-react';
import { useDMLPreview, useDMLExecute } from '../../hooks/useDMLExecution';
import { DMLPreviewPanel } from './DMLPreviewPanel';
import type { ChangeSummary, RowChange } from '../../types/dml';

interface ChangesSummaryBarProps {
  summary: ChangeSummary;
  onPreview: () => void;
  onDiscard: () => void;
  connectionId: number;
  changes: RowChange[];
}

export function ChangesSummaryBar({
  summary,
  onDiscard,
  connectionId,
  changes,
}: ChangesSummaryBarProps) {
  const [showPreview, setShowPreview] = useState(false);
  const previewMutation = useDMLPreview();
  const executeMutation = useDMLExecute();

  const handlePreview = async () => {
    await previewMutation.mutateAsync({
      connection_id: connectionId,
      changes,
    });
    setShowPreview(true);
  };

  const handleExecute = async () => {
    const result = await executeMutation.mutateAsync({
      connection_id: connectionId,
      changes,
    });
    if (result.success) {
      onDiscard(); // Clear changes on success
      setShowPreview(false);
    }
  };

  const parts: string[] = [];
  if (summary.INSERT > 0) parts.push(`${summary.INSERT} insert${summary.INSERT > 1 ? 's' : ''}`);
  if (summary.UPDATE > 0) parts.push(`${summary.UPDATE} update${summary.UPDATE > 1 ? 's' : ''}`);
  if (summary.DELETE > 0) parts.push(`${summary.DELETE} delete${summary.DELETE > 1 ? 's' : ''}`);

  return (
    <>
      <div className="sticky bottom-0 flex items-center justify-between px-5 py-3 bg-gray-900/95 backdrop-blur border-t border-amber-500/20 z-10">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          <span className="text-sm text-gray-300">
            <span className="font-bold text-amber-400">{summary.total}</span> pending{' '}
            {summary.total === 1 ? 'change' : 'changes'}
            <span className="text-gray-500 ml-1">({parts.join(', ')})</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePreview}
            disabled={previewMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
          >
            {previewMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Eye className="w-3.5 h-3.5" />
            )}
            Preview SQL
          </button>
          <button
            onClick={onDiscard}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
          >
            <X className="w-3.5 h-3.5" />
            Discard
          </button>
          <button
            onClick={handleExecute}
            disabled={executeMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-all disabled:opacity-50"
          >
            {executeMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            Save Changes
          </button>
        </div>
      </div>

      {/* Success/error feedback */}
      {executeMutation.isSuccess && (
        <div className="px-5 py-2 bg-emerald-500/10 border-t border-emerald-500/20 text-sm text-emerald-400">
          Changes saved successfully. {executeMutation.data.rows_affected} row(s) affected.
        </div>
      )}
      {executeMutation.isError && (
        <div className="px-5 py-2 bg-red-500/10 border-t border-red-500/20 text-sm text-red-400">
          Error: {executeMutation.error.message}
        </div>
      )}

      {/* Preview modal */}
      {showPreview && previewMutation.data && (
        <DMLPreviewPanel
          preview={previewMutation.data}
          onClose={() => setShowPreview(false)}
          onExecute={handleExecute}
          executing={executeMutation.isPending}
        />
      )}
    </>
  );
}
