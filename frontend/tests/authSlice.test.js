import authReducer, { logout, setCredentials } from '../src/store/slices/authSlice';

describe('authSlice', () => {
  it('sets credentials', () => {
    const state = authReducer(
      undefined,
      setCredentials({ user: { email: 'a@b.com' }, accessToken: 'token' }),
    );
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe('token');
  });

  it('logs out', () => {
    const loggedIn = authReducer(
      undefined,
      setCredentials({ user: { email: 'a@b.com' }, accessToken: 'token' }),
    );
    const state = authReducer(loggedIn, logout());
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
  });
});
