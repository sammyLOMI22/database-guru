import api from './api';

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminUserListQuery {
  search?: string;
  is_active?: boolean;
  is_admin?: boolean;
  limit?: number;
  offset?: number;
}

export interface CreateUserRequest {
  email: string;
  username: string;
  password: string;
  is_admin?: boolean;
}

export interface UpdateUserRequest {
  is_active?: boolean;
  is_admin?: boolean;
}

export interface PasswordResetResponse {
  user_id: number;
  // Phase C: shape varies by AUTH_PASSWORD_RESET_MODE on the backend.
  mode?: 'temp_password' | 'reset_token' | 'both' | string;
  temporary_password?: string | null;
  reset_token?: string | null;
  redemption_url?: string | null;
  expires_at?: string | null;
  detail: string;
  must_change_password?: boolean;
}

const buildParams = (q: AdminUserListQuery): Record<string, any> => {
  const out: Record<string, any> = {};
  for (const [k, v] of Object.entries(q)) {
    if (v !== undefined && v !== '' && v !== null) out[k] = v;
  }
  return out;
};

export const adminUsersApi = {
  async list(query: AdminUserListQuery = {}): Promise<AdminUserListResponse> {
    const { data } = await api.get<AdminUserListResponse>('/api/admin/users', {
      params: buildParams(query),
    });
    return data;
  },

  async create(payload: CreateUserRequest): Promise<AdminUser> {
    const { data } = await api.post<AdminUser>('/api/admin/users', payload);
    return data;
  },

  async update(userId: number, payload: UpdateUserRequest): Promise<AdminUser> {
    const { data } = await api.patch<AdminUser>(`/api/admin/users/${userId}`, payload);
    return data;
  },

  async resetPassword(userId: number): Promise<PasswordResetResponse> {
    const { data } = await api.post<PasswordResetResponse>(
      `/api/admin/users/${userId}/reset-password`,
    );
    return data;
  },

  async deactivate(userId: number): Promise<void> {
    await api.delete(`/api/admin/users/${userId}`);
  },
};
