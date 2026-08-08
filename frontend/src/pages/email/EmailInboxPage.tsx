import { MailOutline } from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { emailApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import { useRequireAuth } from '../../hooks/useRequireAuth';

const EVENT_COLORS: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  interview_schedule: 'info',
  jd_received: 'success',
  offer: 'success',
  rejection: 'error',
  assessment: 'warning',
  application_update: 'default',
  other: 'default',
};

function EmailInboxPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { requireAuth } = useRequireAuth();
  const [filter, setFilter] = useState('');
  const [accountOpen, setAccountOpen] = useState(false);
  const [ingestOpen, setIngestOpen] = useState(false);
  const [form, setForm] = useState({
    label: 'Gmail',
    email_address: '',
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    username: '',
    password: '',
    auto_apply: true,
  });
  const [ingest, setIngest] = useState({
    subject: '',
    body_text: '',
    sender: 'recruiter@acme.com',
    auto_apply: true,
  });

  const accountsQ = useQuery({
    queryKey: ['email-accounts'],
    queryFn: async () => (await emailApi.accounts()).data,
  });
  const messagesQ = useQuery({
    queryKey: ['email-messages', filter],
    queryFn: async () =>
      (
        await emailApi.messages({
          page_size: 50,
          ...(filter ? { event_type: filter } : {}),
        })
      ).data,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
    queryClient.invalidateQueries({ queryKey: ['email-messages'] });
    queryClient.invalidateQueries({ queryKey: ['pipeline'] });
    queryClient.invalidateQueries({ queryKey: ['calendar'] });
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    queryClient.invalidateQueries({ queryKey: ['weekly-story'] });
  };

  const saveAccount = useMutation({
    mutationFn: () => emailApi.upsertAccount(form),
    meta: { successMessage: 'IMAP account saved', errorMessage: 'Could not save account' },
    onSuccess: () => {
      setAccountOpen(false);
      invalidate();
    },
  });

  const syncAll = useMutation({
    mutationFn: () => emailApi.syncAll(),
    meta: { successMessage: 'Inbox synced', errorMessage: 'Sync failed' },
    onSuccess: () => invalidate(),
  });

  const syncOne = useMutation({
    mutationFn: (id: string) => emailApi.syncAccount(id),
    meta: { successMessage: 'Account synced', errorMessage: 'Sync failed' },
    onSuccess: () => invalidate(),
  });

  const applyMsg = useMutation({
    mutationFn: (id: string) => emailApi.apply(id),
    meta: { successMessage: 'Applied to pipeline', errorMessage: 'Apply failed' },
    onSuccess: () => invalidate(),
  });

  const ignoreMsg = useMutation({
    mutationFn: (id: string) => emailApi.ignore(id),
    meta: { successMessage: 'Ignored', errorMessage: 'Ignore failed' },
    onSuccess: () => invalidate(),
  });

  const ingestMut = useMutation({
    mutationFn: () => emailApi.ingest(ingest),
    meta: { successMessage: 'Email ingested', errorMessage: 'Ingest failed' },
    onSuccess: () => {
      setIngestOpen(false);
      setIngest({ subject: '', body_text: '', sender: 'recruiter@acme.com', auto_apply: true });
      invalidate();
    },
  });

  const messages = useMemo(() => messagesQ.data?.items || [], [messagesQ.data]);
  const accounts = useMemo(
    () => (Array.isArray(accountsQ.data) ? accountsQ.data : []),
    [accountsQ.data],
  );

  const loading = accountsQ.isLoading || messagesQ.isLoading;
  const fetching =
    !loading && (accountsQ.isFetching || messagesQ.isFetching);
  const busy =
    syncAll.isPending ||
    syncOne.isPending ||
    applyMsg.isPending ||
    ignoreMsg.isPending ||
    saveAccount.isPending ||
    ingestMut.isPending;

  return (
    <PageShell spacing={2.5} loading={loading} fetching={fetching} busy={busy}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4" sx={{ fontFamily: '"Fraunces", Georgia, serif' }}>
            Email inbox
          </Typography>
          <Typography color="text.secondary">
            Auto-read recruiting mail — interview schedules, JDs, offers, rejections — and update your
            pipeline.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button
            variant="outlined"
            startIcon={<MailOutline />}
            onClick={() => {
              if (!requireAuth('Sign in to connect IMAP')) return;
              setAccountOpen(true);
            }}
          >
            Connect IMAP
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              if (!requireAuth('Sign in to ingest email')) return;
              setIngestOpen(true);
            }}
          >
            Paste email
          </Button>
          <Button
            variant="contained"
            disabled={syncAll.isPending}
            onClick={() => {
              if (!requireAuth('Sign in to sync inbox')) return;
              syncAll.mutate();
            }}
          >
            Sync now
          </Button>
        </Stack>
      </Stack>

      {accounts.length === 0 && (
        <Alert severity="info">
          Connect Gmail/Outlook IMAP (app password) or paste a recruiter email to classify interview /
          JD events. Auto-sync runs every few minutes when an account is enabled.
        </Alert>
      )}

      {accounts.length > 0 && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {accounts.map((a: Record<string, unknown>) => (
            <Chip
              key={String(a.id)}
              label={`${a.label || a.email_address} · ${a.last_sync_at ? 'synced' : 'never synced'}`}
              color={a.last_error ? 'error' : 'success'}
              onClick={() => {
                if (!requireAuth('Sign in to sync')) return;
                syncOne.mutate(String(a.id));
              }}
              variant="outlined"
            />
          ))}
        </Stack>
      )}

      <TextField
        select
        size="small"
        label="Filter type"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        sx={{ maxWidth: 280 }}
      >
        <MenuItem value="">All events</MenuItem>
        <MenuItem value="interview_schedule">Interview schedule</MenuItem>
        <MenuItem value="jd_received">JD received</MenuItem>
        <MenuItem value="offer">Offer</MenuItem>
        <MenuItem value="rejection">Rejection</MenuItem>
        <MenuItem value="assessment">Assessment</MenuItem>
        <MenuItem value="application_update">Application update</MenuItem>
        <MenuItem value="other">Other</MenuItem>
      </TextField>

      <Stack spacing={1.5}>
        {messages.length === 0 && (
          <Typography color="text.secondary">No classified emails yet.</Typography>
        )}
        {messages.map((m: Record<string, unknown>) => {
          const type = String(m.event_type || 'other');
          return (
            <Box
              key={String(m.id)}
              sx={{
                p: 2,
                borderRadius: 3,
                border: '1px solid',
                borderColor: 'divider',
                background: (t) =>
                  `linear-gradient(145deg, ${t.palette.background.paper}, ${alpha(
                    t.palette.info.main,
                    0.05,
                  )})`,
              }}
            >
              <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 800 }}>{String(m.subject || '(no subject)')}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {String(m.sender || '')}
                    {m.received_at ? ` · ${new Date(String(m.received_at)).toLocaleString()}` : ''}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={0.75}>
                  <Chip size="small" color={EVENT_COLORS[type] || 'default'} label={type.replace(/_/g, ' ')} />
                  <Chip size="small" variant="outlined" label={String(m.sync_status)} />
                </Stack>
              </Stack>
              <Typography variant="body2" sx={{ mt: 1 }}>
                {String(m.snippet || '')}
              </Typography>
              {typeof m.extracted === 'object' && m.extracted !== null ? (
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                  {Object.entries(m.extracted as Record<string, unknown>)
                    .filter(([k]) => k !== 'reasons')
                    .slice(0, 6)
                    .map(([k, v]) => (
                      <Chip key={k} size="small" variant="outlined" label={`${k}: ${String(v).slice(0, 40)}`} />
                    ))}
                </Stack>
              ) : null}
              <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} flexWrap="wrap" useFlexGap>
                {m.sync_status === 'pending' ? (
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => {
                      if (!requireAuth('Sign in to apply email events')) return;
                      applyMsg.mutate(String(m.id));
                    }}
                  >
                    Apply to pipeline
                  </Button>
                ) : null}
                {m.matched_job_id ? (
                  <Button size="small" onClick={() => navigate('/pipeline')}>
                    Open pipeline
                  </Button>
                ) : null}
                {m.sync_status !== 'ignored' ? (
                  <Button
                    size="small"
                    color="inherit"
                    onClick={() => {
                      if (!requireAuth('Sign in to ignore')) return;
                      ignoreMsg.mutate(String(m.id));
                    }}
                  >
                    Ignore
                  </Button>
                ) : null}
              </Stack>
            </Box>
          );
        })}
      </Stack>

      <Dialog open={accountOpen} onClose={() => setAccountOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Connect IMAP inbox</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Label"
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              fullWidth
            />
            <TextField
              label="Email address"
              value={form.email_address}
              onChange={(e) => setForm({ ...form, email_address: e.target.value })}
              fullWidth
            />
            <TextField
              label="IMAP host"
              value={form.imap_host}
              onChange={(e) => setForm({ ...form, imap_host: e.target.value })}
              fullWidth
              helperText="Gmail: imap.gmail.com · Outlook: outlook.office365.com"
            />
            <TextField
              label="Username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              fullWidth
            />
            <TextField
              label="App password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              fullWidth
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.auto_apply}
                  onChange={(e) => setForm({ ...form, auto_apply: e.target.checked })}
                />
              }
              label="Auto-apply interview / JD / offer updates to pipeline"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAccountOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!form.username || !form.password || saveAccount.isPending}
            onClick={() => saveAccount.mutate()}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={ingestOpen} onClose={() => setIngestOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Paste recruiter email</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="From"
              value={ingest.sender}
              onChange={(e) => setIngest({ ...ingest, sender: e.target.value })}
              fullWidth
            />
            <TextField
              label="Subject"
              value={ingest.subject}
              onChange={(e) => setIngest({ ...ingest, subject: e.target.value })}
              fullWidth
            />
            <TextField
              label="Body"
              value={ingest.body_text}
              onChange={(e) => setIngest({ ...ingest, body_text: e.target.value })}
              fullWidth
              multiline
              minRows={6}
              placeholder="Interview scheduled for Tuesday Mar 10 at 3pm via Zoom…"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={ingest.auto_apply}
                  onChange={(e) => setIngest({ ...ingest, auto_apply: e.target.checked })}
                />
              }
              label="Apply to pipeline immediately"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIngestOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={(!ingest.subject && !ingest.body_text) || ingestMut.isPending}
            onClick={() => ingestMut.mutate()}
          >
            Classify
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}

export default memo(EmailInboxPage);
