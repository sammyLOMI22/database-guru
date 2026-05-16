import api from './api';

export interface AuditLog {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  timestamp: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditFacets {
  actions: string[];
  resource_types: string[];
}

export interface AuditLogQuery {
  user_id?: number;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

const buildParams = (q: AuditLogQuery): Record<string, any> => {
  const out: Record<string, any> = {};
  for (const [k, v] of Object.entries(q)) {
    if (v !== undefined && v !== '' && v !== null) out[k] = v;
  }
  return out;
};

export const auditApi = {
  async listLogs(query: AuditLogQuery = {}): Promise<AuditLogListResponse> {
    const { data } = await api.get<AuditLogListResponse>('/api/audit/logs', {
      params: buildParams(query),
    });
    return data;
  },

  async listMyLogs(query: AuditLogQuery = {}): Promise<AuditLogListResponse> {
    const { data } = await api.get<AuditLogListResponse>('/api/audit/logs/me', {
      params: buildParams(query),
    });
    return data;
  },

  async getFacets(): Promise<AuditFacets> {
    const { data } = await api.get<AuditFacets>('/api/audit/facets');
    return data;
  },
};
