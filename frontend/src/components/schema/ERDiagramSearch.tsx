/**
 * ERDiagramSearch - Search input for filtering tables in the ER diagram.
 *
 * Filters tables by name or column names.
 */

import React from 'react';
import { Search, X } from 'lucide-react';
import { useDarkMode } from '../../hooks/useDarkMode';

interface ERDiagramSearchProps {
  /** Current search query */
  searchQuery: string;
  /** Callback when search query changes */
  onSearchChange: (query: string) => void;
}

const ERDiagramSearch: React.FC<ERDiagramSearchProps> = ({
  searchQuery,
  onSearchChange,
}) => {
  const { isDarkMode } = useDarkMode();

  return (
    <div className="relative">
      <Search
        className={`
          absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4
          ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}
        `}
      />
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search tables or columns..."
        className={`
          w-64 pl-8 pr-8 py-1.5 text-sm rounded-lg border
          transition-colors focus:outline-none focus:ring-2
          ${isDarkMode
            ? 'bg-gray-700 border-gray-600 text-gray-200 placeholder-gray-500 focus:ring-blue-500/50'
            : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400 focus:ring-blue-500/50'}
        `}
      />
      {searchQuery && (
        <button
          onClick={() => onSearchChange('')}
          className={`
            absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded
            ${isDarkMode
              ? 'text-gray-500 hover:text-gray-300 hover:bg-gray-600'
              : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}
          `}
          title="Clear search"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

export default ERDiagramSearch;
