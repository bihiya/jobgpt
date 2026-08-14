import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import { formatWhen } from '../../utils/datetime';
import type { SyncRun } from '../../utils/loginStory';

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

export default function SyncRunList({
  runs,
  timeZone,
  emptyText = 'No syncs recorded yet. Run Sync to record each login and fetch step.',
  showPortal = false,
}: {
  runs: SyncRun[];
  timeZone?: string;
  emptyText?: string;
  showPortal?: boolean;
}) {
  if (!runs.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText}
      </Typography>
    );
  }

  return (
    <Stack spacing={0.75}>
      {runs.map((run, runIdx) => {
        const panelId = run.id || `run-${runIdx}`;
        return (
          <Accordion
            key={panelId}
            disableGutters
            elevation={0}
            defaultExpanded={runIdx === 0}
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: '12px !important',
              '&:before': { display: 'none' },
              bgcolor: 'background.paper',
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
                  <Chip size="small" color={outcomeColor(run.outcome)} label={run.outcome} />
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
              <Stack spacing={0.75}>
                {run.steps.map((step, idx) => (
                  <Stack key={step.id || `${panelId}-${idx}`} direction="row" spacing={1} alignItems="flex-start">
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
                ))}
              </Stack>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Stack>
  );
}
