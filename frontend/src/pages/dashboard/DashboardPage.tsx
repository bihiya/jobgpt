import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  applicationsApi,
  approvalsApi,
  jobsApi,
  portalsApi,
  questionsApi,
  reportsApi,
} from '../../api';
import BlockersInbox, { type BlockerItem } from '../../components/digest/BlockersInbox';
import DigestCard, { type DigestJob } from '../../components/digest/DigestCard';
import LiveApplyTray, { type LiveApplication } from '../../components/digest/LiveApplyTray';
import PortalHealthStrip from '../../components/digest/PortalHealthStrip';
import WeeklyStory from '../../components/digest/WeeklyStory';
import PageShell from '../../components/common/PageShell';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { useRequireAuth } from '../../hooks/useRequireAuth';
import { useToast } from '../../hooks/useToast';

export default function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { requireAuth } = useRequireAuth();
  const { apiError, success } = useToast();
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const [answerOpen, setAnswerOpen] = useState<null | { application_id: string; questions: string[] }>(
    null,
  );
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [otpOpen, setOtpOpen] = useState<null | { application_id: string; portal: string }>(null);
  const [otpCode, setOtpCode] = useState('');
  const [cancelId, setCancelId] = useState<string | null>(null);

  const storyQ = useQuery({
    queryKey: ['weekly-story'],
    queryFn: async () => (await reportsApi.weeklyStory()).data,
  });
  const approvalsQ = useQuery({
    queryKey: ['approvals'],
    queryFn: async () => (await approvalsApi.list({ status: 'pending', page_size: 20 })).data,
  });
  const blockersQ = useQuery({
    queryKey: ['approval-blockers'],
    queryFn: async () => (await approvalsApi.blockers()).data,
  });
  const portalsQ = useQuery({
    queryKey: ['portals'],
    queryFn: async () => (await portalsApi.list()).data,
  });
  const appsQ = useQuery({
    queryKey: ['applications', 'live'],
    queryFn: async () => (await applicationsApi.list({ page_size: 50 })).data,
  });

  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['approvals'] });
    queryClient.invalidateQueries({ queryKey: ['approval-blockers'] });
    queryClient.invalidateQueries({ queryKey: ['applications'] });
    queryClient.invalidateQueries({ queryKey: ['weekly-story'] });
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    queryClient.invalidateQueries({ queryKey: ['pipeline'] });
    queryClient.invalidateQueries({ queryKey: ['portals'] });
  }, [queryClient]);

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      approve ? approvalsApi.approve(id) : approvalsApi.reject(id),
    onSuccess: () => invalidateAll(),
  });

  const cancelMut = useMutation({
    mutationFn: (id: string) => applicationsApi.cancel(id),
    meta: { successMessage: 'Apply cancelled', errorMessage: 'Could not cancel' },
    onMutate: (id) => setCancelId(id),
    onSettled: () => {
      setCancelId(null);
      invalidateAll();
    },
  });

  const resumeAnswers = useMutation({
    mutationFn: () => {
      if (!answerOpen) return Promise.reject(new Error('No application'));
      return questionsApi.answerAndResume({
        application_id: answerOpen.application_id,
        answers: answerOpen.questions
          .filter((q) => answers[q]?.trim())
          .map((q) => ({ question: q, answer: answers[q], tags: ['from_apply'] })),
      });
    },
    meta: { successMessage: 'Saved — apply resumed', errorMessage: 'Could not resume' },
    onSuccess: () => {
      setAnswerOpen(null);
      setAnswers({});
      invalidateAll();
    },
  });

  const submitOtp = useMutation({
    mutationFn: () => {
      if (!otpOpen) return Promise.reject(new Error('No application'));
      return applicationsApi.submitOtp(otpOpen.application_id, { code: otpCode });
    },
    meta: { successMessage: 'OTP submitted', errorMessage: 'OTP failed' },
    onSuccess: () => {
      setOtpOpen(null);
      setOtpCode('');
      invalidateAll();
    },
  });

  const openJob = useCallback(
    async (jobId: string) => {
      try {
        const { data: job } = await jobsApi.get(jobId);
        setDrawerJob(job);
      } catch (err) {
        apiError(err, 'Could not load job');
      }
    },
    [apiError],
  );

  const digestJobs: DigestJob[] = useMemo(() => {
    const items = approvalsQ.data?.items || [];
    return items.map((a: Record<string, unknown>) => ({
      id: String(a.job_id),
      approval_id: String(a.id),
      title: String(a.title || a.summary || 'Match'),
      company: String(a.company || ''),
      portal: String(a.portal || ''),
      match_score: Number(a.match_score || 0),
      summary: String(a.summary || ''),
      apply_channel: typeof a.apply_channel === 'string' ? a.apply_channel : undefined,
      metadata: (a.metadata as Record<string, unknown> | undefined) || undefined,
    }));
  }, [approvalsQ.data]);

  const liveApps: LiveApplication[] = useMemo(() => {
    const items = appsQ.data?.items || [];
    return items.map((a: Record<string, unknown>) => ({
      id: String(a.id),
      job_id: String(a.job_id),
      status: String(a.status),
      session_steps: (a.session_steps as LiveApplication['session_steps']) || [],
      error_message: String(a.error_message || ''),
    }));
  }, [appsQ.data]);

  const blockers: BlockerItem[] = useMemo(
    () => (Array.isArray(blockersQ.data) ? blockersQ.data : []),
    [blockersQ.data],
  );

  const handleBlocker = useCallback(
    (b: BlockerItem) => {
      if (!requireAuth('Sign in to clear blockers')) return;
      if (b.blocker_type === 'login_expired' || b.blocker_type === 'portal_paused') {
        navigate(b.portal_id ? `/job-portals?reauth=${encodeURIComponent(b.portal_id)}` : '/job-portals');
        return;
      }
      if (b.blocker_type === 'otp' && b.application_id) {
        setOtpOpen({ application_id: b.application_id, portal: b.portal || '' });
        return;
      }
      if (b.blocker_type === 'create_account') {
        if (b.apply_url) window.open(b.apply_url, '_blank', 'noopener,noreferrer');
        navigate('/job-portals');
        return;
      }
      if (b.application_id) {
        const qs = b.unknown_questions || [];
        setAnswers(Object.fromEntries(qs.map((q) => [q, ''])));
        setAnswerOpen({ application_id: b.application_id, questions: qs });
      }
    },
    [navigate, requireAuth],
  );

  const loading =
    storyQ.isLoading ||
    approvalsQ.isLoading ||
    blockersQ.isLoading ||
    portalsQ.isLoading ||
    appsQ.isLoading;
  const fetching =
    !loading &&
    (storyQ.isFetching ||
      approvalsQ.isFetching ||
      blockersQ.isFetching ||
      portalsQ.isFetching ||
      appsQ.isFetching);

  return (
    <PageShell spacing={3} loading={loading} fetching={fetching}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography
            variant="h3"
            sx={{ letterSpacing: '-0.04em', fontSize: { xs: '1.85rem', sm: '2.4rem' } }}
          >
            Digest
          </Typography>
          <Typography color="text.secondary">
            Matches to apply, live applies, and anything that needs you.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={() => navigate('/pipeline')}>
            Pipeline
          </Button>
          <Button variant="contained" onClick={() => navigate('/approvals')}>
            All approvals
          </Button>
        </Stack>
      </Stack>

      {storyQ.data && <WeeklyStory story={storyQ.data} />}

      <Box>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Portal health
        </Typography>
        <PortalHealthStrip
          portals={Array.isArray(portalsQ.data) ? portalsQ.data : []}
          onReauth={(id) => {
            if (!requireAuth('Sign in to re-auth portals')) return;
            navigate(`/job-portals?reauth=${encodeURIComponent(id)}`);
          }}
        />
      </Box>

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Stack spacing={1.5}>
            <Typography variant="h6">Today&apos;s matches</Typography>
            {digestJobs.length === 0 ? (
              <Typography color="text.secondary">No pending approvals — you&apos;re caught up.</Typography>
            ) : (
              digestJobs.map((job) => (
                <DigestCard
                  key={job.approval_id || job.id}
                  job={job}
                  busy={decide.isPending}
                  onOpen={() => openJob(job.id)}
                  onApprove={() => {
                    if (!requireAuth('Sign in to approve')) return;
                    if (!job.approval_id) return;
                    decide.mutate(
                      { id: job.approval_id, approve: true },
                      { onSuccess: () => success('Applying…') },
                    );
                  }}
                  onSkip={() => {
                    if (!requireAuth('Sign in to skip')) return;
                    if (!job.approval_id) return;
                    decide.mutate(
                      { id: job.approval_id, approve: false },
                      { onSuccess: () => success('Skipped') },
                    );
                  }}
                />
              ))
            )}
          </Stack>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Live apply tray
              </Typography>
              <LiveApplyTray
                applications={liveApps}
                busyId={cancelId}
                onCancel={(id) => {
                  if (!requireAuth('Sign in to cancel applies')) return;
                  cancelMut.mutate(id);
                }}
              />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Blockers inbox
              </Typography>
              <BlockersInbox blockers={blockers} onAction={handleBlocker} />
            </Box>
          </Stack>
        </Grid>
      </Grid>

      <JobDetailDrawer open={!!drawerJob} job={drawerJob} onClose={() => setDrawerJob(null)} />

      <Dialog open={!!answerOpen} onClose={() => setAnswerOpen(null)} fullWidth maxWidth="sm">
        <DialogTitle>Teach the question bank</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {(answerOpen?.questions || []).map((q) => (
              <TextField
                key={q}
                label={q}
                value={answers[q] || ''}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [q]: e.target.value }))}
                fullWidth
                multiline
              />
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAnswerOpen(null)}>Cancel</Button>
          <Button variant="contained" disabled={resumeAnswers.isPending} onClick={() => resumeAnswers.mutate()}>
            Save & resume
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!otpOpen} onClose={() => setOtpOpen(null)} fullWidth maxWidth="xs">
        <DialogTitle>Enter {otpOpen?.portal || 'portal'} verification code</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="One-time code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOtpOpen(null)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!otpCode.trim() || submitOtp.isPending}
            onClick={() => submitOtp.mutate()}
          >
            Submit & resume
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
