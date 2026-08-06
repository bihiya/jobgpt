import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
  Chip,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useCallback, useMemo, useState } from 'react';
import { questionsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import PageSkeleton from '../../components/common/PageSkeleton';
import { useRequireAuth } from '../../hooks/useRequireAuth';

function QuestionsPage() {
  const queryClient = useQueryClient();
  const { requireAuth } = useRequireAuth();
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['questions'],
    queryFn: async () => (await questionsApi.list()).data,
  });

  const upsert = useMutation({
    mutationFn: () => questionsApi.upsert({ question, answer, tags: ['manual'] }),
    meta: { successMessage: 'Answer saved', errorMessage: 'Could not save answer' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      setOpen(false);
      setQuestion('');
      setAnswer('');
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => questionsApi.remove(id),
    meta: { successMessage: 'Deleted', errorMessage: 'Could not delete' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['questions'] }),
  });

  const openCreate = useCallback(() => {
    if (!requireAuth('Sign in to manage your question bank')) return;
    setOpen(true);
  }, [requireAuth]);

  const columns: GridColDef[] = useMemo(
    () => [
      { field: 'question', headerName: 'Question', flex: 1.4, minWidth: 200 },
      { field: 'answer', headerName: 'Answer', flex: 1, minWidth: 160 },
      {
        field: 'use_count',
        headerName: 'Used',
        width: 90,
        renderCell: (p) => <Chip size="small" label={p.value || 0} />,
      },
      {
        field: 'actions',
        headerName: '',
        width: 110,
        sortable: false,
        renderCell: (params) => (
          <Button
            size="small"
            color="inherit"
            onClick={() => {
              if (!requireAuth('Sign in to edit the question bank')) return;
              remove.mutate(params.row.id);
            }}
          >
            Delete
          </Button>
        ),
      },
    ],
    [remove, requireAuth],
  );

  if (isLoading) return <PageSkeleton />;

  return (
    <PageShell>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2}>
        <div>
          <Typography variant="h4">Question bank</Typography>
          <Typography color="text.secondary">
            Answer once — automation reuses these on every apply. Unknown fields pause until you teach
            them.
          </Typography>
        </div>
        <Button variant="contained" onClick={openCreate}>
          Add answer
        </Button>
      </Stack>

      <DataGrid
        autoHeight
        rows={Array.isArray(data) ? data : []}
        columns={columns}
        getRowId={(row) => row.id}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%', mt: 2 }}
        disableRowSelectionOnClick
      />

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Save answer</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Question / form label"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              fullWidth
              autoFocus
            />
            <TextField
              label="Your answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              fullWidth
              multiline
              minRows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!question.trim() || !answer.trim() || upsert.isPending}
            onClick={() => upsert.mutate()}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}

export default memo(QuestionsPage);
