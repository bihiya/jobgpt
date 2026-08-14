import axios, { type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios';
import store from '../store/store';
import { logout, setAccessToken, setCredentials } from '../store/slices/authSlice';
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

export function getStoredRefreshToken(): string | null {
  try {
    return localStorage.getItem('refresh_token');
  } catch {
    return null;
  }
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

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post(
      `${API_BASE}/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 15_000 },
    );
    store.dispatch(setAccessToken(data.access_token));
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }
    return data.access_token as string;
  } catch {
    store.dispatch(logout());
    localStorage.removeItem('refresh_token');
    return null;
  }
}

/** Single-flight: reuse an in-flight refresh so page-load requests don't rotate twice. */
export async function ensureAccessToken(): Promise<string | null> {
  const existing = store.getState().auth.accessToken;
  if (existing) return existing;
  if (!getStoredRefreshToken()) return null;
  refreshing = refreshing ?? refreshAccessToken().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

/** Rehydrate Redux auth from the persisted refresh token after a full page reload. */
export async function restoreSession(): Promise<boolean> {
  const token = await ensureAccessToken();
  if (!token) return false;
  try {
    const { data } = await api.get('/auth/me', {
      headers: { 'X-Silent-Toast': '1' },
    });
    store.dispatch(setCredentials({ user: data, accessToken: token }));
    return true;
  } catch {
    store.dispatch(logout());
    localStorage.removeItem('refresh_token');
    return false;
  }
}

api.interceptors.request.use(async (config) => {
  let token = store.getState().auth.accessToken;
  if (!token && !isAuthPublicPath(config.url || '')) {
    token = await ensureAccessToken();
  }
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

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error?.isGuestGate) {
      return Promise.reject(error);
    }

    const original = error.config;
    const headers = original?.headers;
    const silent = Boolean(
      headers?.['X-Silent-Toast'] ||
        headers?.['x-silent-toast'] ||
        (typeof headers?.get === 'function' && headers.get('X-Silent-Toast')),
    );

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAuthPublicPath(original.url || '')
    ) {
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
