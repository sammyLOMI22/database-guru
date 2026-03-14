import { useState, useEffect, useCallback } from 'react';
import { authAPI } from '../services/api';

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
}

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

export function useAuth() {
  const [state, setState] = useState<AuthState>(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const userJson = localStorage.getItem(USER_KEY);
    return {
      token,
      user: userJson ? JSON.parse(userJson) : null,
      isLoading: !!token, // need to verify if we have a stored token
    };
  });

  // Verify stored token on mount
  useEffect(() => {
    if (!state.token) return;

    authAPI.getMe()
      .then((user) => {
        setState({ token: state.token, user, isLoading: false });
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      })
      .catch(() => {
        // Token expired or invalid — clear
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setState({ token: null, user: null, isLoading: false });
      });
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const resp = await authAPI.login({ username, password });
    localStorage.setItem(TOKEN_KEY, resp.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
    setState({ token: resp.access_token, user: resp.user, isLoading: false });
  }, []);

  const register = useCallback(async (email: string, username: string, password: string) => {
    const resp = await authAPI.register({ email, username, password });
    localStorage.setItem(TOKEN_KEY, resp.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
    setState({ token: resp.access_token, user: resp.user, isLoading: false });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setState({ token: null, user: null, isLoading: false });
  }, []);

  return {
    user: state.user,
    token: state.token,
    isLoading: state.isLoading,
    isAuthenticated: !!state.user,
    login,
    register,
    logout,
  };
}

/** Read the stored token (for use in API interceptors). */
export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
