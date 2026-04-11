import api from './api';

export interface ProviderConfig {
  id: number;
  provider_name: string;
  enabled: boolean;
  data_locality: string;
  api_key_masked: string | null;
  has_api_key: boolean;
  endpoint: string | null;
  default_model: string | null;
  extra_config: Record<string, unknown> | null;
  registered?: boolean;
  allowed_by_security?: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface RegistryProvider {
  name: string;
  data_locality: string;
  default_model: string;
  allowed: boolean;
}

export interface RegistryInfo {
  security_level: string;
  providers: RegistryProvider[];
}

export interface ProviderTestResult {
  provider: string;
  healthy: boolean;
  message: string;
  data_locality: string;
}

export interface ProviderModelInfo {
  name: string;
  size: string | null;
  modified_at: string | null;
}

export interface TaskRoutingRule {
  id: number;
  task_type: string;
  primary_provider: string;
  primary_model: string | null;
  fallback_chain: Array<{ provider: string; model?: string }> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProviderHealthResult {
  provider: string;
  healthy: boolean;
  data_locality: string;
  message: string | null;
}

export interface ProviderConfigRequest {
  enabled: boolean;
  data_locality: string;
  api_key?: string | null;
  endpoint?: string | null;
  default_model?: string | null;
  extra_config?: Record<string, unknown> | null;
}

export interface TaskRoutingRequest {
  task_type: string;
  primary_provider: string;
  primary_model?: string | null;
  fallback_chain?: Array<{ provider: string; model?: string }> | null;
}

export const llmProviderApi = {
  // Provider configs
  listConfigs: async (): Promise<ProviderConfig[]> => {
    const response = await api.get('/api/llm-providers/');
    return response.data;
  },

  getConfig: async (providerName: string): Promise<ProviderConfig> => {
    const response = await api.get(`/api/llm-providers/${providerName}`);
    return response.data;
  },

  upsertConfig: async (providerName: string, config: ProviderConfigRequest): Promise<ProviderConfig> => {
    const response = await api.put(`/api/llm-providers/${providerName}/config`, config);
    return response.data;
  },

  deleteConfig: async (providerName: string): Promise<void> => {
    await api.delete(`/api/llm-providers/${providerName}/config`);
  },

  // Registry
  getRegistry: async (): Promise<RegistryInfo> => {
    const response = await api.get('/api/llm-providers/registry');
    return response.data;
  },

  // Test & models
  testProvider: async (providerName: string): Promise<ProviderTestResult> => {
    const response = await api.post(`/api/llm-providers/${providerName}/test`);
    return response.data;
  },

  listModels: async (providerName: string): Promise<ProviderModelInfo[]> => {
    const response = await api.get(`/api/llm-providers/${providerName}/models`);
    return response.data;
  },

  // Task routing
  listRouting: async (): Promise<TaskRoutingRule[]> => {
    const response = await api.get('/api/llm-providers/routing/tasks');
    return response.data;
  },

  upsertRouting: async (routing: TaskRoutingRequest): Promise<TaskRoutingRule> => {
    const response = await api.put('/api/llm-providers/routing/tasks', routing);
    return response.data;
  },

  deleteRouting: async (taskType: string): Promise<void> => {
    await api.delete(`/api/llm-providers/routing/tasks/${taskType}`);
  },

  // Health
  healthCheckAll: async (): Promise<ProviderHealthResult[]> => {
    const response = await api.get('/api/llm-providers/health/all');
    return response.data;
  },
};
