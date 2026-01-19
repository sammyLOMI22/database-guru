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
    <div className="flex flex-col h-full w-full bg-transparent overflow-hidden">
      {/* Header with View Mode Toggle */}
      <div className="px-6 py-6 border-b border-white/5 relative z-20">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl glass-panel flex items-center justify-center text-blue-500 shadow-lg shadow-blue-500/10">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-black uppercase tracking-tight text-gray-900 dark:text-white">Schema Explorer</h2>
              <p className="text-xs font-black uppercase tracking-widest text-gray-400 dark:text-gray-500">Visualize and compare structures</p>
            </div>
          </div>
          <button
            onClick={loadConnections}
            className="p-2.5 glass-panel rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:scale-110 active:scale-95 transition-all"
            title="Refresh connections"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* View Mode Tabs - Premium Segmented Control */}
        <div className="flex p-1 glass-panel rounded-2xl border-white/10 bg-black/5 dark:bg-white/5 max-w-2xl">
          {[
            { id: 'explore', label: 'Explore', icon: List, color: 'blue' },
            { id: 'compare', label: 'Compare', icon: GitCompare, color: 'purple', disabled: connections.length < 2 },
            { id: 'diagram', label: 'ER Diagram', icon: Share2, color: 'emerald' },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = viewMode === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setViewMode(tab.id as ViewMode)}
                disabled={tab.disabled}
                className={`
                  flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-300
                  ${isActive
                    ? `bg-white dark:bg-gray-800 text-${tab.color}-600 dark:text-${tab.color}-400 shadow-xl`
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                  }
                  ${tab.disabled ? 'opacity-30 cursor-not-allowed' : ''}
                `}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? `text-${tab.color}-500` : 'text-gray-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden flex min-h-0 relative z-10">
        {viewMode === 'diagram' ? (
          <>
            {/* Connection Selector Sidebar for Diagram */}
            <div className="w-72 flex-shrink-0 border-r border-white/5 glass-panel overflow-y-auto transition-all animate-slideInLeft p-4 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-400 dark:text-gray-500 ml-1">
                Select Database
              </h3>
              <div className="space-y-2">
                {connections.map((conn) => (
                  <button
                    key={conn.id}
                    onClick={() => setSelectedConnectionId(conn.id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-300 border ${selectedConnectionId === conn.id
                      ? 'glass-card border-emerald-500/30 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400 font-bold shadow-lg shadow-emerald-500/5'
                      : 'border-transparent text-gray-700 dark:text-gray-300 hover:bg-white/5 hover:border-white/10'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${selectedConnectionId === conn.id ? 'bg-emerald-500/10' : 'bg-gray-100 dark:bg-gray-800'}`}>
                      <Database className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1 overflow-hidden">
                      <p className="text-xs font-black uppercase tracking-wider truncate block w-full">{conn.name}</p>
                      <p className="text-[11px] opacity-60 font-bold uppercase tracking-widest truncate block w-full">{conn.database_type}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* ER Diagram */}
            <div className="flex-1 h-full min-h-0 bg-gray-50/30 dark:bg-black/20">
              {selectedConnectionId ? (
                <ERDiagram connectionId={selectedConnectionId} />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400 animate-fadeIn">
                  <Share2 className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm font-black uppercase tracking-widest">Select structure to visualize</p>
                </div>
              )}
            </div>
          </>
        ) : viewMode === 'explore' ? (
          <>
            {/* Connection Selector Sidebar */}
            <div className="w-72 flex-shrink-0 border-r border-white/5 glass-panel overflow-y-auto transition-all animate-slideInLeft p-4 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-400 dark:text-gray-500 ml-1">
                Select Database
              </h3>
              <div className="space-y-2">
                {connections.map((conn) => (
                  <button
                    key={conn.id}
                    onClick={() => setSelectedConnectionId(conn.id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-300 border ${selectedConnectionId === conn.id
                      ? 'glass-card border-blue-500/30 bg-blue-500/5 text-blue-600 dark:text-blue-400 font-bold shadow-lg shadow-blue-500/5'
                      : 'border-transparent text-gray-700 dark:text-gray-300 hover:bg-white/5 hover:border-white/10'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${selectedConnectionId === conn.id ? 'bg-blue-500/10' : 'bg-gray-100 dark:bg-gray-800'}`}>
                      <Database className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-black uppercase tracking-wider truncate">{conn.name}</p>
                      <p className="text-xs opacity-60 font-bold uppercase">{conn.database_type}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Schema Explorer */}
            <div className="flex-1 h-full min-h-0 overflow-y-auto p-6 bg-gray-50/30 dark:bg-black/20 custom-scrollbar">
              {selectedConnectionId ? (
                <div className="max-w-[1600px] mx-auto animate-fadeIn">
                  <SchemaExplorer
                    connectionId={selectedConnectionId}
                    connectionName={
                      connections.find((c) => c.id === selectedConnectionId)?.name
                    }
                  />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500 animate-fadeIn">
                  <List className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm font-black uppercase tracking-widest">Select database to explore</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            {/* Comparison Connection Selector */}
            <div className="w-72 flex-shrink-0 border-r border-white/5 glass-panel overflow-y-auto transition-all animate-slideInLeft p-4 flex flex-col">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-400 dark:text-gray-500 ml-1 mb-1">
                Compare Structures
              </h3>
              <p className="text-xs font-bold text-purple-500 uppercase tracking-widest mb-4 ml-1">
                {compareConnectionIds.length} SELECTED
              </p>

              <div className="space-y-2 flex-1 overflow-y-auto custom-scrollbar pr-1">
                {connections.map((conn) => {
                  const isSelected = compareConnectionIds.includes(conn.id);
                  return (
                    <label
                      key={conn.id}
                      className={`w-full flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-300 border ${isSelected
                        ? 'glass-card border-purple-500/30 bg-purple-500/5 text-purple-600 dark:text-purple-400 font-bold shadow-lg shadow-purple-500/5'
                        : 'border-transparent text-gray-700 dark:text-gray-300 hover:bg-white/5 hover:border-white/10'
                        }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleCompareConnection(conn.id)}
                        className="hidden"
                      />
                      <div className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${isSelected ? 'bg-purple-600 border-purple-600' : 'border-white/20'}`}>
                        {isSelected && (
                          <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-black uppercase tracking-wider truncate">{conn.name}</p>
                        <p className="text-xs opacity-60 font-bold uppercase">{conn.database_type}</p>
                      </div>
                    </label>
                  );
                })}
              </div>

              {/* Quick actions */}
              <div className="mt-4 pt-4 border-t border-white/5 flex gap-4 ml-1">
                <button
                  onClick={() => setCompareConnectionIds(connections.map((c) => c.id))}
                  className="text-xs font-black uppercase tracking-widest text-purple-500 hover:text-purple-600 transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={() => setCompareConnectionIds([])}
                  className="text-xs font-black uppercase tracking-widest text-gray-500 hover:text-gray-700 transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Schema Comparison */}
            <div className="flex-1 h-full min-h-0 overflow-y-auto p-6 bg-gray-50/30 dark:bg-black/20 custom-scrollbar">
              {compareConnectionIds.length >= 2 ? (
                <div className="max-w-[1600px] mx-auto animate-fadeIn">
                  <SchemaComparison
                    connectionIds={compareConnectionIds}
                    connectionNames={Object.fromEntries(
                      connections.map((c) => [c.id, c.name])
                    )}
                  />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500 animate-fadeIn">
                  <GitCompare className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm font-black uppercase tracking-widest">Select at least 2 databases</p>
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
