// API Service Layer
import axios from 'axios';
import type {
  QueryRequest,
  QueryResponse,
  ModelListResponse,
  SchemaResponse,
  QueryHistoryItem,
  HealthCheckResponse,
} from '../types/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 60000, // 60 seconds for LLM queries
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(`[API Error] ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      console.error('[API Error] No response received:', error.request);
    } else {
      console.error('[API Error]', error.message);
    }
    return Promise.reject(error);
  }
);

export const queryAPI = {
  // Process natural language query
  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    const { data } = await api.post<QueryResponse>('/api/query/', request);
    return data;
  },

  // Get query history
  async getHistory(limit = 50, offset = 0): Promise<QueryHistoryItem[]> {
    const { data } = await api.get<QueryHistoryItem[]>('/api/query/history', {
      params: { limit, offset },
    });
    return data;
  },

  // Get specific query by ID
  async getQueryById(id: number): Promise<QueryHistoryItem> {
    const { data} = await api.get<QueryHistoryItem>(`/api/query/history/${id}`);
    return data;
  },

  // Get query statistics
  async getStats() {
    const { data } = await api.get('/api/query/stats');
    return data;
  },
};

export const schemaAPI = {
  // Get database schema
  async getSchema(refresh = false): Promise<SchemaResponse> {
    const { data } = await api.get<SchemaResponse>('/api/schema/', {
      params: { refresh },
    });
    return data;
  },

  // Get list of tables
  async getTables(): Promise<{ tables: string[]; count: number }> {
    const { data } = await api.get('/api/schema/tables');
    return data;
  },

  // Get specific table details
  async getTableDetails(tableName: string) {
    const { data } = await api.get(`/api/schema/tables/${tableName}`);
    return data;
  },

  // Refresh schema cache
  async refreshSchema(): Promise<SchemaResponse> {
    const { data } = await api.post<SchemaResponse>('/api/schema/refresh');
    return data;
  },
};

export const modelsAPI = {
  // List available models
  async listModels(): Promise<ModelListResponse> {
    const { data } = await api.get<ModelListResponse>('/api/models/');
    return data;
  },

  // Get model details
  async getModelDetails() {
    const { data } = await api.get('/api/models/details');
    return data;
  },

  // Get recommended models
  async getRecommended() {
    const { data } = await api.get('/api/models/recommended');
    return data;
  },

  // Pull a model
  async pullModel(modelName: string) {
    const { data } = await api.post(`/api/models/pull/${modelName}`);
    return data;
  },

  // Test a model
  async testModel(modelName: string) {
    const { data } = await api.get(`/api/models/test/${modelName}`);
    return data;
  },
};

export const healthAPI = {
  // Health check
  async check(): Promise<HealthCheckResponse> {
    const { data } = await api.get<HealthCheckResponse>('/health');
    return data;
  },
};

export default api;
