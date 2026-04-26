import { useEffect, useState, useCallback } from 'react';
import {
  Activity,
  Database,
  Cpu,
  HardDrive,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Gauge,
  Search,
  ScrollText,
  HeartPulse,
} from 'lucide-react';
import { healthAPI, queryAPI, settingsAPI } from '../../services/api';
import { cacheAPI } from '../../services/cacheApi';
import { auditApi, type AuditLog } from '../../services/auditApi';
import type {
  HealthCheckResponse,
  ObservabilityConfig,
  QueryHistoryItem,
} from '../../types/api';
import { useLastRequestStore, shortId } from '../../stores/lastRequestStore';
import { formatTimestamp } from '../../utils/formatUtils';

interface CacheStats {
  semantic_cache?: {
    total_lookups?: number;
    hit_rate_percent?: number;
    memory_entries?: number;
  };
  llm_cache?: {
    hit_rate_percent?: number;
  };
}

const formatDuration = (ms: number | null | undefined) => {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
};

export default function SystemHealthPanel() {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [recentQueries, setRecentQueries] = useState<QueryHistoryItem[]>([]);
  const [recentQueriesError, setRecentQueriesError] = useState<string | null>(null);
  const [recentAudit, setRecentAudit] = useState<AuditLog[]>([]);
  const [recentAuditError, setRecentAuditError] = useState<string | null>(null);
  const [cache, setCache] = useState<CacheStats | null>(null);
  const [obsConfig, setObsConfig] = useState<ObservabilityConfig | null>(null);
  const [loading, setLoading] = useState(false);

  const lastRequest = useLastRequestStore((s) => s.last);

  const loadAll = useCallback(async () => {
    setLoading(true);
    // Health
    try {
      const h = await healthAPI.check();
      setHealth(h);
      setHealthError(null);
    } catch (err: any) {
      setHealth(null);
      setHealthError(err?.message || 'Health endpoint unreachable.');
    }

    // Recent queries
    try {
      const items = await queryAPI.getHistory(10, 0);
      setRecentQueries(items);
      setRecentQueriesError(null);
    } catch (err: any) {
      setRecentQueries([]);
      setRecentQueriesError(err?.response?.data?.detail || err?.message || 'Could not load recent queries.');
    }

    // Recent audit
    try {
      const resp = await auditApi.listLogs({ limit: 10, offset: 0 });
      setRecentAudit(resp.items);
      setRecentAuditError(null);
    } catch (err: any) {
      setRecentAudit([]);
      const status = err?.response?.status;
      if (status === 403) setRecentAuditError('Admin access required to view audit activity.');
      else setRecentAuditError(err?.response?.data?.detail || err?.message || 'Could not load audit activity.');
    }

    // Cache (best-effort) — routed through axios so the auth interceptor
    // attaches the bearer token under REQUIRE_AUTH=true and the 401 handler
    // can clear stale credentials consistently with the rest of the app.
    try {
      const stats = await cacheAPI.getStats();
      setCache(stats as unknown as CacheStats);
    } catch {
      // optional
    }

    // Observability config from settings — same axios path as above.
    try {
      const data: any = await settingsAPI.getSettings();
      setObsConfig({
        metrics_enabled: data.metrics_enabled,
        metrics_endpoint_exposed: data.metrics_endpoint_exposed,
        metrics_public_url: data.metrics_public_url,
        otel_enabled: data.otel_enabled,
        otel_service_name: data.otel_service_name,
        otel_traces_sampler_ratio: data.otel_traces_sampler_ratio,
        jaeger_ui_url: data.jaeger_ui_url,
        grafana_url: data.grafana_url,
      });
    } catch {
      // optional
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  return (
    <div className="max-w-[1600px] mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <HeartPulse className="w-6 h-6 text-purple-500" />
          <div>
            <h2 className="text-xl font-black tracking-tight text-gray-900 dark:text-gray-100">
              System Health
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Live readouts from /health, recent queries, audit activity, and cache.
            </p>
          </div>
        </div>
        <button
          onClick={loadAll}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wide bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Health snapshot */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <HealthCard
          label="API"
          ok={!!health && health.status === 'healthy'}
          icon={<Activity className="w-4 h-4" />}
          detail={health?.version ? `v${health.version}` : healthError ?? 'Unknown'}
        />
        <HealthCard
          label="Database"
          ok={health?.services?.database === true}
          icon={<Database className="w-4 h-4" />}
          detail={health?.services?.database ? 'Reachable' : healthError ?? 'Not reporting'}
        />
        <HealthCard
          label="Cache"
          ok={health?.services?.cache === true}
          icon={<HardDrive className="w-4 h-4" />}
          detail={health?.services?.cache ? 'Reachable' : healthError ?? 'Not reporting'}
        />
        <HealthCard
          label="LLM"
          ok={health?.services?.llm === true}
          icon={<Cpu className="w-4 h-4" />}
          detail={health?.services?.llm ? 'Reachable' : healthError ?? 'Not reporting'}
        />
      </section>

      {/* Observability gates */}
      <section className="p-4 rounded-xl glass-panel border border-gray-200 dark:border-gray-800">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-200 mb-3 flex items-center gap-2">
          <Gauge className="w-3.5 h-3.5 text-emerald-500" />
          Observability gates
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <Gate
            label="Prometheus"
            on={!!obsConfig?.metrics_enabled && !!obsConfig?.metrics_endpoint_exposed}
            extra={obsConfig?.metrics_public_url || (obsConfig?.metrics_endpoint_exposed ? '/metrics' : '')}
          />
          <Gate
            label="OpenTelemetry"
            on={!!obsConfig?.otel_enabled}
            extra={obsConfig?.otel_service_name ?? ''}
          />
          <Gate label="Jaeger UI" on={!!obsConfig?.jaeger_ui_url} extra={obsConfig?.jaeger_ui_url ?? ''} />
          <Gate label="Grafana" on={!!obsConfig?.grafana_url} extra={obsConfig?.grafana_url ?? ''} />
        </div>
        {obsConfig?.otel_traces_sampler_ratio != null && (
          <p className="mt-3 text-[11px] text-gray-500">
            Trace sampler ratio: <span className="font-mono">{obsConfig.otel_traces_sampler_ratio}</span>
          </p>
        )}
      </section>

      {/* Cache + correlation */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="p-4 rounded-xl glass-panel border border-gray-200 dark:border-gray-800">
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-200 mb-2 flex items-center gap-2">
            <HardDrive className="w-3.5 h-3.5 text-blue-500" />
            Cache
          </h3>
          {cache ? (
            <ul className="text-xs text-gray-700 dark:text-gray-200 space-y-1">
              <li>
                Semantic hit rate:{' '}
                <span className="font-mono">
                  {cache.semantic_cache?.hit_rate_percent != null
                    ? `${cache.semantic_cache.hit_rate_percent.toFixed(1)}%`
                    : '—'}
                </span>
              </li>
              <li>
                Semantic entries:{' '}
                <span className="font-mono">{cache.semantic_cache?.memory_entries ?? '—'}</span>
              </li>
              <li>
                LLM hit rate:{' '}
                <span className="font-mono">
                  {cache.llm_cache?.hit_rate_percent != null
                    ? `${cache.llm_cache.hit_rate_percent.toFixed(1)}%`
                    : '—'}
                </span>
              </li>
            </ul>
          ) : (
            <p className="text-xs text-gray-500">Cache stats not available.</p>
          )}
        </div>

        <div className="p-4 rounded-xl glass-panel border border-gray-200 dark:border-gray-800">
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-200 mb-2 flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-emerald-500" />
            Last request
          </h3>
          {lastRequest ? (
            <div className="text-xs text-gray-700 dark:text-gray-200 space-y-1">
              <p>
                <span className="font-bold">{lastRequest.method}</span>{' '}
                <span className="font-mono">{lastRequest.url}</span> →{' '}
                <span className="font-mono">{lastRequest.status ?? '—'}</span>
              </p>
              <p className="font-mono text-[11px] text-gray-500">
                request_id: {shortId(lastRequest.requestId)} (full id in header badge)
              </p>
              {lastRequest.traceparent && (
                <p className="font-mono text-[11px] text-gray-500 break-all">
                  traceparent: {lastRequest.traceparent}
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs text-gray-500">
              Run a query — the most recent request id appears here for log correlation.
            </p>
          )}
        </div>
      </section>

      {/* Recent queries */}
      <section className="p-4 rounded-xl glass-panel border border-gray-200 dark:border-gray-800">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-200 mb-3 flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-amber-500" />
          Recent queries
        </h3>
        {recentQueriesError ? (
          <ErrorRow message={recentQueriesError} />
        ) : recentQueries.length === 0 ? (
          <p className="text-xs text-gray-500">
            No queries yet. Run something on the Chat tab and it will show up here.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="text-left px-2 py-1">When</th>
                  <th className="text-left px-2 py-1">Question</th>
                  <th className="text-left px-2 py-1">Status</th>
                  <th className="text-right px-2 py-1">Rows</th>
                  <th className="text-right px-2 py-1">Time</th>
                  <th className="text-left px-2 py-1">Model</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {recentQueries.map((q) => (
                  <tr key={q.id} className="hover:bg-blue-50/40 dark:hover:bg-blue-900/10">
                    <td className="px-2 py-1.5 font-mono text-gray-500 whitespace-nowrap">
                      {formatTimestamp(q.created_at)}
                    </td>
                    <td className="px-2 py-1.5 text-gray-800 dark:text-gray-100 max-w-md truncate">
                      {q.natural_language_query}
                    </td>
                    <td className="px-2 py-1.5">
                      {q.error_message ? (
                        <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400">
                          <AlertCircle className="w-3 h-3" /> Error
                        </span>
                      ) : q.executed ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="w-3 h-3" /> Ok
                        </span>
                      ) : (
                        <span className="text-gray-400">Pending</span>
                      )}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono">
                      {q.result_count ?? '—'}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono">
                      {formatDuration(q.execution_time_ms)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-gray-500">
                      {q.model_used ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Recent audit */}
      <section className="p-4 rounded-xl glass-panel border border-gray-200 dark:border-gray-800">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-700 dark:text-gray-200 mb-3 flex items-center gap-2">
          <ScrollText className="w-3.5 h-3.5 text-purple-500" />
          Recent audit activity
        </h3>
        {recentAuditError ? (
          <ErrorRow message={recentAuditError} />
        ) : recentAudit.length === 0 ? (
          <p className="text-xs text-gray-500">
            No audit entries recorded yet.
          </p>
        ) : (
          <ul className="text-xs space-y-1">
            {recentAudit.map((a) => (
              <li key={a.id} className="flex items-center gap-2 text-gray-700 dark:text-gray-200">
                <span className="font-mono text-gray-400 whitespace-nowrap">
                  {formatTimestamp(a.timestamp)}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-[10px] font-bold uppercase">
                  {a.action}
                </span>
                <span className="font-bold">{a.resource_type}</span>
                {a.resource_id && (
                  <span className="text-gray-400 font-mono">#{a.resource_id}</span>
                )}
                {a.username && <span className="text-gray-500">by {a.username}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function HealthCard({
  label,
  ok,
  detail,
  icon,
}: {
  label: string;
  ok: boolean;
  detail: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="p-4 rounded-xl glass-panel border border-gray-200 dark:border-gray-800 flex items-start gap-3">
      <div
        className={`p-2 rounded-lg ${ok ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">
          {label}
        </p>
        <p className={`text-sm font-bold ${ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
          {ok ? 'Healthy' : 'Degraded'}
        </p>
        <p className="text-[11px] text-gray-500 truncate" title={detail}>
          {detail}
        </p>
      </div>
    </div>
  );
}

function Gate({ label, on, extra }: { label: string; on: boolean; extra?: string }) {
  return (
    <div
      className={`flex items-start gap-2 p-3 rounded-lg border ${
        on
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-gray-200 dark:border-gray-700 bg-gray-50/40 dark:bg-gray-800/40'
      }`}
    >
      <span
        className={`mt-0.5 w-2 h-2 rounded-full ${on ? 'bg-emerald-500' : 'bg-gray-400'}`}
      />
      <div className="min-w-0">
        <p className="text-[11px] font-bold text-gray-800 dark:text-gray-100">{label}</p>
        <p className={`text-[10px] font-bold uppercase tracking-wider ${on ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500'}`}>
          {on ? 'Enabled' : 'Disabled'}
        </p>
        {extra && (
          <p className="text-[10px] font-mono text-gray-400 truncate" title={extra}>
            {extra}
          </p>
        )}
      </div>
    </div>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-md bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-xs">
      <AlertCircle className="w-3.5 h-3.5" />
      {message}
    </div>
  );
}
