import React, { useState } from 'react';
import { Wrench, BarChart3, FolderOpen, Zap } from 'lucide-react';
import { ToolsOverview } from './ToolsOverview';
import { ToolDirectory } from './ToolDirectory';
import { ToolUsageStats } from './ToolUsageStats';

type TabType = 'overview' | 'directory' | 'usage';

interface Tab {
  key: TabType;
  label: string;
  icon: React.ReactNode;
  description: string;
}

/**
 * Main panel for Tool-Using Agent management and monitoring.
 *
 * Provides 3 views:
 * - Overview: Summary stats and quick actions
 * - Tool Directory: Browse all 10 tools with descriptions
 * - Usage Stats: Per-tool execution metrics and charts
 *
 * Part of Phase 3.1: Tool-Using Agent Implementation
 */
export const ToolsPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const tabs: Tab[] = [
    {
      key: 'overview',
      label: 'Overview',
      icon: <Zap className="w-4 h-4" />,
      description:
        'Summary of tool execution statistics and quick actions',
    },
    {
      key: 'directory',
      label: 'Tool Directory',
      icon: <FolderOpen className="w-4 h-4" />,
      description:
        'Browse all 10 specialized tools for schema exploration and query validation',
    },
    {
      key: 'usage',
      label: 'Usage Stats',
      icon: <BarChart3 className="w-4 h-4" />,
      description:
        'Detailed per-tool execution metrics, success rates, and cache performance',
    },
  ];

  const currentTab = tabs.find((t) => t.key === activeTab);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Wrench className="w-6 h-6 text-orange-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Tool-Using Agent</h2>
            <p className="text-gray-600 mt-1">
              10 specialized tools for schema exploration, data sampling, and query validation
            </p>
          </div>
        </div>
      </div>

      {/* Main Content Card */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex overflow-x-auto" aria-label="Tools tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? 'border-orange-500 text-orange-600 bg-orange-50'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                }`}
                aria-current={activeTab === tab.key ? 'page' : undefined}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Description */}
        <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
          <p className="text-sm text-gray-600">{currentTab?.description}</p>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && <ToolsOverview />}
          {activeTab === 'directory' && <ToolDirectory />}
          {activeTab === 'usage' && <ToolUsageStats />}
        </div>
      </div>
    </div>
  );
};

export default ToolsPanel;
