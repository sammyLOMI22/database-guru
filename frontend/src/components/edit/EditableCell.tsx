// Inline editable cell — Phase 18
import { useState, useRef, useEffect } from 'react';
import type { CellChange } from '../../types/dml';

interface EditableCellProps {
  value: any;
  column: string;
  isPrimaryKey: boolean;
  isDeleted: boolean;
  cellChange?: CellChange;
  onUpdate: (column: string, oldValue: any, newValue: any) => void;
}

export function EditableCell({
  value,
  column,
  isPrimaryKey,
  isDeleted,
  cellChange,
  onUpdate,
}: EditableCellProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const displayValue = cellChange ? cellChange.new_value : value;
  const isModified = !!cellChange;

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleClick = () => {
    if (isPrimaryKey || isDeleted) return;
    setEditValue(displayValue === null ? '' : String(displayValue));
    setEditing(true);
  };

  const handleBlur = () => {
    commitEdit();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      commitEdit();
    } else if (e.key === 'Escape') {
      setEditing(false);
    }
  };

  const commitEdit = () => {
    setEditing(false);
    let newValue: any = editValue;

    // Try to preserve type
    if (editValue === '') {
      newValue = null;
    } else if (editValue === 'true') {
      newValue = true;
    } else if (editValue === 'false') {
      newValue = false;
    } else if (!isNaN(Number(editValue)) && editValue.trim() !== '') {
      newValue = Number(editValue);
    }

    if (newValue !== value) {
      onUpdate(column, value, newValue);
    }
  };

  if (editing) {
    return (
      <td className="px-1 py-1">
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          className="w-full px-2 py-1.5 text-sm font-mono bg-gray-900/80 text-white border border-amber-500/50 rounded focus:outline-none focus:ring-2 focus:ring-amber-500/30"
        />
      </td>
    );
  }

  return (
    <td
      onClick={handleClick}
      className={`px-5 py-3 text-sm font-mono transition-colors ${
        isDeleted
          ? 'text-red-400/60 line-through cursor-not-allowed'
          : isPrimaryKey
          ? 'text-gray-500 cursor-not-allowed'
          : isModified
          ? 'text-amber-300 bg-amber-500/10 ring-1 ring-inset ring-amber-500/20 cursor-pointer'
          : 'text-gray-900 dark:text-gray-100 cursor-pointer hover:bg-white/5'
      }`}
      title={
        isPrimaryKey
          ? 'Primary key (read-only)'
          : isDeleted
          ? 'Row marked for deletion'
          : isModified
          ? `Original: ${cellChange?.old_value ?? 'null'}`
          : 'Click to edit'
      }
    >
      {displayValue === null ? (
        <span className="text-gray-400 dark:text-gray-500 italic text-xs">null</span>
      ) : typeof displayValue === 'object' ? (
        JSON.stringify(displayValue)
      ) : (
        String(displayValue)
      )}
    </td>
  );
}
