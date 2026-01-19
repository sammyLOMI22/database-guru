import React, { useState } from 'react';
import { Database, BarChart3, Clock, Zap } from 'lucide-react';
import { CacheOverview } from './CacheOverview';
import { CacheStatistics } from './CacheStatistics';
import { RecentCachedQueries } from './RecentCachedQueries';

type TabType = 'overview' | 'statistics' | 'recent';

interface Tab {
  key: TabType;
  label: string;
  icon: React.ReactNode;
  description: string;
}

/**
 * Main panel for Semantic Cache management and monitoring.
 *
 * Provides 3 views:
 * - Overview: Summary stats and quick actions
 * - Statistics: Distribution charts and hit rates
 * - Recent Queries: Browse cached queries
 *
 * Part of Phase 3.3: Semantic Caching UI Components
 */
export const SemanticCachePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const tabs: Tab[] = [
    {
      key: 'overview',
      label: 'Overview',
      icon: <Zap className="w-4 h-4" />,
      description:
        'Summary of cache performance, hit rates, and quick actions',
    },
    {
      key: 'statistics',
      label: 'Stats',
      icon: <BarChart3 className="w-4 h-4" />,
      description:
        'Cache hit distribution, embedding metrics, and performance breakdown',
    },
    {
      key: 'recent',
      label: 'Recent',
      icon: <Clock className="w-4 h-4" />,
      description:
        'Browse recently cached queries with hit counts and metadata',
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
              <div className="w-14 h-14 rounded-2xl glass-panel flex items-center justify-center text-amber-500 shadow-xl shadow-amber-500/10">
                <Database className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-3xl font-black uppercase tracking-tight text-gray-900 dark:text-white">
                  Semantic Cache
                </h2>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  Intelligent Similarity Matching
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
                    ? 'glass-card bg-white dark:bg-gray-800 text-amber-600 dark:text-amber-400 shadow-[0_10px_20px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_20px_rgba(0,0,0,0.3)] scale-105 z-10'
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
          {activeTab === 'overview' && <CacheOverview />}
          {activeTab === 'statistics' && <CacheStatistics />}
          {activeTab === 'recent' && <RecentCachedQueries />}
        </div>
      </div>
    </div>
  );
};

export default SemanticCachePanel;
