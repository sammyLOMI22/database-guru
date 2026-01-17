import { useState } from 'react';
import { X } from 'lucide-react';
import SchemaPanel from './SchemaPanel';
import HistoryPanel from './HistoryPanel';
import ConnectionsPanel from './ConnectionsPanel';

interface SidebarProps {
  onClose: () => void;
  onSelectQuery?: (question: string) => void;
  onConnectionSelect?: (connectionId: number) => void;
}

type Tab = 'connections' | 'schema' | 'history';

export default function Sidebar({ onClose, onSelectQuery, onConnectionSelect }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<Tab>('connections');

  return (
    <aside className="w-80 glass-panel border-r border-white/10 flex flex-col transition-all duration-500 relative z-20">
      {/* Header */}
      <div className="p-5 border-b border-white/5">
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
                  ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 shadow-sm'
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
      <div className="flex-1 overflow-hidden relative">
        <div className="absolute inset-0 overflow-y-auto px-2 py-4 custom-scrollbar">
          {activeTab === 'connections' && (
            <ConnectionsPanel
              onConnectionSelect={onConnectionSelect || (() => { })}
            />
          )}
          {activeTab === 'schema' && <SchemaPanel />}
          {activeTab === 'history' && (
            <HistoryPanel onSelectQuery={onSelectQuery || (() => { })} />
          )}
        </div>
      </div>
    </aside>
  );
}
