import { Button, Stack, Typography, Chip } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useCallback, useMemo, useState } from 'react';
import { approvalsApi, jobsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import PageSkeleton from '../../components/common/PageSkeleton';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { useToast } from '../../hooks/useToast';

function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const { apiError } = useToast();
  const { data, isLoading } = useQuery({
    queryKey: ['approvals'],
    queryFn: async () => (await approvalsApi.list({ status: 'pending', page_size: 50 })).data,
  });

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      approve ? approvalsApi.approve(id) : approvalsApi.reject(id),
    meta: {
      successMessage: 'Decision saved',
      errorMessage: 'Could not update approval',
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['approvals'] }),
  });

  const openJob = useCallback(async (jobId: string) => {
    try {
      const { data: job } = await jobsApi.get(jobId);
      setDrawerJob(job);
    } catch (err) {
      apiError(err, 'Could not load job details');
    }
  }, [apiError]);

  const columns: GridColDef[] = useMemo(
    () => [
      { field: 'summary', headerName: 'Job', flex: 1.5, minWidth: 180 },
      {
        field: 'match_score',
        headerName: 'Match',
        width: 110,
        valueFormatter: (v: number) => `${Math.round((v || 0) * 100)}%`,
      },
      {
        field: 'status',
        headerName: 'Status',
        width: 140,
        renderCell: (params) => <Chip size="small" label={params.value} color="warning" />,
      },
      { field: 'created_at', headerName: 'Queued', flex: 1, minWidth: 140 },
      {
        field: 'actions',
        headerName: '',
        width: 280,
        sortable: false,
        renderCell: (params) => (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button size="small" onClick={() => openJob(params.row.job_id)}>
              Why
            </Button>
            <Button
              size="small"
              variant="contained"
              onClick={() => decide.mutate({ id: params.row.id, approve: true })}
            >
              Approve
            </Button>
            <Button
              size="small"
              color="inherit"
              onClick={() => decide.mutate({ id: params.row.id, approve: false })}
            >
              Reject
            </Button>
          </Stack>
        ),
      },
    ],
    [decide, openJob],
  );

  if (isLoading) return <PageSkeleton />;

  return (
    <PageShell>
      <Typography variant="h4">Approvals</Typography>
      <Typography color="text.secondary">
        Human-in-the-loop queue — approve to apply, reject to skip.
      </Typography>
      <DataGrid
        autoHeight
        rows={data?.items || []}
        columns={columns}
        getRowId={(row) => row.id}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%' }}
        disableRowSelectionOnClick
      />
      <JobDetailDrawer open={!!drawerJob} job={drawerJob} onClose={() => setDrawerJob(null)} />
    </PageShell>
  );
}

export default memo(ApprovalsPage);
