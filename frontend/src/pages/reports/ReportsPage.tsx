import { Button, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { reportsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import { useToast } from '../../hooks/useToast';

export default function ReportsPage() {
  const [format, setFormat] = useState('csv');
  const queryClient = useQueryClient();
  const { apiSuccess, apiError } = useToast();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => (await reportsApi.list()).data,
  });
  const [downloading, setDownloading] = useState(false);

  const createMutation = useMutation({
    mutationFn: () => reportsApi.create({ type: 'custom', format }),
    meta: { successMessage: 'Report queued', errorMessage: 'Could not generate report' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reports'] }),
  });

  const download = async (id: string) => {
    setDownloading(true);
    try {
      const res = await reportsApi.download(id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${id}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      apiSuccess('Download started');
    } catch (err) {
      apiError(err, 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const columns: GridColDef[] = [
    { field: 'type', headerName: 'Type', width: 120 },
    { field: 'format', headerName: 'Format', width: 100 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'created_at', headerName: 'Created', flex: 1, minWidth: 140 },
    {
      field: 'actions',
      headerName: '',
      width: 140,
      renderCell: (params) => (
        <Button
          size="small"
          disabled={params.row.status !== 'ready' || downloading}
          onClick={() => download(params.row.id)}
        >
          {downloading ? '…' : 'Download'}
        </Button>
      ),
    },
  ];

  return (
    <PageShell
      loading={isLoading}
      fetching={!isLoading && isFetching}
      busy={createMutation.isPending || downloading}
    >
      <Typography variant="h4">Reports</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
        <TextField select size="small" label="Format" value={format} onChange={(e) => setFormat(e.target.value)} sx={{ width: { xs: '100%', sm: 160 } }}>
          {['csv', 'excel', 'pdf'].map((f) => (
            <MenuItem key={f} value={f}>{f.toUpperCase()}</MenuItem>
          ))}
        </TextField>
        <Button variant="contained" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
          {createMutation.isPending ? 'Generating…' : 'Generate report'}
        </Button>
      </Stack>
      <DataGrid
        autoHeight
        rows={data?.items || []}
        columns={columns}
        loading={isFetching}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%' }}
      />
    </PageShell>
  );
}
