/**
 * ER Diagram Utilities - Phase 7
 *
 * Layout algorithms and data transformation for React Flow ER diagrams.
 */

import dagre from 'dagre';
// Node and Edge types imported for reference in JSDoc comments
import type { SchemaTableInfo, SchemaExploreResponse } from '../types/api';
import type {
  ERTableNode,
  ERRelationshipEdge,
  ERDiagramData,
  TableNodeData,
  RelationshipEdgeData,
  LayoutOptions,
  CardinalityType,
} from '../types/erDiagram';
import {
  DEFAULT_LAYOUT_OPTIONS,
  getDatabaseColor,
  NODE_BASE_WIDTH,
  COLUMN_ROW_HEIGHT,
  NODE_HEADER_HEIGHT,
  NODE_COLLAPSED_HEIGHT,
  MAX_VISIBLE_COLUMNS,
} from '../types/erDiagram';

// =============================================================================
// CONSTANTS
// =============================================================================

// Constants now imported from ../types/erDiagram.ts

// =============================================================================
// LAYOUT CALCULATION
// =============================================================================

/**
 * Calculate node dimensions based on table info.
 */
export function calculateNodeDimensions(
  table: SchemaTableInfo,
  isExpanded: boolean
): { width: number; height: number } {
  const width = NODE_BASE_WIDTH;

  if (!isExpanded) {
    return { width, height: NODE_COLLAPSED_HEIGHT };
  }

  const columnCount = Math.min(table.columns.length, MAX_VISIBLE_COLUMNS);
  const height = NODE_HEADER_HEIGHT + columnCount * COLUMN_ROW_HEIGHT + 16; // 16px padding

  return { width, height };
}

/**
 * Apply Dagre layout algorithm to nodes and edges.
 */
export function calculateDagreLayout(
  nodes: ERTableNode[],
  edges: ERRelationshipEdge[],
  options: LayoutOptions = DEFAULT_LAYOUT_OPTIONS
): ERTableNode[] {
  const g = new dagre.graphlib.Graph();

  g.setGraph({
    rankdir: options.direction,
    nodesep: options.nodeSpacingX,
    ranksep: options.nodeSpacingY,
    marginx: options.nodePadding,
    marginy: options.nodePadding,
  });

  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes to graph
  nodes.forEach((node) => {
    const dimensions = calculateNodeDimensions(
      {
        name: node.data.tableName,
        columns: node.data.columns,
        row_count: node.data.rowCount,
        primary_keys: node.data.primaryKeys,
        foreign_keys: node.data.foreignKeys,
        indexes: [],
      },
      node.data.isExpanded
    );
    g.setNode(node.id, { width: dimensions.width, height: dimensions.height });
  });

  // Add edges to graph
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  // Run layout
  dagre.layout(g);

  // Apply positions to nodes
  return nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWithPosition.width / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      },
    };
  });
}

// =============================================================================
// DATA TRANSFORMATION
// =============================================================================

/**
 * Transform schema data to React Flow nodes.
 */
export function transformSchemaToNodes(
  schema: SchemaExploreResponse,
  colorIndex: number = 0,
  isDarkMode: boolean = false
): ERTableNode[] {
  const color = getDatabaseColor(colorIndex);

  return schema.tables.map((table) => {
    const nodeId = `${schema.connection_id}-${table.name}`;

    const nodeData: TableNodeData = {
      tableName: table.name,
      columns: table.columns,
      primaryKeys: table.primary_keys,
      foreignKeys: table.foreign_keys,
      rowCount: table.row_count,
      connectionId: schema.connection_id,
      databaseType: schema.database_type,
      connectionName: schema.connection_name,
      isExpanded: false, // Start collapsed for performance
      isHighlighted: false,
      isDimmed: false,
      isDarkMode,
    };

    return {
      id: nodeId,
      type: 'tableNode',
      position: { x: 0, y: 0 }, // Will be set by layout
      data: nodeData,
      style: {
        borderColor: color,
      },
    } as ERTableNode;
  });
}

/**
 * Determine cardinality of a relationship based on schema constraints.
 *
 * One-to-one relationships are detected when:
 * 1. The FK column is also a primary key (e.g., user_profile.user_id is both FK and PK)
 * 2. The FK column has a unique constraint (enforces 1:1 at the database level)
 *
 * Otherwise, the relationship is considered one-to-many (default for FK relationships).
 *
 * @param sourceTable - The table containing the foreign key
 * @param sourceColumn - The FK column name
 * @returns 'one-to-one' if unique constraint exists, 'one-to-many' otherwise
 */
export function determineCardinality(
  sourceTable: SchemaTableInfo,
  sourceColumn: string
): CardinalityType {
  // Check 1: Is the FK column also a primary key?
  // This pattern is common for 1:1 relationships (e.g., user_profile extends users)
  if (sourceTable.primary_keys.includes(sourceColumn)) {
    return 'one-to-one';
  }

  // Check 2: Does the FK column have a unique constraint?
  // Unique constraints on FK columns enforce one-to-one relationships
  const hasUniqueConstraint = sourceTable.indexes?.some(
    (idx) => idx.unique && idx.columns?.includes(sourceColumn)
  );
  if (hasUniqueConstraint) {
    return 'one-to-one';
  }

  // Default: One-to-many (standard FK relationship)
  return 'one-to-many';
}

/**
 * Transform foreign keys to React Flow edges.
 *
 * Analyzes each FK relationship and determines cardinality based on:
 * - Whether the FK column is also a PK (indicates 1:1)
 * - Whether the FK column has a unique constraint (enforces 1:1)
 */
export function transformRelationshipsToEdges(
  tables: SchemaTableInfo[],
  connectionId: number,
  isDarkMode: boolean = false
): ERRelationshipEdge[] {
  const edges: ERRelationshipEdge[] = [];
  const tableMap = new Map(tables.map((t) => [t.name.toLowerCase(), t]));

  tables.forEach((table) => {
    table.foreign_keys.forEach((fk) => {
      const sourceNodeId = `${connectionId}-${table.name}`;
      const targetNodeId = `${connectionId}-${fk.referred_table}`;

      // Only create edge if target table exists
      if (!tableMap.has(fk.referred_table.toLowerCase())) {
        return;
      }

      // Determine cardinality based on constraints
      const cardinality = determineCardinality(table, fk.column);

      const edgeData: RelationshipEdgeData = {
        sourceColumn: fk.column,
        targetColumn: fk.referred_column,
        cardinality,
        source: 'explicit',
        constraintName: undefined,
        isHighlighted: false,
        isDarkMode,
      };

      edges.push({
        id: `${sourceNodeId}-${fk.column}-${targetNodeId}`,
        source: sourceNodeId,
        target: targetNodeId,
        type: 'relationshipEdge',
        data: edgeData,
        animated: false,
      } as ERRelationshipEdge);
    });
  });

  return edges;
}

/**
 * Transform multiple database schemas to a combined ER diagram.
 */
export function transformMultiSchemaToERDiagram(
  schemas: SchemaExploreResponse[]
): ERDiagramData {
  const allNodes: ERTableNode[] = [];
  const allEdges: ERRelationshipEdge[] = [];

  schemas.forEach((schema, index) => {
    const nodes = transformSchemaToNodes(schema, index);
    const edges = transformRelationshipsToEdges(schema.tables, schema.connection_id);

    allNodes.push(...nodes);
    allEdges.push(...edges);
  });

  return { nodes: allNodes, edges: allEdges };
}

// =============================================================================
// SEARCH & FILTER
// =============================================================================

/**
 * Filter and highlight nodes based on search query.
 */
export function applySearchFilter(
  nodes: ERTableNode[],
  edges: ERRelationshipEdge[],
  searchQuery: string
): { nodes: ERTableNode[]; edges: ERRelationshipEdge[] } {
  if (!searchQuery.trim()) {
    // Reset all highlights
    return {
      nodes: nodes.map((node) => ({
        ...node,
        data: { ...node.data, isHighlighted: false, isDimmed: false },
      })) as ERTableNode[],
      edges: edges.map((edge) => ({
        ...edge,
        data: { ...edge.data!, isHighlighted: false },
      })) as ERRelationshipEdge[],
    };
  }

  const query = searchQuery.toLowerCase();
  const matchingNodeIds = new Set<string>();

  // Find matching nodes
  nodes.forEach((node) => {
    const tableName = node.data.tableName.toLowerCase();
    const hasMatchingColumn = node.data.columns.some((col) =>
      col.name.toLowerCase().includes(query)
    );

    if (tableName.includes(query) || hasMatchingColumn) {
      matchingNodeIds.add(node.id);
    }
  });

  // Also highlight connected nodes
  const connectedNodeIds = new Set<string>();
  edges.forEach((edge) => {
    if (matchingNodeIds.has(edge.source)) {
      connectedNodeIds.add(edge.target);
    }
    if (matchingNodeIds.has(edge.target)) {
      connectedNodeIds.add(edge.source);
    }
  });

  // Apply highlighting
  const updatedNodes = nodes.map((node) => ({
    ...node,
    data: {
      ...node.data,
      isHighlighted: matchingNodeIds.has(node.id),
      isDimmed: !matchingNodeIds.has(node.id) && !connectedNodeIds.has(node.id),
    },
  })) as ERTableNode[];

  const updatedEdges = edges.map((edge) => ({
    ...edge,
    data: {
      ...edge.data!,
      isHighlighted:
        matchingNodeIds.has(edge.source) || matchingNodeIds.has(edge.target),
    },
  })) as ERRelationshipEdge[];

  return { nodes: updatedNodes, edges: updatedEdges };
}

// =============================================================================
// INFERRED RELATIONSHIPS
// =============================================================================

/**
 * Infer relationships from column naming conventions.
 * Patterns:
 * - user_id -> users.<primary_key>
 * - customer_fk -> customers.<primary_key>
 * - order_item_id -> order_items.<primary_key>
 *
 * Uses the target table's actual primary key instead of assuming 'id'.
 */
export function inferRelationships(
  tables: SchemaTableInfo[],
  connectionId: number,
  existingEdges: ERRelationshipEdge[],
  isDarkMode: boolean = false
): ERRelationshipEdge[] {
  const inferredEdges: ERRelationshipEdge[] = [];
  const existingEdgeIds = new Set(existingEdges.map((e) => e.id));
  const tableNames = new Set(tables.map((t) => t.name.toLowerCase()));

  // Pattern: column_name ending in _id
  const idPattern = /^(.+)_id$/i;
  // Pattern: column_name ending in _fk
  const fkPattern = /^(.+)_fk$/i;

  tables.forEach((table) => {
    table.columns.forEach((column) => {
      // Skip if already an explicit FK
      if (column.foreign_key) {
        return;
      }

      let targetTableName: string | null = null;

      // Try _id pattern
      const idMatch = column.name.match(idPattern);
      if (idMatch) {
        const baseName = idMatch[1].toLowerCase();
        // Try plural form
        if (tableNames.has(baseName + 's')) {
          targetTableName = baseName + 's';
        } else if (tableNames.has(baseName + 'es')) {
          targetTableName = baseName + 'es';
        } else if (tableNames.has(baseName)) {
          targetTableName = baseName;
        }
      }

      // Try _fk pattern
      if (!targetTableName) {
        const fkMatch = column.name.match(fkPattern);
        if (fkMatch) {
          const baseName = fkMatch[1].toLowerCase();
          if (tableNames.has(baseName + 's')) {
            targetTableName = baseName + 's';
          } else if (tableNames.has(baseName)) {
            targetTableName = baseName;
          }
        }
      }

      if (targetTableName && targetTableName !== table.name.toLowerCase()) {
        // Find actual table name (case-sensitive)
        const actualTable = tables.find(
          (t) => t.name.toLowerCase() === targetTableName
        );
        if (!actualTable) return;

        // Use the target table's actual primary key, fallback to 'id'
        const targetColumn = actualTable.primary_keys.length > 0
          ? actualTable.primary_keys[0]
          : 'id';

        const sourceNodeId = `${connectionId}-${table.name}`;
        const targetNodeId = `${connectionId}-${actualTable.name}`;
        const edgeId = `${sourceNodeId}-${column.name}-${targetNodeId}-inferred`;

        // Skip if this edge already exists
        if (existingEdgeIds.has(edgeId.replace('-inferred', ''))) {
          return;
        }

        const edgeData: RelationshipEdgeData = {
          sourceColumn: column.name,
          targetColumn,
          cardinality: 'one-to-many',
          source: 'inferred',
          isHighlighted: false,
          isDarkMode,
        };

        inferredEdges.push({
          id: edgeId,
          source: sourceNodeId,
          target: targetNodeId,
          type: 'relationshipEdge',
          data: edgeData,
          animated: false,
          style: { strokeDasharray: '5,5' }, // Dashed line for inferred
        } as ERRelationshipEdge);
      }
    });
  });

  return inferredEdges;
}

// =============================================================================
// UTILITIES
// =============================================================================

/**
 * Get all unique database connections from nodes.
 */
export function getUniqueConnections(
  nodes: ERTableNode[]
): Array<{ id: number; name: string; type: string; color: string }> {
  const connections = new Map<
    number,
    { id: number; name: string; type: string; color: string }
  >();

  nodes.forEach((node) => {
    if (!connections.has(node.data.connectionId)) {
      connections.set(node.data.connectionId, {
        id: node.data.connectionId,
        name: node.data.connectionName,
        type: node.data.databaseType,
        color: getDatabaseColor(connections.size),
      });
    }
  });

  return Array.from(connections.values());
}

/**
 * Toggle node expansion state.
 */
export function toggleNodeExpansion(
  nodes: ERTableNode[],
  nodeId: string
): ERTableNode[] {
  return nodes.map((node) => {
    if (node.id === nodeId) {
      return {
        ...node,
        data: { ...node.data, isExpanded: !node.data.isExpanded },
      };
    }
    return node;
  });
}

/**
 * Expand all nodes.
 */
export function expandAllNodes(nodes: ERTableNode[]): ERTableNode[] {
  return nodes.map((node) => ({
    ...node,
    data: { ...node.data, isExpanded: true },
  }));
}

/**
 * Collapse all nodes.
 */
export function collapseAllNodes(nodes: ERTableNode[]): ERTableNode[] {
  return nodes.map((node) => ({
    ...node,
    data: { ...node.data, isExpanded: false },
  }));
}
