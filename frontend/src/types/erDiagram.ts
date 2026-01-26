/**
 * ER Diagram Types - Phase 7
 *
 * TypeScript interfaces for React Flow-based ER diagram visualization.
 */

import type { Node, Edge } from 'reactflow';
import type { SchemaTableInfo, SchemaColumnInfo } from './api';

// =============================================================================
// ENUMS
// =============================================================================

/**
 * Cardinality types for relationship edges.
 */
export type CardinalityType = 'one-to-one' | 'one-to-many' | 'many-to-many';

/**
 * Relationship source - explicit FK or inferred from naming conventions.
 */
export type RelationshipSource = 'explicit' | 'inferred';

/**
 * Layout direction for Dagre algorithm.
 */
export type LayoutDirection = 'TB' | 'LR' | 'BT' | 'RL';

// =============================================================================
// NODE TYPES
// =============================================================================

/**
 * Data stored in a table node.
 */
export interface TableNodeData {
  /** Table name */
  tableName: string;
  /** Columns in the table */
  columns: SchemaColumnInfo[];
  /** Primary key column names */
  primaryKeys: string[];
  /** Foreign keys from this table */
  foreignKeys: Array<{
    column: string;
    referred_table: string;
    referred_column: string;
  }>;
  /** Row count (if available) */
  rowCount: number | null;
  /** Database connection ID (for multi-DB color coding) */
  connectionId: number;
  /** Database type (postgresql, mysql, sqlite, etc.) */
  databaseType: string;
  /** Database/connection name */
  connectionName: string;
  /** Whether columns are expanded */
  isExpanded: boolean;
  /** Whether this node is highlighted (from search) */
  isHighlighted: boolean;
  /** Whether this node is dimmed (not matching search) */
  isDimmed: boolean;
  /** Current theme mode */
  isDarkMode: boolean;
  /** Query frequency count from pattern analytics (optional) */
  queryFrequency?: number | null;
}

/**
 * React Flow node for a database table.
 */
export type ERTableNode = Node<TableNodeData, 'tableNode'>;

// =============================================================================
// EDGE TYPES
// =============================================================================

/**
 * Data stored in a relationship edge.
 */
export interface RelationshipEdgeData {
  /** Source column name */
  sourceColumn: string;
  /** Target column name */
  targetColumn: string;
  /** Relationship cardinality */
  cardinality: CardinalityType;
  /** Whether FK is explicit or inferred */
  source: RelationshipSource;
  /** Constraint name (if explicit) */
  constraintName?: string;
  /** Whether this edge is highlighted */
  isHighlighted: boolean;
  /** Current theme mode */
  isDarkMode: boolean;
}

/**
 * React Flow edge for a foreign key relationship.
 */
export type ERRelationshipEdge = Edge<RelationshipEdgeData>;

// =============================================================================
// DIAGRAM DATA
// =============================================================================

/**
 * Complete ER diagram data ready for React Flow.
 */
export interface ERDiagramData {
  /** Table nodes */
  nodes: ERTableNode[];
  /** Relationship edges */
  edges: ERRelationshipEdge[];
}

/**
 * Schema data grouped by database connection.
 */
export interface DatabaseSchemaGroup {
  connectionId: number;
  connectionName: string;
  databaseType: string;
  tables: SchemaTableInfo[];
  color: string;
}

// =============================================================================
// LAYOUT OPTIONS
// =============================================================================

/**
 * Options for Dagre layout algorithm.
 */
export interface LayoutOptions {
  /** Layout direction */
  direction: LayoutDirection;
  /** Horizontal spacing between nodes */
  nodeSpacingX: number;
  /** Vertical spacing between nodes */
  nodeSpacingY: number;
  /** Padding within nodes */
  nodePadding: number;
}

/**
 * Default layout options.
 */
export const DEFAULT_LAYOUT_OPTIONS: LayoutOptions = {
  direction: 'TB',
  nodeSpacingX: 200, // Horizontal spacing between nodes in same rank
  nodeSpacingY: 180, // Vertical spacing between ranks (levels)
  nodePadding: 60,   // Margin around the entire graph
};

// =============================================================================
// UI CONSTANTS
// =============================================================================

/** Base width for table nodes */
export const NODE_BASE_WIDTH = 240;

/** Height per column row */
export const COLUMN_ROW_HEIGHT = 28;

/** Header height for table name */
export const NODE_HEADER_HEIGHT = 44;

/** Collapsed node height (header only) */
export const NODE_COLLAPSED_HEIGHT = 56;

/** Maximum columns to show before scrolling */
export const MAX_VISIBLE_COLUMNS = 10;

// =============================================================================
// DIAGRAM STATE
// =============================================================================

/**
 * ER Diagram component state.
 */
export interface ERDiagramState {
  /** All table nodes */
  nodes: ERTableNode[];
  /** All relationship edges */
  edges: ERRelationshipEdge[];
  /** Current search query */
  searchQuery: string;
  /** Whether to show inferred relationships */
  showInferredRelationships: boolean;
  /** Current layout direction */
  layoutDirection: LayoutDirection;
  /** Expanded node IDs */
  expandedNodes: Set<string>;
  /** Selected node ID */
  selectedNodeId: string | null;
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
}

// =============================================================================
// COLORS
// =============================================================================

/**
 * Color palette for multi-database visualization.
 * Each database connection gets a unique color.
 */
export const DATABASE_COLORS = [
  '#3B82F6', // blue
  '#10B981', // emerald
  '#8B5CF6', // violet
  '#F59E0B', // amber
  '#EF4444', // red
  '#06B6D4', // cyan
  '#EC4899', // pink
  '#84CC16', // lime
] as const;

/**
 * Get color for a database connection by index.
 */
export function getDatabaseColor(index: number): string {
  return DATABASE_COLORS[index % DATABASE_COLORS.length];
}
