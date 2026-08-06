import { createSelector } from '@reduxjs/toolkit';

const selectAuthState = (state) => state.auth;

export const selectIsAuthenticated = createSelector(
  [selectAuthState],
  (auth) => auth.isAuthenticated,
);

export const selectCurrentUser = createSelector([selectAuthState], (auth) => auth.user);

export const selectAccessToken = createSelector([selectAuthState], (auth) => auth.accessToken);

export const selectUserDisplayName = createSelector([selectCurrentUser], (user) => {
  if (!user) return 'Guest';
  return user.full_name || user.email || 'User';
});

export const selectIsAdmin = createSelector([selectCurrentUser], (user) => {
  const roles = user?.roles || [];
  return roles.includes('admin');
});
