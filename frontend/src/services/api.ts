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
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
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

// Import new types
import type {
  DatabaseConnection,
  ConnectionListResponse,
  ChatSession,
  ChatMessage,
  CreateChatSessionRequest,
  UpdateChatSessionRequest,
  MultiDatabaseQueryRequest,
  MultiDatabaseQueryResponse,
} from '../types/api';

export const connectionsAPI = {
  // List all database connections
  async listConnections(): Promise<ConnectionListResponse> {
    const { data } = await api.get<ConnectionListResponse>('/api/connections/');
    return data;
  },

  // Get specific connection
  async getConnection(id: number): Promise<DatabaseConnection> {
    const { data } = await api.get<DatabaseConnection>(`/api/connections/${id}`);
    return data;
  },

  // Activate a connection
  async activateConnection(id: number): Promise<DatabaseConnection> {
    const { data } = await api.post<DatabaseConnection>(`/api/connections/${id}/activate`);
    return data;
  },
};

export const chatAPI = {
  // Create chat session
  async createSession(request: CreateChatSessionRequest): Promise<ChatSession> {
    const { data } = await api.post<ChatSession>('/api/chat/sessions', request);
    return data;
  },

  // List chat sessions
  async listSessions(userId?: string, limit = 50, offset = 0): Promise<ChatSession[]> {
    const { data } = await api.get<ChatSession[]>('/api/chat/sessions', {
      params: { user_id: userId, limit, offset },
    });
    return data;
  },

  // Get specific chat session
  async getSession(sessionId: string): Promise<ChatSession> {
    const { data } = await api.get<ChatSession>(`/api/chat/sessions/${sessionId}`);
    return data;
  },

  // Update chat session
  async updateSession(sessionId: string, request: UpdateChatSessionRequest): Promise<ChatSession> {
    const { data } = await api.patch<ChatSession>(`/api/chat/sessions/${sessionId}`, request);
    return data;
  },

  // Delete chat session
  async deleteSession(sessionId: string): Promise<void> {
    await api.delete(`/api/chat/sessions/${sessionId}`);
  },

  // Get chat messages
  async getMessages(sessionId: string, limit = 100, offset = 0): Promise<ChatMessage[]> {
    const { data } = await api.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`, {
      params: { limit, offset },
    });
    return data;
  },

  // Create chat message
  async createMessage(sessionId: string, message: {
    role: 'user' | 'assistant' | 'system';
    content: string;
    query_history_id?: number;
    databases_used?: any[];
  }): Promise<ChatMessage> {
    const { data } = await api.post<ChatMessage>(`/api/chat/sessions/${sessionId}/messages`, message);
    return data;
  },
};

export const multiQueryAPI = {
  // Process multi-database query
  async processQuery(request: MultiDatabaseQueryRequest): Promise<MultiDatabaseQueryResponse> {
    const { data } = await api.post<MultiDatabaseQueryResponse>('/api/multi-query/', request);
    return data;
  },
};

export default api;
