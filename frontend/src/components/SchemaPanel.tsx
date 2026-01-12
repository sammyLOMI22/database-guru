import { useState, useEffect } from 'react';
import { Database, GitCompare, List, RefreshCw, Share2 } from 'lucide-react';
import { connectionsAPI } from '../services/api';
import type { DatabaseConnection } from '../types/api';
import SchemaExplorer from './SchemaExplorer';
import SchemaComparison from './SchemaComparison';
import ERDiagram from './schema/ERDiagram';

type ViewMode = 'explore' | 'compare' | 'diagram';

export default function SchemaPanel() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('explore');
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [compareConnectionIds, setCompareConnectionIds] = useState<number[]>([]);

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    setLoading(true);
    try {
      const data = await connectionsAPI.listConnections();
      setConnections(data.connections);
      // Auto-select first connection for exploration
      if (data.connections.length > 0 && !selectedConnectionId) {
        setSelectedConnectionId(data.connections[0].id);
      }
      // Auto-select all for comparison if we have 2+
      if (data.connections.length >= 2 && compareConnectionIds.length === 0) {
        setCompareConnectionIds(data.connections.map((c) => c.id));
      }
    } catch (error) {
      console.error('Failed to load connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleCompareConnection = (id: number) => {
    setCompareConnectionIds((prev) =>
      prev.includes(id) ? prev.filter((cid) => cid !== id) : [...prev, id]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-6 h-6 animate-spin text-gray-400 dark:text-gray-500" />
        <span className="ml-2 text-gray-500 dark:text-gray-400">Loading connections...</span>
      </div>
    );
  }

  if (connections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
        <Database className="w-12 h-12 mb-4 opacity-30" />
        <p className="text-lg font-medium text-gray-900 dark:text-white">No Database Connections</p>
        <p className="text-sm mt-2">Add a database connection to explore schemas.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with View Mode Toggle */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 transition-colors">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Schema Explorer</h2>
          <button
            onClick={loadConnections}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh connections"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {/* View Mode Tabs */}
        <div className="mt-4 flex gap-2">
          <button
            onClick={() => setViewMode('explore')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${viewMode === 'explore'
                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-transparent'
              }`}
          >
            <List className="w-4 h-4" />
            Explore Single Database
          </button>
          <button
            onClick={() => setViewMode('compare')}
            disabled={connections.length < 2}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${viewMode === 'compare'
                ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-transparent'
              } ${connections.length < 2 ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <GitCompare className="w-4 h-4" />
            Compare Databases
            {connections.length < 2 && (
              <span className="text-xs ml-1">(need 2+)</span>
            )}
          </button>
          <button
            onClick={() => setViewMode('diagram')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${viewMode === 'diagram'
                ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-transparent'
              }`}
          >
            <Share2 className="w-4 h-4" />
            ER Diagram
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden flex">
        {viewMode === 'diagram' ? (
          <>
            {/* Connection Selector Sidebar for Diagram */}
            <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 overflow-y-auto transition-colors">
              <div className="p-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Select Database
                </h3>
                <div className="space-y-2">
                  {connections.map((conn) => (
                    <button
                      key={conn.id}
                      onClick={() => setSelectedConnectionId(conn.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${selectedConnectionId === conn.id
                          ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'
                          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                    >
                      <Database className="w-4 h-4 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{conn.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{conn.database_type}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* ER Diagram */}
            <div className="flex-1 overflow-hidden">
              {selectedConnectionId ? (
                <ERDiagram connectionId={selectedConnectionId} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                  Select a database to view its ER diagram
                </div>
              )}
            </div>
          </>
        ) : viewMode === 'explore' ? (
          <>
            {/* Connection Selector Sidebar */}
            <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 overflow-y-auto transition-colors">
              <div className="p-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Select Database
                </h3>
                <div className="space-y-2">
                  {connections.map((conn) => (
                    <button
                      key={conn.id}
                      onClick={() => setSelectedConnectionId(conn.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${selectedConnectionId === conn.id
                          ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                    >
                      <Database className="w-4 h-4 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{conn.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{conn.database_type}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Schema Explorer */}
            <div className="flex-1 overflow-y-auto p-6">
              {selectedConnectionId ? (
                <SchemaExplorer
                  connectionId={selectedConnectionId}
                  connectionName={
                    connections.find((c) => c.id === selectedConnectionId)?.name
                  }
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  Select a database to explore its schema
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            {/* Comparison Connection Selector */}
            <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 overflow-y-auto transition-colors">
              <div className="p-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Select Databases to Compare
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                  {compareConnectionIds.length} selected
                </p>
                <div className="space-y-2">
                  {connections.map((conn) => {
                    const isSelected = compareConnectionIds.includes(conn.id);
                    return (
                      <label
                        key={conn.id}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${isSelected
                            ? 'bg-purple-100 dark:bg-purple-900/40 border border-purple-200 dark:border-purple-800'
                            : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                          }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleCompareConnection(conn.id)}
                          className="rounded border-gray-300 dark:border-gray-600 text-purple-600 focus:ring-purple-500 bg-white dark:bg-gray-900"
                        />
                        <Database className="w-4 h-4 flex-shrink-0 text-gray-400 dark:text-gray-500" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{conn.name}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{conn.database_type}</p>
                        </div>
                      </label>
                    );
                  })}
                </div>

                {/* Quick actions */}
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => setCompareConnectionIds(connections.map((c) => c.id))}
                    className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 transition-colors"
                  >
                    Select All
                  </button>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <button
                    onClick={() => setCompareConnectionIds([])}
                    className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>

            {/* Schema Comparison */}
            <div className="flex-1 overflow-y-auto p-6">
              {compareConnectionIds.length >= 2 ? (
                <SchemaComparison
                  connectionIds={compareConnectionIds}
                  connectionNames={Object.fromEntries(
                    connections.map((c) => [c.id, c.name])
                  )}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <GitCompare className="w-12 h-12 mb-4 opacity-50" />
                  <p className="text-lg font-medium">Select at least 2 databases</p>
                  <p className="text-sm mt-2">
                    Choose databases from the sidebar to compare their schemas
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export { SchemaPanel };
