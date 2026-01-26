import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect, useCallback } from 'react';
import EnhancedChatInterface from './components/EnhancedChatInterface';
import Header from './components/Header';
import { ObservabilityDemo } from './components/ObservabilityDemo';
import { FeedbackStats } from './components/FeedbackStats';
import { SettingsPanel } from './components/SettingsPanel';
import { ToolsPanel } from './components/ToolsPanel';
import { SemanticCachePanel } from './components/SemanticCachePanel';
import { ConnectionPoolMetrics } from './components/ConnectionPoolMetrics';
import { LineagePanel } from './components/lineage/LineagePanel';
import SchemaPanel from './components/SchemaPanel';
import { healthAPI } from './services/api';
import { useDarkMode } from './hooks/useDarkMode';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const { isDarkMode, toggleDarkMode } = useDarkMode();
  const [isHealthy, setIsHealthy] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'schema' | 'feedback' | 'tools' | 'cache' | 'pools' | 'lineage' | 'settings'>('chat');

  // Cross-component lineage navigation state
  const [lineageNav, setLineageNav] = useState<{ sql?: string; tab?: 'explore' | 'history' | 'impact'; impactTable?: string } | null>(null);
  const [lastExecutedSql, setLastExecutedSql] = useState<string | null>(null);

  const handleViewLineage = useCallback((sql: string) => {
    setLineageNav({ sql, tab: 'explore' });
    setActiveTab('lineage');
  }, []);

  const handleAnalyzeImpact = useCallback((tableName: string) => {
    setLineageNav({ impactTable: tableName, tab: 'impact' });
    setActiveTab('lineage');
  }, []);

  useEffect(() => {
    // Check health on mount
    healthAPI.check()
      .then(() => setIsHealthy(true))
      .catch(() => setIsHealthy(false));

    // Check URL for demo parameter
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === 'true') {
      setShowDemo(true);
    }
  }, []);

  // Show demo if ?demo=true in URL
  if (showDemo) {
    return (
      <QueryClientProvider client={queryClient}>
        <ObservabilityDemo />
      </QueryClientProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex flex-col h-screen bg-transparent transition-colors duration-500">
        <Header
          isHealthy={isHealthy}
          isDarkMode={isDarkMode}
          toggleDarkMode={toggleDarkMode}
          activeTab={activeTab}
          onTabChange={(id) => setActiveTab(id as any)}
        />

        {/* Content Area - Keep all components mounted to preserve state */}
        <div className="flex flex-1 overflow-hidden min-h-0">
          <main className="flex-1 flex h-full">
            {/* Chat - always mounted to preserve history */}
            <div className={`flex-1 flex ${activeTab === 'chat' ? '' : 'hidden'}`}>
              <EnhancedChatInterface onViewLineage={handleViewLineage} onLastSqlChange={setLastExecutedSql} />
            </div>

            {/* Schema */}
            <div className={`flex-1 flex h-full min-h-0 ${activeTab === 'schema' ? '' : 'hidden'}`}>
              <SchemaPanel onAnalyzeImpact={handleAnalyzeImpact} lastSql={lastExecutedSql} />
            </div>

            {/* Lineage */}
            <div className={`flex-1 flex h-full min-h-0 ${activeTab === 'lineage' ? '' : 'hidden'}`}>
              <div className="flex-1 flex flex-col h-full min-h-0">
                <LineagePanel
                  initialSql={lineageNav?.sql}
                  initialTab={lineageNav?.tab}
                  initialImpactTable={lineageNav?.impactTable}
                />
              </div>
            </div>

            {/* Feedback */}
            <div className={`flex-1 overflow-auto p-6 pb-32 ${activeTab === 'feedback' ? '' : 'hidden'}`}>
              <FeedbackStats />
            </div>

            {/* Tools */}
            <div className={`flex-1 overflow-auto p-6 pb-32 ${activeTab === 'tools' ? '' : 'hidden'}`}>
              <ToolsPanel />
            </div>

            {/* Cache */}
            <div className={`flex-1 overflow-auto p-6 pb-32 ${activeTab === 'cache' ? '' : 'hidden'}`}>
              <SemanticCachePanel />
            </div>

            {/* Pools */}
            <div className={`flex-1 overflow-auto p-6 pb-32 ${activeTab === 'pools' ? '' : 'hidden'}`}>
              <ConnectionPoolMetrics />
            </div>

            {/* Settings */}
            <div className={`flex-1 overflow-auto pb-32 ${activeTab === 'settings' ? '' : 'hidden'}`}>
              <SettingsPanel />
            </div>
          </main>
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;
