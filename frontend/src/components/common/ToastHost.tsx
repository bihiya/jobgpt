import { Alert, Slide, Snackbar, Stack } from '@mui/material';
import type { TransitionProps } from '@mui/material/transitions';
import { forwardRef, memo } from 'react';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { selectToasts } from '../../store/selectors/uiSelectors';
import { dismissToast } from '../../store/slices/uiSlice';

const SlideUp = forwardRef(function SlideUp(
  props: TransitionProps & { children: React.ReactElement },
  ref: React.Ref<unknown>,
) {
  return <Slide direction="up" ref={ref} {...props} />;
});

function ToastHostComponent() {
  const dispatch = useAppDispatch();
  const toasts = useAppSelector(selectToasts);

  return (
    <Stack
      spacing={1}
      sx={{
        position: 'fixed',
        bottom: { xs: 16, sm: 24 },
        right: { xs: 12, sm: 24 },
        left: { xs: 12, sm: 'auto' },
        zIndex: (t) => t.zIndex.snackbar,
        maxWidth: { xs: '100%', sm: 420 },
        pointerEvents: 'none',
      }}
    >
      {toasts.map((toast) => (
        <Snackbar
          key={toast.id}
          open
          autoHideDuration={toast.duration}
          onClose={(_, reason) => {
            if (reason === 'clickaway') return;
            dispatch(dismissToast(toast.id));
          }}
          TransitionComponent={SlideUp}
          sx={{ position: 'relative', bottom: 'auto', left: 'auto', right: 'auto', pointerEvents: 'auto' }}
        >
          <Alert
            onClose={() => dispatch(dismissToast(toast.id))}
            severity={toast.severity}
            variant="filled"
            elevation={6}
            sx={{
              width: '100%',
              borderRadius: 2,
              fontWeight: 600,
              boxShadow: '0 12px 40px rgba(15, 40, 30, 0.25)',
              animation: 'toastPop 0.35s cubic-bezier(0.22, 1, 0.36, 1)',
            }}
          >
            {toast.message}
          </Alert>
        </Snackbar>
      ))}
    </Stack>
  );
}

export default memo(ToastHostComponent);
