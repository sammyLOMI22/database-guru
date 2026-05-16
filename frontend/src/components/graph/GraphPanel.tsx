/**
 * Graph Mode — top-level panel (Phase 25.2).
 *
 * Hosts the Neo4j-only experience:
 *   - Connection picker (defaults to first active neo4j connection)
 *   - Sub-tabs: Overview / Schema / Visual / Query Lab / Guru Advice
 *
 * Phase 25.2 ships Overview + Schema with real data. Visual / Query Lab /
 * Guru Advice are empty-state placeholders so the navigation lands now and
 * later sub-phases just fill in the panel content.
 */
import { useEffect, useMemo, useState } from 'react';
import { connectionsAPI } from '../../services/api';
import type { DatabaseConnection } from '../../types/api';
import GraphOverview from './GraphOverview';
import GraphSchemaExplorer from './GraphSchemaExplorer';

type SubTab = 'overview' | 'schema' | 'visual' | 'querylab' | 'advice';

const SUB_TABS: { id: SubTab; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'schema', label: 'Schema', icon: '🗂️' },
  { id: 'visual', label: 'Visual', icon: '🕸️' },
  { id: 'querylab', label: 'Query Lab', icon: '⚙️' },
  { id: 'advice', label: 'Guru Advice', icon: '💡' },
];

export default function GraphPanel() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [loadingConns, setLoadingConns] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('overview');

  useEffect(() => {
    let cancelled = false;
    setLoadingConns(true);
    connectionsAPI
      .listConnections()
      .then((data: any) => {
        if (cancelled) return;
        const all = (data?.connections ?? []) as DatabaseConnection[];
        const graph = all.filter((c) => c.database_type === 'neo4j');
        setConnections(graph);
        const firstActive = graph.find((c) => c.is_active) || graph[0];
        if (firstActive) setSelectedId(firstActive.id);
      })
      .catch((err) => console.error('[GraphPanel] connection load failed', err))
      .finally(() => {
        if (!cancelled) setLoadingConns(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedConn = useMemo(
    () => connections.find((c) => c.id === selectedId) || null,
    [connections, selectedId],
  );

  if (loadingConns) {
    return (
      <div className="flex-1 p-8 text-sm text-gray-500 dark:text-gray-400">
        Loading graph connections…
      </div>
    );
  }

  if (connections.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="max-w-md text-center glass-panel rounded-2xl p-8">
          <div className="text-4xl mb-4">🕸️</div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            No Neo4j connections yet
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            Add a Neo4j connection from the Workspace sidebar to start
            exploring graph schemas, running Cypher queries, and getting
            modeling advice.
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-4">
            Tip: pick <strong>Neo4j</strong> from the database-type dropdown
            in the Add Connection modal, then point it at{' '}
            <code className="px-1 rounded bg-black/5 dark:bg-white/5">
              bolt://localhost:7687
            </code>{' '}
            or a Neo4j Aura URI.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full min-h-0">
      {/* Top bar: connection picker + sub-tabs */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/10 bg-white/5 dark:bg-black/20">
        <div className="flex items-center gap-3">
          <label
            htmlFor="graph-conn"
            className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400"
          >
            Connection
          </label>
          <select
            id="graph-conn"
            value={selectedId ?? ''}
            onChange={(e) => setSelectedId(Number(e.target.value))}
            className="text-sm px-3 py-1.5 rounded-lg glass-panel border border-white/10 bg-white/40 dark:bg-black/40 text-gray-900 dark:text-white"
          >
            {connections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.database_name || 'neo4j'})
              </option>
            ))}
          </select>
        </div>

        <nav className="flex p-1 bg-black/5 dark:bg-white/5 rounded-2xl border border-white/10">
          {SUB_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveSubTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-xl text-[11px] font-bold uppercase tracking-wide transition-all duration-300 ${
                activeSubTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-white/10'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Sub-tab content */}
      <div className="flex-1 overflow-auto p-6 pb-24">
        {activeSubTab === 'overview' && (
          <GraphOverview
            connectionId={selectedConn?.id ?? null}
            connectionName={selectedConn?.name}
          />
        )}
        {activeSubTab === 'schema' && (
          <GraphSchemaExplorer connectionId={selectedConn?.id ?? null} />
        )}
        {activeSubTab === 'visual' && (
          <PlaceholderPanel
            title="Visual Explorer"
            body="Visual graph traversal ships in Phase 25.5 — Cytoscape canvas with start label, depth, and direction controls."
          />
        )}
        {activeSubTab === 'querylab' && (
          <PlaceholderPanel
            title="Cypher Query Lab"
            body="Hand-written Cypher + AI-generated queries with safety classification ship in Phase 25.3 / 25.4."
          />
        )}
        {activeSubTab === 'advice' && (
          <PlaceholderPanel
            title="Guru Advice"
            body="Rule-based + AI modeling advice (missing indexes, overloaded labels, event-as-relationship, etc.) ships in Phase 25.6."
          />
        )}
      </div>
    </div>
  );
}

function PlaceholderPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="max-w-xl mx-auto mt-12 glass-panel rounded-2xl p-8 text-center">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">
        {title}
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">{body}</p>
    </div>
  );
}
