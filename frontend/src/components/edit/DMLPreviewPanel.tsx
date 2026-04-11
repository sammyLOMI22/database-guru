// DML SQL preview modal — Phase 18
import { useState } from 'react';
import { X, Copy, Check, Download, Play, Loader2 } from 'lucide-react';
import type { DMLPreviewResponse } from '../../types/dml';

interface DMLPreviewPanelProps {
  preview: DMLPreviewResponse;
  onClose: () => void;
  onExecute: () => void;
  executing: boolean;
}

export function DMLPreviewPanel({
  preview,
  onClose,
  onExecute,
  executing,
}: DMLPreviewPanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(preview.sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([preview.sql], { type: 'text/sql' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'changes.sql';
    a.click();
    URL.revokeObjectURL(url);
  };

  const parts: string[] = [];
  if (preview.summary.INSERT > 0) parts.push(`${preview.summary.INSERT} INSERT`);
  if (preview.summary.UPDATE > 0) parts.push(`${preview.summary.UPDATE} UPDATE`);
  if (preview.summary.DELETE > 0) parts.push(`${preview.summary.DELETE} DELETE`);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="glass-card rounded-2xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div>
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-200">
              Review Changes
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              {preview.change_count} change{preview.change_count !== 1 ? 's' : ''}
              {' '}({parts.join(', ')})
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* SQL preview */}
        <div className="flex-1 overflow-auto p-6">
          <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap bg-black/30 rounded-xl p-4 border border-white/5">
            {preview.sql}
          </pre>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest text-gray-400 hover:text-white hover:bg-white/10 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={onExecute}
              disabled={executing}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-all disabled:opacity-50"
            >
              {executing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              Execute Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
