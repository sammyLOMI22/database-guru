// Add new row modal — Phase 18
import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import type { TableInfo } from '../../types/dml';

interface AddRowFormProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (rowData: Record<string, any>) => void;
  tableInfo: TableInfo;
}

export function AddRowForm({
  isOpen,
  onClose,
  onAdd,
  tableInfo,
}: AddRowFormProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});

  if (!isOpen) return null;

  const editableColumns = tableInfo.columns.filter(
    (col) => !col.is_autoincrement
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const rowData: Record<string, any> = {};

    for (const col of editableColumns) {
      const raw = formData[col.name];
      if (raw === undefined || raw === '') {
        if (col.nullable || col.default !== null) {
          // Skip — let DB handle the default or NULL
          continue;
        }
        rowData[col.name] = '';
      } else {
        // Type coercion
        const lowerType = col.type.toLowerCase();
        if (
          lowerType.includes('int') ||
          lowerType.includes('float') ||
          lowerType.includes('double') ||
          lowerType.includes('decimal') ||
          lowerType.includes('numeric') ||
          lowerType.includes('real')
        ) {
          rowData[col.name] = Number(raw);
        } else if (lowerType.includes('bool')) {
          rowData[col.name] = raw.toLowerCase() === 'true';
        } else if (raw.toLowerCase() === 'null') {
          rowData[col.name] = null;
        } else {
          rowData[col.name] = raw;
        }
      }
    }

    onAdd(rowData);
    setFormData({});
    onClose();
  };

  const handleAddAnother = () => {
    const rowData: Record<string, any> = {};
    for (const col of editableColumns) {
      const raw = formData[col.name];
      if (raw !== undefined && raw !== '') {
        rowData[col.name] = raw;
      }
    }
    onAdd(rowData);
    setFormData({});
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="glass-card rounded-2xl max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-200">
              Add Row to {tableInfo.table_name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-auto p-6 space-y-4">
          {editableColumns.map((col) => (
            <div key={col.name}>
              <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-gray-400 mb-1.5">
                {col.name}
                {col.is_primary_key && (
                  <span className="text-blue-400 text-[10px]">PK</span>
                )}
                {!col.nullable && !col.default && (
                  <span className="text-red-400">*</span>
                )}
              </label>
              <input
                type="text"
                value={formData[col.name] || ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    [col.name]: e.target.value,
                  }))
                }
                placeholder={
                  col.default
                    ? `Default: ${col.default}`
                    : col.nullable
                    ? 'NULL'
                    : `Required (${col.type})`
                }
                className="w-full px-3 py-2 text-sm font-mono glass-panel rounded-lg text-gray-200 placeholder-gray-600 border border-white/10 focus:border-emerald-500/30 focus:ring-1 focus:ring-emerald-500/20 focus:outline-none"
              />
              <span className="text-[10px] text-gray-600 mt-0.5">
                {col.type}
                {col.nullable ? ' · nullable' : ' · required'}
              </span>
            </div>
          ))}
        </form>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-white/10">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleAddAnother}
            className="px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
          >
            Add & Another
          </button>
          <button
            onClick={handleSubmit as any}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Row
          </button>
        </div>
      </div>
    </div>
  );
}
