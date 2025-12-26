/**
 * Hierarchy Pattern Detector
 *
 * Detects hierarchical/tree structures in data, useful for:
 * - Treemap visualizations
 * - Sunburst charts
 * - Organizational charts
 *
 * Looks for patterns like:
 * - Parent-child ID relationships
 * - Nested category columns (region -> country -> city)
 * - Level indicators (level, depth, tier)
 */

export interface HierarchyInfo {
  /** Whether the data appears to be hierarchical */
  isHierarchical: boolean;
  /** Type of hierarchy detected */
  type: 'parent-child' | 'nested-categories' | 'level-based' | null;
  /** Parent column (for parent-child relationships) */
  parentColumn: string | null;
  /** Child/ID column (for parent-child relationships) */
  childColumn: string | null;
  /** Ordered category columns (for nested categories) */
  categoryColumns: string[];
  /** Depth of the hierarchy */
  maxDepth: number;
  /** Confidence score (0-1) */
  confidence: number;
}

/**
 * Patterns for detecting parent-child relationships
 */
const PARENT_PATTERNS = [
  /^parent[_\s]?id$/i,
  /^parent$/i,
  /^parent[_\s]?name$/i,
  /^manager[_\s]?id$/i,
  /^supervisor[_\s]?id$/i,
  /^reports[_\s]?to$/i,
  /^parent[_\s]?category$/i,
  /^parent[_\s]?node$/i,
];

const CHILD_PATTERNS = [
  /^id$/i,
  /^child[_\s]?id$/i,
  /^node[_\s]?id$/i,
  /^employee[_\s]?id$/i,
  /^category[_\s]?id$/i,
];

/**
 * Patterns for level/depth columns
 */
const LEVEL_PATTERNS = [
  /^level$/i,
  /^depth$/i,
  /^tier$/i,
  /^hierarchy[_\s]?level$/i,
  /^tree[_\s]?level$/i,
];

/**
 * Common hierarchical category names (ordered from high to low)
 */
const HIERARCHICAL_CATEGORIES: string[][] = [
  ['region', 'country', 'state', 'city'],
  ['continent', 'country', 'state', 'city'],
  ['division', 'department', 'team', 'employee'],
  ['category', 'subcategory', 'product'],
  ['group', 'subgroup', 'item'],
  ['year', 'quarter', 'month', 'day'],
  ['year', 'month', 'week', 'day'],
];

/**
 * Main detection function for hierarchical patterns
 */
export function detectHierarchy(
  results: Record<string, unknown>[],
  categoricalColumns: string[]
): HierarchyInfo {
  // Default: not hierarchical
  const defaultResult: HierarchyInfo = {
    isHierarchical: false,
    type: null,
    parentColumn: null,
    childColumn: null,
    categoryColumns: [],
    maxDepth: 0,
    confidence: 0,
  };

  if (!results || results.length < 2) {
    return defaultResult;
  }

  const columns = Object.keys(results[0] || {});

  // Try to detect parent-child relationships first (strongest signal)
  const parentChildResult = detectParentChildRelationship(results, columns);
  if (parentChildResult.isHierarchical) {
    return parentChildResult;
  }

  // Try to detect nested category structure
  const nestedCategoryResult = detectNestedCategories(results, categoricalColumns);
  if (nestedCategoryResult.isHierarchical) {
    return nestedCategoryResult;
  }

  // Try to detect level-based hierarchy
  const levelBasedResult = detectLevelBasedHierarchy(results, columns);
  if (levelBasedResult.isHierarchical) {
    return levelBasedResult;
  }

  return defaultResult;
}

/**
 * Detect parent-child ID relationships
 */
function detectParentChildRelationship(
  results: Record<string, unknown>[],
  columns: string[]
): HierarchyInfo {
  // Find parent column
  const parentColumn = columns.find(col =>
    PARENT_PATTERNS.some(p => p.test(col))
  );

  if (!parentColumn) {
    return createDefaultResult();
  }

  // Find child/ID column
  let childColumn = columns.find(col =>
    CHILD_PATTERNS.some(p => p.test(col))
  );

  // If no explicit child column, look for ID-like column
  if (!childColumn) {
    childColumn = columns.find(col =>
      /id$/i.test(col) && col !== parentColumn
    );
  }

  if (!childColumn) {
    return createDefaultResult();
  }

  // Validate the relationship
  const validation = validateParentChildRelationship(
    results,
    parentColumn,
    childColumn
  );

  if (!validation.isValid) {
    return createDefaultResult();
  }

  return {
    isHierarchical: true,
    type: 'parent-child',
    parentColumn,
    childColumn,
    categoryColumns: [],
    maxDepth: validation.maxDepth,
    confidence: validation.confidence,
  };
}

/**
 * Validate parent-child relationship by checking references
 */
function validateParentChildRelationship(
  results: Record<string, unknown>[],
  parentColumn: string,
  childColumn: string
): { isValid: boolean; maxDepth: number; confidence: number } {
  // Build a set of all child IDs
  const childIds = new Set<unknown>(
    results.map(r => r[childColumn]).filter(v => v != null)
  );

  // Count how many parent values reference valid child IDs
  let validReferences = 0;
  let nullParents = 0;
  const parentToChildren = new Map<unknown, unknown[]>();

  for (const row of results) {
    const parentId = row[parentColumn];
    const childId = row[childColumn];

    if (parentId == null) {
      nullParents++; // Root nodes have null parent
    } else if (childIds.has(parentId)) {
      validReferences++;
    }

    // Track parent-child relationships for depth calculation
    if (!parentToChildren.has(parentId)) {
      parentToChildren.set(parentId, []);
    }
    parentToChildren.get(parentId)!.push(childId);
  }

  // Need at least one root node (null parent) and some valid references
  const hasRootNodes = nullParents > 0;
  const referenceRatio = validReferences / (results.length - nullParents || 1);

  // Calculate max depth by traversing from roots
  let maxDepth = 0;
  if (hasRootNodes) {
    const visited = new Set<unknown>();
    const queue: { id: unknown; depth: number }[] = [];

    // Find root nodes (those with null parent or parent not in child set)
    for (const row of results) {
      const parentId = row[parentColumn];
      if (parentId == null || !childIds.has(parentId)) {
        queue.push({ id: row[childColumn], depth: 1 });
      }
    }

    while (queue.length > 0) {
      const { id, depth } = queue.shift()!;
      if (visited.has(id)) continue;
      visited.add(id);
      maxDepth = Math.max(maxDepth, depth);

      const children = results.filter(r => r[parentColumn] === id);
      for (const child of children) {
        queue.push({ id: child[childColumn], depth: depth + 1 });
      }
    }
  }

  const isValid = hasRootNodes && (referenceRatio >= 0.3 || maxDepth >= 2);
  const confidence = (hasRootNodes ? 0.3 : 0) +
    Math.min(referenceRatio, 1) * 0.4 +
    Math.min(maxDepth / 5, 1) * 0.3;

  return { isValid, maxDepth, confidence };
}

/**
 * Detect nested category columns
 */
function detectNestedCategories(
  results: Record<string, unknown>[],
  categoricalColumns: string[]
): HierarchyInfo {
  if (categoricalColumns.length < 2) {
    return createDefaultResult();
  }

  // Check against known hierarchical patterns
  for (const pattern of HIERARCHICAL_CATEGORIES) {
    const matchingColumns = findMatchingPattern(categoricalColumns, pattern);
    if (matchingColumns.length >= 2) {
      // Validate that categories are actually nested
      const validation = validateNestedCategories(results, matchingColumns);
      if (validation.isValid) {
        return {
          isHierarchical: true,
          type: 'nested-categories',
          parentColumn: null,
          childColumn: null,
          categoryColumns: matchingColumns,
          maxDepth: matchingColumns.length,
          confidence: validation.confidence,
        };
      }
    }
  }

  // Try to detect any decreasing cardinality pattern
  const cardinalityOrder = detectCardinalityPattern(results, categoricalColumns);
  if (cardinalityOrder.length >= 2) {
    return {
      isHierarchical: true,
      type: 'nested-categories',
      parentColumn: null,
      childColumn: null,
      categoryColumns: cardinalityOrder,
      maxDepth: cardinalityOrder.length,
      confidence: 0.6,
    };
  }

  return createDefaultResult();
}

/**
 * Find columns matching a known hierarchical pattern
 */
function findMatchingPattern(
  columns: string[],
  pattern: string[]
): string[] {
  const matchingColumns: string[] = [];
  const normalizedColumns = columns.map(c => c.toLowerCase().replace(/[_\s]/g, ''));

  for (const patternItem of pattern) {
    const match = columns.find((_col, i) =>
      normalizedColumns[i].includes(patternItem.toLowerCase())
    );
    if (match && !matchingColumns.includes(match)) {
      matchingColumns.push(match);
    }
  }

  return matchingColumns;
}

/**
 * Validate nested categories by checking cardinality decreases
 */
function validateNestedCategories(
  results: Record<string, unknown>[],
  columns: string[]
): { isValid: boolean; confidence: number } {
  // Calculate unique counts for each column
  const uniqueCounts = columns.map(col =>
    new Set(results.map(r => r[col])).size
  );

  // Check if cardinality generally decreases (more specific = fewer unique values)
  let isDecreasing = true;
  let decreaseCount = 0;

  for (let i = 1; i < uniqueCounts.length; i++) {
    if (uniqueCounts[i] > uniqueCounts[i - 1]) {
      isDecreasing = false;
    } else if (uniqueCounts[i] < uniqueCounts[i - 1]) {
      decreaseCount++;
    }
  }

  // Also check for consistent grouping
  const hasConsistentGrouping = checkConsistentGrouping(results, columns);

  const confidence = (decreaseCount / (columns.length - 1)) * 0.5 +
    (hasConsistentGrouping ? 0.5 : 0);

  return {
    isValid: (isDecreasing || decreaseCount >= columns.length / 2) && hasConsistentGrouping,
    confidence,
  };
}

/**
 * Check if lower-level categories are consistently grouped within higher levels
 */
function checkConsistentGrouping(
  results: Record<string, unknown>[],
  columns: string[]
): boolean {
  if (columns.length < 2) return false;

  const parentCol = columns[0];
  const childCol = columns[1];

  // Build parent-to-children map
  const parentToChildren = new Map<unknown, Set<unknown>>();
  for (const row of results) {
    const parent = row[parentCol];
    const child = row[childCol];

    if (!parentToChildren.has(parent)) {
      parentToChildren.set(parent, new Set());
    }
    parentToChildren.get(parent)!.add(child);
  }

  // Check that children don't appear under multiple parents
  const allChildren = new Set<unknown>();
  for (const [_parent, children] of parentToChildren) {
    for (const child of children) {
      if (allChildren.has(child)) {
        // Child appears under multiple parents - less hierarchical
        // This is actually okay for some hierarchies, so just reduce confidence
        return false;
      }
      allChildren.add(child);
    }
  }

  return true;
}

/**
 * Detect cardinality-based hierarchy (columns with decreasing unique values)
 */
function detectCardinalityPattern(
  results: Record<string, unknown>[],
  columns: string[]
): string[] {
  // Calculate cardinality for each column
  const columnCardinality = columns.map(col => ({
    column: col,
    uniqueCount: new Set(results.map(r => r[col])).size,
  }));

  // Sort by cardinality (ascending = most general to most specific)
  columnCardinality.sort((a, b) => a.uniqueCount - b.uniqueCount);

  // Need at least a 2:1 ratio between levels
  const orderedColumns: string[] = [];
  let lastCount = 0;

  for (const { column, uniqueCount } of columnCardinality) {
    if (lastCount === 0 || uniqueCount >= lastCount * 1.5) {
      orderedColumns.push(column);
      lastCount = uniqueCount;
    }
  }

  return orderedColumns.length >= 2 ? orderedColumns : [];
}

/**
 * Detect level-based hierarchy (explicit level/depth column)
 */
function detectLevelBasedHierarchy(
  results: Record<string, unknown>[],
  columns: string[]
): HierarchyInfo {
  // Find level column
  const levelColumn = columns.find(col =>
    LEVEL_PATTERNS.some(p => p.test(col))
  );

  if (!levelColumn) {
    return createDefaultResult();
  }

  // Validate level values (should be sequential integers)
  const levelValues = results
    .map(r => Number(r[levelColumn]))
    .filter(v => !isNaN(v) && isFinite(v));

  if (levelValues.length === 0) {
    return createDefaultResult();
  }

  const minLevel = Math.min(...levelValues);
  const maxLevel = Math.max(...levelValues);
  const uniqueLevels = new Set(levelValues).size;

  // Should have at least 2 levels
  if (uniqueLevels < 2) {
    return createDefaultResult();
  }

  // Levels should be reasonably consecutive
  const expectedLevels = maxLevel - minLevel + 1;
  const levelCoverage = uniqueLevels / expectedLevels;

  if (levelCoverage < 0.5) {
    return createDefaultResult();
  }

  return {
    isHierarchical: true,
    type: 'level-based',
    parentColumn: null,
    childColumn: levelColumn,
    categoryColumns: [],
    maxDepth: maxLevel - minLevel + 1,
    confidence: Math.min(levelCoverage, 1) * 0.8 + (uniqueLevels >= 3 ? 0.2 : 0.1),
  };
}

/**
 * Create default result helper
 */
function createDefaultResult(): HierarchyInfo {
  return {
    isHierarchical: false,
    type: null,
    parentColumn: null,
    childColumn: null,
    categoryColumns: [],
    maxDepth: 0,
    confidence: 0,
  };
}
