import { Box, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useMemo, useState } from 'react';
import { jobsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import PageSkeleton from '../../components/common/PageSkeleton';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { useRequireAuth } from '../../hooks/useRequireAuth';
import { useToast } from '../../hooks/useToast';

const COLUMNS: { key: string; label: string; next?: string[] }[] = [
  { key: 'matched', label: 'Matched', next: ['approved', 'rejected'] },
  { key: 'approved', label: 'Approved', next: ['applied', 'rejected'] },
  { key: 'applied', label: 'Applied', next: ['interview', 'rejected'] },
  { key: 'interview', label: 'Interview', next: ['offer', 'rejected'] },
  { key: 'offer', label: 'Offer', next: [] },
  { key: 'rejected', label: 'Rejected', next: [] },
];

type PipeJob = {
  id: string;
  title: string;
  company: string;
  portal: string;
  status: string;
  match_score: number;
  location?: string;
};

function PipelinePage() {
  const queryClient = useQueryClient();
  const { requireAuth } = useRequireAuth();
  const { apiError } = useToast();
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['pipeline'],
    queryFn: async () => (await jobsApi.pipeline()).data,
  });

  const move = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => jobsApi.update(id, { status }),
    meta: { successMessage: 'Stage updated', errorMessage: 'Could not move job' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['weekly-story'] });
    },
  });

  const columns = useMemo(() => data?.columns || {}, [data]);
  const counts = useMemo(() => data?.counts || {}, [data]);

  if (isLoading) return <PageSkeleton />;

  return (
    <PageShell spacing={2}>
      <Box>
        <Typography variant="h4" sx={{ fontFamily: '"Fraunces", Georgia, serif' }}>
          Pipeline
        </Typography>
        <Typography color="text.secondary">
          Matched → Approved → Applied → Interview → Offer → Rejected
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridAutoFlow: 'column',
          gridAutoColumns: { xs: 'minmax(240px, 85%)', md: 'minmax(220px, 1fr)' },
          overflowX: 'auto',
          pb: 1,
        }}
      >
        {COLUMNS.map((col) => {
          const jobs: PipeJob[] = columns[col.key] || [];
          return (
            <Box
              key={col.key}
              sx={{
                p: 1.5,
                borderRadius: 3,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: (t) => alpha(t.palette.background.paper, 0.9),
                minHeight: 360,
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.25 }}>
                <Typography sx={{ fontWeight: 800 }}>{col.label}</Typography>
                <Chip size="small" label={counts[col.key] ?? jobs.length} />
              </Stack>
              <Stack spacing={1}>
                {jobs.map((job) => (
                  <Box
                    key={job.id}
                    sx={{
                      p: 1.25,
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: 'divider',
                      cursor: 'pointer',
                      transition: 'transform 0.15s ease',
                      '&:hover': { transform: 'translateY(-1px)' },
                    }}
                    onClick={async () => {
                      try {
                        const { data: full } = await jobsApi.get(job.id);
                        setDrawerJob(full);
                      } catch (err) {
                        apiError(err, 'Could not open job');
                      }
                    }}
                  >
                    <Typography sx={{ fontWeight: 700, fontSize: '0.95rem' }}>{job.title}</Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {job.company}
                    </Typography>
                    <Stack direction="row" spacing={0.75} sx={{ mt: 0.75 }} alignItems="center">
                      <Chip size="small" label={`${Math.round((job.match_score || 0) * 100)}%`} />
                      {col.next && col.next.length > 0 && (
                        <TextField
                          select
                          size="small"
                          label="Move"
                          value=""
                          sx={{ minWidth: 110 }}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => {
                            if (!requireAuth('Sign in to move pipeline stages')) return;
                            move.mutate({ id: job.id, status: e.target.value });
                          }}
                        >
                          {col.next.map((n) => (
                            <MenuItem key={n} value={n}>
                              {n}
                            </MenuItem>
                          ))}
                        </TextField>
                      )}
                    </Stack>
                  </Box>
                ))}
                {jobs.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    Empty
                  </Typography>
                )}
              </Stack>
            </Box>
          );
        })}
      </Box>

      <JobDetailDrawer open={!!drawerJob} job={drawerJob} onClose={() => setDrawerJob(null)} />
    </PageShell>
  );
}

export default memo(PipelinePage);
