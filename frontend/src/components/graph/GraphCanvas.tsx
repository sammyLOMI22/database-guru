/**
 * GraphCanvas — Phase 25.5
 *
 * Renders a `graph_viz` payload (the Cytoscape-shaped contract the
 * backend's result_formatter produces) using React Flow. We pick
 * React Flow over Cytoscape because it's already a dependency for
 * the lineage + ER diagrams; using it here keeps the bundle lean.
 *
 * Responsibilities:
 *   - Layout `graph_viz.nodes` + `graph_viz.edges` with dagre.
 *   - Surface node selection up to the parent (`onSelectNode`).
 *   - Show a truncation banner when caps were hit.
 *
 * Non-responsibilities (live in `GraphVisualExplorer`):
 *   - Expand controls (depth, direction, rel-type chips).
 *   - Property side panel.
 *   - API calls — this is a pure renderer for an already-fetched payload.
 */

import { useEffect, useMemo } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Node,
  Edge,
  NodeMouseHandler,
  useEdgesState,
  useNodesState,
  Position,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';

import type { GraphVizPayload, GraphVizNode } from '../../services/graphApi';

export interface GraphCanvasProps {
  /** Backend `graph_viz` payload (nodes + edges + has_graph). */
  payload: GraphVizPayload | null;
  /** True when the backend hit `node_cap` or formatter caps. */
  truncated?: boolean;
  /** Warnings the backend wants to surface (will render as a banner). */
  warnings?: string[];
  /** Currently selected node id (for highlight). */
  selectedNodeId?: string | null;
  /** Fired when the user clicks a node. */
  onSelectNode?: (node: GraphVizNode | null) => void;
  /** Optional fixed height — defaults to filling the parent. */
  height?: number | string;
}

const NODE_W = 180;
const NODE_H = 56;

/** Lay out nodes with dagre — same approach used by ERDiagram + LineageGraph. */
function layoutNodes(
  nodes: Node[],
  edges: Edge[],
  direction: 'LR' | 'TB' = 'LR',
): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 60, ranksep: 90 });

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));

  dagre.layout(g);

  return nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      // Dagre returns centre points; React Flow wants top-left.
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });
}

// Stable label-colour assignment so each label gets a consistent accent
// across renders. Sorted alphabetically so the palette is deterministic.
const LABEL_COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
];

function colorForLabel(label: string): string {
  // Cheap deterministic hash — fine for at most a few dozen labels.
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = (hash * 31 + label.charCodeAt(i)) | 0;
  }
  return LABEL_COLORS[Math.abs(hash) % LABEL_COLORS.length];
}

function GraphCanvasInner({
  payload,
  truncated,
  warnings,
  selectedNodeId,
  onSelectNode,
  height,
}: GraphCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Memoize the transform so we don't redo layout on every render.
  const laidOut = useMemo(() => {
    if (!payload || !payload.has_graph || payload.nodes.length === 0) {
      return { nodes: [] as Node[], edges: [] as Edge[] };
    }

    const rawNodes: Node[] = payload.nodes.map((n) => {
      const primary = n.labels[0] || 'Node';
      const color = colorForLabel(primary);
      return {
        id: n.id,
        type: 'default',
        data: {
          label: (
            <div className="text-center px-2">
              <div className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                {n.labels.join(' / ') || 'Node'}
              </div>
              <div className="text-xs font-medium truncate" title={n.displayName}>
                {n.displayName}
              </div>
            </div>
          ) as unknown as string,
          // Carry the raw node through so the click handler can recover it.
          _graphNode: n,
        },
        position: { x: 0, y: 0 },
        style: {
          borderRadius: 12,
          background: `${color}15`,
          border: `2px solid ${color}`,
          color: 'inherit',
          width: NODE_W,
          fontSize: 12,
          padding: 6,
        },
      };
    });

    const rawEdges: Edge[] = payload.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.type,
      labelStyle: { fontSize: 10, fontWeight: 600 },
      labelBgStyle: { fill: 'rgba(0,0,0,0.6)' },
      labelBgPadding: [4, 2],
      labelBgBorderRadius: 4,
      labelShowBg: true,
      type: 'smoothstep',
      animated: false,
      style: { stroke: '#94a3b8', strokeWidth: 1.5 },
    }));

    return { nodes: layoutNodes(rawNodes, rawEdges), edges: rawEdges };
  }, [payload]);

  useEffect(() => {
    setNodes(laidOut.nodes);
    setEdges(laidOut.edges);
  }, [laidOut, setNodes, setEdges]);

  // Apply selection highlight as a style overlay so we don't have to
  // re-run dagre when the selection changes.
  useEffect(() => {
    setNodes((curr) =>
      curr.map((n) => ({
        ...n,
        style: {
          ...n.style,
          boxShadow:
            selectedNodeId && n.id === selectedNodeId
              ? '0 0 0 3px rgba(59,130,246,0.6)'
              : undefined,
        },
      })),
    );
  }, [selectedNodeId, setNodes]);

  const handleNodeClick: NodeMouseHandler = (_e, node) => {
    const raw = (node.data as { _graphNode?: GraphVizNode })?._graphNode;
    if (raw && onSelectNode) onSelectNode(raw);
  };

  const handlePaneClick = () => {
    if (onSelectNode) onSelectNode(null);
  };

  const isEmpty = !payload || !payload.has_graph || payload.nodes.length === 0;

  return (
    <div
      className="relative w-full"
      style={{ height: height ?? '100%', minHeight: 360 }}
      data-testid="graph-canvas"
    >
      {/* Truncation / warning banner */}
      {(truncated || (warnings && warnings.length > 0)) && (
        <div
          role="status"
          data-testid="graph-canvas-warnings"
          className="absolute z-10 top-2 left-2 right-2 px-3 py-2 rounded-lg text-[11px] font-medium bg-amber-100/95 dark:bg-amber-900/60 text-amber-900 dark:text-amber-100 border border-amber-300/60 shadow-sm pointer-events-none"
        >
          {truncated && <div>Result truncated to fit visualization caps.</div>}
          {(warnings || []).map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </div>
      )}

      {isEmpty ? (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
          No graph data to display.
        </div>
      ) : (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onPaneClick={handlePaneClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable />
        </ReactFlow>
      )}
    </div>
  );
}

/**
 * GraphCanvas — public wrapper that mounts the React Flow provider.
 *
 * React Flow requires `ReactFlowProvider` higher in the tree than any
 * `useReactFlow` hook. We wrap here so callers don't have to think about
 * it — they can drop a `<GraphCanvas payload={...} />` anywhere.
 */
export default function GraphCanvas(props: GraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
