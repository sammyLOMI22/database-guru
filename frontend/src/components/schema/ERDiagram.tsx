/**
 * ERDiagram - Main container for the ER diagram visualization.
 *
 * Uses React Flow to render an interactive entity-relationship diagram
 * with tables as nodes and foreign keys as edges.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  NodeMouseHandler,
  ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { schemaAPI } from '../../services/api';
import type { SchemaExploreResponse } from '../../types/api';
import type { ERTableNode, ERRelationshipEdge, LayoutDirection } from '../../types/erDiagram';
import {
  transformSchemaToNodes,
  transformRelationshipsToEdges,
  calculateDagreLayout,
  applySearchFilter,
  inferRelationships,
  toggleNodeExpansion,
  expandAllNodes,
  collapseAllNodes,
} from '../../utils/erDiagramUtils';
import { useDarkMode } from '../../hooks/useDarkMode';

import TableNode from './TableNode';
import RelationshipEdge from './RelationshipEdge';
import ERDiagramControls from './ERDiagramControls';
import ERDiagramSearch from './ERDiagramSearch';

// Custom node and edge types
const nodeTypes = {
  tableNode: TableNode,
};

const edgeTypes = {
  relationshipEdge: RelationshipEdge,
};

interface ERDiagramProps {
  /** Database connection ID */
  connectionId: number;
  /** Optional connection IDs for multi-database view */
  connectionIds?: number[];
}

const ERDiagramInner: React.FC<ERDiagramProps> = ({
  connectionId,
  connectionIds,
}) => {
  const { isDarkMode } = useDarkMode();

  // Schema data state
  const [schemas, setSchemas] = useState<SchemaExploreResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // React Flow state with proper typing
  const [nodes, setNodes, onNodesChange] = useNodesState<ERTableNode['data']>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<ERRelationshipEdge['data']>([]);

  // UI state
  const [searchQuery, setSearchQuery] = useState('');
  const [layoutDirection, setLayoutDirection] = useState<LayoutDirection>('TB');
  const [showInferred, setShowInferred] = useState(true);

  // Get all connection IDs to load
  const allConnectionIds = useMemo(() => {
    if (connectionIds && connectionIds.length > 0) {
      return connectionIds;
    }
    return [connectionId];
  }, [connectionId, connectionIds]);

  // Load schema data
  useEffect(() => {
    const loadSchemas = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const schemaPromises = allConnectionIds.map((id) =>
          schemaAPI.exploreSchema(id)
        );
        const loadedSchemas = await Promise.all(schemaPromises);
        setSchemas(loadedSchemas);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load schema');
      } finally {
        setIsLoading(false);
      }
    };

    loadSchemas();
  }, [allConnectionIds]);

  // Transform schema to nodes and edges when data changes
  useEffect(() => {
    if (schemas.length === 0) return;

    // Create nodes for all schemas
    let allNodes: ERTableNode[] = [];
    let allEdges: ERRelationshipEdge[] = [];

    schemas.forEach((schema, index) => {
      const schemaNodes = transformSchemaToNodes(schema, index);
      const schemaEdges = transformRelationshipsToEdges(
        schema.tables,
        schema.connection_id
      );

      allNodes = [...allNodes, ...schemaNodes];
      allEdges = [...allEdges, ...schemaEdges];

      // Add inferred relationships if enabled
      if (showInferred) {
        const inferred = inferRelationships(
          schema.tables,
          schema.connection_id,
          schemaEdges
        );
        allEdges = [...allEdges, ...inferred];
      }
    });

    // Apply layout
    const layoutedNodes = calculateDagreLayout(allNodes, allEdges, {
      direction: layoutDirection,
      nodeSpacingX: 100,
      nodeSpacingY: 80,
      nodePadding: 20,
    });

    // Type assertion needed as React Flow's generic types don't perfectly align with our custom types
    setNodes(layoutedNodes as unknown as typeof nodes);
    setEdges(allEdges as unknown as typeof edges);
  }, [schemas, layoutDirection, showInferred, setNodes, setEdges]);

  // Apply search filter
  // NOTE: We intentionally omit nodes/edges from dependencies to avoid infinite loops.
  // The effect reads current nodes/edges state but should only re-run when searchQuery changes.
  // This is a controlled violation of exhaustive-deps for performance reasons.
  useEffect(() => {
    if (nodes.length === 0) return;

    const { nodes: filteredNodes, edges: filteredEdges } = applySearchFilter(
      nodes as ERTableNode[],
      edges as ERRelationshipEdge[],
      searchQuery
    );

    // Only update if search actually changed something to prevent unnecessary re-renders
    const hasHighlightChanges = filteredNodes.some(
      (n, i) =>
        n.data?.isHighlighted !== (nodes[i] as ERTableNode)?.data?.isHighlighted ||
        n.data?.isDimmed !== (nodes[i] as ERTableNode)?.data?.isDimmed
    );

    if (hasHighlightChanges) {
      setNodes(filteredNodes as unknown as typeof nodes);
      setEdges(filteredEdges as unknown as typeof edges);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  // Handle node click to toggle expansion
  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      setNodes((nds) => toggleNodeExpansion(nds as ERTableNode[], node.id) as unknown as typeof nds);
    },
    [setNodes]
  );

  // Handle layout change
  const handleLayoutChange = useCallback((direction: LayoutDirection) => {
    setLayoutDirection(direction);
  }, []);

  // Handle expand/collapse all
  const handleExpandAll = useCallback(() => {
    setNodes((nds) => expandAllNodes(nds as ERTableNode[]) as unknown as typeof nds);
  }, [setNodes]);

  const handleCollapseAll = useCallback(() => {
    setNodes((nds) => collapseAllNodes(nds as ERTableNode[]) as unknown as typeof nds);
  }, [setNodes]);

  // Handle fit view (exposed via ref if needed)
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const handleFitView = useCallback(() => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.2 });
    }
  }, [reactFlowInstance]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>
            Loading schema...
          </span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div
          className={`
            p-4 rounded-lg border
            ${isDarkMode ? 'bg-red-900/20 border-red-800 text-red-400' : 'bg-red-50 border-red-200 text-red-600'}
          `}
        >
          <p className="font-medium">Failed to load schema</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (schemas.length === 0 || nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>
          No tables found in schema
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col">
      {/* Toolbar */}
      <div
        className={`
          flex items-center justify-between px-4 py-2 border-b
          ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'}
        `}
      >
        <ERDiagramSearch
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        <ERDiagramControls
          layoutDirection={layoutDirection}
          onLayoutChange={handleLayoutChange}
          showInferred={showInferred}
          onShowInferredChange={setShowInferred}
          onExpandAll={handleExpandAll}
          onCollapseAll={handleCollapseAll}
          onFitView={handleFitView}
        />
      </div>

      {/* Diagram - React Flow requires explicit dimensions */}
      <div className="flex-1 w-full relative">
        <div className="absolute inset-0">
          <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onInit={setReactFlowInstance}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
          defaultEdgeOptions={{
            type: 'relationshipEdge',
          }}
        >
          <Background
            color={isDarkMode ? '#374151' : '#E5E7EB'}
            gap={20}
            size={1}
          />
          <Controls
            className={isDarkMode ? 'react-flow-controls-dark' : ''}
            showInteractive={false}
          />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as any;
              return data?.isHighlighted
                ? '#FBBF24'
                : data?.isDimmed
                ? '#9CA3AF'
                : '#3B82F6';
            }}
            maskColor={isDarkMode ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.8)'}
            className={isDarkMode ? 'react-flow-minimap-dark' : ''}
          />
        </ReactFlow>
        </div>
      </div>

      {/* Legend */}
      <div
        className={`
          flex items-center gap-4 px-4 py-2 text-xs border-t
          ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-gray-50 border-gray-200 text-gray-500'}
        `}
      >
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-gray-400" />
          <span>Explicit FK</span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className="w-4 h-0.5 bg-gray-400"
            style={{ borderTop: '2px dashed' }}
          />
          <span>Inferred</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-yellow-500">●</span>
          <span>PK</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-purple-500">●</span>
          <span>FK</span>
        </div>
        <div className="ml-auto">
          {nodes.length} tables · {edges.length} relationships
        </div>
      </div>
    </div>
  );
};

/**
 * ERDiagram with ReactFlowProvider wrapper.
 */
const ERDiagram: React.FC<ERDiagramProps> = (props) => {
  return (
    <ReactFlowProvider>
      <ERDiagramInner {...props} />
    </ReactFlowProvider>
  );
};

export default ERDiagram;
