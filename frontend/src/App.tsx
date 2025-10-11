import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import EnhancedChatInterface from './components/EnhancedChatInterface';
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
          <main className="flex-1 flex">
            <EnhancedChatInterface />
          </main>
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;
