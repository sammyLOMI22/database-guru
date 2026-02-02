/**
 * Lineage Layout Utilities - Phase 11
 *
 * Transforms LineageGraphResponse → React Flow nodes/edges with Dagre layout.
 * LR (left-to-right) direction for data flow: sources → transforms → outputs.
 */

import dagre from 'dagre';
import type { Node, Edge } from 'reactflow';
import type { LineageGraphResponse, LineageNodeType } from '../types/lineage';

// =============================================================================
// Constants
// =============================================================================

const NODE_WIDTH = 180;
const NODE_HEIGHT_TABLE = 50;
const NODE_HEIGHT_COLUMN = 40;
const NODE_HEIGHT_TRANSFORM = 44;
const NODE_HEIGHT_OUTPUT = 40;
const NODE_SPACING_X = 80;
const NODE_SPACING_Y = 40;

// Color coding per node type
export const NODE_COLORS: Record<LineageNodeType, { bg: string; border: string; text: string }> = {
  source_table: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },     // blue
  source_column: { bg: '#e0e7ff', border: '#6366f1', text: '#3730a3' },    // indigo
  transformation: { bg: '#f3e8ff', border: '#a855f7', text: '#6b21a8' },   // purple
  output_column: { bg: '#dcfce7', border: '#22c55e', text: '#166534' },    // green
};

export const NODE_COLORS_DARK: Record<LineageNodeType, { bg: string; border: string; text: string }> = {
  source_table: { bg: '#1e3a5f', border: '#60a5fa', text: '#bfdbfe' },
  source_column: { bg: '#2e1065', border: '#818cf8', text: '#c7d2fe' },
  transformation: { bg: '#3b0764', border: '#c084fc', text: '#e9d5ff' },
  output_column: { bg: '#14532d', border: '#4ade80', text: '#bbf7d0' },
};

// =============================================================================
// Layout
// =============================================================================

export interface LayoutResult {
  nodes: Node[];
  edges: Edge[];
}

/**
 * Transform a LineageGraphResponse into React Flow nodes and edges with Dagre layout.
 */
export function layoutLineageGraph(
  graphData: LineageGraphResponse,
  isDarkMode: boolean = false
): LayoutResult {
  if (!graphData.nodes.length) {
    return { nodes: [], edges: [] };
  }

  const colors = isDarkMode ? NODE_COLORS_DARK : NODE_COLORS;

  // Create React Flow nodes
  const rfNodes: Node[] = graphData.nodes.map((node) => {
    const nodeColors = colors[node.node_type] || colors.source_column;
    const height = getNodeHeight(node.node_type);

    return {
      id: node.id,
      type: 'lineageNode',
      position: { x: 0, y: 0 }, // Will be set by dagre
      data: {
        ...node,
        colors: nodeColors,
        isDarkMode,
      },
      style: {
        width: NODE_WIDTH,
        height,
      },
    };
  });

  // Create React Flow edges
  const rfEdges: Edge[] = graphData.edges.map((edge, index) => ({
    id: `edge-${index}`,
    source: edge.source_id,
    target: edge.target_id,
    type: 'lineageEdge',
    data: {
      label: edge.label,
      edgeType: edge.edge_type,
      isDarkMode,
    },
    animated: edge.edge_type === 'feeds' || edge.edge_type === 'direct',
  }));

  // Apply dagre layout
  const layoutedNodes = applyDagreLayout(rfNodes, rfEdges);

  return { nodes: layoutedNodes, edges: rfEdges };
}

function getNodeHeight(nodeType: LineageNodeType): number {
  switch (nodeType) {
    case 'source_table':
      return NODE_HEIGHT_TABLE;
    case 'source_column':
      return NODE_HEIGHT_COLUMN;
    case 'transformation':
      return NODE_HEIGHT_TRANSFORM;
    case 'output_column':
      return NODE_HEIGHT_OUTPUT;
    default:
      return NODE_HEIGHT_COLUMN;
  }
}

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();

  g.setGraph({
    rankdir: 'LR', // Left-to-right data flow
    nodesep: NODE_SPACING_Y,
    ranksep: NODE_SPACING_X,
    marginx: 40,
    marginy: 40,
  });

  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes
  nodes.forEach((node) => {
    g.setNode(node.id, {
      width: NODE_WIDTH,
      height: (node.style?.height as number) || NODE_HEIGHT_COLUMN,
    });
  });

  // Add edges
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  // Run layout
  dagre.layout(g);

  // Apply positions
  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - ((node.style?.height as number) || NODE_HEIGHT_COLUMN) / 2,
      },
    };
  });
}
