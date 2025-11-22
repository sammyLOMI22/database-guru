/**
 * Tools API Service
 *
 * Provides API methods for interacting with the Tool-Using Agent system.
 * Part of Phase 3.1: Tool-Using Agent Implementation
 */
import axios from 'axios';
import type {
  ToolResponse,
  ToolStatsResponse,
  AllToolStatsResponse,
  ToolsPromptResponse,
} from '../types/api';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 10000,
});

// Request logging
api.interceptors.request.use((config) => {
  console.log(`[Tools API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[Tools API] Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface ToolFilters {
  category?: 'schema' | 'data' | 'query' | 'validation';
}

export const toolsAPI = {
  /**
   * Get all available tools, optionally filtered by category
   */
  async listTools(filters?: ToolFilters): Promise<ToolResponse[]> {
    const { data } = await api.get<ToolResponse[]>('/api/tools', {
      params: filters,
    });
    return data;
  },

  /**
   * Get execution statistics for all tools
   */
  async getAllStats(): Promise<AllToolStatsResponse> {
    const { data } = await api.get<AllToolStatsResponse>('/api/tools/stats');
    return data;
  },

  /**
   * Get execution statistics for a specific tool
   */
  async getToolStats(toolName: string): Promise<ToolStatsResponse> {
    const { data } = await api.get<ToolStatsResponse>(
      `/api/tools/stats/${toolName}`
    );
    return data;
  },

  /**
   * Get tools formatted for LLM prompt inclusion
   */
  async getToolsPrompt(category?: string): Promise<ToolsPromptResponse> {
    const { data } = await api.get<ToolsPromptResponse>('/api/tools/prompt', {
      params: category ? { category } : undefined,
    });
    return data;
  },

  /**
   * Invalidate cache for a specific tool
   */
  async invalidateToolCache(toolName: string): Promise<{ message: string }> {
    const { data } = await api.post<{ message: string }>(
      `/api/tools/${toolName}/invalidate-cache`
    );
    return data;
  },

  /**
   * Invalidate cache for all tools
   */
  async invalidateAllCache(): Promise<{ message: string }> {
    const { data } = await api.post<{ message: string }>(
      '/api/tools/invalidate-all-cache'
    );
    return data;
  },
};

export default toolsAPI;
