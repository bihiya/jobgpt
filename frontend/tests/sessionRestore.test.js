import axios from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ensureAccessToken, restoreSession } from '../src/api/client';
import store from '../src/store/store';
import { logout } from '../src/store/slices/authSlice';

describe('session restore', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    store.dispatch(logout());
  });

  it('returns false when no refresh token is stored', async () => {
    expect(await restoreSession()).toBe(false);
    expect(store.getState().auth.isAuthenticated).toBe(false);
  });

  it('restores access token and user after a full reload', async () => {
    localStorage.setItem('refresh_token', 'old-refresh');
    vi.spyOn(axios, 'post').mockResolvedValue({
      data: { access_token: 'new-access', refresh_token: 'new-refresh' },
    });
    vi.spyOn(api, 'get').mockResolvedValue({
      data: { email: 'ada@example.com', full_name: 'Ada' },
    });

    const ok = await restoreSession();

    expect(ok).toBe(true);
    expect(store.getState().auth.isAuthenticated).toBe(true);
    expect(store.getState().auth.accessToken).toBe('new-access');
    expect(store.getState().auth.user.email).toBe('ada@example.com');
    expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      { refresh_token: 'old-refresh' },
      expect.any(Object),
    );
  });

  it('clears the persisted session when refresh fails', async () => {
    localStorage.setItem('refresh_token', 'expired-refresh');
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('unauthorized'));

    expect(await restoreSession()).toBe(false);
    expect(store.getState().auth.isAuthenticated).toBe(false);
    expect(store.getState().auth.accessToken).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('does not treat a stored refresh token as a guest (refreshes first)', async () => {
    localStorage.setItem('refresh_token', 'stored-refresh');
    vi.spyOn(axios, 'post').mockResolvedValue({
      data: { access_token: 'boot-access', refresh_token: 'rotated-refresh' },
    });

    const token = await ensureAccessToken();

    expect(token).toBe('boot-access');
    expect(store.getState().auth.accessToken).toBe('boot-access');
    expect(store.getState().auth.isAuthenticated).toBe(true);
  });

  it('sends the restored bearer token instead of demo guest data', async () => {
    localStorage.setItem('refresh_token', 'stored-refresh');
    vi.spyOn(axios, 'post').mockResolvedValue({
      data: { access_token: 'boot-access', refresh_token: 'rotated-refresh' },
    });
    const adapter = vi.fn(async (config) => ({
      data: { source: 'live-api' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }));
    const previousAdapter = api.defaults.adapter;
    api.defaults.adapter = adapter;
    try {
      const { data } = await api.get('/jobs');
      expect(data).toEqual({ source: 'live-api' });
      expect(adapter).toHaveBeenCalled();
      const config = adapter.mock.calls[0][0];
      const authorization =
        config.headers.Authorization ||
        config.headers.authorization ||
        config.headers.get?.('Authorization');
      expect(authorization).toBe('Bearer boot-access');
    } finally {
      api.defaults.adapter = previousAdapter;
    }
  });

  it('still serves demo data when there is no refresh token', async () => {
    const { data, headers } = await api.get('/jobs');
    const demo =
      headers['x-jobpilot-demo'] || headers['X-Jobpilot-Demo'] || headers.get?.('x-jobpilot-demo');
    expect(demo).toBe('1');
    expect(data.items?.length).toBeGreaterThan(0);
  });
});
