import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Filter } from 'lucide-react';
import type { LineageGraphResponse, LineageNode } from '../../types/lineage';

interface ColumnTrace {
  outputColumn: string;
  sourceTable: string;
  sourceColumn: string;
  transformation: string | null;
  expression: string | null;
  isComplex: boolean;
}

interface ColumnLineageProps {
  graphData: LineageGraphResponse;
}

function traceColumnLineage(graphData: LineageGraphResponse): ColumnTrace[] {
  const { nodes, edges } = graphData;
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  // Build reverse edge map: target_id → [source nodes]
  const reverseEdges = new Map<string, { sourceId: string; edgeType: string }[]>();
  for (const edge of edges) {
    const list = reverseEdges.get(edge.target_id) || [];
    list.push({ sourceId: edge.source_id, edgeType: edge.edge_type });
    reverseEdges.set(edge.target_id, list);
  }

  const outputNodes = nodes.filter((n) => n.node_type === 'output_column');
  const traces: ColumnTrace[] = [];

  for (const outNode of outputNodes) {
    const incomingEdges = reverseEdges.get(outNode.id) || [];

    for (const incoming of incomingEdges) {
      const sourceNode = nodeMap.get(incoming.sourceId);
      if (!sourceNode) continue;

      if (sourceNode.node_type === 'source_column') {
        // Direct mapping: source_column → output_column
        traces.push({
          outputColumn: outNode.label,
          sourceTable: sourceNode.table_name || '—',
          sourceColumn: sourceNode.column_name || sourceNode.label,
          transformation: null,
          expression: null,
          isComplex: false,
        });
      } else if (sourceNode.node_type === 'transformation') {
        // Transformation: source_column(s) → transformation → output_column
        const transformInputs = reverseEdges.get(sourceNode.id) || [];
        const sourceColumns = transformInputs
          .map((ti) => nodeMap.get(ti.sourceId))
          .filter((n): n is LineageNode => !!n && n.node_type === 'source_column');

        if (sourceColumns.length > 0) {
          for (const sc of sourceColumns) {
            traces.push({
              outputColumn: outNode.label,
              sourceTable: sc.table_name || '—',
              sourceColumn: sc.column_name || sc.label,
              transformation: sourceNode.transformation_type || 'expression',
              expression: sourceNode.expression || sourceNode.label,
              isComplex: sourceNode.transformation_type === 'expression' || sourceColumns.length > 1,
            });
          }
        } else {
          // Transformation with no detected source columns (e.g., COUNT(*))
          traces.push({
            outputColumn: outNode.label,
            sourceTable: '—',
            sourceColumn: '*',
            transformation: sourceNode.transformation_type || 'expression',
            expression: sourceNode.expression || sourceNode.label,
            isComplex: true,
          });
        }
      } else if (sourceNode.node_type === 'source_table') {
        // Table → output (SELECT *)
        traces.push({
          outputColumn: outNode.label,
          sourceTable: sourceNode.table_name || sourceNode.label,
          sourceColumn: '*',
          transformation: null,
          expression: null,
          isComplex: false,
        });
      }
    }
  }

  return traces;
}

const TRANSFORM_COLORS: Record<string, string> = {
  aggregation: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  expression: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  function: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  direct: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
};

export function ColumnLineage({ graphData }: ColumnLineageProps) {
  const [filter, setFilter] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const traces = useMemo(() => traceColumnLineage(graphData), [graphData]);

  const filteredTraces = useMemo(() => {
    if (!filter.trim()) return traces;
    const term = filter.toLowerCase();
    return traces.filter(
      (t) =>
        t.outputColumn.toLowerCase().includes(term) ||
        t.sourceTable.toLowerCase().includes(term) ||
        t.sourceColumn.toLowerCase().includes(term)
    );
  }, [traces, filter]);

  const toggleRow = (idx: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (traces.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
        No column-level lineage traces found.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header + Filter */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Column Lineage ({filteredTraces.length})
        </h3>
        <div className="relative">
          <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter..."
            className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 w-48 focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-50 dark:bg-gray-800/90 backdrop-blur-sm">
            <tr className="text-left text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <th className="px-4 py-2 font-bold w-8"></th>
              <th className="px-4 py-2 font-bold">Output Column</th>
              <th className="px-4 py-2 font-bold">Source Table</th>
              <th className="px-4 py-2 font-bold">Source Column</th>
              <th className="px-4 py-2 font-bold">Transformation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
            {filteredTraces.map((trace, idx) => (
              <React.Fragment key={idx}>
                <tr
                  className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                  onClick={() => trace.isComplex && toggleRow(idx)}
                >
                  <td className="px-4 py-2.5 text-gray-400">
                    {trace.isComplex ? (
                      expandedRows.has(idx) ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )
                    ) : (
                      <span className="w-3.5 h-3.5 inline-block text-center text-gray-300 dark:text-gray-600">·</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-white">
                    {trace.outputColumn}
                  </td>
                  <td className="px-4 py-2.5 text-blue-600 dark:text-blue-400 font-mono">
                    {trace.sourceTable}
                  </td>
                  <td className="px-4 py-2.5 text-gray-700 dark:text-gray-300 font-mono">
                    {trace.sourceColumn}
                  </td>
                  <td className="px-4 py-2.5">
                    {trace.transformation ? (
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${TRANSFORM_COLORS[trace.transformation] || TRANSFORM_COLORS.direct}`}>
                        {trace.transformation}
                      </span>
                    ) : (
                      <span className="text-gray-400 dark:text-gray-500">direct</span>
                    )}
                  </td>
                </tr>
                {/* Expanded expression row */}
                {trace.isComplex && expandedRows.has(idx) && trace.expression && (
                  <tr className="bg-gray-50 dark:bg-gray-800/30">
                    <td></td>
                    <td colSpan={4} className="px-4 py-2">
                      <pre className="text-[11px] font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {trace.expression}
                      </pre>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
