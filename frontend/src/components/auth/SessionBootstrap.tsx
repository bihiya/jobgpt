import { Box, CircularProgress, Typography } from '@mui/material';
import { useEffect, type ReactNode } from 'react';
import { restoreSession } from '../../api/client';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { setAuthStatus } from '../../store/slices/authSlice';

function hasStoredRefreshToken() {
  try {
    return Boolean(localStorage.getItem('refresh_token'));
  } catch {
    return false;
  }
}

/** Reloads persist only the refresh token — restore access token + user before painting the app. */
export default function SessionBootstrap({ children }: { children: ReactNode }) {
  const dispatch = useAppDispatch();
  const status = useAppSelector((s) => s.auth.status);
  const waitForRestore = status === 'restoring' || (status === 'idle' && hasStoredRefreshToken());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (hasStoredRefreshToken()) {
        dispatch(setAuthStatus('restoring'));
      }
      await restoreSession();
      if (!cancelled) dispatch(setAuthStatus('ready'));
    })();
    return () => {
      cancelled = true;
    };
  }, [dispatch]);

  if (waitForRestore) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress size={36} />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Restoring your session…
          </Typography>
        </Box>
      </Box>
    );
  }

  return children;
}
