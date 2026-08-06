import { Button, Stack, TextField, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { applicationsApi, jobsApi } from '../../api';

type Mode = 'all' | 'tracked' | 'applied' | 'history';

const fetchers = {
  all: jobsApi.list,
  tracked: jobsApi.tracked,
  applied: jobsApi.applied,
  history: jobsApi.history,
};

export default function JobsPage({ mode = 'all' }: { mode?: Mode }) {
  const [q, setQ] = useState('');
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['jobs', mode, q],
    queryFn: async () => (await fetchers[mode]({ q: q || undefined, page_size: 50 })).data,
  });

  const trackMutation = useMutation({
    mutationFn: (id: string) => jobsApi.track(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const applyMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.create({ job_id: id }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const columns: GridColDef[] = [
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
      width: 200,
      sortable: false,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={() => trackMutation.mutate(params.row.id)}>
            Track
          </Button>
          <Button size="small" variant="contained" onClick={() => applyMutation.mutate(params.row.id)}>
            Apply
          </Button>
        </Stack>
      ),
    },
  ];

  const titleMap = {
    all: 'Jobs',
    tracked: 'Tracked jobs',
    applied: 'Applied jobs',
    history: 'Job history',
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h4">{titleMap[mode]}</Typography>
      <TextField
        size="small"
        placeholder="Search title, company, description"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        sx={{ maxWidth: 420 }}
      />
      <DataGrid
        autoHeight
        rows={data?.items || []}
        columns={columns}
        loading={isLoading}
        pageSizeOptions={[10, 25, 50]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        disableRowSelectionOnClick
        sx={{ bgcolor: 'background.paper', borderRadius: 2 }}
      />
    </Stack>
  );
}
