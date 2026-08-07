import {
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { portalsApi } from '../../api';
import PageShell from '../../components/common/PageShell';

const PORTALS = [
  'linkedin', 'naukri', 'indeed', 'foundit', 'wellfound', 'greenhouse',
  'lever', 'ashby', 'workday', 'smartrecruiters', 'oracle', 'sap_successfactors', 'taleo',
];

export default function PortalsPage() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('linkedin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['portals'],
    queryFn: async () => (await portalsApi.list()).data,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      portalsApi.create({
        name,
        credentials: { username, password },
      }),
    meta: { successMessage: 'Portal connected', errorMessage: 'Could not connect portal' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portals'] });
      setOpen(false);
    },
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => portalsApi.sync(id),
    meta: { successMessage: 'Sync started', errorMessage: 'Sync failed' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portals'] }),
  });

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Portal', flex: 1, minWidth: 120 },
    {
      field: 'status',
      headerName: 'Status',
      width: 140,
      renderCell: (params) => (
        <Chip
          size="small"
          label={params.value}
          color={params.value === 'connected' ? 'success' : params.value === 'error' ? 'error' : 'default'}
        />
      ),
    },
    { field: 'last_sync_at', headerName: 'Last sync', flex: 1, minWidth: 140 },
    {
      field: 'actions',
      headerName: '',
      width: 140,
      renderCell: (params) => (
        <Button
          size="small"
          variant="outlined"
          disabled={syncMutation.isPending}
          onClick={() => syncMutation.mutate(params.row.id)}
        >
          {syncMutation.isPending ? 'Syncing…' : 'Sync'}
        </Button>
      ),
    },
  ];

  return (
    <PageShell
      loading={isLoading}
      fetching={!isLoading && isFetching}
      busy={createMutation.isPending || syncMutation.isPending}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Typography variant="h4">Job portals</Typography>
        <Button variant="contained" onClick={() => setOpen(true)}>Connect portal</Button>
      </Stack>
      <DataGrid
        autoHeight
        rows={data || []}
        columns={columns}
        loading={isFetching}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%' }}
      />

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Connect portal</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField select label="Portal" value={name} onChange={(e) => setName(e.target.value)} fullWidth>
              {PORTALS.map((p) => (
                <MenuItem key={p} value={p}>{p}</MenuItem>
              ))}
            </TextField>
            <TextField label="Username / Email" value={username} onChange={(e) => setUsername(e.target.value)} fullWidth />
            <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} fullWidth />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            Connect
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
