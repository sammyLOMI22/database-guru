/**
 * GraphVisualExplorer — Phase 25.5
 *
 * The Graph mode "Visual" sub-tab. Lets the user:
 *   1. Pick a starting label (sourced from cached schema introspection).
 *   2. Pick a property + value to anchor the starting node.
 *   3. Tweak depth (1-3), direction, and rel-type filter.
 *   4. Hit Explore → fetches `POST /api/graph/connections/:id/explore`.
 *   5. Click a node in the canvas → side panel shows full properties +
 *      an "Expand from here" follow-up that fires the same endpoint with
 *      the clicked node's primary key as the new anchor.
 *
 * The rendering itself lives in `GraphCanvas`; this file is purely the
 * controls, state machine, and property panel.
 */

import { useEffect, useMemo, useState } from 'react';
import { graphAPI } from '../../services/graphApi';
import type {
  ExpandDirection,
  GraphExploreResponse,
  GraphSchemaResponse,
  GraphVizNode,
} from '../../services/graphApi';
import GraphCanvas from './GraphCanvas';

interface GraphVisualExplorerProps {
  connectionId: number | null;
}

interface ErrorBanner {
  message: string;
  hint?: string | null;
}

const DEFAULT_DEPTH = 1;
const DEFAULT_DIRECTION: ExpandDirection = 'any';
const DEFAULT_NODE_CAP = 100;

/**
 * Pick the most useful "lookup" property for a label.
 *
 * The expand endpoint needs one indexed-ish property to anchor on. We
 * prefer `id` / `email` / `slug` / `sku` / `externalId` (the same list
 * the Phase 25.6 advisor rule uses) and fall back to the first property
 * the schema lists.
 */
function pickAnchorProperty(props: { name: string }[]): string {
  const preferred = ['id', 'uuid', 'email', 'slug', 'sku', 'externalId', 'externalid'];
  const lowerMap = new Map(props.map((p) => [p.name.toLowerCase(), p.name]));
  for (const pref of preferred) {
    const match = lowerMap.get(pref);
    if (match) return match;
  }
  return props[0]?.name ?? '';
}

export default function GraphVisualExplorer({ connectionId }: GraphVisualExplorerProps) {
  const [schema, setSchema] = useState<GraphSchemaResponse | null>(null);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [loadingSchema, setLoadingSchema] = useState(false);

  // Expand form state
  const [startLabel, setStartLabel] = useState<string>('');
  const [startProperty, setStartProperty] = useState<string>('');
  const [startValue, setStartValue] = useState<string>('');
  const [depth, setDepth] = useState<number>(DEFAULT_DEPTH);
  const [direction, setDirection] = useState<ExpandDirection>(DEFAULT_DIRECTION);
  const [nodeCap, setNodeCap] = useState<number>(DEFAULT_NODE_CAP);
  const [selectedRelTypes, setSelectedRelTypes] = useState<Set<string>>(new Set());

  // Result state
  const [result, setResult] = useState<GraphExploreResponse | null>(null);
  const [exploring, setExploring] = useState(false);
  const [error, setError] = useState<ErrorBanner | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphVizNode | null>(null);

  // Fetch cached schema when the connection changes — we need labels +
  // properties for the form dropdowns. Force-refresh is the user's job
  // via the Schema tab.
  useEffect(() => {
    if (connectionId == null) {
      setSchema(null);
      return;
    }
    setLoadingSchema(true);
    setSchemaError(null);
    graphAPI
      .getSchema(connectionId)
      .then((s) => setSchema(s))
      .catch((err) => {
        const detail =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to load schema.';
        setSchemaError(typeof detail === 'string' ? detail : 'Failed to load schema.');
      })
      .finally(() => setLoadingSchema(false));
  }, [connectionId]);

  // When the schema (re)loads, auto-pick a sensible default label so the
  // form is immediately runnable. The user can override.
  useEffect(() => {
    if (!schema || schema.labels.length === 0) return;
    if (!startLabel) {
      const first = schema.labels[0];
      setStartLabel(first.name);
      setStartProperty(pickAnchorProperty(first.properties));
    }
  }, [schema, startLabel]);

  // When the start label changes, reset the anchor property to the
  // best-guess for that label.
  useEffect(() => {
    if (!schema || !startLabel) return;
    const lbl = schema.labels.find((l) => l.name === startLabel);
    if (lbl) {
      setStartProperty(pickAnchorProperty(lbl.properties));
      setStartValue('');
    }
  }, [startLabel, schema]);

  const currentLabel = useMemo(
    () => schema?.labels.find((l) => l.name === startLabel) ?? null,
    [schema, startLabel],
  );

  // Relationship types visible to the user — pulled from cached schema
  // patterns so we don't offer types that don't exist for the chosen label.
  const availableRelTypes = useMemo(() => {
    if (!schema || !startLabel) return [];
    const types = new Set<string>();
    for (const p of schema.patterns) {
      if (p.source_labels.includes(startLabel) || p.target_labels.includes(startLabel)) {
        types.add(p.relationship_type);
      }
    }
    return Array.from(types).sort();
  }, [schema, startLabel]);

  const toggleRelType = (t: string) => {
    setSelectedRelTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const handleExplore = async (overrides?: {
    startLabel?: string;
    startProperty?: string;
    startValue?: string;
  }) => {
    if (connectionId == null) return;
    const lbl = overrides?.startLabel ?? startLabel;
    const prop = overrides?.startProperty ?? startProperty;
    const val = overrides?.startValue ?? startValue;
    if (!lbl || !prop || val === '') {
      setError({ message: 'Pick a label, property, and value to start.' });
      return;
    }

    setExploring(true);
    setError(null);
    setSelectedNode(null);

    try {
      const res = await graphAPI.explore(connectionId, {
        start_label: lbl,
        start_property: prop,
        start_value: val,
        depth,
        rel_types: selectedRelTypes.size > 0 ? Array.from(selectedRelTypes) : undefined,
        direction,
        node_cap: nodeCap,
      });
      setResult(res);
      if (!res.graph_viz.has_graph) {
        setError({
          message: 'No graph data returned — the starting node may not match.',
          hint: 'Double-check the property name and value, then try again.',
        });
      }
    } catch (err: any) {
      const data = err?.response?.data?.detail || err?.response?.data;
      if (data && typeof data === 'object') {
        setError({
          message:
            data.error_message ||
            data.blocked_reason ||
            data.message ||
            'Expand failed.',
          hint: data.error_hint ?? data.reasons?.[0] ?? null,
        });
      } else {
        setError({ message: err?.message || 'Expand failed.' });
      }
      setResult(null);
    } finally {
      setExploring(false);
    }
  };

  const handleExpandFromSelected = () => {
    if (!selectedNode || !schema) return;
    const lbl = selectedNode.labels[0];
    if (!lbl) return;
    // Use the same anchor property the schema would pick.
    const lblDef = schema.labels.find((l) => l.name === lbl);
    if (!lblDef) return;
    const prop = pickAnchorProperty(lblDef.properties);
    const val = selectedNode.properties[prop];
    if (val == null) {
      setError({
        message: `Selected node has no ${prop} value to expand from.`,
        hint: 'Pick a different starting label / property.',
      });
      return;
    }
    setStartLabel(lbl);
    setStartProperty(prop);
    setStartValue(String(val));
    handleExplore({ startLabel: lbl, startProperty: prop, startValue: String(val) });
  };

  // ── Empty / loading states ──
  if (connectionId == null) {
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-8 text-center text-sm text-gray-500 dark:text-gray-400">
        Select a Neo4j connection above to start exploring.
      </div>
    );
  }

  if (loadingSchema) {
    return (
      <div className="max-w-xl mx-auto mt-12 text-sm text-gray-500 dark:text-gray-400">
        Loading schema…
      </div>
    );
  }

  if (schemaError) {
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-6 text-sm">
        <div className="font-bold text-red-600 dark:text-red-400 mb-1">
          Couldn't load schema
        </div>
        <div className="text-gray-600 dark:text-gray-400">{schemaError}</div>
        <div className="text-xs text-gray-500 mt-3">
          Open the <strong>Schema</strong> tab to introspect this database first.
        </div>
      </div>
    );
  }

  if (!schema || schema.labels.length === 0) {
    return (
      <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-6 text-sm text-gray-500 dark:text-gray-400">
        No labels found in the cached schema. Run an introspection from the
        Schema tab to populate the explorer.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 gap-4">
      {/* ── Controls row ── */}
      <div className="glass-panel rounded-xl p-4 flex flex-wrap items-end gap-3">
        {/* Start label */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
            Start label
          </label>
          <select
            data-testid="start-label"
            value={startLabel}
            onChange={(e) => setStartLabel(e.target.value)}
            className="text-sm px-3 py-1.5 rounded-lg border border-white/10 bg-white/40 dark:bg-black/40 text-gray-900 dark:text-white min-w-[140px]"
          >
            {schema.labels.map((l) => (
              <option key={l.name} value={l.name}>
                {l.name} ({l.estimated_count ?? '?'})
              </option>
            ))}
          </select>
        </div>

        {/* Start property */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
            Property
          </label>
          <select
            data-testid="start-property"
            value={startProperty}
            onChange={(e) => setStartProperty(e.target.value)}
            className="text-sm px-3 py-1.5 rounded-lg border border-white/10 bg-white/40 dark:bg-black/40 text-gray-900 dark:text-white min-w-[120px]"
          >
            {(currentLabel?.properties || []).map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Value */}
        <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
          <label className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
            Equals
          </label>
          <input
            data-testid="start-value"
            type="text"
            value={startValue}
            onChange={(e) => setStartValue(e.target.value)}
            placeholder="e.g. alice@example.com"
            className="text-sm px-3 py-1.5 rounded-lg border border-white/10 bg-white/40 dark:bg-black/40 text-gray-900 dark:text-white"
          />
        </div>

        {/* Depth */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
            Depth ({depth})
          </label>
          <input
            data-testid="depth-slider"
            type="range"
            min={1}
            max={3}
            step={1}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="w-24"
          />
        </div>

        {/* Direction */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
            Direction
          </label>
          <select
            data-testid="direction"
            value={direction}
            onChange={(e) => setDirection(e.target.value as ExpandDirection)}
            className="text-sm px-3 py-1.5 rounded-lg border border-white/10 bg-white/40 dark:bg-black/40 text-gray-900 dark:text-white"
          >
            <option value="any">Both ↔</option>
            <option value="out">Outgoing →</option>
            <option value="in">Incoming ←</option>
          </select>
        </div>

        {/* Node cap */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
            Node cap
          </label>
          <input
            data-testid="node-cap"
            type="number"
            min={1}
            max={1000}
            value={nodeCap}
            onChange={(e) => setNodeCap(Number(e.target.value))}
            className="text-sm px-3 py-1.5 rounded-lg border border-white/10 bg-white/40 dark:bg-black/40 text-gray-900 dark:text-white w-24"
          />
        </div>

        {/* Explore button */}
        <button
          data-testid="explore-btn"
          type="button"
          disabled={exploring}
          onClick={() => handleExplore()}
          className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold shadow"
        >
          {exploring ? 'Exploring…' : 'Explore'}
        </button>
      </div>

      {/* Rel-type chips */}
      {availableRelTypes.length > 0 && (
        <div className="glass-panel rounded-xl px-4 py-3 flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mr-2">
            Rel types ({selectedRelTypes.size || 'all'})
          </span>
          {availableRelTypes.map((t) => {
            const active = selectedRelTypes.has(t);
            return (
              <button
                key={t}
                type="button"
                data-testid={`rel-chip-${t}`}
                onClick={() => toggleRelType(t)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  active
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white/40 dark:bg-black/40 text-gray-700 dark:text-gray-300 border-white/10 hover:border-blue-400'
                }`}
              >
                {t}
              </button>
            );
          })}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          data-testid="explore-error"
          className="px-4 py-3 rounded-xl bg-red-100/80 dark:bg-red-900/40 text-red-900 dark:text-red-100 text-sm"
        >
          <div className="font-bold">{error.message}</div>
          {error.hint && <div className="text-xs opacity-80 mt-1">{error.hint}</div>}
        </div>
      )}

      {/* Result summary */}
      {result && (
        <div
          data-testid="explore-summary"
          className="text-xs text-gray-500 dark:text-gray-400 px-1"
        >
          {result.record_count} record(s) ·{' '}
          {result.graph_viz.nodes.length} node(s) ·{' '}
          {result.graph_viz.edges.length} edge(s) ·{' '}
          {result.execution_time_ms.toFixed(0)} ms
          {result.truncated && (
            <span className="ml-2 text-amber-600 dark:text-amber-400 font-medium">
              (truncated)
            </span>
          )}
        </div>
      )}

      {/* Canvas + property panel */}
      <div className="flex flex-1 min-h-[400px] gap-4">
        <div className="flex-1 glass-panel rounded-xl overflow-hidden">
          <GraphCanvas
            payload={result?.graph_viz ?? null}
            truncated={result?.truncated}
            warnings={result?.warnings}
            selectedNodeId={selectedNode?.id ?? null}
            onSelectNode={(n) => setSelectedNode(n)}
          />
        </div>

        {/* Property panel */}
        {selectedNode && (
          <aside
            data-testid="property-panel"
            className="w-72 glass-panel rounded-xl p-4 overflow-auto text-sm"
          >
            <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
              {selectedNode.labels.join(' / ') || 'Node'}
            </div>
            <div className="font-semibold text-gray-900 dark:text-white mb-3 break-words">
              {selectedNode.displayName}
            </div>

            <button
              type="button"
              data-testid="expand-from-selected"
              onClick={handleExpandFromSelected}
              className="w-full mb-3 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
            >
              Expand from here
            </button>

            <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
              Properties
            </div>
            <dl className="text-xs space-y-1.5">
              {Object.entries(selectedNode.properties).map(([k, v]) => (
                <div key={k} className="grid grid-cols-3 gap-1">
                  <dt className="col-span-1 truncate text-gray-500" title={k}>
                    {k}
                  </dt>
                  <dd
                    className="col-span-2 truncate text-gray-900 dark:text-gray-100"
                    title={String(v)}
                  >
                    {String(v)}
                  </dd>
                </div>
              ))}
              {Object.keys(selectedNode.properties).length === 0 && (
                <div className="text-gray-500">(no properties)</div>
              )}
            </dl>
          </aside>
        )}
      </div>
    </div>
  );
}
