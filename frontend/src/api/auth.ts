import { api } from './client';

export type LoginPayload = { email: string; password: string };
export type RegisterPayload = LoginPayload & { full_name: string };

export const authApi = {
  login: (payload: LoginPayload) => api.post('/auth/login', payload),
  register: (payload: RegisterPayload) => api.post('/auth/register', payload),
  me: () => api.get('/auth/me'),
  logout: (refresh_token: string) => api.post('/auth/logout', { refresh_token }),
};
