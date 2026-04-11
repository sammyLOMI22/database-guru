// Edit Mode toggle button — Phase 18
import { Pencil, PenLine } from 'lucide-react';

interface EditModeToggleProps {
  isEditMode: boolean;
  canEdit: boolean;
  onToggle: () => void;
  disabledReason: string | null;
}

export function EditModeToggle({
  isEditMode,
  canEdit,
  onToggle,
  disabledReason,
}: EditModeToggleProps) {
  return (
    <div className="relative group">
      <button
        onClick={onToggle}
        disabled={!canEdit}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest transition-all ${
          isEditMode
            ? 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30'
            : canEdit
            ? 'text-gray-400 hover:text-emerald-400 hover:bg-white/10'
            : 'text-gray-600 cursor-not-allowed opacity-50'
        }`}
        title={disabledReason || (isEditMode ? 'Exit edit mode' : 'Enter edit mode')}
      >
        {isEditMode ? (
          <PenLine className="w-3.5 h-3.5" />
        ) : (
          <Pencil className="w-3.5 h-3.5" />
        )}
        {isEditMode ? 'Editing' : 'Edit'}
      </button>
      {disabledReason && !canEdit && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 rounded-lg bg-gray-900 text-gray-300 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
          {disabledReason}
        </div>
      )}
    </div>
  );
}
