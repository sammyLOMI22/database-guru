/**
 * Hierarchical Chart Utilities
 *
 * Data preparation and transformation for hierarchical charts:
 * - Treemap
 * - Sunburst
 * - Sankey
 */

export interface TreemapNode {
  name: string;
  value?: number;
  children?: TreemapNode[];
  color?: string;
  path?: string[];
  [key: string]: unknown; // Index signature for Recharts compatibility
}

export interface SunburstNode {
  name: string;
  value?: number;
  children?: SunburstNode[];
  color?: string;
  depth?: number;
}

export interface SankeyNode {
  name: string;
  value?: number;
}

export interface SankeyLink {
  source: number;
  target: number;
  value: number;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

/**
 * Converts flat hierarchical data to treemap format
 *
 * @param data - Array of records with category columns and a value column
 * @param categoryColumns - Ordered category columns (parent to child)
 * @param valueColumn - Column containing numeric values
 * @returns TreemapNode structure
 */
export function prepareTreemapData(
  data: Record<string, unknown>[],
  categoryColumns: string[],
  valueColumn: string
): TreemapNode {
  if (!data || data.length === 0 || categoryColumns.length === 0) {
    return { name: 'root', children: [] };
  }

  // Build hierarchical structure
  const root: TreemapNode = { name: 'root', children: [] };

  for (const row of data) {
    let currentNode = root;
    const path: string[] = [];

    for (let i = 0; i < categoryColumns.length; i++) {
      const categoryValue = String(row[categoryColumns[i]] ?? 'Unknown');
      path.push(categoryValue);

      // Find or create child node
      let childNode = currentNode.children?.find(c => c.name === categoryValue);

      if (!childNode) {
        childNode = {
          name: categoryValue,
          children: i < categoryColumns.length - 1 ? [] : undefined,
          path: [...path],
        };
        if (!currentNode.children) currentNode.children = [];
        currentNode.children.push(childNode);
      }

      // If this is the leaf level, add the value
      if (i === categoryColumns.length - 1) {
        const value = Number(row[valueColumn]) || 0;
        childNode.value = (childNode.value || 0) + value;
      }

      currentNode = childNode;
    }
  }

  // Calculate parent values from children
  calculateParentValues(root);

  return root;
}

/**
 * Recursively calculates parent values from children
 */
function calculateParentValues(node: TreemapNode): number {
  if (!node.children || node.children.length === 0) {
    return node.value || 0;
  }

  let total = 0;
  for (const child of node.children) {
    total += calculateParentValues(child);
  }

  node.value = total;
  return total;
}

/**
 * Converts flat data to sunburst format (same as treemap but with depth)
 */
export function prepareSunburstData(
  data: Record<string, unknown>[],
  categoryColumns: string[],
  valueColumn: string
): SunburstNode {
  const treemapData = prepareTreemapData(data, categoryColumns, valueColumn);
  return addDepthToNodes(treemapData as SunburstNode, 0);
}

/**
 * Adds depth information to nodes
 */
function addDepthToNodes(node: SunburstNode, depth: number): SunburstNode {
  node.depth = depth;
  if (node.children) {
    node.children = node.children.map(child => addDepthToNodes(child, depth + 1));
  }
  return node;
}

/**
 * Prepares data for Sankey diagram (flow visualization)
 *
 * @param data - Array of records with source, target, and value columns
 * @param sourceColumn - Column for source node
 * @param targetColumn - Column for target node
 * @param valueColumn - Column for flow value
 * @returns SankeyData with nodes and links
 */
export function prepareSankeyData(
  data: Record<string, unknown>[],
  sourceColumn: string,
  targetColumn: string,
  valueColumn: string
): SankeyData {
  if (!data || data.length === 0) {
    return { nodes: [], links: [] };
  }

  // Collect unique nodes
  const nodeSet = new Set<string>();
  for (const row of data) {
    const source = String(row[sourceColumn] ?? '');
    const target = String(row[targetColumn] ?? '');
    if (source) nodeSet.add(source);
    if (target) nodeSet.add(target);
  }

  // Create node array with indices
  const nodes: SankeyNode[] = Array.from(nodeSet).map(name => ({ name }));
  const nodeIndex = new Map(nodes.map((n, i) => [n.name, i]));

  // Create links
  const linkMap = new Map<string, number>();
  for (const row of data) {
    const source = String(row[sourceColumn] ?? '');
    const target = String(row[targetColumn] ?? '');
    const value = Number(row[valueColumn]) || 0;

    if (!source || !target || source === target) continue;

    const key = `${source}->${target}`;
    linkMap.set(key, (linkMap.get(key) || 0) + value);
  }

  const links: SankeyLink[] = Array.from(linkMap.entries()).map(([key, value]) => {
    const [source, target] = key.split('->');
    return {
      source: nodeIndex.get(source) ?? 0,
      target: nodeIndex.get(target) ?? 0,
      value,
    };
  });

  return { nodes, links };
}

/**
 * Flattens hierarchical data for display in tooltips
 */
export function flattenHierarchy(node: TreemapNode, prefix: string = ''): string {
  const path = prefix ? `${prefix} > ${node.name}` : node.name;
  if (!node.children || node.children.length === 0) {
    return path;
  }
  return path;
}

/**
 * Calculates the total value of a hierarchical dataset
 */
export function getTotalValue(node: TreemapNode): number {
  if (!node.children || node.children.length === 0) {
    return node.value || 0;
  }
  return node.children.reduce((sum, child) => sum + getTotalValue(child), 0);
}

/**
 * Gets the maximum depth of a hierarchical structure
 */
export function getMaxDepth(node: TreemapNode, currentDepth: number = 0): number {
  if (!node.children || node.children.length === 0) {
    return currentDepth;
  }
  return Math.max(...node.children.map(child => getMaxDepth(child, currentDepth + 1)));
}

/**
 * Filters hierarchical data by minimum value threshold
 */
export function filterByValue(node: TreemapNode, minValue: number): TreemapNode {
  if (!node.children) {
    return node;
  }

  const filteredChildren = node.children
    .filter(child => (child.value || 0) >= minValue)
    .map(child => filterByValue(child, minValue));

  return {
    ...node,
    children: filteredChildren.length > 0 ? filteredChildren : undefined,
  };
}

/**
 * Color palettes for hierarchical charts
 */
export const HIERARCHICAL_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
];

/**
 * Assigns colors to hierarchical nodes based on top-level category
 */
export function assignColors(node: TreemapNode, colorIndex: number = 0): TreemapNode {
  if (!node.children) {
    return { ...node, color: HIERARCHICAL_COLORS[colorIndex % HIERARCHICAL_COLORS.length] };
  }

  return {
    ...node,
    color: HIERARCHICAL_COLORS[colorIndex % HIERARCHICAL_COLORS.length],
    children: node.children.map((child, i) =>
      assignColors(child, node.name === 'root' ? i : colorIndex)
    ),
  };
}

/**
 * Detects if data is suitable for hierarchical visualization
 */
export function isHierarchicalData(
  data: Record<string, unknown>[],
  categoricalColumns: string[]
): boolean {
  if (!data || data.length < 2 || categoricalColumns.length < 2) {
    return false;
  }

  // Check if there's a natural hierarchy (fewer unique values at higher levels)
  const uniqueCounts = categoricalColumns.map(col =>
    new Set(data.map(row => row[col])).size
  );

  // Hierarchy exists if counts generally increase
  for (let i = 1; i < uniqueCounts.length; i++) {
    if (uniqueCounts[i] <= uniqueCounts[i - 1]) {
      return false;
    }
  }

  return true;
}
