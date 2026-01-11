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
      label: 'Statistics',
      icon: <BarChart3 className="w-4 h-4" />,
      description:
        'Cache hit distribution, embedding metrics, and performance breakdown',
    },
    {
      key: 'recent',
      label: 'Recent Queries',
      icon: <Clock className="w-4 h-4" />,
      description:
        'Browse recently cached queries with hit counts and metadata',
    },
  ];

  const currentTab = tabs.find((t) => t.key === activeTab);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
            <Database className="w-6 h-6 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Semantic Cache</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Intelligent caching with similarity matching - 30-50% higher hit rates
            </p>
          </div>
        </div>
      </div>

      {/* Main Content Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-100 dark:border-gray-700">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex overflow-x-auto" aria-label="Cache tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${activeTab === tab.key
                    ? 'border-amber-500 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50'
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
        <div className="bg-gray-50 dark:bg-gray-900/50 px-6 py-3 border-b border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-600 dark:text-gray-400">{currentTab?.description}</p>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && <CacheOverview />}
          {activeTab === 'statistics' && <CacheStatistics />}
          {activeTab === 'recent' && <RecentCachedQueries />}
        </div>
      </div>
    </div>
  );
};

export default SemanticCachePanel;
