import axios from 'axios';
import store from '../store/store';
import { logout, setAccessToken } from '../store/slices/authSlice';
import { toastFromStore } from '../hooks/useToast';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

api.interceptors.request.use((config) => {
  const token = store.getState().auth.accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    store.dispatch(setAccessToken(data.access_token));
    localStorage.setItem('refresh_token', data.refresh_token);
    return data.access_token as string;
  } catch {
    store.dispatch(logout());
    localStorage.removeItem('refresh_token');
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const silent = Boolean(original?.headers?.['X-Silent-Toast']);

    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      refreshing = refreshing ?? refreshAccessToken().finally(() => {
        refreshing = null;
      });
      const token = await refreshing;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      }
      if (!silent) {
        toastFromStore('Session expired — please sign in again', 'warning', 5000);
      }
    }

    return Promise.reject(error);
  },
);
