import { Alert, Box, Button, Stack, Typography } from '@mui/material';
import { memo } from 'react';
import ApplySessionTimeline from '../automation/ApplySessionTimeline';

export type BlockerItem = {
  id?: string;
  application_id?: string;
  portal_id?: string;
  job_id?: string;
  blocker_type?: string;
  status?: string;
  title?: string;
  company?: string;
  portal?: string;
  error_message?: string;
  unknown_questions?: string[];
  session_steps?: Array<Record<string, unknown>>;
};

function actionLabel(type?: string) {
  if (type === 'otp') return 'Enter OTP';
  if (type === 'unknown_question') return 'Answer';
  if (type === 'captcha') return 'Resolve';
  if (type === 'login_expired' || type === 'portal_paused') return 'Re-auth';
  return 'Fix';
}

function BlockersInbox({
  blockers,
  onAction,
}: {
  blockers: BlockerItem[];
  onAction: (blocker: BlockerItem) => void;
}) {
  if (!blockers.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        No blockers — automation is clear.
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      {blockers.map((b) => (
        <Alert
          key={b.id || b.application_id || b.portal_id}
          severity={b.blocker_type === 'login_expired' ? 'error' : 'warning'}
          action={
            <Button color="inherit" size="small" onClick={() => onAction(b)}>
              {actionLabel(b.blocker_type)}
            </Button>
          }
        >
          <Typography variant="subtitle2">
            {b.title || 'Blocker'}
            {b.portal ? ` · ${b.portal}` : ''}
          </Typography>
          <Typography variant="body2">{b.error_message || b.blocker_type}</Typography>
          {Array.isArray(b.session_steps) && b.session_steps.length > 0 ? (
            <Box sx={{ mt: 1 }}>
              <ApplySessionTimeline steps={b.session_steps as never[]} dense />
            </Box>
          ) : null}
        </Alert>
      ))}
    </Stack>
  );
}

export default memo(BlockersInbox);
