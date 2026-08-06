import { useDispatch, useSelector, type TypedUseSelectorHook } from 'react-redux';

// Root state shape from configureStore reducers (auth + ui)
export type RootState = {
  auth: {
    user: any;
    accessToken: string | null;
    isAuthenticated: boolean;
  };
  ui: {
    darkMode: boolean;
    sidebarOpen: boolean;
    toasts: Array<{
      id: string;
      message: string;
      severity: 'success' | 'error' | 'info' | 'warning';
      duration: number;
    }>;
    snackbar: { open: boolean; message: string; severity: string };
  };
};

export type AppDispatch = ReturnType<typeof useDispatch>;

export const useAppDispatch = () => useDispatch();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
