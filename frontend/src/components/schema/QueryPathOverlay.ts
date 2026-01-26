/**
 * QueryPathOverlay - Utility to highlight tables used by a SQL query on the ER diagram.
 *
 * Extracts table names from SQL and applies highlight/dim state to ER nodes.
 */

import type { ERTableNode } from '../../types/erDiagram';

/**
 * Extract table names referenced in a SQL query.
 * Handles FROM, JOIN, and comma-separated table lists.
 */
export function extractTablesFromSql(sql: string): string[] {
  if (!sql) return [];

  const tables = new Set<string>();

  // Match FROM/JOIN followed by table name (with optional schema prefix)
  const pattern = /(?:FROM|JOIN)\s+(?:(\w+)\.)?(\w+)/gi;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(sql)) !== null) {
    // Use the table name (group 2), ignore schema prefix
    tables.add(match[2].toLowerCase());
  }

  return Array.from(tables);
}

/**
 * Apply query path overlay to ER diagram nodes.
 *
 * When enabled with SQL, highlights nodes whose table names appear in the query
 * and dims all other nodes. When disabled, resets all nodes.
 */
export function applyQueryPathOverlay(
  nodes: ERTableNode[],
  sql: string | null | undefined,
  enabled: boolean
): ERTableNode[] {
  if (!enabled || !sql) {
    // Reset all nodes to default state
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isHighlighted: false,
        isDimmed: false,
      },
    }));
  }

  const referencedTables = extractTablesFromSql(sql);

  return nodes.map((node) => {
    const tableName = node.data.tableName.toLowerCase();
    const isReferenced = referencedTables.includes(tableName);

    return {
      ...node,
      data: {
        ...node.data,
        isHighlighted: isReferenced,
        isDimmed: !isReferenced,
      },
    };
  });
}
