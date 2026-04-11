// DML API client — Phase 18
// Uses the shared axios instance from api.ts for consistent auth + 401 handling
import api from './api';
import type {
  DMLPreviewRequest,
  DMLPreviewResponse,
  DMLExecuteRequest,
  DMLExecuteResponse,
  WritePermission,
  WritePermissionRequest,
  TableInfo,
} from '../types/dml';

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
