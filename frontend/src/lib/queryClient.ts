import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query';
import { toastFromStore } from '../hooks/useToast';
import { getApiErrorMessage } from '../utils/apiError';

type MutationMeta = {
  silent?: boolean;
  successMessage?: string;
  errorMessage?: string;
};

type QueryMeta = {
  silent?: boolean;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      const meta = query.meta as QueryMeta | undefined;
      if (meta?.silent) return;
      // Toast only when a background refetch fails after we already had data
      if (query.state.data !== undefined) {
        toastFromStore(`Refresh failed: ${getApiErrorMessage(error)}`, 'warning', 5000);
      }
    },
  }),
  mutationCache: new MutationCache({
    onSuccess: (_data, _vars, _ctx, mutation) => {
      const meta = mutation.meta as MutationMeta | undefined;
      if (meta?.silent) return;
      if (meta?.successMessage) {
        toastFromStore(meta.successMessage, 'success');
      }
    },
    onError: (error, _vars, _ctx, mutation) => {
      const meta = mutation.meta as MutationMeta | undefined;
      if (meta?.silent) return;
      const prefix = meta?.errorMessage ? `${meta.errorMessage}: ` : '';
      toastFromStore(`${prefix}${getApiErrorMessage(error)}`, 'error', 6000);
    },
  }),
});
