import React, { useState, useEffect, useRef } from 'react';
import {
  Database,
  FileText,
  Search,
  CheckCircle,
  ChevronDown,
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

  const categoryStyles: Record<string, { icon: string; bg: string; border: string }> = {
    schema: { icon: 'text-blue-500', bg: 'from-blue-500/10 to-blue-500/5', border: 'border-blue-500/20' },
    data: { icon: 'text-emerald-500', bg: 'from-emerald-500/10 to-emerald-500/5', border: 'border-emerald-500/20' },
    query: { icon: 'text-purple-500', bg: 'from-purple-500/10 to-purple-500/5', border: 'border-purple-500/20' },
    validation: { icon: 'text-orange-500', bg: 'from-orange-500/10 to-orange-500/5', border: 'border-orange-500/20' },
  };

  const categories: Array<{ value: ToolCategory | 'all'; label: string }> = [
    { value: 'all', label: 'All' },
    { value: 'schema', label: 'Schema' },
    { value: 'data', label: 'Data' },
    { value: 'query', label: 'Query' },
    { value: 'validation', label: 'Validation' },
  ];

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-20 glass-panel rounded-2xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="glass-panel rounded-2xl p-8 max-w-md mx-auto">
          <div className="text-red-500 mb-4 text-sm font-bold uppercase tracking-widest">Error: {error}</div>
          <button
            onClick={() => loadTools(true)}
            className="px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg shadow-orange-500/20"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Filter Bar */}
      <div className="flex items-center gap-4 pb-5 border-b border-white/10">
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Filter className="w-4 h-4" />
          <span className="text-[11px] font-black uppercase tracking-[0.2em]">Filter</span>
        </div>
        <div className="flex p-1 glass-panel rounded-xl border-white/10 bg-black/5 dark:bg-white/5">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setCategoryFilter(cat.value)}
              className={`px-4 py-2 text-xs font-black uppercase tracking-widest rounded-lg transition-all duration-300 ${
                categoryFilter === cat.value
                  ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-lg shadow-orange-500/20'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/10'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tools List */}
      {!tools || tools.length === 0 ? (
        <div className="text-center py-12">
          <div className="glass-panel rounded-2xl p-8 max-w-md mx-auto">
            <Search className="w-12 h-12 mx-auto mb-3 text-gray-400 opacity-50" />
            <p className="text-sm font-bold text-gray-500 uppercase tracking-widest">No tools found</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {tools.map((tool) => {
            const isExpanded = expandedTools.has(tool.name);
            const style = categoryStyles[tool.category] || categoryStyles.validation;

            return (
              <div
                key={tool.name}
                className={`glass-card rounded-2xl overflow-hidden ${style.border} transition-all duration-300 ${isExpanded ? 'shadow-xl' : ''}`}
              >
                {/* Tool Header */}
                <button
                  onClick={() => toggleTool(tool.name)}
                  className={`w-full flex items-center justify-between p-5 text-left bg-gradient-to-r ${style.bg} hover:opacity-90 transition-all group`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl glass-panel flex items-center justify-center ${style.icon} group-hover:scale-110 transition-transform`}>
                      {categoryIcons[tool.category] || <Zap className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-sm font-black uppercase tracking-widest text-gray-900 dark:text-white">{tool.name}</h3>
                        <span className={`text-[11px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg glass-panel ${style.icon}`}>
                          {tool.category}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">{tool.description}</p>
                    </div>
                  </div>
                  <div className={`flex-shrink-0 ${style.icon} transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
                    <ChevronDown className="w-5 h-5" />
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="p-5 border-t border-white/10 bg-black/5 dark:bg-white/5 animate-fadeIn">
                    {/* Parameters */}
                    <div className="mb-5">
                      <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
                        <div className="w-1 h-1 rounded-full bg-orange-500" />
                        Parameters
                      </h4>
                      {Object.keys(tool.parameters).length === 0 ? (
                        <p className="text-xs font-medium text-gray-400 dark:text-gray-500 italic">No parameters required</p>
                      ) : (
                        <div className="space-y-2">
                          {Object.entries(tool.parameters).map(([name, param]) => (
                            <div
                              key={name}
                              className="flex items-start gap-3 p-4 glass-panel rounded-xl border-white/10"
                            >
                              <code className="text-xs font-mono font-bold bg-gradient-to-r from-orange-500/20 to-amber-500/20 text-orange-600 dark:text-orange-400 px-2.5 py-1 rounded-lg border border-orange-500/20">
                                {name}
                              </code>
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">({param.type})</span>
                                  {tool.required_params.includes(name) && (
                                    <span className="text-[11px] font-black uppercase tracking-widest text-red-500 bg-red-500/10 px-2 py-0.5 rounded">required</span>
                                  )}
                                </div>
                                <p className="text-xs font-medium text-gray-600 dark:text-gray-300 mt-1">{param.description}</p>
                                {param.default !== undefined && (
                                  <p className="text-[11px] font-bold text-gray-400 mt-1 uppercase tracking-widest">
                                    Default: <span className="text-gray-500">{JSON.stringify(param.default)}</span>
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Cache Info */}
                    <div className="flex items-center gap-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
                      <div className="flex items-center gap-2 glass-panel px-3 py-2 rounded-lg">
                        <Clock className="w-4 h-4" />
                        <span>
                          TTL: {tool.cache_ttl}s
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
