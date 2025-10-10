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
    <aside className="w-80 bg-white border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Database</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors md:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1">
          <button
            onClick={() => setActiveTab('connections')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded-lg transition-colors ${
              activeTab === 'connections'
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Connections
          </button>
          <button
            onClick={() => setActiveTab('schema')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded-lg transition-colors ${
              activeTab === 'schema'
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Schema
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded-lg transition-colors ${
              activeTab === 'history'
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            History
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'connections' && (
          <ConnectionsPanel
            onConnectionSelect={onConnectionSelect || (() => {})}
          />
        )}
        {activeTab === 'schema' && <SchemaPanel />}
        {activeTab === 'history' && (
          <HistoryPanel onSelectQuery={onSelectQuery || (() => {})} />
        )}
      </div>
    </aside>
  );
}
