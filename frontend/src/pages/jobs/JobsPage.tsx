import { Button, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { applicationsApi, jobsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { useToast } from '../../hooks/useToast';
import { JOB_TAB_PATHS, JOB_TABS } from '../../layouts/nav';

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
  showApply: boolean;
  onApply: (id: string) => void;
  onDetails: (id: string) => void;
};

const ActionCell = memo(function ActionCell({ id, showApply, onApply, onDetails }: ActionCellProps) {
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      <Button size="small" onClick={() => onDetails(id)}>
        Details
      </Button>
      {showApply && (
        <Button size="small" variant="contained" onClick={() => onApply(id)}>
          Apply
        </Button>
      )}
    </Stack>
  );
});

function JobsPage({ mode = 'all' }: { mode?: Mode }) {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const debouncedQ = useDebouncedValue(q, 350);
  const queryClient = useQueryClient();
  const { apiError } = useToast();
  const showApply = mode === 'all' || mode === 'tracked';
  const onTabChange = useCallback(
    (_: unknown, next: Mode) => {
      navigate(JOB_TAB_PATHS[next]);
    },
    [navigate],
  );

  const listQuery = useQuery({
    queryKey: ['jobs', mode, debouncedQ],
    queryFn: async () =>
      (await fetchers[mode]({ q: debouncedQ || undefined, page_size: 50 })).data,
    staleTime: 30_000,
  });

  const applyMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.create({ job_id: id }),
    meta: { successMessage: 'Applying…', errorMessage: 'Could not apply' },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['jobs', mode, debouncedQ] });
      const previous = queryClient.getQueryData(['jobs', mode, debouncedQ]);
      queryClient.setQueryData(['jobs', mode, debouncedQ], (old: { items?: Array<{ id: string; status: string }> } | undefined) => {
        if (!old?.items) return old;
        return {
          ...old,
          items: old.items.map((job) =>
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
      void queryClient.invalidateQueries({ queryKey: ['pipeline'] });
      void queryClient.invalidateQueries({ queryKey: ['applications'] });
    },
  });

  const onApply = useCallback((id: string) => applyMutation.mutate(id), [applyMutation]);
  const openDetails = useCallback(async (id: string) => {
    try {
      const { data } = await jobsApi.get(id);
      setDrawerJob(data);
    } catch (err) {
      apiError(err, 'Could not load job details');
    }
  }, [apiError]);
  const closeDrawer = useCallback(() => setDrawerJob(null), []);
  const onSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQ(e.target.value);
  }, []);

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
        headerName: '',
        width: 180,
        sortable: false,
        renderCell: (params) => (
          <ActionCell
            id={params.row.id}
            showApply={showApply}
            onApply={onApply}
            onDetails={openDetails}
          />
        ),
      },
    ],
    [onApply, openDetails, showApply],
  );

  return (
    <PageShell loading={listQuery.isLoading} fetching={!listQuery.isLoading && listQuery.isFetching}>
      <Typography variant="h4">{titleMap[mode]}</Typography>
      <Tabs
        value={mode}
        onChange={onTabChange}
        variant="scrollable"
        allowScrollButtonsMobile
        aria-label="Job lists"
        sx={{ borderBottom: 1, borderColor: 'divider', maxWidth: '100%' }}
      >
        {JOB_TABS.map((tab) => (
          <Tab key={tab.value} value={tab.value} label={tab.label} />
        ))}
      </Tabs>
      <TextField
        size="small"
        placeholder="Search title, company, description"
        value={q}
        onChange={onSearchChange}
        sx={{ maxWidth: { sm: 420 }, width: '100%' }}
      />

      <DataGrid
        autoHeight
        rows={listQuery.data?.items || []}
        columns={columns}
        loading={listQuery.isFetching}
        getRowId={(row) => row.id}
        pageSizeOptions={[10, 25, 50]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        disableRowSelectionOnClick
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%' }}
      />
      <JobDetailDrawer
        open={!!drawerJob}
        job={drawerJob}
        onClose={closeDrawer}
        applyBusy={applyMutation.isPending}
        onApply={
          showApply
            ? (id) => {
                onApply(id);
                closeDrawer();
              }
            : undefined
        }
      />
    </PageShell>
  );
}

export default memo(JobsPage);
