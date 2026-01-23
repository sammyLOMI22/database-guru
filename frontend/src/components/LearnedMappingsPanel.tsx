import React, { useState } from 'react';
import { Database, Table, AlertCircle, BarChart3, BookOpen } from 'lucide-react';
import { ColumnMappingsList } from './ColumnMappingsList';
import { TableMappingsList } from './TableMappingsList';
import { ResultPatternsList } from './ResultPatternsList';
import { MappingStatsDisplay } from './MappingStatsDisplay';

interface LearnedMappingsPanelProps {
  connectionName?: string;
}

type TabType = 'columns' | 'tables' | 'patterns' | 'stats';

export const LearnedMappingsPanel: React.FC<LearnedMappingsPanelProps> = ({
  connectionName,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('columns');

  const tabs: { key: TabType; label: string; icon: React.ReactNode; description: string; color: string }[] = [
    {
      key: 'columns',
      label: 'Columns',
      icon: <Database className="w-3.5 h-3.5" />,
      description: 'Learned column name corrections and aliases',
      color: 'blue',
    },
    {
      key: 'tables',
      label: 'Tables',
      icon: <Table className="w-3.5 h-3.5" />,
      description: 'Learned table name corrections and aliases',
      color: 'emerald',
    },
    {
      key: 'patterns',
      label: 'Patterns',
      icon: <AlertCircle className="w-3.5 h-3.5" />,
      description: 'Learned validation patterns for common issues',
      color: 'purple',
    },
    {
      key: 'stats',
      label: 'Stats',
      icon: <BarChart3 className="w-3.5 h-3.5" />,
      description: 'Overall mapping usage and effectiveness metrics',
      color: 'amber',
    },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl glass-panel flex items-center justify-center text-indigo-500">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white">Learned Patterns</h2>
            <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">
              Mappings and patterns learned from your feedback
            </p>
          </div>
        </div>
        {connectionName && (
          <span className="text-[11px] font-black uppercase tracking-[0.15em] px-3 py-1.5 rounded-xl glass-card text-blue-600 dark:text-blue-400 border-blue-500/20">
            {connectionName}
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="glass-panel rounded-2xl border-white/10 overflow-hidden">
        {/* Tab Headers */}
        <div className="border-b border-white/5 p-2 bg-black/5 dark:bg-white/5">
          <nav className="flex gap-2" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-[11px] font-black uppercase tracking-[0.15em]
                  transition-all hover:scale-[1.02] active:scale-[0.98]
                  ${
                    activeTab === tab.key
                      ? 'glass-card bg-gradient-to-r from-indigo-500/10 via-transparent to-purple-500/5 text-indigo-600 dark:text-indigo-400 border-indigo-500/20'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }
                `}
                aria-current={activeTab === tab.key ? 'page' : undefined}
              >
                {tab.icon}
                <span className="whitespace-nowrap">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Description */}
        <div className="px-6 py-3 border-b border-white/5 bg-gradient-to-r from-indigo-500/5 via-transparent to-transparent">
          <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400">
            {tabs.find((t) => t.key === activeTab)?.description}
          </p>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'columns' && <ColumnMappingsList connectionName={connectionName} />}
          {activeTab === 'tables' && <TableMappingsList connectionName={connectionName} />}
          {activeTab === 'patterns' && <ResultPatternsList />}
          {activeTab === 'stats' && <MappingStatsDisplay connectionName={connectionName} />}
        </div>
      </div>
    </div>
  );
};
