import { useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectIsAuthenticated } from '../store/selectors/authSelectors';
import { openLoginGate } from '../store/slices/uiSlice';

/** Returns helpers to gate write actions for guests while keeping pages browsable. */
export function useRequireAuth() {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const location = useLocation();

  const requireAuth = useCallback(
    (reason = 'Sign in to use this feature') => {
      if (isAuthenticated) return true;
      dispatch(
        openLoginGate({
          reason,
          redirectTo: `${location.pathname}${location.search}`,
        }),
      );
      return false;
    },
    [dispatch, isAuthenticated, location.pathname, location.search],
  );

  return { isAuthenticated, requireAuth };
}
