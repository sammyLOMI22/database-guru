/**
 * GraphSchemaExplorer — Phase 25.2 Schema sub-tab.
 *
 * Five inner views:
 *   - Labels       (with property table for each)
 *   - Rel Types    (with property table for each)
 *   - Patterns     (sampled source → rel → target)
 *   - Indexes
 *   - Constraints
 *
 * Each view has a search filter; selecting a label/rel surfaces its
 * property grid in a side panel.
 */
import { useMemo, useState } from 'react';
import { useGraphSchema } from '../../hooks/useGraphSchema';
import type {
  GraphConstraint,
  GraphIndex,
  GraphNodeLabel,
  GraphProperty,
  GraphRelationshipPattern,
  GraphRelationshipType,
} from '../../services/graphApi';

type View = 'labels' | 'relationships' | 'patterns' | 'indexes' | 'constraints';

const VIEWS: { id: View; label: string }[] = [
  { id: 'labels', label: 'Labels' },
  { id: 'relationships', label: 'Rel Types' },
  { id: 'patterns', label: 'Patterns' },
  { id: 'indexes', label: 'Indexes' },
  { id: 'constraints', label: 'Constraints' },
];

interface Props {
  connectionId: number | null;
}

export default function GraphSchemaExplorer({ connectionId }: Props) {
  const schemaQuery = useGraphSchema(connectionId);
  const [view, setView] = useState<View>('labels');
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  const schema = schemaQuery.data;

  const filtered = useMemo(() => {
    if (!schema) {
      return {
        labels: [] as GraphNodeLabel[],
        relationships: [] as GraphRelationshipType[],
        patterns: [] as GraphRelationshipPattern[],
        indexes: [] as GraphIndex[],
        constraints: [] as GraphConstraint[],
      };
    }
    const f = filter.trim().toLowerCase();
    const matchStr = (s: string) => !f || s.toLowerCase().includes(f);
    return {
      labels: schema.labels.filter((l) => matchStr(l.name)),
      relationships: schema.relationships.filter((r) => matchStr(r.name)),
      patterns: schema.patterns.filter(
        (p) =>
          matchStr(p.relationship_type) ||
          p.source_labels.some(matchStr) ||
          p.target_labels.some(matchStr),
      ),
      indexes: schema.indexes.filter(
        (i) =>
          matchStr(i.name) ||
          i.labels_or_types.some(matchStr) ||
          i.properties.some(matchStr),
      ),
      constraints: schema.constraints.filter(
        (c) =>
          matchStr(c.name) ||
          c.labels_or_types.some(matchStr) ||
          c.properties.some(matchStr),
      ),
    };
  }, [schema, filter]);

  if (connectionId === null) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Select a Neo4j connection to inspect its schema.
      </div>
    );
  }

  if (schemaQuery.isLoading) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Loading schema…
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400">
        No schema available — try the Overview tab and click "Refresh schema".
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-4">
      {/* View tabs + filter */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav
          className="flex flex-wrap gap-2"
          aria-label="Schema view selector"
        >
          {VIEWS.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => {
                setView(v.id);
                setSelected(null);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-colors ${
                view === v.id
                  ? 'bg-blue-600 text-white'
                  : 'glass-panel text-gray-600 dark:text-gray-300 hover:bg-white/20'
              }`}
            >
              {v.label}
            </button>
          ))}
        </nav>
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter…"
          aria-label="Filter schema entries"
          className="px-3 py-1.5 rounded-lg glass-panel text-sm w-64 bg-white/40 dark:bg-black/40 border border-white/10 text-gray-900 dark:text-white placeholder:text-gray-400"
        />
      </div>

      {view === 'labels' && (
        <LabelsView
          labels={filtered.labels}
          selected={selected}
          onSelect={setSelected}
        />
      )}
      {view === 'relationships' && (
        <RelTypesView
          relationships={filtered.relationships}
          selected={selected}
          onSelect={setSelected}
        />
      )}
      {view === 'patterns' && (
        <PatternsView patterns={filtered.patterns} />
      )}
      {view === 'indexes' && <IndexesView indexes={filtered.indexes} />}
      {view === 'constraints' && (
        <ConstraintsView constraints={filtered.constraints} />
      )}
    </div>
  );
}

// ── Sub-views ────────────────────────────────────────────────────────────

function LabelsView({
  labels,
  selected,
  onSelect,
}: {
  labels: GraphNodeLabel[];
  selected: string | null;
  onSelect: (name: string | null) => void;
}) {
  const selectedLabel = labels.find((l) => l.name === selected) ?? labels[0] ?? null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4">
      <ListPanel
        items={labels.map((l) => ({
          key: l.name,
          primary: l.name,
          secondary: l.estimated_count?.toLocaleString() ?? '—',
        }))}
        selectedKey={selectedLabel?.name ?? null}
        onSelect={onSelect}
        emptyLabel="No labels match the current filter."
      />
      <DetailPanel
        title={selectedLabel?.name ?? '—'}
        subtitle={
          selectedLabel?.estimated_count !== undefined &&
          selectedLabel?.estimated_count !== null
            ? `${selectedLabel.estimated_count.toLocaleString()} nodes`
            : null
        }
      >
        {selectedLabel ? (
          <PropertyTable properties={selectedLabel.properties} />
        ) : (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Select a label to see its properties.
          </p>
        )}
      </DetailPanel>
    </div>
  );
}

function RelTypesView({
  relationships,
  selected,
  onSelect,
}: {
  relationships: GraphRelationshipType[];
  selected: string | null;
  onSelect: (name: string | null) => void;
}) {
  const selectedRel =
    relationships.find((r) => r.name === selected) ?? relationships[0] ?? null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4">
      <ListPanel
        items={relationships.map((r) => ({
          key: r.name,
          primary: r.name,
          secondary: r.estimated_count?.toLocaleString() ?? '—',
        }))}
        selectedKey={selectedRel?.name ?? null}
        onSelect={onSelect}
        emptyLabel="No relationship types match the current filter."
      />
      <DetailPanel title={selectedRel?.name ?? '—'}>
        {selectedRel ? (
          <PropertyTable properties={selectedRel.properties} />
        ) : (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Select a relationship type to see its properties.
          </p>
        )}
      </DetailPanel>
    </div>
  );
}

function PatternsView({ patterns }: { patterns: GraphRelationshipPattern[] }) {
  if (patterns.length === 0) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        No patterns match the current filter.
      </p>
    );
  }
  return (
    <div className="glass-panel rounded-2xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-black/5 dark:bg-white/5">
          <tr>
            <Th>Source labels</Th>
            <Th>Relationship</Th>
            <Th>Target labels</Th>
            <Th>Sampled count</Th>
          </tr>
        </thead>
        <tbody>
          {patterns.map((p, i) => (
            <tr
              key={`${p.relationship_type}-${i}`}
              className="border-t border-white/10"
            >
              <Td mono>{p.source_labels.join(', ') || '—'}</Td>
              <Td mono>{p.relationship_type}</Td>
              <Td mono>{p.target_labels.join(', ') || '—'}</Td>
              <Td className="tabular-nums">
                {p.estimated_count?.toLocaleString() ?? '—'}
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IndexesView({ indexes }: { indexes: GraphIndex[] }) {
  if (indexes.length === 0) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        No indexes match the current filter.
      </p>
    );
  }
  return (
    <div className="glass-panel rounded-2xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-black/5 dark:bg-white/5">
          <tr>
            <Th>Name</Th>
            <Th>Entity</Th>
            <Th>Labels / types</Th>
            <Th>Properties</Th>
            <Th>Type</Th>
            <Th>State</Th>
          </tr>
        </thead>
        <tbody>
          {indexes.map((idx) => (
            <tr key={idx.name} className="border-t border-white/10">
              <Td mono>{idx.name}</Td>
              <Td>{idx.entity_type}</Td>
              <Td mono>{idx.labels_or_types.join(', ') || '—'}</Td>
              <Td mono>{idx.properties.join(', ') || '—'}</Td>
              <Td>{idx.type ?? '—'}</Td>
              <Td>{idx.state ?? '—'}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConstraintsView({ constraints }: { constraints: GraphConstraint[] }) {
  if (constraints.length === 0) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        No constraints match the current filter.
      </p>
    );
  }
  return (
    <div className="glass-panel rounded-2xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-black/5 dark:bg-white/5">
          <tr>
            <Th>Name</Th>
            <Th>Entity</Th>
            <Th>Labels / types</Th>
            <Th>Properties</Th>
            <Th>Type</Th>
          </tr>
        </thead>
        <tbody>
          {constraints.map((c) => (
            <tr key={c.name} className="border-t border-white/10">
              <Td mono>{c.name}</Td>
              <Td>{c.entity_type}</Td>
              <Td mono>{c.labels_or_types.join(', ') || '—'}</Td>
              <Td mono>{c.properties.join(', ') || '—'}</Td>
              <Td>{c.type}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Shared bits ──────────────────────────────────────────────────────────

interface ListItem {
  key: string;
  primary: string;
  secondary?: string;
}

function ListPanel({
  items,
  selectedKey,
  onSelect,
  emptyLabel,
}: {
  items: ListItem[];
  selectedKey: string | null;
  onSelect: (key: string | null) => void;
  emptyLabel: string;
}) {
  if (items.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-4">
        <p className="text-xs text-gray-500 dark:text-gray-400">{emptyLabel}</p>
      </div>
    );
  }
  return (
    <ul className="glass-panel rounded-2xl divide-y divide-white/10 overflow-hidden max-h-[600px] overflow-y-auto">
      {items.map((it) => (
        <li key={it.key}>
          <button
            type="button"
            onClick={() => onSelect(it.key)}
            className={`w-full flex items-center justify-between px-4 py-2 text-left text-sm transition-colors ${
              selectedKey === it.key
                ? 'bg-blue-600/10 text-blue-700 dark:text-blue-300'
                : 'hover:bg-white/10 text-gray-800 dark:text-gray-200'
            }`}
          >
            <span className="font-mono truncate">{it.primary}</span>
            {it.secondary && (
              <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
                {it.secondary}
              </span>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}

function DetailPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string | null;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-panel rounded-2xl p-4">
      <h3 className="text-base font-bold text-gray-900 dark:text-white font-mono">
        {title}
      </h3>
      {subtitle && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {subtitle}
        </p>
      )}
      <div className="mt-3">{children}</div>
    </div>
  );
}

function PropertyTable({ properties }: { properties: GraphProperty[] }) {
  if (properties.length === 0) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        No properties observed via schema introspection.
      </p>
    );
  }
  return (
    <table className="w-full text-xs">
      <thead className="text-gray-500 dark:text-gray-400">
        <tr>
          <Th>Property</Th>
          <Th>Types</Th>
          <Th>Nullable</Th>
          <Th>Indexed</Th>
        </tr>
      </thead>
      <tbody>
        {properties.map((p) => (
          <tr key={p.name} className="border-t border-white/10">
            <Td mono>{p.name}</Td>
            <Td mono>{p.types.join(', ') || '—'}</Td>
            <Td>{p.nullable === null ? '—' : p.nullable ? 'yes' : 'no'}</Td>
            <Td>{p.indexed ? '✅' : '—'}</Td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
      {children}
    </th>
  );
}

function Td({
  children,
  mono,
  className = '',
}: {
  children: React.ReactNode;
  mono?: boolean;
  className?: string;
}) {
  return (
    <td
      className={`px-3 py-2 text-gray-800 dark:text-gray-100 ${
        mono ? 'font-mono' : ''
      } ${className}`}
    >
      {children}
    </td>
  );
}
