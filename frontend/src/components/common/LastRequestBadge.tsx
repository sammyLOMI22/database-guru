import { useState } from 'react';
import { Activity, Check, Copy } from 'lucide-react';
import { useLastRequestStore, shortId } from '../../stores/lastRequestStore';

export default function LastRequestBadge() {
  const last = useLastRequestStore((s) => s.last);
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);

  if (!last) return null;

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const payload = last.traceparent
      ? `request_id=${last.requestId}\ntraceparent=${last.traceparent}`
      : last.requestId;
    try {
      await navigator.clipboard.writeText(payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard write blocked — silently ignore
    }
  };

  const statusColor =
    last.status == null
      ? 'text-gray-400'
      : last.status >= 500
        ? 'text-red-500'
        : last.status >= 400
          ? 'text-amber-500'
          : 'text-emerald-500';

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        title={`Last request: ${last.method} ${last.url} → ${last.status ?? '—'}`}
        className="flex items-center gap-1.5 px-2.5 py-1.5 glass-panel rounded-xl text-[10px] font-mono font-bold tracking-wide text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-all"
      >
        <Activity className={`w-3 h-3 ${statusColor}`} />
        <span>{shortId(last.requestId)}</span>
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-2 z-50 w-80 p-3 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-xl text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Last Request
              </span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-600 dark:text-gray-300 transition-colors"
                title="Copy request id (and traceparent if present)"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-500" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <dl className="space-y-1.5 font-mono">
              <div>
                <dt className="text-[10px] uppercase text-gray-400">request_id</dt>
                <dd className="break-all text-gray-800 dark:text-gray-200">{last.requestId}</dd>
              </div>
              {last.traceparent && (
                <div>
                  <dt className="text-[10px] uppercase text-gray-400">traceparent</dt>
                  <dd className="break-all text-gray-800 dark:text-gray-200">{last.traceparent}</dd>
                </div>
              )}
              <div className="flex justify-between gap-2">
                <div className="min-w-0">
                  <dt className="text-[10px] uppercase text-gray-400">endpoint</dt>
                  <dd className="truncate text-gray-800 dark:text-gray-200">
                    {last.method} {last.url}
                  </dd>
                </div>
                <div className="text-right">
                  <dt className="text-[10px] uppercase text-gray-400">status</dt>
                  <dd className={`font-bold ${statusColor}`}>{last.status ?? '—'}</dd>
                </div>
              </div>
            </dl>
          </div>
        </>
      )}
    </div>
  );
}
