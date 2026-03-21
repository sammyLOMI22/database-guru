import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect, useCallback } from 'react';
import EnhancedChatInterface from './components/EnhancedChatInterface';
import Header from './components/Header';
import AuthPage from './components/AuthPage';
import { ObservabilityDemo } from './components/ObservabilityDemo';
import { FeedbackStats } from './components/FeedbackStats';
import { SettingsPanel } from './components/SettingsPanel';
import { ToolsPanel } from './components/ToolsPanel';
import { SemanticCachePanel } from './components/SemanticCachePanel';
import { ConnectionPoolMetrics } from './components/ConnectionPoolMetrics';
import { LineagePanel } from './components/lineage/LineagePanel';
import { LLMUsageDashboard } from './components/dashboard/LLMUsageDashboard';
import { MigrationPanel } from './components/migration/MigrationPanel';
import { PerformancePanel } from './components/performance/PerformancePanel';
import SchemaPanel from './components/SchemaPanel';
import { healthAPI, settingsAPI } from './services/api';
import { useDarkMode } from './hooks/useDarkMode';
import { useAuth } from './hooks/useAuth';

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
  const { user, isLoading: authLoading, isAuthenticated, login, register, logout } = useAuth();
  const [isHealthy, setIsHealthy] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [requireAuth, setRequireAuth] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'schema' | 'feedback' | 'tools' | 'cache' | 'pools' | 'lineage' | 'usage' | 'migration' | 'performance' | 'settings'>('chat');

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

  // Cross-component performance navigation state (Phase 22)
  const [performanceNav, setPerformanceNav] = useState<{ sql?: string; connectionId?: number } | null>(null);

  const handleAnalyzePerformance = useCallback((sql: string, connectionId?: number) => {
    setPerformanceNav({ sql, connectionId });
    setActiveTab('performance');
  }, []);

  useEffect(() => {
    // Check health on mount
    healthAPI.check()
      .then(() => setIsHealthy(true))
      .catch(() => setIsHealthy(false));

    // Check if backend requires auth via the public settings endpoint.
    settingsAPI.getSettings()
      .then((data: any) => {
        if (data?.require_auth) {
          setRequireAuth(true);
        }
      })
      .catch(() => {/* settings fetch failed — default to no auth required */});

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

  // Show loading while verifying stored token
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-blue-950">
        <div className="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>
    );
  }

  // Show auth page when required or user explicitly opened it
  if ((requireAuth && !isAuthenticated) || (showAuth && !isAuthenticated)) {
    return (
      <AuthPage
        onLogin={async (u, p) => { await login(u, p); setShowAuth(false); }}
        onRegister={async (e, u, p) => { await register(e, u, p); setShowAuth(false); }}
        onSkip={requireAuth ? undefined : () => setShowAuth(false)}
        requireAuth={requireAuth}
      />
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
          user={user}
          onLogout={() => { logout(); if (requireAuth) setShowAuth(true); }}
          onSignIn={() => setShowAuth(true)}
        />

        {/* Content Area - Keep all components mounted to preserve state */}
        <div className="flex flex-1 overflow-hidden min-h-0">
          <main className="flex-1 flex h-full">
            {/* Chat - always mounted to preserve history */}
            <div className={`flex-1 flex ${activeTab === 'chat' ? '' : 'hidden'}`}>
              <EnhancedChatInterface onViewLineage={handleViewLineage} onAnalyzePerformance={handleAnalyzePerformance} onLastSqlChange={setLastExecutedSql} />
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

            {/* LLM Usage */}
            <div className={`flex-1 flex h-full min-h-0 ${activeTab === 'usage' ? '' : 'hidden'}`}>
              <div className="flex-1 overflow-auto">
                <LLMUsageDashboard />
              </div>
            </div>

            {/* Migration */}
            <div className={`flex-1 flex h-full min-h-0 ${activeTab === 'migration' ? '' : 'hidden'}`}>
              <div className="flex-1 flex flex-col h-full min-h-0">
                <MigrationPanel />
              </div>
            </div>

            {/* Performance */}
            <div className={`flex-1 flex h-full min-h-0 ${activeTab === 'performance' ? '' : 'hidden'}`}>
              <div className="flex-1 flex flex-col h-full min-h-0">
                <PerformancePanel
                  initialSql={performanceNav?.sql}
                  initialConnectionId={performanceNav?.connectionId}
                />
              </div>
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
