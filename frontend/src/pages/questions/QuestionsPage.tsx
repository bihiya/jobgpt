import { Search } from '@mui/icons-material';
import {
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  InputAdornment,
  Stack,
  TextField,
  Typography,
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
  const [search, setSearch] = useState('');
  const [learnedOnly, setLearnedOnly] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['questions'],
    queryFn: async () => (await questionsApi.list()).data,
  });

  const upsert = useMutation({
    mutationFn: () =>
      questionsApi.upsert({
        question,
        answer,
        tags: learnedOnly ? ['from_apply'] : ['manual'],
      }),
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

  const rows = useMemo(() => {
    const list = Array.isArray(data) ? data : [];
    const q = search.trim().toLowerCase();
    return list.filter((item: Record<string, unknown>) => {
      const tags = (item.tags as string[]) || [];
      if (learnedOnly && !tags.includes('from_apply')) return false;
      if (!q) return true;
      const hay = `${item.question || ''} ${item.answer || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [data, search, learnedOnly]);

  const learnedCount = useMemo(() => {
    const list = Array.isArray(data) ? data : [];
    return list.filter((i: Record<string, unknown>) =>
      ((i.tags as string[]) || []).includes('from_apply'),
    ).length;
  }, [data]);

  const columns: GridColDef[] = useMemo(
    () => [
      { field: 'question', headerName: 'Question', flex: 1.4, minWidth: 200 },
      { field: 'answer', headerName: 'Answer', flex: 1, minWidth: 160 },
      {
        field: 'tags',
        headerName: 'Source',
        width: 140,
        renderCell: (p) => {
          const tags = (p.value as string[]) || [];
          if (tags.includes('from_apply')) {
            return <Chip size="small" color="success" label="Learned from apply" />;
          }
          return <Chip size="small" variant="outlined" label={tags[0] || 'manual'} />;
        },
      },
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
            Searchable Q&A — answers learned from the last apply resume here automatically.
          </Typography>
        </div>
        <Button variant="contained" onClick={openCreate}>
          Add answer
        </Button>
      </Stack>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ sm: 'center' }}>
        <TextField
          size="small"
          placeholder="Search questions or answers…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: { sm: 280 }, flex: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <Chip
          clickable
          color={learnedOnly ? 'success' : 'default'}
          variant={learnedOnly ? 'filled' : 'outlined'}
          label={`Learned from apply (${learnedCount})`}
          onClick={() => setLearnedOnly((v) => !v)}
        />
      </Stack>

      <DataGrid
        autoHeight
        rows={rows}
        columns={columns}
        getRowId={(row) => row.id}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%', mt: 1 }}
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
