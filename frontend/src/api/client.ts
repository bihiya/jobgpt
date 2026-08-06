import axios, { type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios';
import store from '../store/store';
import { logout, setAccessToken } from '../store/slices/authSlice';
import { openLoginGate } from '../store/slices/uiSlice';
import { toastFromStore } from '../hooks/useToast';
import { resolveDemoData } from '../lib/demoData';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

function isAuthPublicPath(url = ''): boolean {
  return (
    url.includes('/auth/login') ||
    url.includes('/auth/register') ||
    url.includes('/auth/refresh') ||
    url.includes('/auth/forgot')
  );
}

function guestAdapter(config: InternalAxiosRequestConfig): AxiosAdapter {
  return async () => {
    const method = (config.method || 'get').toLowerCase();
    const url = `${config.baseURL || ''}${config.url || ''}`;

    if (method === 'get') {
      const data = resolveDemoData(url, method);
      return {
        data,
        status: 200,
        statusText: 'OK',
        headers: { 'x-jobpilot-demo': '1' },
        config,
      };
    }

    const redirectTo =
      typeof window !== 'undefined'
        ? `${window.location.pathname}${window.location.search}`
        : '/dashboard';
    store.dispatch(
      openLoginGate({
        reason: 'Sign in to perform this action',
        redirectTo,
      }),
    );

    const error: any = new Error('Authentication required');
    error.config = config;
    error.response = {
      status: 401,
      data: { detail: 'Sign in required' },
      headers: {},
      statusText: 'Unauthorized',
      config,
    };
    error.isGuestGate = true;
    return Promise.reject(error);
  };
}

api.interceptors.request.use((config) => {
  const token = store.getState().auth.accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    return config;
  }

  // Guests can browse via demo GET responses; writes open the login gate.
  if (!isAuthPublicPath(config.url || '')) {
    config.adapter = guestAdapter(config);
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
    if (error?.isGuestGate) {
      return Promise.reject(error);
    }

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
        store.dispatch(
          openLoginGate({
            reason: 'Session expired — sign in to continue',
            redirectTo:
              typeof window !== 'undefined'
                ? `${window.location.pathname}${window.location.search}`
                : '/dashboard',
          }),
        );
        toastFromStore('Session expired — please sign in again', 'warning', 5000);
      }
    }

    return Promise.reject(error);
  },
);
