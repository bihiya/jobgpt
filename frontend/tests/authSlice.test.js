import authReducer, {
  logout,
  setAccessToken,
  setAuthStatus,
  setCredentials,
} from '../src/store/slices/authSlice';

describe('authSlice', () => {
  it('sets credentials', () => {
    const state = authReducer(
      undefined,
      setCredentials({ user: { email: 'a@b.com' }, accessToken: 'token' }),
    );
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe('token');
    expect(state.status).toBe('ready');
  });

  it('marks the session authenticated when an access token is restored', () => {
    const state = authReducer(undefined, setAccessToken('refreshed-token'));
    expect(state.accessToken).toBe('refreshed-token');
    expect(state.isAuthenticated).toBe(true);
  });

  it('tracks restore status', () => {
    const restoring = authReducer(undefined, setAuthStatus('restoring'));
    expect(restoring.status).toBe('restoring');
    const ready = authReducer(restoring, setAuthStatus('ready'));
    expect(ready.status).toBe('ready');
  });

  it('logs out', () => {
    const loggedIn = authReducer(
      undefined,
      setCredentials({ user: { email: 'a@b.com' }, accessToken: 'token' }),
    );
    const state = authReducer(loggedIn, logout());
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.status).toBe('ready');
  });
});
