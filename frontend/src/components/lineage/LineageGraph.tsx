/**
 * LineageGraph - Main React Flow container for lineage visualization.
 *
 * Features:
 * - SQL textarea input with "Parse" button
 * - React Flow graph with custom nodes and edges
 * - Loading/error states
 * - Controls, MiniMap, Background
 * - fitView on data load
 * - Click node to highlight connected path
 * - Phase 12.1: LLM narrative explanation toggle
 */

import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  Controls,
  MiniMap,
  Background,
  useNodesState,
  useEdgesState,
  NodeMouseHandler,
  ReactFlowProvider,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';

import LineageNode from './LineageNode';
import LineageEdge from './LineageEdge';
import LineageNarrative from './LineageNarrative';
import { layoutLineageGraph } from '../../utils/lineageLayoutUtils';
import { lineageAPI } from '../../services/lineageApi';
import { useDarkMode } from '../../hooks/useDarkMode';
import type { LineageGraphResponse, LineageNarrative as LineageNarrativeType } from '../../types/lineage';

// Register custom node and edge types
const nodeTypes = { lineageNode: LineageNode };
const edgeTypes = { lineageEdge: LineageEdge };

interface LineageGraphProps {
  initialSql?: string;
  graphData?: LineageGraphResponse | null;
  onParseComplete?: (data: LineageGraphResponse) => void;
}

function LineageGraphInner({ initialSql, graphData, onParseComplete }: LineageGraphProps) {
  const { isDarkMode } = useDarkMode();
  const [sql, setSql] = useState(initialSql || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null);
  // Phase 12.1: Narrative explanation
  const [explainEnabled, setExplainEnabled] = useState(false);
  const [narrative, setNarrative] = useState<LineageNarrativeType | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);

  // Auto-fill and parse when initialSql prop changes
  useEffect(() => {
    if (initialSql && initialSql !== sql) {
      setSql(initialSql);
    }
  }, [initialSql]); // eslint-disable-line react-hooks/exhaustive-deps

  // Apply layout when graphData changes
  useEffect(() => {
    if (graphData && graphData.nodes.length > 0) {
      const { nodes: layoutNodes, edges: layoutEdges } = layoutLineageGraph(graphData, isDarkMode);
      setNodes(layoutNodes);
      setEdges(layoutEdges);
      // Phase 12.1: Set narrative from props if provided
      if (graphData.narrative) {
        setNarrative(graphData.narrative);
      }
    } else if (graphData && graphData.nodes.length === 0) {
      setNodes([]);
      setEdges([]);
    }
  }, [graphData, isDarkMode, setNodes, setEdges]);

  const handleParse = useCallback(async () => {
    if (!sql.trim()) return;

    setLoading(true);
    setError(null);
    setNarrative(null);

    // If explain is enabled, show narrative loading state
    if (explainEnabled) {
      setNarrativeLoading(true);
    }

    try {
      const result = await lineageAPI.parseSql(sql.trim(), undefined, explainEnabled);
      const { nodes: layoutNodes, edges: layoutEdges } = layoutLineageGraph(result, isDarkMode);
      setNodes(layoutNodes);
      setEdges(layoutEdges);

      // Set narrative if returned (Phase 12.1)
      if (result.narrative) {
        setNarrative(result.narrative);
      }

      onParseComplete?.(result);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to parse SQL';
      setError(msg);
      setNodes([]);
      setEdges([]);
    } finally {
      setLoading(false);
      setNarrativeLoading(false);
    }
  }, [sql, isDarkMode, explainEnabled, setNodes, setEdges, onParseComplete]);

  // Highlight connected nodes on click
  const handleNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    if (highlightedNodeId === node.id) {
      setHighlightedNodeId(null);
      // Reset all edges to default
      setEdges((eds) => eds.map((e) => ({ ...e, style: { ...e.style, opacity: 1 } })));
    } else {
      setHighlightedNodeId(node.id);
      // Dim edges not connected to this node
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          style: {
            ...e.style,
            opacity: e.source === node.id || e.target === node.id ? 1 : 0.2,
          },
        }))
      );
    }
  }, [highlightedNodeId, setEdges]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleParse();
    }
  }, [handleParse]);

  return (
    <div className="flex flex-col h-full">
      {/* SQL Input */}
      <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-3">
          <textarea
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Paste SQL query here to visualize data lineage..."
            className="flex-1 min-h-[80px] max-h-[160px] px-3 py-2 text-sm font-mono rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-y focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            data-testid="sql-input"
          />
          <div className="flex flex-col gap-2 self-end">
            <button
              onClick={handleParse}
              disabled={loading || !sql.trim()}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white text-sm font-bold transition-all duration-300 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 disabled:shadow-none active:scale-95"
              data-testid="parse-button"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Parsing...
                </span>
              ) : 'Parse'}
            </button>
            {/* Phase 12.1: Explain toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={explainEnabled}
                onChange={(e) => setExplainEnabled(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
              />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">
                AI Explain
              </span>
            </label>
          </div>
        </div>
        {error && (
          <div className="mt-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg" data-testid="error-message">
            {error}
          </div>
        )}
        <p className="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
          Ctrl+Enter to parse. Supports SELECT queries with JOINs, aggregations, and expressions.
          {explainEnabled && <span className="text-indigo-500"> AI explanation enabled.</span>}
        </p>
      </div>

      {/* Phase 12.1: Narrative Section */}
      {(narrative || narrativeLoading) && (
        <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700">
          <LineageNarrative narrative={narrative} isLoading={narrativeLoading} />
        </div>
      )}

      {/* Graph Area */}
      <div className="flex-1 min-h-[300px]" data-testid="graph-container">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.3}
            maxZoom={2}
            className="bg-gray-50/50 dark:bg-gray-900/50"
          >
            <Controls className="!rounded-xl !shadow-lg !border-gray-200 dark:!border-gray-700" />
            <MiniMap
              className="!rounded-xl !shadow-lg !border-gray-200 dark:!border-gray-700"
              nodeColor={(node) => {
                const nodeType = node.data?.node_type;
                if (nodeType === 'source_table') return '#3b82f6';
                if (nodeType === 'transformation') return '#a855f7';
                if (nodeType === 'output_column') return '#22c55e';
                return '#6366f1';
              }}
            />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color={isDarkMode ? '#374151' : '#e5e7eb'} />
          </ReactFlow>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-3">🔍</div>
              <p className="text-sm font-medium">
                {loading ? 'Parsing SQL...' : 'Enter a SQL query above to visualize its data lineage'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function LineageGraph(props: LineageGraphProps) {
  return (
    <ReactFlowProvider>
      <LineageGraphInner {...props} />
    </ReactFlowProvider>
  );
}
