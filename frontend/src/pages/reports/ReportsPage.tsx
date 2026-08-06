import { Button, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { reportsApi } from '../../api';

export default function ReportsPage() {
  const [format, setFormat] = useState('csv');
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => (await reportsApi.list()).data,
  });

  const createMutation = useMutation({
    mutationFn: () => reportsApi.create({ type: 'custom', format }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reports'] }),
  });

  const download = async (id: string) => {
    const res = await reportsApi.download(id);
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-${id}.${format}`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const columns: GridColDef[] = [
    { field: 'type', headerName: 'Type', width: 120 },
    { field: 'format', headerName: 'Format', width: 100 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'created_at', headerName: 'Created', flex: 1 },
    {
      field: 'actions',
      headerName: '',
      width: 140,
      renderCell: (params) => (
        <Button
          size="small"
          disabled={params.row.status !== 'ready'}
          onClick={() => download(params.row.id)}
        >
          Download
        </Button>
      ),
    },
  ];

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Reports</Typography>
      <Stack direction="row" spacing={1} alignItems="center">
        <TextField select size="small" label="Format" value={format} onChange={(e) => setFormat(e.target.value)} sx={{ width: 160 }}>
          {['csv', 'excel', 'pdf'].map((f) => (
            <MenuItem key={f} value={f}>{f.toUpperCase()}</MenuItem>
          ))}
        </TextField>
        <Button variant="contained" onClick={() => createMutation.mutate()}>
          Generate report
        </Button>
      </Stack>
      <DataGrid
        autoHeight
        rows={data?.items || []}
        columns={columns}
        loading={isLoading}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 2 }}
      />
    </Stack>
  );
}
