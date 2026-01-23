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
      label: 'Directory',
      icon: <FolderOpen className="w-4 h-4" />,
      description:
        'Browse all 10 specialized tools for schema exploration and query validation',
    },
    {
      key: 'usage',
      label: 'Usage',
      icon: <BarChart3 className="w-4 h-4" />,
      description:
        'Detailed per-tool execution metrics, success rates, and cache performance',
    },
  ];

  const currentTab = tabs.find((t) => t.key === activeTab);

  return (
    <div className="max-w-[1600px] mx-auto animate-fadeIn">
      {/* Main Glass Container */}
      <div className="glass-panel rounded-[2rem] shadow-2xl border-white/10 overflow-hidden">
        {/* Header */}
        <div className="border-b border-white/5 px-8 py-8 bg-white/5 dark:bg-black/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-5">
              <div className="w-14 h-14 rounded-2xl glass-panel flex items-center justify-center text-orange-500 shadow-xl shadow-orange-500/10">
                <Wrench className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-3xl font-black uppercase tracking-tight text-gray-900 dark:text-white">
                  Tool Agent
                </h2>
                <p className="text-[11px] font-black uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
                  Schema Exploration & Query Validation
                </p>
              </div>
            </div>
          </div>

          {/* Tab Navigation - Segmented Control */}
          <div className="mt-6 flex p-1.5 glass-panel rounded-2xl border-white/10 bg-black/5 dark:bg-white/5 shadow-inner max-w-md">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-300
                  ${activeTab === tab.key
                    ? 'glass-card bg-white dark:bg-gray-800 text-orange-600 dark:text-orange-400 shadow-[0_10px_20px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_20px_rgba(0,0,0,0.3)] scale-105 z-10'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/5'
                  }
                `}
                aria-current={activeTab === tab.key ? 'page' : undefined}
              >
                {tab.icon}
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Description */}
        <div className="px-8 py-4 border-b border-white/5 bg-black/5 dark:bg-white/5">
          <p className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
            {currentTab?.description}
          </p>
        </div>

        {/* Tab Content */}
        <div className="p-8">
          {activeTab === 'overview' && <ToolsOverview />}
          {activeTab === 'directory' && <ToolDirectory />}
          {activeTab === 'usage' && <ToolUsageStats />}
        </div>
      </div>
    </div>
  );
};

export default ToolsPanel;
