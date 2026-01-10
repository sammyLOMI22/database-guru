import React, { useState, useEffect, useRef } from 'react';
import {
  Database,
  FileText,
  Search,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Zap,
  Filter,
} from 'lucide-react';
import { toolsAPI } from '../services/toolsApi';
import type { ToolResponse, ToolCategory } from '../types/api';
import axios from 'axios';

/** Extract error message from unknown error type */
const getErrorMessage = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message || fallback;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return fallback;
};

/**
 * Browsable directory of all available tools.
 *
 * Shows:
 * - All 10 tools organized by category
 * - Tool descriptions and parameters
 * - Expandable details for each tool
 * - Category filtering
 */
export const ToolDirectory: React.FC = () => {
  const [tools, setTools] = useState<ToolResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [categoryFilter, setCategoryFilter] = useState<ToolCategory | 'all'>('all');

  // Track if this is the initial load for the current filter
  const isInitialLoadRef = useRef(true);

  useEffect(() => {
    // Always show loading for filter changes
    loadTools(isInitialLoadRef.current);
    isInitialLoadRef.current = false;
  }, [categoryFilter]);

  useEffect(() => {
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadTools(false);
    }, 30000);

    return () => clearInterval(interval);
  }, [categoryFilter]);

  const loadTools = async (isInitial = false) => {
    if (isInitial) {
      setLoading(true);
    }
    setError(null);
    try {
      const data = await toolsAPI.listTools(
        categoryFilter !== 'all' ? { category: categoryFilter } : undefined
      );
      setTools(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load tools'));
    } finally {
      setLoading(false);
    }
  };

  const toggleTool = (toolName: string) => {
    setExpandedTools((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(toolName)) {
        newSet.delete(toolName);
      } else {
        newSet.add(toolName);
      }
      return newSet;
    });
  };

  const categoryIcons: Record<string, React.ReactNode> = {
    schema: <Database className="w-5 h-5" />,
    data: <FileText className="w-5 h-5" />,
    query: <Search className="w-5 h-5" />,
    validation: <CheckCircle className="w-5 h-5" />,
  };

  const categoryColors: Record<string, { bg: string; text: string; border: string }> = {
    schema: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    data: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
    query: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
    validation: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
  };

  const categories: Array<{ value: ToolCategory | 'all'; label: string }> = [
    { value: 'all', label: 'All Categories' },
    { value: 'schema', label: 'Schema' },
    { value: 'data', label: 'Data' },
    { value: 'query', label: 'Query' },
    { value: 'validation', label: 'Validation' },
  ];

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <button
          onClick={() => loadTools(true)}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter Bar */}
      <div className="flex items-center gap-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
          <Filter className="w-4 h-4" />
          <span className="text-sm font-medium">Filter:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setCategoryFilter(cat.value)}
              className={`px-3 py-1.5 text-sm rounded-full transition-colors ${categoryFilter === cat.value
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tools List */}
      {!tools || tools.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No tools found in this category</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tools.map((tool) => {
            const isExpanded = expandedTools.has(tool.name);
            const colors = categoryColors[tool.category] || categoryColors.validation;

            return (
              <div
                key={tool.name}
                className={`rounded-lg border ${colors.border} overflow-hidden`}
              >
                {/* Tool Header */}
                <button
                  onClick={() => toggleTool(tool.name)}
                  className={`w-full flex items-center justify-between p-4 text-left ${colors.bg} dark:bg-opacity-10 dark:hover:bg-opacity-20 transition-all`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-white dark:bg-gray-800 ${colors.text} shadow-sm border border-transparent dark:border-gray-700`}>
                      {categoryIcons[tool.category] || <Zap className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className={`font-semibold ${colors.text} dark:text-white`}>{tool.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full bg-white dark:bg-gray-700 ${colors.text} dark:text-gray-300 border border-transparent dark:border-gray-600`}>
                          {tool.category}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">{tool.description}</p>
                    </div>
                  </div>
                  <div className={`flex-shrink-0 ${colors.text}`}>
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5" />
                    ) : (
                      <ChevronRight className="w-5 h-5" />
                    )}
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="p-4 bg-white dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-700">
                    {/* Parameters */}
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Parameters</h4>
                      {Object.keys(tool.parameters).length === 0 ? (
                        <p className="text-sm text-gray-500 dark:text-gray-500">No parameters required</p>
                      ) : (
                        <div className="space-y-2">
                          {Object.entries(tool.parameters).map(([name, param]) => (
                            <div
                              key={name}
                              className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-700"
                            >
                              <code className="text-sm font-mono bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-green-400 px-2 py-0.5 rounded">
                                {name}
                              </code>
                              <div className="flex-1 text-sm">
                                <span className="text-gray-500 dark:text-gray-400">({param.type})</span>
                                {tool.required_params.includes(name) && (
                                  <span className="ml-2 text-red-500 dark:text-red-400 text-xs">required</span>
                                )}
                                <p className="text-gray-600 dark:text-gray-300 mt-1">{param.description}</p>
                                {param.default !== undefined && (
                                  <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
                                    Default: {JSON.stringify(param.default)}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Cache Info */}
                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        <span>
                          Cache TTL: {tool.cache_ttl}s
                          {!tool.cacheable && ' (disabled)'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ToolDirectory;
