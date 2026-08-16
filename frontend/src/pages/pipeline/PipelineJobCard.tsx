import DragIndicator from '@mui/icons-material/DragIndicator';
import { Box, Button, Chip, CircularProgress, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo, type DragEvent } from 'react';
import {
  applyStatusLabel,
  isJobApplying,
  isLiveApplyStatus,
  isStaleApply,
  latestSessionStep,
  type ApplySnapshot,
} from '../../lib/applyLive';
import { fromNowLocal } from '../../utils/datetime';
import type { PipeJob, PipelineColumnKey } from './pipelineColumns';

type Props = {
  job: PipeJob;
  column: PipelineColumnKey;
  live?: ApplySnapshot;
  dragging?: boolean;
  onOpen: (id: string) => void;
  onApply?: () => void;
  onCancel?: (applicationId: string) => void;
  onRetry?: (applicationId: string) => void;
  cancelBusy?: boolean;
  retryBusy?: boolean;
  onDragStart: (event: DragEvent<HTMLDivElement>) => void;
  onDragEnd: () => void;
};

function PipelineJobCard({
  job,
  column,
  live,
  dragging,
  onOpen,
  onApply,
  onCancel,
  onRetry,
  cancelBusy,
  retryBusy,
  onDragStart,
  onDragEnd,
}: Props) {
  const applying = isJobApplying(job.status, live?.status);
  const stale = applying && isStaleApply(live?.updated_at || job.updated_at);
  const steps = live?.session_steps || [];
  const latest = latestSessionStep(steps);
  const recent = steps.slice(-3);

  return (
    <Box
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      sx={{
        p: 1.25,
        borderRadius: 2,
        border: '1px solid',
        borderColor: stale ? 'error.main' : applying ? 'warning.main' : 'divider',
        cursor: 'grab',
        opacity: dragging ? 0.45 : 1,
        position: 'relative',
        overflow: 'hidden',
        transition: 'transform 0.15s ease, opacity 0.15s ease',
        '&:hover': { transform: 'translateY(-1px)' },
        '&:active': { cursor: 'grabbing' },
      }}
      onClick={() => onOpen(job.id)}
    >
      {applying && !stale && (
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 0,
            height: 3,
            overflow: 'hidden',
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
      <Stack direction="row" spacing={0.5} alignItems="flex-start">
        <DragIndicator fontSize="small" sx={{ mt: 0.15, color: 'text.disabled' }} />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography sx={{ fontWeight: 700, fontSize: '0.95rem' }}>{job.title}</Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {job.company}
            {job.portal ? ` · ${job.portal}` : ''}
          </Typography>
          {applying && (
            <Stack direction="row" spacing={0.75} alignItems="flex-start" sx={{ mt: 0.75 }}>
              {!stale ? <CircularProgress size={14} sx={{ mt: 0.25 }} /> : null}
              <Typography
                variant="caption"
                color={stale ? 'error.main' : 'warning.main'}
                sx={{ fontWeight: 700, display: 'block' }}
              >
                {stale
                  ? `Stuck — no update ${fromNowLocal(live?.updated_at || job.updated_at)}`
                  : latest
                    ? `${latest.label}${latest.detail ? ` — ${latest.detail}` : ''}`
                    : 'Waiting for worker…'}
              </Typography>
            </Stack>
          )}
          {!applying && latest && column === 'queued' && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              {latest.label}
              {latest.detail ? ` — ${latest.detail}` : ''}
            </Typography>
          )}
          {applying && recent.length > 1 && (
            <Stack spacing={0.25} sx={{ mt: 0.75, pl: 0.25 }}>
              {recent.slice(0, -1).map((step, idx) => (
                <Typography key={`${step.key}-${idx}`} variant="caption" color="text.disabled" display="block" noWrap>
                  {step.label}
                </Typography>
              ))}
            </Stack>
          )}
          <Stack direction="row" spacing={0.75} sx={{ mt: 0.75 }} alignItems="center" flexWrap="wrap" useFlexGap>
            <Chip size="small" label={`${Math.round((job.match_score || 0) * 100)}%`} />
            {applying && (
              <Chip
                size="small"
                color={stale ? 'error' : 'warning'}
                label={stale ? 'Stuck' : applyStatusLabel(live?.status || 'applying')}
                sx={stale ? undefined : { animation: 'jp-pulse-soft 2.2s ease infinite' }}
              />
            )}
            {column === 'fetched' && onApply && (
              <Button
                size="small"
                variant="contained"
                onClick={(e) => {
                  e.stopPropagation();
                  onApply();
                }}
              >
                Apply
              </Button>
            )}
            {column === 'queued' && live?.id && isLiveApplyStatus(live.status) && onCancel && (
              <Button
                size="small"
                color="inherit"
                disabled={cancelBusy}
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel(live.id);
                }}
              >
                Cancel
              </Button>
            )}
            {column === 'queued' && live?.id && (stale || live.status === 'failed') && onRetry && (
              <Button
                size="small"
                variant="outlined"
                disabled={retryBusy}
                onClick={(e) => {
                  e.stopPropagation();
                  onRetry(live.id);
                }}
              >
                Retry
              </Button>
            )}
          </Stack>
        </Box>
      </Stack>
    </Box>
  );
}

export default memo(PipelineJobCard);
