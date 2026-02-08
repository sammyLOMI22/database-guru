import api from './api';

export interface LLMUsageStats {
  period_days: number;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  avg_response_time_ms: number | null;
  unique_sessions: number;
  models_used: number;
  total_cost_usd: number;
}

export interface LLMUsageByAgent {
  agent_type: string;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  avg_response_time_ms: number | null;
}

export interface LLMUsageTimeSeries {
  period: string;
  total_calls: number;
  total_tokens: number;
}

export interface LLMUsageRecord {
  id: number;
  agent_type: string;
  agent_name: string | null;
  provider: string;
  model_name: string;
  llm_method: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  token_estimation_method: string;
  response_time_ms: number | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export const llmUsageApi = {
  getStats: async (days: number = 7): Promise<LLMUsageStats> => {
    const response = await api.get(`/llm/usage/stats?days=${days}`);
    return response.data;
  },

  getByAgent: async (days: number = 7): Promise<LLMUsageByAgent[]> => {
    const response = await api.get(`/llm/usage/by-agent?days=${days}`);
    return response.data;
  },

  getByModel: async (days: number = 7): Promise<any[]> => {
    const response = await api.get(`/llm/usage/by-model?days=${days}`);
    return response.data;
  },

  getByProvider: async (days: number = 7): Promise<any[]> => {
    const response = await api.get(`/llm/usage/by-provider?days=${days}`);
    return response.data;
  },

  getTimeSeries: async (days: number = 7, granularity: string = 'hour'): Promise<LLMUsageTimeSeries[]> => {
    const response = await api.get(`/llm/usage/timeseries?days=${days}&granularity=${granularity}`);
    return response.data;
  },

  getRecent: async (limit: number = 50): Promise<LLMUsageRecord[]> => {
    const response = await api.get(`/llm/usage/recent?limit=${limit}`);
    return response.data;
  },

  getSessionUsage: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/llm/usage/session/${sessionId}`);
    return response.data;
  }
};
