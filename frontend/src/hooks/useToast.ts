import { useCallback } from 'react';
import { useAppDispatch } from '../store/hooks';
import store from '../store/store';
import { showSnackbar } from '../store/slices/uiSlice';
import { getApiErrorMessage } from '../utils/apiError';

export type ToastSeverity = 'success' | 'error' | 'info' | 'warning';

export function useToast() {
  const dispatch = useAppDispatch();

  const toast = useCallback(
    (message: string, severity: ToastSeverity = 'info', duration?: number) => {
      dispatch(showSnackbar({ message, severity, duration }));
    },
    [dispatch],
  );

  const success = useCallback((message: string) => toast(message, 'success'), [toast]);
  const error = useCallback((message: string) => toast(message, 'error', 6000), [toast]);
  const info = useCallback((message: string) => toast(message, 'info'), [toast]);
  const warning = useCallback((message: string) => toast(message, 'warning'), [toast]);

  const apiError = useCallback(
    (err: unknown, fallback?: string) => {
      toast(getApiErrorMessage(err, fallback), 'error', 6000);
    },
    [toast],
  );

  const apiSuccess = useCallback((message: string) => toast(message, 'success'), [toast]);

  return { toast, success, error, info, warning, apiError, apiSuccess };
}

/** Non-hook helper for interceptors / QueryClient (outside React tree). */
export function toastFromStore(
  message: string,
  severity: ToastSeverity = 'info',
  duration?: number,
) {
  store.dispatch(showSnackbar({ message, severity, duration }));
}
