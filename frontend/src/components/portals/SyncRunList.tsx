import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useEffect, useMemo, useRef } from 'react';
import { formatWhen } from '../../utils/datetime';
import { shortSyncId, type SyncRun } from '../../utils/loginStory';

function outcomeColor(outcome: SyncRun['outcome']): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (outcome === 'success') return 'success';
  if (outcome === 'warning') return 'warning';
  if (outcome === 'error') return 'error';
  if (outcome === 'info') return 'info';
  return 'default';
}

function stepColor(level?: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (level === 'success') return 'success';
  if (level === 'warning') return 'warning';
  if (level === 'error') return 'error';
  if (level === 'info') return 'info';
  return 'default';
}

function useNewStepIds(stepIds: string[], resetKey?: string | null) {
  const seen = useRef(new Set<string>());
  const prevKey = useRef(resetKey);
  if (prevKey.current !== resetKey) {
    seen.current = new Set();
    prevKey.current = resetKey;
  }
  const incoming = stepIds.filter((id) => id && !seen.current.has(id));
  useEffect(() => {
    stepIds.forEach((id) => {
      if (id) seen.current.add(id);
    });
  }, [stepIds]);
  return useMemo(() => new Set(incoming), [incoming]);
}

export default function SyncRunList({
  runs,
  timeZone,
  emptyText = 'No syncs yet. Press Sync to start one.',
  showPortal = false,
  liveId = null,
  maxRuns,
}: {
  runs: SyncRun[];
  timeZone?: string;
  emptyText?: string;
  showPortal?: boolean;
  liveId?: string | null;
  maxRuns?: number;
}) {
  const visible = maxRuns ? runs.slice(0, maxRuns) : runs;
  const liveStepIds = useMemo(() => {
    const live = visible.find((run) => run.id === liveId);
    return (live?.steps || []).map((step) => step.id);
  }, [visible, liveId]);
  const newStepIds = useNewStepIds(liveStepIds, liveId);

  if (!visible.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText}
      </Typography>
    );
  }

  return (
    <Stack spacing={1}>
      {visible.map((run, runIdx) => {
        const panelId = run.id || `run-${runIdx}`;
        const live = Boolean(liveId && run.id === liveId);
        const finished = run.outcome === 'success' || run.outcome === 'error' || run.outcome === 'warning';
        return (
          <Accordion
            key={panelId}
            disableGutters
            elevation={0}
            defaultExpanded={runIdx === 0}
            expanded={live ? true : undefined}
            sx={{
              border: '1px solid',
              borderColor: live ? 'secondary.main' : 'divider',
              borderRadius: '14px !important',
              overflow: 'hidden',
              '&:before': { display: 'none' },
              bgcolor: 'background.paper',
              animation: runIdx === 0 ? 'jp-scale-in 0.35s cubic-bezier(0.22, 1, 0.36, 1)' : 'none',
              boxShadow: live
                ? (theme) => `0 0 0 1px ${alpha(theme.palette.secondary.main, 0.35)}`
                : 'none',
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 1.5 }}>
              <Stack spacing={0.25} sx={{ width: '100%', pr: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  {showPortal && (
                    <Typography sx={{ textTransform: 'capitalize', fontWeight: 700 }}>
                      {run.portal}
                    </Typography>
                  )}
                  <Chip
                    size="small"
                    label={`sync ${shortSyncId(run.id)}`}
                    variant="outlined"
                    sx={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontWeight: 700 }}
                  />
                  {live && !finished ? (
                    <Chip size="small" color="info" label="Live" sx={{ animation: 'jp-pulse-soft 1.8s ease infinite' }} />
                  ) : (
                    <Chip size="small" color={outcomeColor(run.outcome)} label={run.outcome} />
                  )}
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`${run.stepCount} step${run.stepCount === 1 ? '' : 's'}`}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {run.endedAt ? formatWhen(run.endedAt, timeZone) : '—'}
                  </Typography>
                </Stack>
                <Typography variant="body2" noWrap title={run.summary}>
                  {run.summary}
                </Typography>
              </Stack>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 1.5, pt: 0, pb: 1.5 }}>
              {live && !finished && (
                <Box sx={{ position: 'relative', overflow: 'hidden', height: 3, borderRadius: 1, mb: 1.25, bgcolor: 'action.hover' }}>
                  <Box
                    sx={{
                      position: 'absolute',
                      inset: 0,
                      width: '45%',
                      background: (t) =>
                        `linear-gradient(90deg, transparent, ${alpha(t.palette.secondary.main, 0.85)}, transparent)`,
                      animation: 'jp-live-sweep 1.4s ease-in-out infinite',
                    }}
                  />
                </Box>
              )}
              <Stack spacing={0.75}>
                {run.steps.map((step, idx) => {
                  const appear = live && newStepIds.has(step.id);
                  return (
                    <Stack
                      key={step.id || `${panelId}-${idx}`}
                      direction="row"
                      spacing={1}
                      alignItems="flex-start"
                      sx={{
                        animation: appear ? 'jp-step-in 0.38s cubic-bezier(0.22, 1, 0.36, 1)' : 'none',
                      }}
                    >
                      <Chip
                        size="small"
                        label={idx + 1}
                        color={stepColor(step.level)}
                        sx={{ minWidth: 36 }}
                      />
                      <Stack spacing={0} sx={{ minWidth: 0 }}>
                        <Typography variant="body2">{step.message || step.action}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatWhen(step.created_at, timeZone)}
                          {step.action ? ` · ${step.action}` : ''}
                        </Typography>
                      </Stack>
                    </Stack>
                  );
                })}
                {live && !finished && (
                  <Typography variant="caption" color="text.secondary" sx={{ pl: 5.5 }}>
                    Waiting for the next step…
                  </Typography>
                )}
              </Stack>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Stack>
  );
}
