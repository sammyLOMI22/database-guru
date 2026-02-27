// Phase 22: Execution Plan Tree Viewer
import { useState } from 'react';
import { ChevronRight, ChevronDown, AlertTriangle, CheckCircle2, HardDrive } from 'lucide-react';
import type { PlanNode } from '../../types/performance';

interface ExecutionPlanTreeProps {
  rootNode?: PlanNode | null;
  allNodes: PlanNode[];
  rawPlan: string[];
}

function getSeverityColor(node: PlanNode): string {
  if (node.disk_spill) return 'text-red-600 dark:text-red-400';
  const type = node.node_type.toLowerCase();
  if (type.includes('seq scan') || type === 'scan' || type === 'full table scan' || type === 'seq_scan')
    return 'text-amber-600 dark:text-amber-400';
  if (type.includes('index') || type === 'search')
    return 'text-green-600 dark:text-green-400';
  return 'text-gray-600 dark:text-gray-400';
}

function getNodeIcon(node: PlanNode) {
  if (node.disk_spill) return <HardDrive className="w-3.5 h-3.5 text-red-500" />;
  const type = node.node_type.toLowerCase();
  if (type.includes('seq scan') || type === 'scan' || type === 'full table scan' || type === 'seq_scan')
    return <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />;
  if (type.includes('index') || type === 'search')
    return <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />;
  return null;
}

function PlanNodeRow({ node, depth = 0 }: { node: PlanNode; depth?: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  const colorClass = getSeverityColor(node);

  return (
    <div>
      <div
        className={`flex items-center gap-2 py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg cursor-pointer text-sm`}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}

        {getNodeIcon(node)}

        <span className={`font-semibold ${colorClass}`}>
          {node.node_type}
        </span>

        {node.relation && (
          <span className="text-gray-500 dark:text-gray-400">
            on <span className="font-medium text-gray-700 dark:text-gray-300">{node.relation}</span>
          </span>
        )}

        {node.index_name && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
            {node.index_name}
          </span>
        )}

        {node.cost_total != null && (
          <span className="text-xs text-gray-400 ml-auto">
            cost: {node.cost_total.toLocaleString()}
          </span>
        )}

        {node.rows_estimated != null && (
          <span className="text-xs text-gray-400">
            rows: {node.rows_estimated.toLocaleString()}
          </span>
        )}

        {node.actual_time_ms != null && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
            {node.actual_time_ms.toFixed(2)}ms
          </span>
        )}

        {node.disk_spill && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-bold">
            DISK SPILL
          </span>
        )}
      </div>

      {node.filter && (
        <div
          className="text-xs text-gray-400 truncate"
          style={{ paddingLeft: `${depth * 20 + 38}px` }}
          title={node.filter}
        >
          Filter: {node.filter.length > 80 ? node.filter.slice(0, 80) + '...' : node.filter}
        </div>
      )}

      {expanded && hasChildren && node.children.map((child, i) => (
        <PlanNodeRow key={i} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export function ExecutionPlanTree({ rootNode, allNodes, rawPlan }: ExecutionPlanTreeProps) {
  const [showRaw, setShowRaw] = useState(false);

  // For dialects without tree structure (MySQL, some SQLite), show flat list
  const hasTree = rootNode && rootNode.children && rootNode.children.length > 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          Execution Plan
        </h3>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          {showRaw ? 'Show Tree' : 'Show Raw'}
        </button>
      </div>

      {showRaw ? (
        <pre className="text-xs bg-gray-50 dark:bg-gray-800 p-3 rounded-xl overflow-x-auto font-mono text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
          {rawPlan.join('\n') || 'No plan data'}
        </pre>
      ) : hasTree ? (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-2 bg-white dark:bg-gray-800/50">
          <PlanNodeRow node={rootNode} />
        </div>
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-2 bg-white dark:bg-gray-800/50">
          {allNodes.map((node, i) => (
            <PlanNodeRow key={i} node={node} />
          ))}
        </div>
      )}
    </div>
  );
}
