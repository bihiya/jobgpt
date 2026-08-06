import { Button, Stack, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { automationApi } from '../../api';
import PageShell from '../../components/common/PageShell';

export default function AutomationPage() {
  const queryClient = useQueryClient();
  const { data: status } = useQuery({
    queryKey: ['automation-status'],
    queryFn: async () => (await automationApi.status()).data,
  });
  const { data: logs, isLoading } = useQuery({
    queryKey: ['automation-logs'],
    queryFn: async () => (await automationApi.logs({ page_size: 50 })).data,
  });

  const runMutation = useMutation({
    mutationFn: (jobType: string) => automationApi.run(jobType),
    meta: { successMessage: 'Worker triggered', errorMessage: 'Could not run worker' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automation-status'] });
      queryClient.invalidateQueries({ queryKey: ['automation-logs'] });
    },
  });

  const columns: GridColDef[] = [
    { field: 'created_at', headerName: 'Time', flex: 1, minWidth: 140 },
    { field: 'portal', headerName: 'Portal', width: 140 },
    { field: 'action', headerName: 'Action', width: 120 },
    { field: 'level', headerName: 'Level', width: 100 },
    { field: 'message', headerName: 'Message', flex: 1.5, minWidth: 180 },
  ];

  return (
    <PageShell>
      <Typography variant="h4">Automation</Typography>
      <Typography color="text.secondary">
        Total logs: {status?.total_logs ?? 0}. Trigger workers manually when needed.
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {['fetch', 'match', 'apply', 'report'].map((job) => (
          <Button key={job} variant="outlined" onClick={() => runMutation.mutate(job)} disabled={runMutation.isPending}>
            Run {job}
          </Button>
        ))}
      </Stack>
      <DataGrid
        autoHeight
        rows={logs?.items || []}
        columns={columns}
        loading={isLoading}
        pageSizeOptions={[10, 25, 50]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%' }}
      />
    </PageShell>
  );
}
