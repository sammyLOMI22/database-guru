import { useState, useEffect } from 'react';
import { X, Database } from 'lucide-react';
import SchemaExplorer from './SchemaExplorer';
import HistoryPanel from './HistoryPanel';
import ConnectionsPanel from './ConnectionsPanel';
import { connectionsAPI } from '../services/api';
import type { DatabaseConnection } from '../types/api';

interface SidebarProps {
  onClose: () => void;
  onSelectQuery?: (question: string) => void;
  onConnectionSelect?: (connectionId: number) => void;
}

type Tab = 'connections' | 'schema' | 'history';

export default function Sidebar({ onClose, onSelectQuery, onConnectionSelect }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<Tab>('connections');
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [selectedConnId, setSelectedConnId] = useState<number | null>(null);

  useEffect(() => {
    const loadConnections = async () => {
      try {
        const data = await connectionsAPI.listConnections();
        setConnections(data.connections);
        const active = data.connections.find((c: any) => c.is_active);
        if (active) setSelectedConnId(active.id);
        else if (data.connections.length > 0) setSelectedConnId(data.connections[0].id);
      } catch (error) {
        console.error('Failed to load connections in sidebar:', error);
      }
    };
    loadConnections();
  }, []);

  return (
    <aside className="w-[450px] flex-shrink-0 glass-panel border-r border-white/10 flex flex-col transition-all duration-500 relative z-20 overflow-hidden shadow-[20px_0_50px_rgba(0,0,0,0.3)]">
      {/* Header */}
      <div className="p-6 border-b border-white/5 bg-white/5 dark:bg-black/20">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-gray-900 dark:text-white flex items-center gap-3">
            <div className="relative">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-blue-500 animate-ping opacity-20" />
            </div>
            Workspace
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-all md:hidden glass-panel rounded-xl hover:scale-110 active:scale-95"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs - Premium Segmented Control */}
        <div className="flex p-1.5 glass-panel rounded-2xl border-white/10 bg-black/5 dark:bg-white/5 shadow-inner">
          {[
            { id: 'connections', label: 'DBs' },
            { id: 'schema', label: 'Schema' },
            { id: 'history', label: 'History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`
                flex-1 px-2 py-2.5 text-xs font-black uppercase tracking-widest rounded-xl transition-all duration-300
                ${activeTab === tab.id
                  ? 'glass-card bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-[0_10px_20px_rgba(0,0,0,0.1)] dark:shadow-[0_10_20px_rgba(0,0,0,0.3)] scale-105 z-10'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/5 dark:hover:bg-white/5'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden relative flex flex-col">
        {activeTab === 'schema' && connections.length > 0 && (
          <div className="p-4 border-b border-white/5 bg-black/5 dark:bg-white/5 flex gap-2 overflow-x-auto custom-scrollbar no-scrollbar">
            {connections.map((conn) => (
              <button
                key={conn.id}
                onClick={() => setSelectedConnId(conn.id)}
                className={`flex-shrink-0 px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-[0.15em] transition-all border ${selectedConnId === conn.id
                  ? 'bg-blue-600 border-blue-500 text-white shadow-[0_5px_15px_rgba(59,130,246,0.3)]'
                  : 'glass-panel bg-white/5 border-white/5 text-gray-500 hover:border-white/20 hover:text-gray-300'
                  }`}
              >
                {conn.name}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-2 py-4 custom-scrollbar">
          {activeTab === 'connections' && (
            <ConnectionsPanel
              onConnectionSelect={(id) => {
                setSelectedConnId(id);
                onConnectionSelect?.(id);
              }}
            />
          )}
          {activeTab === 'schema' && (
            selectedConnId ? (
              <SchemaExplorer
                connectionId={selectedConnId}
                connectionName={connections.find(c => c.id === selectedConnId)?.name}
                compact={true}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-50 py-20">
                <Database className="w-8 h-8 mb-3" />
                <p className="text-xs font-black uppercase tracking-widest text-center">Select a database to explore schema</p>
              </div>
            )
          )}
          {activeTab === 'history' && (
            <HistoryPanel onSelectQuery={onSelectQuery || (() => { })} />
          )}
        </div>
      </div>
    </aside>
  );
}
