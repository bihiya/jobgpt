import { useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from 'react';
import { jobsApi, reportsApi } from '../api';

type PrefetchApi = {
  prefetchDashboard: () => Promise<void>;
  prefetchJobs: () => Promise<void>;
};

const PrefetchContext = createContext<PrefetchApi | null>(null);

/** Avoid prop drilling prefetch helpers — consume via usePrefetch(). */
export function PrefetchProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const prefetchDashboard = useCallback(async () => {
    await queryClient.prefetchQuery({
      queryKey: ['analytics'],
      queryFn: async () => (await reportsApi.analytics()).data,
      staleTime: 60_000,
    });
  }, [queryClient]);

  const prefetchJobs = useCallback(async () => {
    await queryClient.prefetchQuery({
      queryKey: ['jobs', 'all', ''],
      queryFn: async () => (await jobsApi.list({ page_size: 50 })).data,
      staleTime: 30_000,
    });
  }, [queryClient]);

  const value = useMemo(
    () => ({ prefetchDashboard, prefetchJobs }),
    [prefetchDashboard, prefetchJobs],
  );

  return <PrefetchContext.Provider value={value}>{children}</PrefetchContext.Provider>;
}

export function usePrefetch() {
  const ctx = useContext(PrefetchContext);
  if (!ctx) throw new Error('usePrefetch must be used within PrefetchProvider');
  return ctx;
}
