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
  const { data, isLoading } = useQuery({
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      setOpen(false);
      setForm(empty);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => companiesApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['companies'] }),
  });

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Company', flex: 1 },
    { field: 'platform', headerName: 'Platform', width: 140 },
    { field: 'priority', headerName: 'Priority', width: 100 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'career_url', headerName: 'Career URL', flex: 1.4 },
    {
      field: 'actions',
      headerName: '',
      width: 110,
      renderCell: (params) => (
        <Button color="error" size="small" onClick={() => deleteMutation.mutate(params.row.id)}>
          Delete
        </Button>
      ),
    },
  ];

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h4">Companies</Typography>
        <Button variant="contained" onClick={() => setOpen(true)}>
          Add company
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

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add company</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <TextField label="Career URL" value={form.career_url} onChange={(e) => setForm({ ...form, career_url: e.target.value })} />
            <TextField select label="Platform" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
              {['custom', 'greenhouse', 'lever', 'ashby', 'workday'].map((p) => (
                <MenuItem key={p} value={p}>{p}</MenuItem>
              ))}
            </TextField>
            <TextField label="Priority" type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} />
            <TextField label="Tags (comma separated)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => createMutation.mutate()} disabled={!form.name || !form.career_url}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
