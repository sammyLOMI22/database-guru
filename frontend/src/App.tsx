import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import EnhancedChatInterface from './components/EnhancedChatInterface';
import Header from './components/Header';
import { ObservabilityDemo } from './components/ObservabilityDemo';
import { FeedbackStats } from './components/FeedbackStats';
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
  const [activeTab, setActiveTab] = useState<'chat' | 'feedback'>('chat');

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
          </div>
        </div>

        {/* Content Area */}
        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 flex">
            {activeTab === 'chat' ? (
              <EnhancedChatInterface />
            ) : (
              <div className="flex-1 overflow-auto p-6">
                <FeedbackStats />
              </div>
            )}
          </main>
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;
