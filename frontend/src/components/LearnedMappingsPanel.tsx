import React, { useState } from 'react';
import { Database, Table, AlertCircle, BarChart3 } from 'lucide-react';
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

  const tabs: { key: TabType; label: string; icon: React.ReactNode; description: string }[] = [
    {
      key: 'columns',
      label: 'Column Mappings',
      icon: <Database className="w-4 h-4" />,
      description: 'Learned column name corrections and aliases',
    },
    {
      key: 'tables',
      label: 'Table Mappings',
      icon: <Table className="w-4 h-4" />,
      description: 'Learned table name corrections and aliases',
    },
    {
      key: 'patterns',
      label: 'Result Patterns',
      icon: <AlertCircle className="w-4 h-4" />,
      description: 'Learned validation patterns for common issues',
    },
    {
      key: 'stats',
      label: 'Statistics',
      icon: <BarChart3 className="w-4 h-4" />,
      description: 'Overall mapping usage and effectiveness metrics',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Learned Patterns</h2>
        <p className="text-gray-600 mt-1">
          Column/table mappings and result validation patterns learned from your feedback
        </p>
        {connectionName && (
          <p className="text-sm text-blue-600 mt-2">
            Filtered by connection: <span className="font-semibold">{connectionName}</span>
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {/* Tab Headers */}
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px overflow-x-auto" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  group relative min-w-0 flex-1 overflow-hidden py-4 px-4 text-sm font-medium text-center
                  hover:bg-gray-50 transition-colors
                  ${
                    activeTab === tab.key
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }
                `}
                aria-current={activeTab === tab.key ? 'page' : undefined}
              >
                <span className="flex items-center justify-center gap-2">
                  {tab.icon}
                  <span className="whitespace-nowrap">{tab.label}</span>
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Description */}
        <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
          <p className="text-sm text-gray-600">
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
