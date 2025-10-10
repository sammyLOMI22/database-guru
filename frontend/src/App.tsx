import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    // Check health on mount
    healthAPI.check()
      .then(() => setIsHealthy(true))
      .catch(() => setIsHealthy(false));
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex flex-col h-screen bg-gray-50">
        <Header isHealthy={isHealthy} />

        <div className="flex flex-1 overflow-hidden">
          {sidebarOpen && (
            <Sidebar onClose={() => setSidebarOpen(false)} />
          )}

          <main className="flex-1 flex flex-col">
            <ChatInterface />
          </main>
        </div>

        {/* Sidebar toggle button for mobile */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="fixed bottom-4 left-4 p-3 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 transition-colors md:hidden"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        )}
      </div>
    </QueryClientProvider>
  );
}

export default App;
