/**
 * ERContextMenu - Right-click context menu for ER diagram table nodes.
 */

import { useEffect, useRef } from 'react';
import { Zap } from 'lucide-react';

interface ERContextMenuProps {
  position: { x: number; y: number };
  tableName: string;
  onClose: () => void;
  onAnalyzeImpact: (tableName: string) => void;
}

export default function ERContextMenu({
  position,
  tableName,
  onClose,
  onAnalyzeImpact,
}: ERContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="absolute z-50 min-w-[180px] py-1.5 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 backdrop-blur-lg animate-fadeIn"
      style={{ left: position.x, top: position.y }}
    >
      <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700 mb-1">
        {tableName}
      </div>
      <button
        onClick={() => {
          onAnalyzeImpact(tableName);
          onClose();
        }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
      >
        <Zap className="w-3.5 h-3.5" />
        <span>Analyze Impact</span>
      </button>
    </div>
  );
}
