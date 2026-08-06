import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';
import { memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { closeLoginGate } from '../../store/slices/uiSlice';

function LoginGateDialogComponent() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const gate = useAppSelector((s) => s.ui.loginGate);

  const close = () => dispatch(closeLoginGate());

  const go = (path: string) => {
    const redirect = gate.redirectTo || '/dashboard';
    close();
    navigate(`${path}?redirect=${encodeURIComponent(redirect)}`);
  };

  return (
    <Dialog open={Boolean(gate?.open)} onClose={close} fullWidth maxWidth="xs">
      <DialogTitle>Sign in to continue</DialogTitle>
      <DialogContent>
        <Typography color="text.secondary">
          {gate?.reason || 'Create a free account or sign in to take this action.'}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
          You can keep browsing JobPilot features as a guest anytime.
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1, flexWrap: 'wrap' }}>
        <Button onClick={close} color="inherit">
          Keep browsing
        </Button>
        <Button variant="outlined" onClick={() => go('/register')}>
          Register
        </Button>
        <Button variant="contained" onClick={() => go('/login')}>
          Sign in
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default memo(LoginGateDialogComponent);
