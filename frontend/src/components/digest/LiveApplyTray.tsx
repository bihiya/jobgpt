import { Box, Button, Chip, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo } from 'react';
import ApplySessionTimeline, {
  type SessionStep,
} from '../automation/ApplySessionTimeline';

export type LiveApplication = {
  id: string;
  job_id: string;
  status: string;
  session_steps?: SessionStep[];
  error_message?: string;
  title?: string;
  company?: string;
  portal?: string;
};

const LIVE = new Set(['pending', 'in_progress', 'retrying', 'needs_input', 'needs_otp']);

function LiveApplyTray({
  applications,
  onCancel,
  busyId,
}: {
  applications: LiveApplication[];
  onCancel: (id: string) => void;
  busyId?: string | null;
}) {
  const live = applications.filter((a) => LIVE.has(a.status));

  if (!live.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        No applies running right now.
      </Typography>
    );
  }

  return (
    <Stack spacing={1.5}>
      {live.map((app) => {
        const steps = app.session_steps || [];
        const latest = steps[steps.length - 1];
        return (
          <Box
            key={app.id}
            sx={{
              p: 1.75,
              borderRadius: 2.5,
              border: '1px solid',
              borderColor: 'divider',
              bgcolor: (t) => alpha(t.palette.info.main, 0.05),
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
              <Box>
                <Typography sx={{ fontWeight: 700 }}>
                  {app.title || `Job ${app.job_id.slice(0, 8)}`}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {[app.company, app.portal].filter(Boolean).join(' · ') || app.status}
                </Typography>
              </Box>
              <Chip
                size="small"
                label={app.status.replace(/_/g, ' ')}
                color={app.status.includes('needs') ? 'warning' : 'info'}
                sx={{
                  animation:
                    app.status === 'in_progress' ? 'jp-pulse-soft 2.2s ease infinite' : 'none',
                }}
              />
            </Stack>
            {latest && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                {latest.label}
                {latest.detail ? ` — ${latest.detail}` : ''}
              </Typography>
            )}
            {steps.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <ApplySessionTimeline steps={steps.slice(-4)} dense />
              </Box>
            )}
            <Button
              size="small"
              color="inherit"
              sx={{ mt: 1 }}
              disabled={busyId === app.id}
              onClick={() => onCancel(app.id)}
            >
              Cancel
            </Button>
          </Box>
        );
      })}
    </Stack>
  );
}

export default memo(LiveApplyTray);
