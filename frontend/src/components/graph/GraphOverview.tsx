/**
 * GraphOverview — Phase 25.2 Overview sub-tab.
 *
 * Cards:
 *   1. Provider / server-version / edition / database name / last refreshed
 *   2. Counts: labels, relationship types, patterns, indexes, constraints
 *   3. Top relationship patterns (up to 5)
 *   4. AI-generated 2-3 sentence summary blurb (lazy — fetched on demand)
 *   5. Warnings (only if non-empty)
 *
 * The Refresh button forces a fresh introspection via POST /introspect.
 */
import { useMemo, useState } from 'react';
import {
  useGraphSchema,
  useGraphSchemaSummary,
  useIntrospectGraph,
} from '../../hooks/useGraphSchema';

interface Props {
  connectionId: number | null;
  connectionName?: string;
}

export default function GraphOverview({ connectionId, connectionName }: Props) {
  const schemaQuery = useGraphSchema(connectionId);
  const introspect = useIntrospectGraph(connectionId);
  const summarize = useGraphSchemaSummary(connectionId);

  const schema = schemaQuery.data;
  const [showRawWarnings, setShowRawWarnings] = useState(false);

  const topPatterns = useMemo(() => {
    if (!schema) return [];
    return [...schema.patterns]
      .sort(
        (a, b) =>
          (b.estimated_count ?? 0) - (a.estimated_count ?? 0),
      )
      .slice(0, 5);
  }, [schema]);

  if (connectionId === null) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Select a Neo4j connection to load its schema.
      </div>
    );
  }

  if (schemaQuery.isLoading) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Loading graph schema…
      </div>
    );
  }

  if (schemaQuery.isError) {
    return (
      <div className="glass-panel rounded-2xl p-6 max-w-2xl">
        <h3 className="text-base font-bold text-red-600 dark:text-red-400 mb-2">
          Failed to load schema
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          {(schemaQuery.error as any)?.response?.data?.detail ||
            (schemaQuery.error as Error)?.message ||
            'Unknown error'}
        </p>
        <button
          type="button"
          onClick={() => schemaQuery.refetch()}
          className="px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!schema) return null;

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header card */}
      <section className="glass-panel rounded-2xl p-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-blue-600/80 dark:text-blue-400/80 mb-1">
            Graph Connection
          </p>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {connectionName || schema.database_name}
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Provider: <span className="font-semibold">{schema.provider}</span>
            {schema.server_version
              ? ` · Server ${schema.server_version}`
              : ''}
            {schema.edition ? ` · ${schema.edition}` : ''}
            {schema.database_name
              ? ` · Database "${schema.database_name}"`
              : ''}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
            {schema.cached ? 'Cached' : 'Freshly introspected'}
            {schema.schema_updated_at
              ? ` · Last updated ${new Date(
                  schema.schema_updated_at,
                ).toLocaleString()}`
              : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={() => introspect.mutate()}
          disabled={introspect.isPending}
          className="px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {introspect.isPending ? 'Refreshing…' : 'Refresh schema'}
        </button>
      </section>

      {/* Counts */}
      <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Node labels" value={schema.label_count} />
        <StatCard label="Rel types" value={schema.relationship_type_count} />
        <StatCard label="Patterns" value={schema.pattern_count} />
        <StatCard label="Indexes" value={schema.index_count} />
        <StatCard label="Constraints" value={schema.constraint_count} />
      </section>

      {/* AI summary */}
      <section className="glass-panel rounded-2xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
            AI summary
          </h3>
          <button
            type="button"
            onClick={() => summarize.mutate()}
            disabled={summarize.isPending}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {summarize.isPending
              ? 'Generating…'
              : summarize.data
              ? 'Regenerate'
              : 'Generate summary'}
          </button>
        </div>
        {summarize.isError && (
          <p className="text-xs text-red-500">
            {(summarize.error as any)?.response?.data?.detail ||
              'Failed to generate summary.'}
          </p>
        )}
        {summarize.data ? (
          <>
            <p className="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
              {summarize.data.summary}
            </p>
            <p className="text-[10px] text-gray-500 dark:text-gray-500 mt-2">
              {summarize.data.used_fallback
                ? 'Deterministic fallback summary (LLM unavailable).'
                : `Generated by ${summarize.data.provider ?? 'LLM'}${
                    summarize.data.model ? ` · ${summarize.data.model}` : ''
                  }`}
            </p>
          </>
        ) : (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Click <strong>Generate summary</strong> for a 2-3 sentence LLM
            overview of this graph's domain, scale, and one actionable
            observation.
          </p>
        )}
      </section>

      {/* Top patterns */}
      <section className="glass-panel rounded-2xl p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-4">
          Top relationship patterns
        </h3>
        {topPatterns.length === 0 ? (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            No relationship patterns sampled yet. Refresh to re-sample.
          </p>
        ) : (
          <ul className="space-y-2">
            {topPatterns.map((p, i) => (
              <li
                key={`${p.relationship_type}-${i}`}
                className="flex items-center justify-between text-sm font-mono text-gray-800 dark:text-gray-100"
              >
                <span>
                  (:
                  <span className="text-blue-600 dark:text-blue-400">
                    {p.source_labels.join(',') || '?'}
                  </span>
                  )-[:
                  <span className="text-purple-600 dark:text-purple-400">
                    {p.relationship_type}
                  </span>
                  ]-&gt;(:
                  <span className="text-blue-600 dark:text-blue-400">
                    {p.target_labels.join(',') || '?'}
                  </span>
                  )
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
                  {p.estimated_count?.toLocaleString() ?? '—'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Warnings */}
      {schema.warnings.length > 0 && (
        <section className="glass-panel rounded-2xl p-6 border border-amber-500/30 bg-amber-50/30 dark:bg-amber-900/10">
          <button
            type="button"
            onClick={() => setShowRawWarnings((s) => !s)}
            className="flex items-center justify-between w-full text-left"
          >
            <h3 className="text-sm font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Introspection warnings ({schema.warnings.length})
            </h3>
            <span className="text-xs text-amber-700 dark:text-amber-400">
              {showRawWarnings ? 'Hide' : 'Show'}
            </span>
          </button>
          {showRawWarnings && (
            <ul className="mt-3 space-y-1 text-xs text-amber-900 dark:text-amber-200 list-disc list-inside">
              {schema.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass-panel rounded-2xl p-4 text-center">
      <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className="text-2xl font-black text-gray-900 dark:text-white tabular-nums mt-1">
        {value.toLocaleString()}
      </p>
    </div>
  );
}
