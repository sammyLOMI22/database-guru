// DML API client — Phase 18
import axios from 'axios';
import { getStoredToken } from '../hooks/useAuth';
import type {
  DMLPreviewRequest,
  DMLPreviewResponse,
  DMLExecuteRequest,
  DMLExecuteResponse,
  WritePermission,
  WritePermissionRequest,
  TableInfo,
} from '../types/dml';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const dmlAPI = {
  async preview(request: DMLPreviewRequest): Promise<DMLPreviewResponse> {
    const { data } = await api.post('/api/dml/preview', request);
    return data;
  },

  async execute(request: DMLExecuteRequest): Promise<DMLExecuteResponse> {
    const { data } = await api.post('/api/dml/execute', request);
    return data;
  },

  async getPermissions(connectionId: number): Promise<WritePermission> {
    const { data } = await api.get(`/api/dml/permissions/${connectionId}`);
    return data;
  },

  async updatePermissions(
    connectionId: number,
    request: WritePermissionRequest
  ): Promise<WritePermission> {
    const { data } = await api.put(
      `/api/dml/permissions/${connectionId}`,
      request
    );
    return data;
  },

  async getTableInfo(
    connectionId: number,
    tableName: string
  ): Promise<TableInfo> {
    const { data } = await api.get(
      `/api/dml/table-info/${connectionId}/${tableName}`
    );
    return data;
  },
};
