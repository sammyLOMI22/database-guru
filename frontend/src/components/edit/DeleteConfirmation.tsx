// Delete confirmation modal — Phase 18
import { AlertTriangle, X, Trash2 } from 'lucide-react';

interface DeleteConfirmationProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  rowCount: number;
  tableName: string;
}

export function DeleteConfirmation({
  isOpen,
  onClose,
  onConfirm,
  rowCount,
  tableName,
}: DeleteConfirmationProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="glass-card rounded-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-200">
              Confirm Delete
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <p className="text-sm text-gray-300">
            You are about to mark{' '}
            <span className="font-bold text-red-400">{rowCount}</span>{' '}
            row{rowCount !== 1 ? 's' : ''} from{' '}
            <span className="font-mono text-gray-200">{tableName}</span>{' '}
            for deletion.
          </p>
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-xs text-red-300">
              This action cannot be undone after execution. The rows will be
              permanently deleted from the database.
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete {rowCount} Row{rowCount !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </div>
  );
}
