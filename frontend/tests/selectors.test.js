import {
  selectIsAdmin,
  selectIsAuthenticated,
  selectUserDisplayName,
} from '../src/store/selectors/authSelectors';

describe('authSelectors', () => {
  const state = {
    auth: {
      isAuthenticated: true,
      accessToken: 't',
      user: { full_name: 'Ada', email: 'a@b.com', roles: ['admin'] },
    },
  };

  it('selects auth flags and display name', () => {
    expect(selectIsAuthenticated(state)).toBe(true);
    expect(selectUserDisplayName(state)).toBe('Ada');
    expect(selectIsAdmin(state)).toBe(true);
  });
});
