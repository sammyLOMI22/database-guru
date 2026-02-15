// API Service Layer
import axios from 'axios';
import type {
  QueryRequest,
  QueryResponse,
  ModelListResponse,
  SchemaResponse,
  QueryHistoryItem,
  HealthCheckResponse,
  ConversationContextResponse,
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

  // Stream query results with Server-Sent Events
  async streamQuery(
    request: QueryRequest,
    callbacks: {
      onStatus?: (status: { status: string; message: string }) => void;
      onSqlGenerated?: (data: { sql: string; used_context: boolean }) => void;
      onMetadata?: (data: { columns: string[] }) => void;
      onData?: (data: { data: any[]; batch_number: number; rows_in_batch: number; rows_sent: number }) => void;
      onComplete?: (data: { truncated: boolean; total_rows: number; execution_time_ms: number }) => void;
      onError?: (error: string) => void;
    }
  ): Promise<void> {
    const baseURL = (import.meta as any).env?.VITE_API_URL || '';
    const url = `${baseURL}/api/query/stream`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        let currentEvent = '';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.substring(6).trim();
          } else if (line.startsWith('data:')) {
            currentData = line.substring(5).trim();
          } else if (line === '') {
            // Empty line signals end of event
            if (currentEvent && currentData) {
              try {
                const parsedData = JSON.parse(currentData);

                // Route to appropriate callback
                switch (currentEvent) {
                  case 'status':
                    callbacks.onStatus?.(parsedData);
                    break;
                  case 'sql_generated':
                    callbacks.onSqlGenerated?.(parsedData);
                    break;
                  case 'metadata':
                    callbacks.onMetadata?.(parsedData);
                    break;
                  case 'data':
                    callbacks.onData?.(parsedData);
                    break;
                  case 'complete':
                    callbacks.onComplete?.(parsedData);
                    break;
                  case 'error':
                    callbacks.onError?.(parsedData.error || 'Unknown error');
                    break;
                }
              } catch (parseError) {
                console.error('[Stream] Error parsing event data:', parseError);
              }

              currentEvent = '';
              currentData = '';
            }
          }
        }
      }
    } catch (error) {
      console.error('[Stream] Error:', error);
      callbacks.onError?.(error instanceof Error ? error.message : 'Stream error');
      throw error;
    }
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
    const { data } = await api.get<QueryHistoryItem>(`/api/query/history/${id}`);
    return data;
  },

  // Get query statistics
  async getStats() {
    const { data } = await api.get('/api/query/stats');
    return data;
  },
};

import type {
  SchemaExploreResponse,
  SchemaCompareRequest,
  SchemaCompareResponse,
} from '../types/api';

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

  // Get detailed schema for a specific connection (Phase 2.5)
  async exploreSchema(connectionId: number, refresh: boolean = false): Promise<SchemaExploreResponse> {
    const { data } = await api.get<SchemaExploreResponse>(
      `/api/schema/explore/${connectionId}`,
      { params: { refresh } }
    );
    return data;
  },

  // Compare schemas across multiple connections (Phase 2.5)
  async compareSchemas(request: SchemaCompareRequest): Promise<SchemaCompareResponse> {
    const { data } = await api.post<SchemaCompareResponse>('/api/schema/compare', request);
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
  ValidateMultiDBRequest,
  ValidateMultiDBResponse,
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

  // Create a new connection
  async createConnection(connectionData: Record<string, unknown>): Promise<DatabaseConnection> {
    const { data } = await api.post<DatabaseConnection>('/api/connections/', connectionData);
    return data;
  },

  // Update an existing connection
  async updateConnection(id: number, connectionData: Record<string, unknown>): Promise<DatabaseConnection> {
    const { data } = await api.put<DatabaseConnection>(`/api/connections/${id}`, connectionData);
    return data;
  },

  // Delete a connection
  async deleteConnection(id: number): Promise<void> {
    await api.delete(`/api/connections/${id}`);
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
  async getMessages(sessionId: string, limit = 100, offset = 0, order: 'asc' | 'desc' = 'asc'): Promise<ChatMessage[]> {
    const { data } = await api.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`, {
      params: { limit, offset, order },
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

  // Get conversation context
  async getContext(sessionId: string): Promise<ConversationContextResponse> {
    const { data } = await api.get<ConversationContextResponse>(`/api/chat/sessions/${sessionId}/context`);
    return data;
  },

  // Clear conversation context
  async clearContext(sessionId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await api.delete<{ success: boolean; message: string }>(
      `/api/chat/sessions/${sessionId}/context`
    );
    return data;
  },
};

export const multiQueryAPI = {
  // Process multi-database query
  async processQuery(request: MultiDatabaseQueryRequest): Promise<MultiDatabaseQueryResponse> {
    const { data } = await api.post<MultiDatabaseQueryResponse>('/api/multi-query/', request);
    return data;
  },

  // Pre-flight validation for multi-database queries (Phase 2.4)
  async validateQuery(request: ValidateMultiDBRequest): Promise<ValidateMultiDBResponse> {
    const { data } = await api.post<ValidateMultiDBResponse>('/api/multi-query/validate', request);
    return data;
  },
};

// Feedback API types
export interface FeedbackCreateRequest {
  query_id: number;
  feedback_type: string;
  corrected_sql?: string;
  correction_description?: string;
  correction_details?: any;
  user_notes?: string;
  user_confidence: number;
}

export interface FeedbackResponse {
  id: number;
  query_id: number;
  feedback_type: string;
  original_sql: string;
  corrected_sql?: string;
  correction_description?: string;
  correction_details?: any;
  user_confidence: number;
  applied_successfully: boolean;
  learned_correction_id?: number;
  user_notes?: string;
  created_at: string;
  applied_at?: string;
}

export interface FeedbackStatsResponse {
  total_feedback: number;
  applied_to_learning: number;
  pending: number;
  by_type: Record<string, number>;
}

export const feedbackAPI = {
  // Submit user feedback
  async submitFeedback(feedback: FeedbackCreateRequest): Promise<FeedbackResponse> {
    const { data } = await api.post<FeedbackResponse>('/api/feedback/', feedback);
    return data;
  },

  // Apply feedback to learning system
  async applyFeedback(feedbackId: number, testBeforeLearning = true): Promise<FeedbackResponse> {
    const { data } = await api.post<FeedbackResponse>('/api/feedback/apply', {
      feedback_id: feedbackId,
      test_before_learning: testBeforeLearning,
    });
    return data;
  },

  // Get feedback for specific query
  async getQueryFeedback(queryId: number): Promise<FeedbackResponse[]> {
    const { data } = await api.get<FeedbackResponse[]>(`/api/feedback/query/${queryId}`);
    return data;
  },

  // Get recent feedback
  async getRecentFeedback(limit = 50, offset = 0, appliedFilter?: 'all' | 'pending' | 'applied'): Promise<FeedbackResponse[]> {
    const { data } = await api.get<FeedbackResponse[]>('/api/feedback/recent', {
      params: {
        limit,
        offset,
        applied_filter: appliedFilter
      },
    });
    return data;
  },

  // Get feedback statistics
  async getStats(): Promise<FeedbackStatsResponse> {
    const { data } = await api.get<FeedbackStatsResponse>('/api/feedback/stats');
    return data;
  },

  // Delete feedback
  async deleteFeedback(feedbackId: number): Promise<void> {
    await api.delete(`/api/feedback/${feedbackId}`);
  },
};

export const settingsAPI = {
  // Get all application settings
  async getSettings() {
    const { data } = await api.get('/api/settings/');
    return data;
  },

  // Update specific setting
  async updateSetting(key: string, value: any) {
    const { data } = await api.patch(`/api/settings/`, { [key]: value });
    return data;
  },
};

// File Source Types (Phase 13: CSV & Excel Support)
import type {
  FileSource,
  FileSchemaResponse,
  FilePreviewResponse,
  ExcelSheetsResponse,
  FileSourceListResponse,
  FileUploadOptions,
} from '../types/api';

export const filesAPI = {
  // Upload a file
  async uploadFile(file: File, options?: FileUploadOptions): Promise<FileSource> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.name) formData.append('name', options.name);
    if (options?.sheet_name) formData.append('sheet_name', options.sheet_name);
    if (options?.session_id) formData.append('chat_session_id', options.session_id);
    if (options?.is_global !== undefined) formData.append('is_global', String(options.is_global));

    const { data } = await api.post<FileSource>('/api/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 2 minutes for large files
    });
    return data;
  },

  // List file sources
  async listFiles(sessionId?: string, includeGlobal = true): Promise<FileSourceListResponse> {
    const { data } = await api.get<FileSourceListResponse>('/api/files/', {
      params: { session_id: sessionId, include_global: includeGlobal },
    });
    return data;
  },

  // Get specific file source
  async getFile(fileId: number): Promise<FileSource> {
    const { data } = await api.get<FileSource>(`/api/files/${fileId}`);
    return data;
  },

  // Delete file source
  async deleteFile(fileId: number): Promise<void> {
    await api.delete(`/api/files/${fileId}`);
  },

  // Get file schema
  async getFileSchema(fileId: number): Promise<FileSchemaResponse> {
    const { data } = await api.get<FileSchemaResponse>(`/api/files/${fileId}/schema`);
    return data;
  },

  // Get file preview
  async getFilePreview(fileId: number, limit = 20): Promise<FilePreviewResponse> {
    const { data } = await api.get<FilePreviewResponse>(`/api/files/${fileId}/preview`, {
      params: { limit },
    });
    return data;
  },

  // Refresh file schema
  async refreshFileSchema(fileId: number): Promise<FileSource> {
    const { data } = await api.post<FileSource>(`/api/files/${fileId}/refresh`);
    return data;
  },

  // Get Excel sheets before upload
  async getExcelSheets(file: File): Promise<ExcelSheetsResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post<ExcelSheetsResponse>('/api/files/excel-sheets', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Add file to chat session
  async addFileToSession(sessionId: string, fileId: number): Promise<void> {
    await api.post(`/api/chat/sessions/${sessionId}/files/${fileId}`);
  },

  // Remove file from chat session
  async removeFileFromSession(sessionId: string, fileId: number): Promise<void> {
    await api.delete(`/api/chat/sessions/${sessionId}/files/${fileId}`);
  },

  // Get files in chat session
  async getSessionFiles(sessionId: string): Promise<{ success: boolean; session_id: string; active_file_source_ids: number[]; file_sources: Array<{ id: number; name: string; file_type: string; original_filename: string; row_count?: number; processing_status?: string }> }> {
    const { data } = await api.get(`/api/chat/sessions/${sessionId}/files`);
    return data;
  },
};

export default api;
