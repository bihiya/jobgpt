import { Alert, Button, Stack } from '@mui/material';
import { memo } from 'react';
import { useLocation } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { selectAuthStatus, selectIsAuthenticated } from '../../store/selectors/authSelectors';
import { openLoginGate } from '../../store/slices/uiSlice';

function GuestBannerComponent() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authStatus = useAppSelector(selectAuthStatus);
  const dispatch = useAppDispatch();
  const location = useLocation();

  if (isAuthenticated || authStatus === 'restoring') return null;

  return (
    <Alert
      severity="info"
      sx={{
        mb: 2,
        borderRadius: 2,
        alignItems: 'center',
        '& .MuiAlert-message': { width: '100%' },
      }}
      action={
        <Stack direction="row" spacing={1}>
          <Button
            color="inherit"
            size="small"
            onClick={() =>
              dispatch(
                openLoginGate({
                  reason: 'Create a free account to save progress and run automation',
                  redirectTo: `${location.pathname}${location.search}`,
                }),
              )
            }
          >
            Sign in
          </Button>
        </Stack>
      }
    >
      You&apos;re browsing JobPilot as a guest — explore every page with sample data. Sign in when
      you want to take action.
    </Alert>
  );
}

export default memo(GuestBannerComponent);
