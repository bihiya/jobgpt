import { Alert, Box, Button, Chip, CircularProgress, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo } from 'react';
import { applicationsApi } from '../../api';
import {
  applyStatusLabel,
  isJobApplying,
  isLiveApplyStatus,
  isStaleApply,
  latestSessionStep,
  type ApplySnapshot,
} from '../../lib/applyLive';
import { fromNowLocal } from '../../utils/datetime';
import ApplySessionTimeline from '../automation/ApplySessionTimeline';

type Props = {
  jobId: string;
  jobStatus?: string;
  open: boolean;
  fallback?: ApplySnapshot | null;
};

function ApplySessionPanel({ jobId, jobStatus, open, fallback }: Props) {
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ['job-application', jobId],
    queryFn: async () => (await applicationsApi.forJob(jobId)).data,
    enabled: open && !!jobId,
    refetchInterval: (query) => {
      const item = (query.state.data as { items?: ApplySnapshot[] } | undefined)?.items?.[0];
      return isJobApplying(jobStatus, item?.status) ? 4000 : false;
    },
  });

  const live = (data?.items?.[0] as ApplySnapshot | undefined) || fallback || undefined;
  const applying = isJobApplying(jobStatus, live?.status);
  const stale = applying && isStaleApply(live?.updated_at);
  const steps = live?.session_steps || [];
  const latest = latestSessionStep(steps);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['job-application', jobId] });
    void queryClient.invalidateQueries({ queryKey: ['applications'] });
    void queryClient.invalidateQueries({ queryKey: ['pipeline'] });
    void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    void queryClient.invalidateQueries({ queryKey: ['job-activity', jobId] });
  };

  const retry = useMutation({
    mutationFn: (id: string) => applicationsApi.retry(id),
    meta: { successMessage: 'Retry queued', errorMessage: 'Could not retry' },
    onSettled: invalidate,
  });

  const cancel = useMutation({
    mutationFn: (id: string) => applicationsApi.cancel(id),
    meta: { successMessage: 'Apply cancelled', errorMessage: 'Could not cancel' },
    onSettled: invalidate,
  });

  if (!live && !applying) {
    return null;
  }

  return (
    <Box
      sx={{
        mb: 2,
        p: 1.75,
        borderRadius: 2.5,
        border: '1px solid',
        borderColor: stale ? 'error.main' : applying ? 'warning.main' : 'divider',
        bgcolor: (t) =>
          alpha(
            stale ? t.palette.error.main : applying ? t.palette.warning.main : t.palette.success.main,
            applying || stale ? 0.08 : 0.04,
          ),
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
        {applying && !stale ? <CircularProgress size={16} /> : null}
        <Typography variant="h6" sx={{ fontSize: '1rem' }}>
          Apply session
        </Typography>
        <Chip
          size="small"
          color={stale ? 'error' : applying ? 'warning' : live?.status === 'success' ? 'success' : 'default'}
          label={stale ? 'Stuck' : applyStatusLabel(live?.status || jobStatus)}
          sx={applying && !stale ? { animation: 'jp-pulse-soft 2.2s ease infinite' } : undefined}
        />
        {typeof live?.attempts === 'number' && live.attempts > 0 ? (
          <Chip size="small" variant="outlined" label={`Attempt ${live.attempts}`} />
        ) : null}
      </Stack>

      {applying && !stale && (
        <Box
          sx={{
            position: 'relative',
            overflow: 'hidden',
            height: 3,
            borderRadius: 1,
            mb: 1.25,
            bgcolor: 'action.hover',
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              inset: 0,
              width: '45%',
              background: (t) =>
                `linear-gradient(90deg, transparent, ${alpha(t.palette.warning.main, 0.9)}, transparent)`,
              animation: 'jp-live-sweep 1.4s ease-in-out infinite',
            }}
          />
        </Box>
      )}

      {latest ? (
        <Typography sx={{ fontWeight: 700, mb: 0.5 }}>
          {applying ? 'Now: ' : 'Last: '}
          {latest.label || latest.key}
          {latest.detail ? ` — ${latest.detail}` : ''}
        </Typography>
      ) : applying ? (
        <Typography color="text.secondary" sx={{ mb: 0.5 }}>
          Waiting for the apply worker to start…
        </Typography>
      ) : null}

      {live?.updated_at ? (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          Last update {fromNowLocal(live.updated_at)}
        </Typography>
      ) : null}

      {stale ? (
        <Alert severity="warning" sx={{ mb: 1.25 }}>
          No worker updates for a while — this apply looks stuck. Retry to start it again.
        </Alert>
      ) : null}

      {live?.error_message && (stale || !isLiveApplyStatus(live.status) || live.status?.startsWith('needs')) ? (
        <Alert severity={live.status?.startsWith('needs') ? 'warning' : 'error'} sx={{ mb: 1.25 }}>
          {live.error_message}
        </Alert>
      ) : null}

      <ApplySessionTimeline steps={steps} live={applying && !stale} />

      {live?.id && (applying || live.status === 'failed') ? (
        <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
          {(stale || live.status === 'failed' || live.status === 'pending') && (
            <Button
              size="small"
              variant="contained"
              disabled={retry.isPending}
              onClick={() => retry.mutate(live.id)}
            >
              Retry
            </Button>
          )}
          {isLiveApplyStatus(live.status) && (
            <Button
              size="small"
              color="inherit"
              disabled={cancel.isPending}
              onClick={() => cancel.mutate(live.id)}
            >
              Cancel
            </Button>
          )}
        </Stack>
      ) : null}
    </Box>
  );
}

export default memo(ApplySessionPanel);
