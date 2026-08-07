import {
  Button,
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
import { companiesApi } from '../../api';
import PageShell from '../../components/common/PageShell';

const empty = {
  name: '',
  career_url: '',
  platform: 'custom',
  priority: 1,
  tags: '',
  status: 'active',
};

export default function CompaniesPage() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const queryClient = useQueryClient();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['companies'],
    queryFn: async () => (await companiesApi.list()).data,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      companiesApi.create({
        ...form,
        tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
        priority: Number(form.priority),
      }),
    meta: { successMessage: 'Company added', errorMessage: 'Could not add company' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      setOpen(false);
      setForm(empty);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => companiesApi.remove(id),
    meta: { successMessage: 'Company removed', errorMessage: 'Could not delete company' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['companies'] }),
  });

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Company', flex: 1, minWidth: 140 },
    { field: 'platform', headerName: 'Platform', width: 140 },
    { field: 'priority', headerName: 'Priority', width: 100 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'career_url', headerName: 'Career URL', flex: 1.4, minWidth: 160 },
    {
      field: 'actions',
      headerName: '',
      width: 110,
      renderCell: (params) => (
        <Button
          color="error"
          size="small"
          disabled={deleteMutation.isPending}
          onClick={() => deleteMutation.mutate(params.row.id)}
        >
          {deleteMutation.isPending ? '…' : 'Delete'}
        </Button>
      ),
    },
  ];

  return (
    <PageShell
      loading={isLoading}
      fetching={!isLoading && isFetching}
      busy={createMutation.isPending || deleteMutation.isPending}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Typography variant="h4">Companies</Typography>
        <Button variant="contained" onClick={() => setOpen(true)}>
          Add company
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

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add company</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} fullWidth />
            <TextField label="Career URL" value={form.career_url} onChange={(e) => setForm({ ...form, career_url: e.target.value })} fullWidth />
            <TextField select label="Platform" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })} fullWidth>
              {['custom', 'greenhouse', 'lever', 'ashby', 'workday'].map((p) => (
                <MenuItem key={p} value={p}>{p}</MenuItem>
              ))}
            </TextField>
            <TextField label="Priority" type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} fullWidth />
            <TextField label="Tags (comma separated)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} fullWidth />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => createMutation.mutate()} disabled={!form.name || !form.career_url || createMutation.isPending}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
