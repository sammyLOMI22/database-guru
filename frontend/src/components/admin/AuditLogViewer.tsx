import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  ShieldCheck,
  X,
} from 'lucide-react';
import {
  auditApi,
  type AuditFacets,
  type AuditLog,
  type AuditLogQuery,
} from '../../services/auditApi';
import { formatTimestamp } from '../../utils/formatUtils';

const PAGE_SIZE = 50;

const STATUS_DEFAULT: AuditLogQuery = { limit: PAGE_SIZE, offset: 0 };

interface FilterState {
  action: string;
  resource_type: string;
  user_id: string;
  start_date: string;
  end_date: string;
}

const EMPTY_FILTERS: FilterState = {
  action: '',
  resource_type: '',
  user_id: '',
  start_date: '',
  end_date: '',
};

const toIsoOrUndefined = (v: string): string | undefined => {
  if (!v) return undefined;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
};

export default function AuditLogViewer() {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [page, setPage] = useState(0);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facets, setFacets] = useState<AuditFacets>({ actions: [], resource_types: [] });
  const [selected, setSelected] = useState<AuditLog | null>(null);

  const buildQuery = useCallback(
    (f: FilterState, offset: number): AuditLogQuery => ({
      ...STATUS_DEFAULT,
      offset,
      action: f.action || undefined,
      resource_type: f.resource_type || undefined,
      user_id: f.user_id ? Number(f.user_id) : undefined,
      start_date: toIsoOrUndefined(f.start_date),
      end_date: toIsoOrUndefined(f.end_date),
    }),
    [],
  );

  const fetchLogs = useCallback(
    async (f: FilterState, offset: number) => {
      setLoading(true);
      setError(null);
      try {
        const resp = await auditApi.listLogs(buildQuery(f, offset));
        setLogs(resp.items);
        setTotal(resp.total);
      } catch (err: any) {
        const status = err?.response?.status;
        if (status === 403) {
          setError('Admin access required to view audit logs.');
        } else if (status === 401) {
          setError('Sign in to view audit logs.');
        } else {
          setError(err?.message || 'Failed to load audit logs.');
        }
        setLogs([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [buildQuery],
  );

  useEffect(() => {
    auditApi
      .getFacets()
      .then(setFacets)
      .catch(() => {/* facets are best-effort */});
  }, []);

  useEffect(() => {
    fetchLogs(appliedFilters, page * PAGE_SIZE);
  }, [appliedFilters, page, fetchLogs]);

  const applyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setAppliedFilters(filters);
  };

  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(0);
  };

  const updateFilter = (key: keyof FilterState, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const showingFrom = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const showingTo = Math.min(total, page * PAGE_SIZE + logs.length);

  const filtersActive = useMemo(
    () => Object.values(appliedFilters).some((v) => v !== ''),
    [appliedFilters],
  );

  return (
    <div className="max-w-[1600px] mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-6 h-6 text-purple-500" />
          <div>
            <h2 className="text-xl font-black tracking-tight text-gray-900 dark:text-gray-100">
              Audit Log
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Security-relevant actions taken in this deployment.
            </p>
          </div>
        </div>
        <button
          onClick={() => fetchLogs(appliedFilters, page * PAGE_SIZE)}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wide bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <form
        onSubmit={applyFilters}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 p-4 rounded-xl bg-white/60 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-800"
      >
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Action
          </span>
          <select
            value={filters.action}
            onChange={(e) => updateFilter('action', e.target.value)}
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          >
            <option value="">All</option>
            {facets.actions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Resource type
          </span>
          <select
            value={filters.resource_type}
            onChange={(e) => updateFilter('resource_type', e.target.value)}
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          >
            <option value="">All</option>
            {facets.resource_types.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            User id
          </span>
          <input
            type="number"
            min={1}
            value={filters.user_id}
            onChange={(e) => updateFilter('user_id', e.target.value)}
            placeholder="Any"
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Start
          </span>
          <input
            type="datetime-local"
            value={filters.start_date}
            onChange={(e) => updateFilter('start_date', e.target.value)}
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            End
          </span>
          <input
            type="datetime-local"
            value={filters.end_date}
            onChange={(e) => updateFilter('end_date', e.target.value)}
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          />
        </label>

        <div className="flex items-end gap-2">
          <button
            type="submit"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold uppercase bg-blue-600 text-white hover:bg-blue-700"
          >
            <Filter className="w-3.5 h-3.5" />
            Apply
          </button>
          {filtersActive && (
            <button
              type="button"
              onClick={clearFilters}
              className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-bold uppercase text-gray-500 hover:text-red-500"
            >
              <X className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="p-3 rounded-md bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2 text-left">Timestamp</th>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Action</th>
                <th className="px-3 py-2 text-left">Resource</th>
                <th className="px-3 py-2 text-left">IP</th>
                <th className="px-3 py-2 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {logs.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-gray-400">
                    No audit log entries match the current filters.
                  </td>
                </tr>
              )}
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className="hover:bg-blue-50/40 dark:hover:bg-blue-900/10 transition-colors"
                >
                  <td className="px-3 py-2 font-mono text-gray-700 dark:text-gray-200 whitespace-nowrap">
                    {formatTimestamp(log.timestamp)}
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-200">
                    {log.username ?? <span className="text-gray-400">—</span>}
                    {log.user_id != null && (
                      <span className="ml-1 text-[10px] text-gray-400">#{log.user_id}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-bold uppercase tracking-wider text-[10px]">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-200">
                    <span className="font-bold">{log.resource_type}</span>
                    {log.resource_id && (
                      <span className="ml-1 text-gray-400 font-mono">#{log.resource_id}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-500 dark:text-gray-400">
                    {log.ip_address ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {log.details ? (
                      <button
                        onClick={() => setSelected(log)}
                        className="text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        View
                      </button>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
          {loading
            ? 'Loading…'
            : total === 0
              ? 'No results'
              : `Showing ${showingFrom}–${showingTo} of ${total}`}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || loading}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-mono">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => (p + 1 < totalPages ? p + 1 : p))}
            disabled={page + 1 >= totalPages || loading}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {selected && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40"
            onClick={() => setSelected(null)}
          />
          <aside className="fixed top-0 right-0 h-full w-full sm:w-[480px] bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 z-50 shadow-2xl overflow-y-auto">
            <header className="sticky top-0 px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                  Audit entry #{selected.id}
                </h3>
                <p className="text-[10px] text-gray-500">
                  {formatTimestamp(selected.timestamp)}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="w-4 h-4" />
              </button>
            </header>
            <div className="p-4 space-y-3 text-xs">
              <Field label="Action" value={selected.action} />
              <Field
                label="Resource"
                value={`${selected.resource_type}${selected.resource_id ? ` #${selected.resource_id}` : ''}`}
              />
              <Field
                label="User"
                value={
                  selected.username
                    ? `${selected.username}${selected.user_id != null ? ` (#${selected.user_id})` : ''}`
                    : selected.user_id != null
                      ? `#${selected.user_id}`
                      : '—'
                }
              />
              <Field label="IP address" value={selected.ip_address ?? '—'} />
              <div>
                <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400 mb-1">
                  Details
                </p>
                <pre className="p-3 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 overflow-x-auto whitespace-pre-wrap break-all font-mono">
                  {JSON.stringify(selected.details, null, 2) || '—'}
                </pre>
              </div>
            </div>
          </aside>
        </>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400">{label}</p>
      <p className="text-gray-800 dark:text-gray-200 font-mono break-all">{value}</p>
    </div>
  );
}
