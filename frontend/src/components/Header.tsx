import { Database, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  isHealthy: boolean;
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

const TABS = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'schema', label: 'Schema', icon: '🗂️' },
  { id: 'feedback', label: 'Stats', icon: '📊' },
  { id: 'tools', label: 'Tools', icon: '🔧' },
  { id: 'cache', label: 'Cache', icon: '💾' },
  { id: 'pools', label: 'Pools', icon: '🔗' },
  { id: 'settings', label: 'Config', icon: '⚙️' },
];

export default function Header({ isHealthy, isDarkMode, toggleDarkMode, activeTab, onTabChange }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 bg-white/60 dark:bg-gray-900/60 backdrop-blur-2xl border-b border-white/20 dark:border-white/5 px-8 py-3 transition-all duration-500 animate-fadeIn">
      <div className="max-w-[1800px] mx-auto flex items-center justify-between">
        {/* Left Side: Logo */}
        <div className="flex items-center space-x-4 group cursor-default min-w-[240px]">
          <div className="relative">
            <div className="text-3xl transform transition-all duration-700 group-hover:scale-125 group-hover:rotate-12 animate-float">🧙‍♂️</div>
            <div className="absolute -inset-2 bg-blue-500/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
          </div>
          <div className="flex flex-col">
            <h1 className="text-lg font-black tracking-tight text-gradient leading-none">
              Database Guru
            </h1>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-600/70 dark:text-blue-400/70 mt-0.5">
              AI SQL Assistant
            </p>
          </div>
        </div>

        {/* Center: Navigation */}
        <div className="flex-1 flex justify-center px-4">
          <nav className="flex p-1 bg-black/5 dark:bg-white/5 rounded-2xl border border-white/10 dark:border-white/5 backdrop-blur-xl">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-wide transition-all duration-500 ${activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 scale-105 active:scale-95'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-white/10'
                  }`}
              >
                <span className="text-xs">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Right Side: Status & Controls */}
        <div className="flex items-center space-x-6 min-w-[240px] justify-end">
          {/* Theme Toggle */}
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-xl glass-panel text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:scale-110 active:scale-95 transition-all duration-300 shadow-sm"
            title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDarkMode ? <Sun className="w-4 h-4 animate-spin-slow" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Database Status */}
          <div className="flex items-center space-x-3 px-3 py-1.5 glass-panel rounded-xl transition-all duration-500 hover:shadow-lg hover:shadow-blue-500/10">
            <div className="relative">
              <Database className={`w-3.5 h-3.5 transition-colors duration-500 ${isHealthy ? 'text-blue-500 animate-pulse' : 'text-gray-400'}`} />
              {isHealthy && <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-green-500 rounded-full animate-ping"></div>}
              {isHealthy && <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>}
            </div>
            <span className="text-xs font-bold tracking-wide text-gray-700 dark:text-gray-300 uppercase">
              {isHealthy ? 'Online' : 'Offline'}
            </span>
          </div>

          <a
            href="https://github.com/sammyLOMI22/database-guru"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors duration-300"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}
