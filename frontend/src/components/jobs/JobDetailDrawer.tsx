import {
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { memo, useMemo } from 'react';
import { activityApi } from '../../api';
import ActivityTimeline from '../activity/ActivityTimeline';

export type JobDetail = {
  id: string;
  title: string;
  company: string;
  location: string;
  portal: string;
  status: string;
  match_score: number;
  description?: string;
  skills?: string[];
  apply_url?: string;
  match_breakdown?: {
    total?: number;
    skills?: number;
    keywords?: number;
    location?: number;
    experience?: number;
    llm_score?: number | null;
    llm_rationale?: string;
    reasons?: string[];
    missing_skills?: string[];
  };
};

const APPLYABLE = new Set([
  'new',
  'matched',
  'awaiting_approval',
  'tracked',
  'failed',
  'approved',
]);

type Props = {
  open: boolean;
  job: JobDetail | null;
  onClose: () => void;
  onApply?: (jobId: string) => void;
  applyBusy?: boolean;
};

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <Box sx={{ mb: 1.5 }}>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2">{pct}%</Typography>
      </Stack>
      <LinearProgress variant="determinate" value={pct} sx={{ height: 8, borderRadius: 4 }} />
    </Box>
  );
}

function JobDetailDrawerComponent({ open, job, onClose, onApply, applyBusy }: Props) {
  const breakdown = job?.match_breakdown;
  const reasons = useMemo(() => breakdown?.reasons || [], [breakdown]);
  const { data: activity } = useQuery({
    queryKey: ['job-activity', job?.id],
    queryFn: async () => (await activityApi.forJob(job!.id, { page_size: 50 })).data,
    enabled: open && !!job?.id,
  });
  const canApply = Boolean(onApply && job && APPLYABLE.has(job.status));

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 440 } } }}>
      {job && (
        <Box sx={{ p: 3 }}>
          <Typography variant="h5" sx={{ mb: 0.5 }}>
            {job.title}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {job.company} · {job.location}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
            <Chip label={job.portal} size="small" />
            <Chip label={job.status} size="small" color="primary" variant="outlined" />
            <Chip label={`${Math.round((job.match_score || 0) * 100)}% match`} size="small" color="success" />
          </Stack>

          {canApply && (
            <Button
              variant="contained"
              fullWidth
              sx={{ mb: 2 }}
              disabled={applyBusy}
              onClick={() => onApply?.(job.id)}
            >
              Apply
            </Button>
          )}

          <Typography variant="h6" sx={{ mb: 1 }}>
            Why this score
          </Typography>
          <ScoreBar label="Skills" value={breakdown?.skills || 0} />
          <ScoreBar label="Keywords" value={breakdown?.keywords || 0} />
          <ScoreBar label="Location" value={breakdown?.location || 0} />
          <ScoreBar label="Experience" value={breakdown?.experience || 0} />
          {breakdown?.llm_score != null && (
            <ScoreBar label="LLM ranking" value={breakdown.llm_score} />
          )}

          <Divider sx={{ my: 2 }} />
          <List dense>
            {reasons.map((reason) => (
              <ListItem key={reason} disableGutters>
                <ListItemText primary={reason} />
              </ListItem>
            ))}
          </List>
          {!!breakdown?.missing_skills?.length && (
            <>
              <Typography variant="subtitle2" sx={{ mt: 1 }}>
                Missing skills
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                {breakdown.missing_skills.map((skill) => (
                  <Chip key={skill} size="small" label={skill} variant="outlined" />
                ))}
              </Stack>
            </>
          )}
          {breakdown?.llm_rationale && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {breakdown.llm_rationale}
            </Typography>
          )}

          <Divider sx={{ my: 2 }} />
          <Typography variant="h6" sx={{ mb: 1 }}>
            Activity
          </Typography>
          <ActivityTimeline
            dense
            items={activity?.items || []}
            emptyText="No activity for this job yet."
          />
        </Box>
      )}
    </Drawer>
  );
}

export default memo(JobDetailDrawerComponent);
