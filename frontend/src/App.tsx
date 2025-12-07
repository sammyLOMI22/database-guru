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
import CompilationStats from './components/CompilationStats';
import { healthAPI } from './services/api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [isHealthy, setIsHealthy] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'feedback' | 'tools' | 'cache' | 'pools' | 'compilation' | 'settings'>('chat');

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
      <div className="flex flex-col h-screen bg-gray-50">
        <Header isHealthy={isHealthy} />

        {/* Tab Navigation */}
        <div className="bg-white border-b border-gray-200">
          <div className="flex px-6">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'chat'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              💬 Query Interface
            </button>
            <button
              onClick={() => setActiveTab('feedback')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'feedback'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📊 Feedback Dashboard
            </button>
            <button
              onClick={() => setActiveTab('tools')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'tools'
                  ? 'border-orange-500 text-orange-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🔧 Tools
            </button>
            <button
              onClick={() => setActiveTab('cache')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'cache'
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              💾 Cache
            </button>
            <button
              onClick={() => setActiveTab('pools')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'pools'
                  ? 'border-cyan-500 text-cyan-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🔗 Pools
            </button>
            <button
              onClick={() => setActiveTab('compilation')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'compilation'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              ⚡ Compilation
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'settings'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              ⚙️ Settings
            </button>
          </div>
        </div>

        {/* Content Area - Keep all components mounted to preserve state */}
        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 flex">
            {/* Chat - always mounted to preserve history */}
            <div className={`flex-1 flex ${activeTab === 'chat' ? '' : 'hidden'}`}>
              <EnhancedChatInterface />
            </div>

            {/* Feedback */}
            <div className={`flex-1 overflow-auto p-6 ${activeTab === 'feedback' ? '' : 'hidden'}`}>
              <FeedbackStats />
            </div>

            {/* Tools */}
            <div className={`flex-1 overflow-auto p-6 ${activeTab === 'tools' ? '' : 'hidden'}`}>
              <ToolsPanel />
            </div>

            {/* Cache */}
            <div className={`flex-1 overflow-auto p-6 ${activeTab === 'cache' ? '' : 'hidden'}`}>
              <SemanticCachePanel />
            </div>

            {/* Pools */}
            <div className={`flex-1 overflow-auto p-6 ${activeTab === 'pools' ? '' : 'hidden'}`}>
              <ConnectionPoolMetrics />
            </div>

            {/* Compilation */}
            <div className={`flex-1 overflow-auto ${activeTab === 'compilation' ? '' : 'hidden'}`}>
              <CompilationStats />
            </div>

            {/* Settings */}
            <div className={`flex-1 overflow-auto ${activeTab === 'settings' ? '' : 'hidden'}`}>
              <SettingsPanel />
            </div>
          </main>
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;
