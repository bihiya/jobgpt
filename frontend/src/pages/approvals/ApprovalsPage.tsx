import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef, GridRowSelectionModel } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useCallback, useMemo, useState } from 'react';
import { approvalsApi, applicationsApi, jobsApi, questionsApi, settingsApi } from '../../api';
import ApplyChannelChip from '../../components/jobs/ApplyChannelChip';
import ApplySessionTimeline from '../../components/automation/ApplySessionTimeline';
import PageShell from '../../components/common/PageShell';
import JobDetailDrawer, { type JobDetail } from '../../components/jobs/JobDetailDrawer';
import { applyChannelFromSteps } from '../../lib/applyLive';
import { useRequireAuth } from '../../hooks/useRequireAuth';
import { useToast } from '../../hooks/useToast';

function ApprovalsPage() {
  const queryClient = useQueryClient();
  const { requireAuth } = useRequireAuth();
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const [selection, setSelection] = useState<GridRowSelectionModel>([]);
  const [batchOpen, setBatchOpen] = useState(false);
  const [minScore, setMinScore] = useState(85);
  const [portal, setPortal] = useState('linkedin');
  const [answerOpen, setAnswerOpen] = useState<null | {
    application_id: string;
    questions: string[];
  }>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [otpOpen, setOtpOpen] = useState<null | { application_id: string; portal: string }>(null);
  const [otpCode, setOtpCode] = useState('');
  const { apiError, success } = useToast();

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['approvals'],
    queryFn: async () => (await approvalsApi.list({ status: 'pending', page_size: 50 })).data,
  });

  const { data: blockers, isLoading: blockersLoading, isFetching: blockersFetching } = useQuery({
    queryKey: ['approval-blockers'],
    queryFn: async () => (await approvalsApi.blockers()).data,
  });

  const { data: settings, isLoading: settingsLoading, isFetching: settingsFetching } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => (await settingsApi.get()).data,
  });

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      approve ? approvalsApi.approve(id) : approvalsApi.reject(id),
    meta: {
      successMessage: 'Decision saved',
      errorMessage: 'Could not update approval',
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['approvals'] }),
  });

  const batch = useMutation({
    mutationFn: () =>
      approvalsApi.batch({
        min_score: minScore / 100,
        portal: portal || undefined,
        limit: settings?.max_applications_per_day || 15,
        approval_ids: selection.length ? (selection as string[]) : undefined,
      }),
    meta: { errorMessage: 'Batch approve failed' },
    onSuccess: (res) => {
      const count = res.data?.count ?? 0;
      success(`Batch approved ${count} job(s)`);
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      setBatchOpen(false);
      setSelection([]);
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
      queryClient.invalidateQueries({ queryKey: ['approval-blockers'] });
    },
  });

  const submitOtp = useMutation({
    mutationFn: () => {
      if (!otpOpen) return Promise.reject(new Error('No application'));
      return applicationsApi.submitOtp(otpOpen.application_id, { code: otpCode });
    },
    meta: { successMessage: 'OTP submitted — apply resumed', errorMessage: 'OTP failed' },
    onSuccess: () => {
      setOtpOpen(null);
      setOtpCode('');
      queryClient.invalidateQueries({ queryKey: ['approval-blockers'] });
    },
  });

  const openJob = useCallback(
    async (jobId: string) => {
      try {
        const { data: job } = await jobsApi.get(jobId);
        setDrawerJob(job);
      } catch (err) {
        apiError(err, 'Could not load job details');
      }
    },
    [apiError],
  );

  const columns: GridColDef[] = useMemo(
    () => [
      { field: 'summary', headerName: 'Job', flex: 1.5, minWidth: 180 },
      { field: 'portal', headerName: 'Portal', width: 120 },
      {
        field: 'apply_channel',
        headerName: 'Apply type',
        width: 190,
        sortable: false,
        renderCell: (params) => {
          const channel = applyChannelFromSteps(null, {
            portal: params.row.portal,
            metadata: params.row.metadata || { apply_channel: params.row.apply_channel },
          });
          return channel ? <ApplyChannelChip channel={channel} /> : '—';
        },
      },
      {
        field: 'match_score',
        headerName: 'Match',
        width: 110,
        valueFormatter: (v: number) => `${Math.round((v || 0) * 100)}%`,
      },
      {
        field: 'status',
        headerName: 'Status',
        width: 140,
        renderCell: (params) => <Chip size="small" label={params.value} color="warning" />,
      },
      { field: 'created_at', headerName: 'Queued', flex: 1, minWidth: 140 },
      {
        field: 'actions',
        headerName: '',
        width: 280,
        sortable: false,
        renderCell: (params) => (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button size="small" onClick={() => openJob(params.row.job_id)}>
              Why
            </Button>
            <Button
              size="small"
              variant="contained"
              disabled={decide.isPending}
              onClick={() => {
                if (!requireAuth('Sign in to approve applications')) return;
                decide.mutate({ id: params.row.id, approve: true });
              }}
            >
              {decide.isPending ? '…' : 'Apply'}
            </Button>
            <Button
              size="small"
              color="inherit"
              disabled={decide.isPending}
              onClick={() => {
                if (!requireAuth('Sign in to reject applications')) return;
                decide.mutate({ id: params.row.id, approve: false });
              }}
            >
              Reject
            </Button>
          </Stack>
        ),
      },
    ],
    [decide, openJob, requireAuth],
  );

  const loading = isLoading || blockersLoading || settingsLoading;
  const fetching =
    !loading && (isFetching || blockersFetching || settingsFetching);

  const blockerList = Array.isArray(blockers) ? blockers : [];

  return (
    <PageShell
      loading={loading}
      fetching={fetching}
      busy={decide.isPending || batch.isPending}
    >
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
        <div>
          <Typography variant="h4">Approvals</Typography>
          <Typography color="text.secondary">
            Apply a match, or answer OTP / questions that blocked an apply.
          </Typography>
        </div>
        <Button
          variant="contained"
          onClick={() => {
            if (!requireAuth('Sign in for batch approve')) return;
            setMinScore(Math.round(((settings?.batch_min_score ?? 0.85) as number) * 100));
            setBatchOpen(true);
          }}
        >
          Smart batch approve
        </Button>
      </Stack>

      {blockerList.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Needs your help
          </Typography>
          <Stack spacing={1.5}>
            {blockerList.map((b: Record<string, unknown>) => (
              <Alert
                key={String(b.application_id)}
                severity="warning"
                action={
                  b.blocker_type === 'otp' ? (
                    <Button
                      color="inherit"
                      size="small"
                      onClick={() =>
                        setOtpOpen({
                          application_id: String(b.application_id),
                          portal: String(b.portal || ''),
                        })
                      }
                    >
                      Enter OTP
                    </Button>
                  ) : b.blocker_type === 'create_account' ? (
                    <Button
                      color="inherit"
                      size="small"
                      onClick={() => {
                        const url = String(b.apply_url || '');
                        if (url) window.open(url, '_blank', 'noopener,noreferrer');
                      }}
                    >
                      Open site
                    </Button>
                  ) : (
                    <Button
                      color="inherit"
                      size="small"
                      onClick={() => {
                        const qs = (b.unknown_questions as string[]) || [];
                        setAnswers(Object.fromEntries(qs.map((q) => [q, ''])));
                        setAnswerOpen({
                          application_id: String(b.application_id),
                          questions: qs,
                        });
                      }}
                    >
                      Answer
                    </Button>
                  )
                }
              >
                <Typography variant="subtitle2">
                  {String(b.title || 'Application')} · {String(b.portal || '')} ·{' '}
                  {String(b.blocker_type || b.status)}
                </Typography>
                <Typography variant="body2">{String(b.error_message || '')}</Typography>
                {Array.isArray(b.session_steps) && b.session_steps.length > 0 ? (
                  <Box sx={{ mt: 1 }}>
                    <ApplySessionTimeline steps={b.session_steps as never[]} dense />
                  </Box>
                ) : null}
              </Alert>
            ))}
          </Stack>
        </Box>
      )}

      <DataGrid
        autoHeight
        checkboxSelection
        rows={data?.items || []}
        columns={columns}
        getRowId={(row) => row.id}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        rowSelectionModel={selection}
        onRowSelectionModelChange={setSelection}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%', mt: 2 }}
      />

      <JobDetailDrawer open={!!drawerJob} job={drawerJob} onClose={() => setDrawerJob(null)} />

      <Dialog open={batchOpen} onClose={() => setBatchOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Smart batch approve</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Approve matches at or above your threshold for a portal. Respects daily cap (
              {settings?.max_applications_per_day ?? 15}/day) and cooldown (
              {settings?.apply_cooldown_seconds ?? 45}s).
            </Typography>
            <TextField
              label="Min match %"
              type="number"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              inputProps={{ min: 50, max: 100 }}
            />
            <TextField select label="Portal" value={portal} onChange={(e) => setPortal(e.target.value)}>
              <MenuItem value="linkedin">LinkedIn</MenuItem>
              <MenuItem value="indeed">Indeed</MenuItem>
              <MenuItem value="greenhouse">Greenhouse</MenuItem>
              <MenuItem value="lever">Lever</MenuItem>
              <MenuItem value="">Any portal</MenuItem>
            </TextField>
            {selection.length > 0 && (
              <Alert severity="info">Using {selection.length} selected row(s).</Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatchOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={batch.isPending} onClick={() => batch.mutate()}>
            Approve batch
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!answerOpen} onClose={() => setAnswerOpen(null)} fullWidth maxWidth="sm">
        <DialogTitle>Teach the question bank</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Answer once — we save these and resume the apply.
            </Typography>
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
          <Button
            variant="contained"
            disabled={resumeAnswers.isPending}
            onClick={() => resumeAnswers.mutate()}
          >
            Save & resume
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!otpOpen} onClose={() => setOtpOpen(null)} fullWidth maxWidth="xs">
        <DialogTitle>Enter {otpOpen?.portal || 'portal'} OTP</DialogTitle>
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

export default memo(ApprovalsPage);
