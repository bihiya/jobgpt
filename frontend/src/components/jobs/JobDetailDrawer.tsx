import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined';
import ScheduleOutlinedIcon from '@mui/icons-material/ScheduleOutlined';
import {
  Avatar,
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  IconButton,
  LinearProgress,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo, useMemo, type ReactNode } from 'react';
import { listingUrlFor } from '../../lib/jobListing';
import { jobDescriptionBody, parseJobDescription, type JobDescriptionBlock } from '../../lib/jobDescription';
import { formatLocal, fromNowLocal } from '../../utils/datetime';

export type JobDetail = {
  id: string;
  title: string;
  company: string;
  location: string;
  salary?: string;
  experience?: string;
  portal: string;
  status: string;
  match_score: number;
  description?: string;
  skills?: string[];
  apply_url?: string;
  listing_url?: string;
  external_id?: string;
  source?: string;
  fetched_at?: string;
  created_at?: string;
  metadata?: Record<string, unknown>;
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
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
          {label}
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
          {pct}%
        </Typography>
      </Stack>
      <LinearProgress variant="determinate" value={pct} sx={{ height: 8, borderRadius: 4 }} />
    </Box>
  );
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '148px 1fr' },
        columnGap: 2,
        rowGap: 0.25,
        py: 1.25,
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.secondary' }}>
        {label}
      </Typography>
      <Box sx={{ minWidth: 0, color: 'text.primary', fontSize: '0.95rem', lineHeight: 1.5 }}>
        {children}
      </Box>
    </Box>
  );
}

function DescriptionBlocks({ blocks }: { blocks: JobDescriptionBlock[] }) {
  return (
    <Box
      sx={{
        color: 'text.primary',
        '& p, & li': { fontSize: '15px', lineHeight: 1.65 },
        '& ul': { m: 0, pl: 2.5 },
        '& li': { mb: 0.75 },
      }}
    >
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          return (
            <Typography
              key={`${block.text}-${index}`}
              variant="subtitle1"
              sx={{ fontWeight: 800, mt: index === 0 ? 0 : 2.75, mb: 1, color: 'text.primary' }}
            >
              {block.text}
            </Typography>
          );
        }
        if (block.type === 'list') {
          return (
            <Box component="ul" key={`list-${index}`} sx={{ mb: 1.5 }}>
              {block.items.map((item) => (
                <Box component="li" key={item}>
                  {item}
                </Box>
              ))}
            </Box>
          );
        }
        return (
          <Typography key={`p-${index}`} component="p" sx={{ mb: 1.5, color: 'text.primary' }}>
            {block.text}
          </Typography>
        );
      })}
    </Box>
  );
}

function JobDetailDrawerComponent({ open, job, onClose, onApply, applyBusy }: Props) {
  const breakdown = job?.match_breakdown;
  const reasons = useMemo(() => breakdown?.reasons || [], [breakdown]);
  const listingUrl = useMemo(() => listingUrlFor(job), [job]);
  const descriptionBody = useMemo(
    () => (job ? jobDescriptionBody(job.description || '', job) : ''),
    [job],
  );
  const descriptionBlocks = useMemo(
    () => parseJobDescription(descriptionBody),
    [descriptionBody],
  );
  const canApply = Boolean(onApply && job && APPLYABLE.has(job.status));
  const posted = job?.fetched_at ? fromNowLocal(job.fetched_at) : '';
  const fetchedExact = job?.fetched_at ? formatLocal(job.fetched_at) : '';
  const companyInitial = (job?.company || '?').trim().slice(0, 1).toUpperCase() || '?';
  const portalLabel = job?.portal === 'linkedin' ? 'LinkedIn' : job?.portal || '';

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{
        paper: {
          sx: {
            width: { xs: '100%', sm: 560, md: 680 },
            bgcolor: 'background.paper',
            color: 'text.primary',
            backgroundImage: 'none',
            background: (theme) => theme.palette.background.paper,
          },
        },
      }}
    >
      {job && (
        <Box sx={{ px: { xs: 2.5, sm: 3.5 }, py: 2.5, pb: 5 }}>
          <Stack direction="row" justifyContent="flex-end" sx={{ mb: 0.5 }}>
            <IconButton onClick={onClose} aria-label="Close job details" size="small">
              <CloseIcon />
            </IconButton>
          </Stack>

          <Stack direction="row" spacing={2} alignItems="flex-start" sx={{ mb: 2 }}>
            <Avatar
              sx={{
                width: 56,
                height: 56,
                fontWeight: 800,
                bgcolor: (t) => alpha(t.palette.primary.main, 0.16),
                color: 'primary.main',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              {companyInitial}
            </Avatar>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography
                variant="body1"
                sx={{ fontWeight: 700, color: 'text.primary', lineHeight: 1.3 }}
              >
                {job.company}
              </Typography>
              <Typography
                variant="h4"
                sx={{
                  mt: 0.35,
                  mb: 1,
                  fontSize: { xs: '1.45rem', sm: '1.7rem' },
                  lineHeight: 1.2,
                  color: 'text.primary',
                }}
              >
                {job.title}
              </Typography>
              <Stack
                direction="row"
                spacing={1.5}
                flexWrap="wrap"
                useFlexGap
                sx={{ color: 'text.secondary', alignItems: 'center' }}
              >
                {job.location ? (
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <PlaceOutlinedIcon sx={{ fontSize: 18 }} />
                    <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                      {job.location}
                    </Typography>
                  </Stack>
                ) : null}
                {posted && posted !== '—' ? (
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <ScheduleOutlinedIcon sx={{ fontSize: 18 }} />
                    <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                      {posted}
                    </Typography>
                  </Stack>
                ) : null}
              </Stack>
            </Box>
          </Stack>

          {job.salary ? (
            <Box
              sx={{
                mb: 2,
                px: 2,
                py: 1.25,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: (t) => alpha(t.palette.primary.main, 0.06),
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary', letterSpacing: 0.4 }}>
                PAY RANGE
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 800, color: 'text.primary' }}>
                {job.salary}
              </Typography>
            </Box>
          ) : null}

          <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
            {canApply && (
              <Button
                variant="contained"
                disabled={applyBusy}
                onClick={() => onApply?.(job.id)}
                sx={{ minWidth: 120 }}
              >
                Apply
              </Button>
            )}
            {listingUrl ? (
              <Button
                href={listingUrl}
                target="_blank"
                rel="noopener noreferrer"
                variant="outlined"
                endIcon={<OpenInNewIcon />}
              >
                Open job listing
              </Button>
            ) : null}
          </Stack>

          <Stack direction="row" spacing={1} sx={{ mb: 3 }} flexWrap="wrap" useFlexGap>
            {portalLabel ? <Chip label={portalLabel} size="small" /> : null}
            <Chip label={job.status} size="small" color="primary" variant="outlined" />
            <Chip
              label={`${Math.round((job.match_score || 0) * 100)}% match`}
              size="small"
              color="success"
            />
            {job.source ? <Chip label={job.source} size="small" variant="outlined" /> : null}
          </Stack>

          <Typography variant="h6" sx={{ mb: 1.25, color: 'text.primary' }}>
            About the job
          </Typography>
          {descriptionBlocks.length ? (
            <DescriptionBlocks blocks={descriptionBlocks} />
          ) : (
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 1 }}>
              {listingUrl
                ? `The full description wasn’t captured for this listing. Open the job on ${portalLabel || 'the portal'} to read it.`
                : 'No description was captured for this job.'}
            </Typography>
          )}

          {!!job.skills?.length && (
            <Box sx={{ mt: 2.5, mb: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1, color: 'text.primary' }}>
                Skills
              </Typography>
              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                {job.skills.map((skill) => (
                  <Chip key={skill} size="small" label={skill} />
                ))}
              </Stack>
            </Box>
          )}

          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ mb: 1.5, color: 'text.primary' }}>
            How you match
          </Typography>
          <ScoreBar label="Skills" value={breakdown?.skills || 0} />
          <ScoreBar label="Keywords" value={breakdown?.keywords || 0} />
          <ScoreBar label="Location" value={breakdown?.location || 0} />
          <ScoreBar label="Experience" value={breakdown?.experience || 0} />
          {breakdown?.llm_score != null && (
            <ScoreBar label="LLM ranking" value={breakdown.llm_score} />
          )}
          {reasons.length > 0 && (
            <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2.5, color: 'text.primary' }}>
              {reasons.map((reason) => (
                <Typography component="li" key={reason} variant="body2" sx={{ mb: 0.75, color: 'text.primary' }}>
                  {reason}
                </Typography>
              ))}
            </Box>
          )}
          {!!breakdown?.missing_skills?.length && (
            <>
              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1, fontWeight: 800, color: 'text.primary' }}>
                Missing skills
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                {breakdown.missing_skills.map((skill) => (
                  <Chip key={skill} size="small" label={skill} variant="outlined" />
                ))}
              </Stack>
            </>
          )}
          {breakdown?.llm_rationale && (
            <Typography variant="body2" sx={{ mt: 2, color: 'text.primary' }}>
              {breakdown.llm_rationale}
            </Typography>
          )}

          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ mb: 0.5, color: 'text.primary' }}>
            Job details
          </Typography>
          {listingUrl ? (
            <DetailRow label="Job link">
              <Link
                href={listingUrl}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ wordBreak: 'break-all', fontWeight: 600 }}
              >
                {listingUrl}
              </Link>
            </DetailRow>
          ) : (
            <DetailRow label="Job link">No listing URL was captured for this job.</DetailRow>
          )}
          {job.location ? <DetailRow label="Location">{job.location}</DetailRow> : null}
          {job.salary ? <DetailRow label="Salary">{job.salary}</DetailRow> : null}
          {job.experience ? <DetailRow label="Experience">{job.experience}</DetailRow> : null}
          {job.external_id ? <DetailRow label="External id">{job.external_id}</DetailRow> : null}
          {fetchedExact && fetchedExact !== '—' ? (
            <DetailRow label="Fetched">{fetchedExact}</DetailRow>
          ) : null}
        </Box>
      )}
    </Drawer>
  );
}

export default memo(JobDetailDrawerComponent);
