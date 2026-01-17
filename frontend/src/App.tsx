import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import EnhancedChatInterface from './components/EnhancedChatInterface';
import Header from './components/Header';
import { ObservabilityDemo } from './components/ObservabilityDemo';
import { FeedbackStats } from './components/FeedbackStats';
import { SettingsPanel } from './components/SettingsPanel';
import { ToolsPanel } from './components/ToolsPanel';
import { SemanticCachePanel } from './components/SemanticCachePanel';
import { ConnectionPoolMetrics } from './components/ConnectionPoolMetrics';
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
  const [activeTab, setActiveTab] = useState<'chat' | 'schema' | 'feedback' | 'tools' | 'cache' | 'pools' | 'settings'>('chat');

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
        <Header isHealthy={isHealthy} isDarkMode={isDarkMode} toggleDarkMode={toggleDarkMode} />

        {/* Tab Navigation - Premium Floating Segmented Control */}
        <div className="fixed bottom-32 left-1/2 -translate-x-1/2 z-50 pointer-events-none w-full max-w-2xl px-4">
          <div className="flex p-2 glass-card rounded-[2rem] shadow-2xl pointer-events-auto border-white/10 dark:border-white/5 backdrop-blur-3xl">
            {[
              { id: 'chat', label: 'Chat', icon: '💬' },
              { id: 'schema', label: 'Schema', icon: '🗂️' },
              { id: 'feedback', label: 'Stats', icon: '📊' },
              { id: 'tools', label: 'Tools', icon: '🔧' },
              { id: 'settings', label: 'Config', icon: '⚙️' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  relative flex-1 py-3 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all duration-500 flex flex-col items-center gap-1.5
                  ${activeTab === tab.id
                    ? 'text-white shadow-xl shadow-blue-500/20'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-white/5'
                  }
                `}
              >
                {activeTab === tab.id && (
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl -z-10 animate-scaleUp shadow-[0_0_20px_rgba(59,130,246,0.4)]" />
                )}
                <span className="text-xl leading-none">{tab.icon}</span>
                <span className="opacity-80 font-black">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content Area - Keep all components mounted to preserve state */}
        <div className="flex flex-1 overflow-hidden min-h-0">
          <main className="flex-1 flex h-full">
            {/* Chat - always mounted to preserve history */}
            <div className={`flex-1 flex ${activeTab === 'chat' ? '' : 'hidden'}`}>
              <EnhancedChatInterface />
            </div>

            {/* Schema */}
            <div className={`flex-1 flex h-full min-h-0 ${activeTab === 'schema' ? '' : 'hidden'}`}>
              <SchemaPanel />
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
