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
    <aside className="w-80 glass-panel border-r border-white/10 flex flex-col transition-all duration-500 relative z-20 overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/5 bg-white/5 dark:bg-black/10">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            Workspace
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors md:hidden glass-panel rounded-lg"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs - Premium Segmented Control */}
        <div className="flex p-1 glass-panel rounded-xl border-white/5 bg-black/5 dark:bg-white/5">
          {[
            { id: 'connections', label: 'DBs' },
            { id: 'schema', label: 'Schema' },
            { id: 'history', label: 'History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`
                flex-1 px-2 py-2 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all duration-300
                ${activeTab === tab.id
                  ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-xl'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
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
                className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all border ${selectedConnId === conn.id
                  ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-500/20'
                  : 'bg-white/5 border-white/5 text-gray-500 hover:border-white/10'
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
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-50 py-20">
                <Database className="w-8 h-8 mb-3" />
                <p className="text-[10px] font-black uppercase tracking-widest text-center">Select a database to explore schema</p>
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
