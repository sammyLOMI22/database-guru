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
  estimated_cost_usd: number | null;
  created_at: string;
}

export interface DailyCostEntry {
  date: string;
  cost_usd: number;
  calls: number;
  tokens: number;
}

export interface CostSummary {
  period_days: number;
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  avg_cost_per_call: number;
  daily_costs: DailyCostEntry[];
  by_provider: Record<string, number>;
}

export interface ProviderAgentStats {
  calls: number;
  avg_latency_ms: number | null;
  total_cost_usd: number;
  avg_tokens_per_call: number | null;
  success_rate: number;
}

export interface ProviderComparison {
  period_days: number;
  by_agent_type: Record<string, Record<string, ProviderAgentStats>>;
}

export interface ModelConfig {
  id: number;
  model_name: string;
  display_name: string | null;
  provider: string;
  cost_per_1m_input_tokens: number | null;
  cost_per_1m_output_tokens: number | null;
  is_active: boolean;
}

export interface UnpricedModel {
  model_name: string;
  provider: string;
  call_count: number;
  total_tokens: number;
}

export interface ModelConfigCreateRequest {
  model_name: string;
  provider: string;
  cost_per_1m_input_tokens: number;
  cost_per_1m_output_tokens: number;
  display_name?: string;
}

export const llmUsageApi = {
  getStats: async (days: number = 7): Promise<LLMUsageStats> => {
    const response = await api.get(`/api/llm/usage/stats?days=${days}`);
    return response.data;
  },

  getByAgent: async (days: number = 7): Promise<LLMUsageByAgent[]> => {
    const response = await api.get(`/api/llm/usage/by-agent?days=${days}`);
    return response.data;
  },

  getByModel: async (days: number = 7): Promise<any[]> => {
    const response = await api.get(`/api/llm/usage/by-model?days=${days}`);
    return response.data;
  },

  getByProvider: async (days: number = 7): Promise<any[]> => {
    const response = await api.get(`/api/llm/usage/by-provider?days=${days}`);
    return response.data;
  },

  getTimeSeries: async (days: number = 7, granularity: string = 'hour'): Promise<LLMUsageTimeSeries[]> => {
    const response = await api.get(`/api/llm/usage/timeseries?days=${days}&granularity=${granularity}`);
    return response.data;
  },

  getRecent: async (limit: number = 50): Promise<LLMUsageRecord[]> => {
    const response = await api.get(`/api/llm/usage/recent?limit=${limit}`);
    return response.data;
  },

  getSessionUsage: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/api/llm/usage/session/${sessionId}`);
    return response.data;
  },

  getCostSummary: async (days: number = 30): Promise<CostSummary> => {
    const response = await api.get(`/api/llm/usage/cost-summary?days=${days}`);
    return response.data;
  },

  getProviderComparison: async (days: number = 7): Promise<ProviderComparison> => {
    const response = await api.get(`/api/llm/usage/provider-comparison?days=${days}`);
    return response.data;
  },

  getModelConfigs: async (): Promise<ModelConfig[]> => {
    const response = await api.get('/api/llm/usage/model-configs');
    return response.data;
  },

  getUnpricedModels: async (): Promise<UnpricedModel[]> => {
    const response = await api.get('/api/llm/usage/unpriced-models');
    return response.data;
  },

  upsertModelConfig: async (config: ModelConfigCreateRequest): Promise<ModelConfig> => {
    const response = await api.post('/api/llm/usage/model-configs', config);
    return response.data;
  },

  deleteModelConfig: async (provider: string, modelName: string): Promise<void> => {
    await api.delete(
      `/api/llm/usage/model-configs/${encodeURIComponent(provider)}/${encodeURIComponent(modelName)}`
    );
  },
};
