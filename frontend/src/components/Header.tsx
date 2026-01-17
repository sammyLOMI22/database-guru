import { Database, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  isHealthy: boolean;
  isDarkMode: boolean;
  toggleDarkMode: () => void;
}

export default function Header({ isHealthy, isDarkMode, toggleDarkMode }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 bg-white/60 dark:bg-gray-900/60 backdrop-blur-2xl border-b border-white/20 dark:border-white/5 px-8 py-4 transition-all duration-500 animate-fadeIn">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-4 group cursor-default">
          <div className="relative">
            <div className="text-4xl transform transition-all duration-700 group-hover:scale-125 group-hover:rotate-12 animate-float">🧙‍♂️</div>
            <div className="absolute -inset-2 bg-blue-500/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
          </div>
          <div className="flex flex-col">
            <h1 className="text-2xl font-black tracking-tight text-gradient">
              Database Guru
            </h1>
            <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-blue-600/70 dark:text-blue-400/70">
              AI-Powered SQL Assistant
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          {/* Theme Toggle */}
          <button
            onClick={toggleDarkMode}
            className="p-2.5 rounded-2xl glass-panel text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:scale-110 active:scale-95 transition-all duration-300 shadow-sm"
            title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDarkMode ? <Sun className="w-5 h-5 animate-spin-slow" /> : <Moon className="w-5 h-5" />}
          </button>

          {/* Database Status */}
          <div className="flex items-center space-x-3 px-4 py-2 glass-panel rounded-2xl transition-all duration-500 hover:shadow-lg hover:shadow-blue-500/10">
            <div className="relative">
              <Database className={`w-4 h-4 transition-colors duration-500 ${isHealthy ? 'text-blue-500 animate-pulse' : 'text-gray-400'}`} />
              {isHealthy && <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-ping"></div>}
              {isHealthy && <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>}
            </div>
            <span className="text-[11px] font-extrabold tracking-wider text-gray-700 dark:text-gray-300 uppercase">
              {isHealthy ? 'System Online' : 'Offline'}
            </span>
          </div>

          {/* GitHub link omitted/simplified for brevity if needed, but keeping it premium */}
          <a
            href="https://github.com/sammyLOMI22/database-guru"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors duration-300"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}
