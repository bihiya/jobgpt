import { DeleteOutline, EditOutlined } from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { automationApi, portalsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import { useUserTimeZone } from '../../hooks/useUserTimeZone';
import { formatWhen, fromNowLocal, parseApiDate } from '../../utils/datetime';
import { lastPortalRun, type AutomationLogItem } from '../../utils/loginStory';

const PORTALS = [
  'linkedin', 'naukri', 'indeed', 'foundit', 'wellfound', 'greenhouse',
  'lever', 'ashby', 'workday', 'smartrecruiters', 'oracle', 'sap_successfactors', 'taleo',
];

/** Treat sync as stale if the worker never cleared sync_started_at. */
const SYNC_STALE_MS = 15 * 60 * 1000;

type PortalRow = {
  id: string;
  name: string;
  status?: string;
  last_sync_at?: string | null;
  last_attempt_at?: string | null;
  sync_started_at?: string | null;
  username?: string;
  has_credentials?: boolean;
  has_password?: boolean;
  has_session?: boolean;
  has_totp?: boolean;
  session_updated_at?: string | null;
  health?: {
    score?: number;
    auto_paused?: boolean;
    last_error?: string;
    consecutive_failures?: number;
    paused_reason?: string;
  };
};

type CredsDialog =
  | { mode: 'connect' }
  | { mode: 'edit'; portal: PortalRow }
  | { mode: 'reauth'; portal: PortalRow };

function isSyncInFlight(portal: PortalRow, optimisticId?: string | null): boolean {
  if (optimisticId && portal.id === optimisticId) return true;
  const started = parseApiDate(portal.sync_started_at);
  if (!started) return false;
  return Date.now() - started.valueOf() < SYNC_STALE_MS;
}

function roughlySame(a?: string | null, b?: string | null): boolean {
  const pa = parseApiDate(a);
  const pb = parseApiDate(b);
  if (!pa || !pb) return false;
  return Math.abs(pa.valueOf() - pb.valueOf()) < 5000;
}

function loginState(portal: PortalRow): {
  label: string;
  color: 'success' | 'warning' | 'error' | 'default';
  detail: string;
} {
  const paused = Boolean(portal.health?.auto_paused);
  if (paused) {
    return {
      label: 'Paused',
      color: 'error',
      detail: portal.health?.paused_reason || portal.health?.last_error || 'Re-auth required',
    };
  }
  if (portal.status === 'error') {
    return {
      label: 'Login failed',
      color: 'error',
      detail: portal.health?.last_error || 'Last sync failed',
    };
  }
  if (portal.has_session) {
    const when = portal.session_updated_at
      ? fromNowLocal(portal.session_updated_at)
      : null;
    return {
      label: 'Logged in',
      color: 'success',
      detail: when ? `Session updated ${when}` : 'Browser session saved',
    };
  }
  if (portal.has_credentials) {
    return {
      label: 'Not verified',
      color: 'warning',
      detail: 'Credentials saved — login is checked on the next sync',
    };
  }
  return {
    label: 'Needs login',
    color: 'warning',
    detail: 'Add username/password (or re-auth) before syncing',
  };
}

function stepColor(level?: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (level === 'success') return 'success';
  if (level === 'warning') return 'warning';
  if (level === 'error') return 'error';
  if (level === 'info') return 'info';
  return 'default';
}

export default function PortalsPage() {
  const [dialog, setDialog] = useState<CredsDialog | null>(null);
  const [name, setName] = useState('linkedin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [pollUntil, setPollUntil] = useState(0);
  const queryClient = useQueryClient();
  const timeZone = useUserTimeZone();

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['portals'],
    queryFn: async () => (await portalsApi.list()).data as PortalRow[],
    refetchInterval: Date.now() < pollUntil ? 2000 : false,
  });
  const { data: logsData } = useQuery({
    queryKey: ['automation-logs'],
    queryFn: async () => (await automationApi.logs({ page_size: 80 })).data,
    refetchInterval: Date.now() < pollUntil ? 2000 : false,
  });

  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);
  const logItems = useMemo<AutomationLogItem[]>(
    () => (Array.isArray(logsData?.items) ? logsData.items : []),
    [logsData],
  );
  const anySyncing = useMemo(
    () => rows.some((p) => isSyncInFlight(p, syncingId)),
    [rows, syncingId],
  );

  useEffect(() => {
    if (anySyncing && Date.now() >= pollUntil) {
      setPollUntil(Date.now() + 30_000);
    }
  }, [anySyncing, pollUntil]);

  useEffect(() => {
    if (!syncingId) return;
    const row = rows.find((p) => p.id === syncingId);
    if (row?.sync_started_at) setSyncingId(null);
  }, [rows, syncingId]);

  const closeDialog = () => {
    setDialog(null);
    setUsername('');
    setPassword('');
    setName('linkedin');
  };

  const openConnect = () => {
    setName('linkedin');
    setUsername('');
    setPassword('');
    setDialog({ mode: 'connect' });
  };

  const openEdit = (portal: PortalRow) => {
    setUsername(portal.username || '');
    setPassword('');
    setDialog({ mode: 'edit', portal });
  };

  const openReauth = (portal: PortalRow) => {
    setUsername(portal.username || '');
    setPassword('');
    setDialog({ mode: 'reauth', portal });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      portalsApi.create({
        name,
        credentials: { username, password },
      }),
    meta: { successMessage: 'Portal connected — credentials saved', errorMessage: 'Could not connect portal' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portals'] });
      closeDialog();
    },
  });

  const saveMutation = useMutation({
    mutationFn: ({ id, user, pass }: { id: string; user: string; pass: string }) =>
      portalsApi.update(id, { credentials: { username: user, password: pass } }),
    meta: { successMessage: 'Credentials saved', errorMessage: 'Could not save credentials' },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
      closeDialog();
    },
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => portalsApi.sync(id),
    meta: { successMessage: 'Sync queued — watching live…', errorMessage: 'Sync failed' },
    onMutate: (id) => {
      setSyncingId(id);
      setPollUntil(Date.now() + 45_000);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
      void queryClient.invalidateQueries({ queryKey: ['automation-logs'] });
    },
    onError: () => setSyncingId(null),
  });

  const reauthMutation = useMutation({
    mutationFn: ({ id, user, pass }: { id: string; user: string; pass: string }) =>
      portalsApi.reauth(id, {
        credentials: { username: user, password: pass },
      }),
    meta: { successMessage: 'Credentials saved — sync started', errorMessage: 'Re-auth failed' },
    onMutate: ({ id }) => {
      setSyncingId(id);
      setPollUntil(Date.now() + 45_000);
    },
    onSuccess: () => {
      closeDialog();
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
      void queryClient.invalidateQueries({ queryKey: ['approval-blockers'] });
      void queryClient.invalidateQueries({ queryKey: ['automation-logs'] });
    },
    onError: () => setSyncingId(null),
  });

  const clearMutation = useMutation({
    mutationFn: (id: string) => portalsApi.clearCredentials(id),
    meta: { successMessage: 'Credentials removed', errorMessage: 'Could not clear credentials' },
    onSuccess: () => {
      closeDialog();
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => portalsApi.remove(id),
    meta: { successMessage: 'Portal disconnected', errorMessage: 'Could not disconnect' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portals'] }),
  });

  const dialogBusy =
    createMutation.isPending || saveMutation.isPending || reauthMutation.isPending;
  const editingPortal = dialog && dialog.mode !== 'connect' ? dialog.portal : null;
  const saveNeedsPassword = dialog?.mode === 'connect' || (dialog?.mode === 'reauth' && !editingPortal?.has_password);
  const canSubmit =
    Boolean(username.trim()) &&
    (saveNeedsPassword ? Boolean(password) : true) &&
    (dialog?.mode !== 'connect' || Boolean(password));

  return (
    <PageShell
      loading={isLoading}
      fetching={!isLoading && isFetching}
      busy={dialogBusy || syncMutation.isPending || clearMutation.isPending}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Stack spacing={0.5}>
          <Typography variant="h4">Job portals</Typography>
          <Typography color="text.secondary" variant="body2">
            Each portal stores its own email/password. Sync uses those credentials to log in.
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button component={RouterLink} to="/automation" variant="outlined">
            Watch logs
          </Button>
          <Button variant="contained" onClick={openConnect}>
            Connect portal
          </Button>
        </Stack>
      </Stack>

      <Alert severity="info" sx={{ borderRadius: 2 }}>
        <strong>Credentials:</strong> email is shown here; the password is stored and used on Sync
        but never sent back to the browser. Edit to change, Clear to delete. Times use your device
        timezone ({timeZone}).
      </Alert>

      {anySyncing && (
        <Alert severity="success" sx={{ borderRadius: 2 }}>
          Live sync in progress — this page refreshes every few seconds. Step-by-step progress is
          also on{' '}
          <Button component={RouterLink} to="/automation" size="small" sx={{ verticalAlign: 'baseline' }}>
            Automation
          </Button>
          .
        </Alert>
      )}

      {!rows.length && !isFetching && (
        <Typography color="text.secondary">
          No portals yet — connect LinkedIn, Naukri, or Indeed to start.
        </Typography>
      )}

      {rows.map((portal) => {
        const state = loginState(portal);
        const syncing = isSyncInFlight(portal, syncingId);
        const lastTry = portal.last_attempt_at;
        const lastOk = portal.last_sync_at;
        const same = roughlySame(lastTry, lastOk);
        const score = Math.round(portal.health?.score ?? 100);
        const steps = lastPortalRun(logItems, portal.name);
        const stamp = steps[steps.length - 1]?.created_at;
        return (
          <Box
            key={portal.id}
            sx={{
              bgcolor: 'background.paper',
              borderRadius: 3,
              p: { xs: 1.5, sm: 2 },
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              spacing={2}
              justifyContent="space-between"
              alignItems={{ xs: 'stretch', md: 'flex-start' }}
            >
              <Stack spacing={1} sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography variant="h6" sx={{ textTransform: 'capitalize', fontWeight: 700 }}>
                    {portal.name}
                  </Typography>
                  <Chip size="small" color={state.color} label={state.label} />
                  {syncing && <Chip size="small" color="info" label="Syncing live…" />}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {state.detail}
                </Typography>

                <Box
                  sx={{
                    mt: 0.5,
                    p: 1.25,
                    borderRadius: 2,
                    bgcolor: 'action.hover',
                  }}
                >
                  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.75 }}>
                    Credentials
                  </Typography>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">
                      Email / username · {portal.username || 'Not saved'}
                    </Typography>
                    <Typography variant="body2">
                      Password · {portal.has_password ? '••••••••  (stored, used on Sync)' : 'Not saved'}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<EditOutlined />}
                      onClick={() => openEdit(portal)}
                    >
                      Edit
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<DeleteOutline />}
                      disabled={!portal.has_credentials && !portal.has_password}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Delete saved ${portal.name} email/password? Sync will not be able to log in until you add them again.`,
                          )
                        ) {
                          clearMutation.mutate(portal.id);
                        }
                      }}
                    >
                      Clear
                    </Button>
                  </Stack>
                </Box>
              </Stack>

              <Stack spacing={1} sx={{ minWidth: { md: 220 } }}>
                {syncing ? (
                  <LinearProgress sx={{ height: 3, borderRadius: 1 }} />
                ) : same || (!lastTry && lastOk) ? (
                  <Typography variant="body2">
                    Last sync · {lastOk ? formatWhen(lastOk, timeZone) : 'Never'}
                  </Typography>
                ) : (
                  <>
                    <Typography variant="body2">
                      Last try · {lastTry ? formatWhen(lastTry, timeZone) : 'Never'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Last success · {lastOk ? fromNowLocal(lastOk) : 'Never'}
                    </Typography>
                  </>
                )}
                <Typography variant="caption" color="text.secondary">
                  Health {score}
                  {portal.health?.last_error && !syncing ? ` · ${portal.health.last_error}` : ''}
                </Typography>
                <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                  <Button
                    size="small"
                    variant="contained"
                    disabled={syncing || syncMutation.isPending}
                    onClick={() => syncMutation.mutate(portal.id)}
                  >
                    {syncing ? 'Syncing…' : 'Sync'}
                  </Button>
                  <Button size="small" variant="outlined" onClick={() => openReauth(portal)}>
                    Save & sync
                  </Button>
                  <Button
                    size="small"
                    color="inherit"
                    disabled={removeMutation.isPending}
                    onClick={() => {
                      if (window.confirm(`Disconnect ${portal.name}? This removes the portal and its credentials.`)) {
                        removeMutation.mutate(portal.id);
                      }
                    }}
                  >
                    Remove
                  </Button>
                </Stack>
              </Stack>
            </Stack>

            {!!steps.length && (
              <Stack spacing={0.75} sx={{ mt: 2, pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
                <Typography variant="subtitle2" fontWeight={700}>
                  Last login
                  {stamp ? ` · ${formatWhen(stamp, timeZone)}` : ''}
                </Typography>
                {steps.map((step, idx) => (
                  <Stack key={step.id} direction="row" spacing={1} alignItems="flex-start">
                    <Chip size="small" label={idx + 1} color={stepColor(step.level)} sx={{ minWidth: 36 }} />
                    <Stack spacing={0}>
                      <Typography variant="body2">{step.message || step.action}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatWhen(step.created_at, timeZone)}
                        {step.action === 'fetch.login' ? '' : ` · ${step.action}`}
                      </Typography>
                    </Stack>
                  </Stack>
                ))}
              </Stack>
            )}
          </Box>
        );
      })}

      <Dialog open={Boolean(dialog)} onClose={closeDialog} fullWidth maxWidth="sm">
        <DialogTitle>
          {dialog?.mode === 'connect'
            ? 'Connect portal'
            : dialog?.mode === 'reauth'
              ? `Save & sync ${editingPortal?.name || ''}`
              : `Edit ${editingPortal?.name || ''} credentials`}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {dialog?.mode === 'connect' ? (
              <>
                <Alert severity="warning" sx={{ borderRadius: 2 }}>
                  Email and password are stored on this portal and used the next time you press Sync.
                </Alert>
                <TextField
                  select
                  label="Portal"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  fullWidth
                >
                  {PORTALS.map((p) => (
                    <MenuItem key={p} value={p}>{p}</MenuItem>
                  ))}
                </TextField>
              </>
            ) : (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                Leave password blank to keep the stored one. Email is shown; the saved password is
                never returned to the browser.
              </Alert>
            )}
            <TextField
              label="Username / Email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              fullWidth
              autoComplete="username"
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              fullWidth
              autoComplete="current-password"
              placeholder={editingPortal?.has_password ? '••••••••' : ''}
              helperText={
                editingPortal?.has_password && !password
                  ? 'Stored password will be kept'
                  : 'Stored and used on the next Sync — never shown again'
              }
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2, justifyContent: 'space-between' }}>
          {editingPortal ? (
            <Button
              color="error"
              disabled={clearMutation.isPending || (!editingPortal.has_credentials && !editingPortal.has_password)}
              onClick={() => {
                if (
                  window.confirm(
                    `Delete saved ${editingPortal.name} email/password?`,
                  )
                ) {
                  clearMutation.mutate(editingPortal.id);
                }
              }}
            >
              Delete credentials
            </Button>
          ) : (
            <span />
          )}
          <Stack direction="row" spacing={1}>
            <Button onClick={closeDialog}>Cancel</Button>
            {dialog?.mode === 'connect' && (
              <Button
                variant="contained"
                onClick={() => createMutation.mutate()}
                disabled={dialogBusy || !canSubmit}
              >
                {createMutation.isPending ? 'Saving…' : 'Save credentials'}
              </Button>
            )}
            {dialog?.mode === 'edit' && editingPortal && (
              <Button
                variant="contained"
                disabled={dialogBusy || !username.trim()}
                onClick={() =>
                  saveMutation.mutate({
                    id: editingPortal.id,
                    user: username,
                    pass: password,
                  })
                }
              >
                {saveMutation.isPending ? 'Saving…' : 'Save'}
              </Button>
            )}
            {dialog?.mode === 'reauth' && editingPortal && (
              <Button
                variant="contained"
                disabled={dialogBusy || !username.trim() || (saveNeedsPassword && !password)}
                onClick={() =>
                  reauthMutation.mutate({
                    id: editingPortal.id,
                    user: username,
                    pass: password,
                  })
                }
              >
                {reauthMutation.isPending ? 'Starting…' : 'Save & sync'}
              </Button>
            )}
          </Stack>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
