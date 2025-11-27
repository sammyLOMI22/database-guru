/**
 * IndexRecommendationsPanel - Main Container
 *
 * Tabbed interface for database index recommendations:
 * - Overview: Stats dashboard with quick actions
 * - Recommendations: Browsable list with filters
 * - Statistics: Charts and performance metrics
 *
 * Part of Phase 4: Database Index Recommendations
 */

import { useState } from 'react';
import { Database } from 'lucide-react';
import IndexOverview from './IndexOverview';
import RecommendationsList from './RecommendationsList';
import IndexStatistics from './IndexStatistics';

type TabId = 'overview' | 'recommendations' | 'statistics';

interface Tab {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'recommendations', label: 'Recommendations', icon: '💡' },
  { id: 'statistics', label: 'Statistics', icon: '📈' },
];

export default function IndexRecommendationsPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  const handleNavigate = (tab: TabId) => {
    setActiveTab(tab);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Database className="w-8 h-8 text-purple-600" />
          <h1 className="text-3xl font-bold text-gray-900">Index Recommendations</h1>
        </div>
        <p className="text-gray-600">
          Analyze slow queries and get intelligent index recommendations to improve database performance
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2
                transition-colors duration-200
                ${
                  activeTab === tab.id
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow">
        {activeTab === 'overview' && <IndexOverview onNavigate={handleNavigate} />}
        {activeTab === 'recommendations' && <RecommendationsList />}
        {activeTab === 'statistics' && <IndexStatistics />}
      </div>
    </div>
  );
}
