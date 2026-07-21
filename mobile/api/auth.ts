import { apiRequest } from './client';

export interface Tokens {
  access: string;
  refresh: string;
}

export interface UserProfile {
  id: number;
  email: string;
  date_joined?: string;
}

export const register = (email: string, password: string) =>
  apiRequest<{ id: number; email: string }>('/api/v1/auth/register/', {
    method: 'POST',
    body: { email, password },
  });

export const obtainTokens = (email: string, password: string) =>
  apiRequest<Tokens>('/api/v1/auth/token/', { method: 'POST', body: { email, password } });

export const refreshAccess = (refresh: string) =>
  apiRequest<{ access: string }>('/api/v1/auth/token/refresh/', {
    method: 'POST',
    body: { refresh },
  });

export const fetchMe = (token: string) =>
  apiRequest<UserProfile>('/api/v1/auth/me/', { token });
