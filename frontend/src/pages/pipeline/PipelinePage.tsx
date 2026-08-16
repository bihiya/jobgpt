import { Box, Chip, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { applicationsApi, jobsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import { type LiveApplication } from '../../components/digest/LiveApplyTray';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { useRequireAuth } from '../../hooks/useRequireAuth';
import { useToast } from '../../hooks/useToast';
import { mergeApplySnapshots, pipelineHasLiveApply, type ApplySnapshot } from '../../lib/applyLive';
import PipelineJobCard from './PipelineJobCard';
import {
  PIPELINE_COLUMNS,
  moveJobInColumns,
  shouldQueueApply,
  statusForColumn,
  type PipeJob,
  type PipelineColumnKey,
  type PipelineColumnsState,
} from './pipelineColumns';

const COLUMN_ACCENT: Record<PipelineColumnKey, 'primary' | 'secondary' | 'info' | 'success' | 'warning'> = {
  fetched: 'info',
  queued: 'warning',
  applied: 'success',
  interview: 'secondary',
  shortlisted: 'primary',
};

function PipelinePage() {
  const queryClient = useQueryClient();
  const { requireAuth } = useRequireAuth();
  const { apiError, success } = useToast();
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const [drawerLive, setDrawerLive] = useState<ApplySnapshot | null>(null);
  const [dragging, setDragging] = useState<{ id: string; from: PipelineColumnKey } | null>(null);
  const [overColumn, setOverColumn] = useState<PipelineColumnKey | null>(null);
  const draggedRef = useRef(false);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['pipeline'],
    queryFn: async () => (await jobsApi.pipeline()).data,
    refetchInterval: (query) =>
      pipelineHasLiveApply(query.state.data?.columns as PipelineColumnsState | undefined) ? 4000 : false,
  });

  const appsQ = useQuery({
    queryKey: ['applications', 'pipeline'],
    queryFn: async () => (await applicationsApi.list({ page_size: 100 })).data,
    refetchInterval: (query) => {
      const items = (query.state.data as { items?: LiveApplication[] } | undefined)?.items || [];
      return items.some((app) =>
        ['pending', 'in_progress', 'retrying', 'needs_input', 'needs_otp', 'needs_account'].includes(app.status),
      )
        ? 4000
        : false;
    },
  });

  const liveByJob = useMemo(() => {
    const map = new Map<string, ApplySnapshot>();
    for (const app of (appsQ.data?.items || []) as ApplySnapshot[]) {
      if (app.job_id) map.set(app.job_id, app);
    }
    return map;
  }, [appsQ.data]);

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['pipeline'] });
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    queryClient.invalidateQueries({ queryKey: ['applications'] });
    queryClient.invalidateQueries({ queryKey: ['weekly-story'] });
  }, [queryClient]);

  const move = useMutation({
    mutationFn: ({ id, column }: { id: string; column: PipelineColumnKey; from: PipelineColumnKey }) =>
      jobsApi.move(id, { column }),
    meta: { errorMessage: 'Could not move job' },
    onMutate: async ({ id, column, from }) => {
      await queryClient.cancelQueries({ queryKey: ['pipeline'] });
      const previous = queryClient.getQueryData(['pipeline']);
      queryClient.setQueryData(['pipeline'], (old: { columns?: PipelineColumnsState; counts?: Record<string, number> } | undefined) => {
        if (!old?.columns) return old;
        const nextStatus = statusForColumn(column);
        const columns = moveJobInColumns(old.columns, id, from, column, nextStatus);
        const counts = { ...(old.counts || {}) };
        counts[from] = Math.max(0, (counts[from] ?? 0) - (from === column ? 0 : 1));
        counts[column] = (counts[column] ?? 0) + (from === column ? 0 : 1);
        return { ...old, columns, counts };
      });
      return { previous };
    },
    onSuccess: (res) => {
      if (res.data?.queued) {
        success('Applying…');
      } else {
        success('Stage updated');
      }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['pipeline'], context.previous);
      }
    },
    onSettled: invalidate,
  });

  const cancel = useMutation({
    mutationFn: (id: string) => applicationsApi.cancel(id),
    meta: { successMessage: 'Apply cancelled', errorMessage: 'Could not cancel' },
    onSettled: invalidate,
  });

  const retry = useMutation({
    mutationFn: (id: string) => applicationsApi.retry(id),
    meta: { successMessage: 'Retry queued', errorMessage: 'Could not retry' },
    onSettled: invalidate,
  });

  const columns = useMemo<PipelineColumnsState>(() => data?.columns || {}, [data]);
  const counts = useMemo(() => data?.counts || {}, [data]);

  const requestMove = useCallback(
    (job: PipeJob, from: PipelineColumnKey, to: PipelineColumnKey) => {
      if (from === to) return;
      if (!requireAuth(to === 'queued' ? 'Sign in to apply' : 'Sign in to move pipeline stages')) {
        return;
      }
      move.mutate({ id: job.id, column: to, from });
    },
    [move, requireAuth],
  );

  const applyFromDrawer = useMutation({
    mutationFn: (id: string) => applicationsApi.create({ job_id: id }),
    meta: { successMessage: 'Applying…', errorMessage: 'Could not apply' },
    onSuccess: () => {
      setDrawerJob(null);
      setDrawerLive(null);
    },
    onSettled: invalidate,
  });

  const openJob = useCallback(
    async (id: string, live?: ApplySnapshot) => {
      try {
        const { data: full } = await jobsApi.get(id);
        setDrawerLive(live || null);
        setDrawerJob(full);
      } catch (err) {
        apiError(err, 'Could not open job');
      }
    },
    [apiError],
  );

  return (
    <PageShell spacing={2} loading={isLoading} fetching={!isLoading && isFetching}>
      <Box>
        <Typography variant="h4">
          Pipeline
        </Typography>
        <Typography color="text.secondary">
          Click Apply on a fetched job. Drag to change stages. Open a card to see every apply step.
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(5, minmax(0, 1fr))' },
          alignItems: 'stretch',
        }}
      >
        {PIPELINE_COLUMNS.map((col) => {
          const jobs: PipeJob[] = columns[col.key] || [];
          const accent = COLUMN_ACCENT[col.key];
          const isOver = overColumn === col.key && dragging && dragging.from !== col.key;
          const willAutoApply = Boolean(dragging && shouldQueueApply(dragging.from, col.key));
          return (
            <Box
              key={col.key}
              onDragOver={(e) => {
                e.preventDefault();
                setOverColumn(col.key);
              }}
              onDragLeave={() => {
                setOverColumn((current) => (current === col.key ? null : current));
              }}
              onDrop={(e) => {
                e.preventDefault();
                setOverColumn(null);
                const raw = e.dataTransfer.getData('application/json') || e.dataTransfer.getData('text/plain');
                setDragging(null);
                if (!raw) return;
                try {
                  const payload = JSON.parse(raw) as { id: string; from: PipelineColumnKey };
                  const job = (columns[payload.from] || []).find((item) => item.id === payload.id);
                  if (!job) return;
                  requestMove(job, payload.from, col.key);
                } catch {
                  /* ignore malformed drag payload */
                }
              }}
              sx={{
                p: 1.5,
                borderRadius: 3,
                border: '1px solid',
                borderColor: isOver ? `${accent}.main` : 'divider',
                bgcolor: (t) =>
                  alpha(t.palette.background.paper, isOver ? 0.98 : 0.9),
                boxShadow: (t) =>
                  isOver ? `0 0 0 2px ${alpha(t.palette[accent].main, 0.45)}` : 'none',
                minHeight: { xs: 220, md: 420 },
                maxHeight: { md: '72vh' },
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.75 }}>
                <Typography sx={{ fontWeight: 800 }}>{col.label}</Typography>
                <Chip size="small" color={accent} label={counts[col.key] ?? jobs.length} />
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1.25, display: 'block' }}>
                {isOver ? (willAutoApply ? 'Drop to apply' : col.dropHint) : col.hint}
              </Typography>
              <Stack spacing={1} sx={{ flex: 1 }}>
                {jobs.map((job) => {
                  const live = mergeApplySnapshots(job.application, liveByJob.get(job.id));
                  return (
                    <PipelineJobCard
                      key={job.id}
                      job={job}
                      column={col.key}
                      live={live}
                      dragging={dragging?.id === job.id}
                      onOpen={(id) => {
                        if (draggedRef.current) return;
                        void openJob(id, live);
                      }}
                      onApply={
                        col.key === 'fetched'
                          ? () => requestMove(job, 'fetched', 'queued')
                          : undefined
                      }
                      onCancel={(applicationId) => {
                        if (!requireAuth('Sign in to cancel an apply')) return;
                        cancel.mutate(applicationId);
                      }}
                      onRetry={(applicationId) => {
                        if (!requireAuth('Sign in to retry an apply')) return;
                        retry.mutate(applicationId);
                      }}
                      cancelBusy={cancel.isPending && cancel.variables === live?.id}
                      retryBusy={retry.isPending && retry.variables === live?.id}
                      onDragStart={(e) => {
                        draggedRef.current = true;
                        setDragging({ id: job.id, from: col.key });
                        e.dataTransfer.effectAllowed = 'move';
                        e.dataTransfer.setData(
                          'application/json',
                          JSON.stringify({ id: job.id, from: col.key }),
                        );
                        e.dataTransfer.setData('text/plain', JSON.stringify({ id: job.id, from: col.key }));
                      }}
                      onDragEnd={() => {
                        setDragging(null);
                        setOverColumn(null);
                        window.setTimeout(() => {
                          draggedRef.current = false;
                        }, 0);
                      }}
                    />
                  );
                })}
                {jobs.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {col.key === 'queued' ? 'Apply a fetched job to start' : 'Empty'}
                  </Typography>
                )}
              </Stack>
            </Box>
          );
        })}
      </Box>

      <JobDetailDrawer
        open={!!drawerJob}
        job={drawerJob}
        liveApplication={drawerLive}
        onClose={() => {
          setDrawerJob(null);
          setDrawerLive(null);
        }}
        applyBusy={applyFromDrawer.isPending}
        onApply={(id) => {
          if (!requireAuth('Sign in to apply')) return;
          applyFromDrawer.mutate(id);
        }}
      />
    </PageShell>
  );
}

export default memo(PipelinePage);
