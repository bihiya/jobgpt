import {
  Button,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { memo, useCallback, useMemo, useState } from 'react';
import { applicationsApi, jobsApi } from '../../api';
import VirtualizedJobList from '../../components/jobs/VirtualizedJobList';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import PageSkeleton from '../../components/common/PageSkeleton';

type Mode = 'all' | 'tracked' | 'applied' | 'history';

const fetchers = {
  all: jobsApi.list,
  tracked: jobsApi.tracked,
  applied: jobsApi.applied,
  history: jobsApi.history,
};

const titleMap = {
  all: 'Jobs',
  tracked: 'Tracked jobs',
  applied: 'Applied jobs',
  history: 'Job history',
} as const;

type ActionCellProps = {
  id: string;
  onTrack: (id: string) => void;
  onApply: (id: string) => void;
  onDetails: (id: string) => void;
};

const ActionCell = memo(function ActionCell({ id, onTrack, onApply, onDetails }: ActionCellProps) {
  const handleTrack = useCallback(() => onTrack(id), [id, onTrack]);
  const handleApply = useCallback(() => onApply(id), [id, onApply]);
  const handleDetails = useCallback(() => onDetails(id), [id, onDetails]);
  return (
    <Stack direction="row" spacing={1}>
      <Button size="small" onClick={handleDetails}>
        Why
      </Button>
      <Button size="small" onClick={handleTrack}>
        Track
      </Button>
      <Button size="small" variant="contained" onClick={handleApply}>
        Apply
      </Button>
    </Stack>
  );
});

function JobsPage({ mode = 'all' }: { mode?: Mode }) {
  const [q, setQ] = useState('');
  const [virtualized, setVirtualized] = useState(false);
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const debouncedQ = useDebouncedValue(q, 350);
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ['jobs', mode, debouncedQ],
    queryFn: async () =>
      (await fetchers[mode]({ q: debouncedQ || undefined, page_size: 50 })).data,
    staleTime: 30_000,
    enabled: !virtualized,
  });

  // Infinite scrolling / pagination via React Query
  const infiniteQuery = useInfiniteQuery({
    queryKey: ['jobs-infinite', mode, debouncedQ],
    queryFn: async ({ pageParam }) =>
      (
        await fetchers[mode]({
          q: debouncedQ || undefined,
          page: pageParam,
          page_size: 25,
        })
      ).data,
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.page < last.pages ? last.page + 1 : undefined,
    enabled: virtualized,
    staleTime: 30_000,
  });

  const trackMutation = useMutation({
    mutationFn: (id: string) => jobsApi.track(id),
    // Optimistic UI update
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['jobs', mode, debouncedQ] });
      const previous = queryClient.getQueryData(['jobs', mode, debouncedQ]);
      queryClient.setQueryData(['jobs', mode, debouncedQ], (old: any) => {
        if (!old?.items) return old;
        return {
          ...old,
          items: old.items.map((job: any) =>
            job.id === id ? { ...job, status: 'tracked' } : job,
          ),
        };
      });
      return { previous };
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['jobs', mode, debouncedQ], context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
      void queryClient.invalidateQueries({ queryKey: ['jobs-infinite'] });
    },
  });

  const applyMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.create({ job_id: id }),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['jobs', mode, debouncedQ] });
      const previous = queryClient.getQueryData(['jobs', mode, debouncedQ]);
      queryClient.setQueryData(['jobs', mode, debouncedQ], (old: any) => {
        if (!old?.items) return old;
        return {
          ...old,
          items: old.items.map((job: any) =>
            job.id === id ? { ...job, status: 'applying' } : job,
          ),
        };
      });
      return { previous };
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['jobs', mode, debouncedQ], context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const onTrack = useCallback((id: string) => trackMutation.mutate(id), [trackMutation]);
  const onApply = useCallback((id: string) => applyMutation.mutate(id), [applyMutation]);
  const openDetails = useCallback(async (id: string) => {
    const { data } = await jobsApi.get(id);
    setDrawerJob(data);
  }, []);
  const onSelect = useCallback((id: string) => {
    void openDetails(id);
  }, [openDetails]);
  const closeDrawer = useCallback(() => setDrawerJob(null), []);
  const onSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQ(e.target.value);
  }, []);
  const onToggleVirtual = useCallback((_: unknown, checked: boolean) => {
    setVirtualized(checked);
  }, []);
  const loadMore = useCallback(() => {
    if (infiniteQuery.hasNextPage && !infiniteQuery.isFetchingNextPage) {
      void infiniteQuery.fetchNextPage();
    }
  }, [infiniteQuery]);

  const columns: GridColDef[] = useMemo(
    () => [
      { field: 'title', headerName: 'Title', flex: 1.4, minWidth: 180 },
      { field: 'company', headerName: 'Company', flex: 1, minWidth: 140 },
      { field: 'location', headerName: 'Location', flex: 0.8, minWidth: 120 },
      { field: 'portal', headerName: 'Portal', width: 120 },
      {
        field: 'match_score',
        headerName: 'Match',
        width: 100,
        valueFormatter: (value: number) => `${Math.round((value || 0) * 100)}%`,
      },
      { field: 'status', headerName: 'Status', width: 120 },
      {
        field: 'actions',
        headerName: 'Actions',
        width: 260,
        sortable: false,
        renderCell: (params) => (
          <ActionCell
            id={params.row.id}
            onTrack={onTrack}
            onApply={onApply}
            onDetails={openDetails}
          />
        ),
      },
    ],
    [onTrack, onApply, openDetails],
  );

  const virtualJobs = useMemo(
    () => infiniteQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [infiniteQuery.data],
  );

  if ((!virtualized && listQuery.isLoading) || (virtualized && infiniteQuery.isLoading)) {
    return <PageSkeleton />;
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4">{titleMap[mode]}</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
        <TextField
          size="small"
          placeholder="Search title, company, description"
          value={q}
          onChange={onSearchChange}
          sx={{ maxWidth: 420, flex: 1 }}
        />
        <FormControlLabel
          control={<Switch checked={virtualized} onChange={onToggleVirtual} />}
          label="Virtualized infinite list"
        />
      </Stack>

      {virtualized ? (
        <>
          <VirtualizedJobList jobs={virtualJobs} onSelect={onSelect} />
          {infiniteQuery.hasNextPage && (
            <Button onClick={loadMore} disabled={infiniteQuery.isFetchingNextPage}>
              {infiniteQuery.isFetchingNextPage ? 'Loading…' : 'Load more'}
            </Button>
          )}
        </>
      ) : (
        <DataGrid
          autoHeight
          rows={listQuery.data?.items || []}
          columns={columns}
          loading={listQuery.isFetching}
          getRowId={(row) => row.id}
          pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          disableRowSelectionOnClick
          sx={{ bgcolor: 'background.paper', borderRadius: 2 }}
        />
      )}
      <JobDetailDrawer open={!!drawerJob} job={drawerJob} onClose={closeDrawer} />
    </Stack>
  );
}

export default memo(JobsPage);
