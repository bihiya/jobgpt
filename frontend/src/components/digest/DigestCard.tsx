import { Box, Button, Chip, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo } from 'react';

export type DigestJob = {
  id: string;
  approval_id?: string;
  title: string;
  company: string;
  portal?: string;
  match_score: number;
  summary?: string;
  match_breakdown?: {
    reasons?: string[];
    llm_rationale?: string;
  };
  easy_apply?: boolean;
};

type Props = {
  job: DigestJob;
  onApprove: () => void;
  onSkip: () => void;
  onOpen: () => void;
  busy?: boolean;
};

function DigestCard({ job, onApprove, onSkip, onOpen, busy }: Props) {
  const score = Math.round((job.match_score || 0) * 100);
  const why =
    job.match_breakdown?.reasons?.[0] ||
    job.match_breakdown?.llm_rationale ||
    job.summary ||
    'Strong match for your profile';
  const easy =
    job.easy_apply ??
    ['linkedin', 'indeed'].includes((job.portal || '').toLowerCase());

  return (
    <Box
      sx={{
        p: 2.25,
        borderRadius: 3,
        border: '1px solid',
        borderColor: 'divider',
        background: (t) =>
          `linear-gradient(145deg, ${t.palette.background.paper}, ${alpha(t.palette.secondary.main, 0.07)})`,
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: (t) => `0 12px 28px ${alpha(t.palette.primary.main, 0.12)}`,
        },
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h6" sx={{ fontFamily: '"Fraunces", Georgia, serif', lineHeight: 1.25 }}>
            {job.title}
          </Typography>
          <Typography color="text.secondary" noWrap>
            {job.company}
            {job.portal ? ` · ${job.portal}` : ''}
          </Typography>
        </Box>
        <Chip
          label={`${score}%`}
          color={score >= 85 ? 'success' : score >= 70 ? 'warning' : 'default'}
          sx={{ fontWeight: 800 }}
        />
      </Stack>

      <Typography variant="body2" sx={{ mt: 1.5, mb: 1.5 }}>
        {why}
      </Typography>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.75 }}>
        {easy && <Chip size="small" color="info" label="Easy Apply" />}
        {job.portal && <Chip size="small" variant="outlined" label={job.portal} />}
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Button size="small" variant="contained" disabled={busy} onClick={onApprove}>
          Approve
        </Button>
        <Button size="small" color="inherit" disabled={busy} onClick={onSkip}>
          Skip
        </Button>
        <Button size="small" onClick={onOpen}>
          Open
        </Button>
      </Stack>
    </Box>
  );
}

export default memo(DigestCard);
