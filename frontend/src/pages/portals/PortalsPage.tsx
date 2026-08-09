import {
  Alert,
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
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { portalsApi } from '../../api';
import PageShell from '../../components/common/PageShell';

dayjs.extend(relativeTime);

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
  sync_started_at?: string | null;
  has_credentials?: boolean;
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

function isSyncInFlight(portal: PortalRow, optimisticId?: string | null): boolean {
  if (optimisticId && portal.id === optimisticId) return true;
  if (!portal.sync_started_at) return false;
  const started = new Date(portal.sync_started_at).getTime();
  if (Number.isNaN(started)) return false;
  return Date.now() - started < SYNC_STALE_MS;
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
      label: 'Error',
      color: 'error',
      detail: portal.health?.last_error || 'Last sync failed',
    };
  }
  if (portal.has_session) {
    const when = portal.session_updated_at
      ? dayjs(portal.session_updated_at).fromNow()
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

export default function PortalsPage() {
  const [open, setOpen] = useState(false);
  const [reauthOpen, setReauthOpen] = useState<null | PortalRow>(null);
  const [name, setName] = useState('linkedin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [reauthId, setReauthId] = useState<string | null>(null);
  const [pollUntil, setPollUntil] = useState(0);
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['portals'],
    queryFn: async () => (await portalsApi.list()).data as PortalRow[],
    refetchInterval: Date.now() < pollUntil ? 2000 : false,
  });

  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);
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
    // Once the server has sync_started_at, drop the optimistic id.
    if (row?.sync_started_at) setSyncingId(null);
  }, [rows, syncingId]);

  const createMutation = useMutation({
    mutationFn: () =>
      portalsApi.create({
        name,
        credentials: { username, password },
      }),
    meta: { successMessage: 'Portal connected — sync to verify login', errorMessage: 'Could not connect portal' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portals'] });
      setOpen(false);
      setUsername('');
      setPassword('');
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
    meta: { successMessage: 'Re-auth + sync started', errorMessage: 'Re-auth failed' },
    onMutate: ({ id }) => {
      setReauthId(id);
      setSyncingId(id);
      setPollUntil(Date.now() + 45_000);
    },
    onSuccess: () => {
      setReauthOpen(null);
      setUsername('');
      setPassword('');
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
      void queryClient.invalidateQueries({ queryKey: ['approval-blockers'] });
      void queryClient.invalidateQueries({ queryKey: ['automation-logs'] });
    },
    onError: () => setSyncingId(null),
    onSettled: () => setReauthId(null),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => portalsApi.remove(id),
    meta: { successMessage: 'Portal disconnected', errorMessage: 'Could not disconnect' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portals'] }),
  });

  const columns: GridColDef<PortalRow>[] = useMemo(
    () => [
      {
        field: 'name',
        headerName: 'Portal',
        flex: 0.9,
        minWidth: 120,
        renderCell: (params) => (
          <Typography sx={{ textTransform: 'capitalize', fontWeight: 600 }}>
            {params.value}
          </Typography>
        ),
      },
      {
        field: 'login',
        headerName: 'Login',
        flex: 1.2,
        minWidth: 180,
        sortable: false,
        renderCell: (params) => {
          const state = loginState(params.row);
          return (
            <Stack spacing={0.25} justifyContent="center" sx={{ py: 0.5, width: '100%' }}>
              <Chip size="small" color={state.color} label={state.label} sx={{ width: 'fit-content' }} />
              <Typography variant="caption" color="text.secondary" noWrap title={state.detail}>
                {state.detail}
              </Typography>
            </Stack>
          );
        },
      },
      {
        field: 'sync',
        headerName: 'Sync',
        flex: 1.1,
        minWidth: 170,
        sortable: false,
        renderCell: (params) => {
          const syncing = isSyncInFlight(params.row, syncingId);
          const last = params.row.last_sync_at
            ? dayjs(params.row.last_sync_at).fromNow()
            : 'Never';
          const score = Math.round(params.row.health?.score ?? 100);
          return (
            <Stack spacing={0.5} justifyContent="center" sx={{ py: 0.5, width: '100%' }}>
              {syncing ? (
                <>
                  <Chip size="small" color="info" label="Syncing live…" sx={{ width: 'fit-content' }} />
                  <LinearProgress sx={{ height: 3, borderRadius: 1 }} />
                </>
              ) : (
                <Typography variant="body2">Last sync · {last}</Typography>
              )}
              <Typography variant="caption" color="text.secondary">
                Health {score}
                {params.row.health?.last_error && !syncing
                  ? ` · ${params.row.health.last_error}`
                  : ''}
              </Typography>
            </Stack>
          );
        },
      },
      {
        field: 'actions',
        headerName: '',
        width: 280,
        sortable: false,
        renderCell: (params) => {
          const syncing = isSyncInFlight(params.row, syncingId);
          const needsAuth =
            !params.row.has_session ||
            Boolean(params.row.health?.auto_paused) ||
            params.row.status === 'error';
          return (
            <Stack direction="row" spacing={0.75} alignItems="center">
              <Button
                size="small"
                variant="contained"
                disabled={syncing || syncMutation.isPending}
                onClick={() => syncMutation.mutate(params.row.id)}
              >
                {syncing ? 'Syncing…' : 'Sync'}
              </Button>
              {needsAuth && (
                <Button
                  size="small"
                  variant="outlined"
                  disabled={reauthId === params.row.id}
                  onClick={() => {
                    setUsername('');
                    setPassword('');
                    setReauthOpen(params.row);
                  }}
                >
                  Re-auth
                </Button>
              )}
              <Button
                size="small"
                color="inherit"
                disabled={removeMutation.isPending}
                onClick={() => {
                  if (window.confirm(`Disconnect ${params.row.name}?`)) {
                    removeMutation.mutate(params.row.id);
                  }
                }}
              >
                Remove
              </Button>
            </Stack>
          );
        },
      },
    ],
    [syncingId, syncMutation, reauthId, removeMutation],
  );

  return (
    <PageShell
      loading={isLoading}
      fetching={!isLoading && isFetching}
      busy={createMutation.isPending || syncMutation.isPending || reauthMutation.isPending}
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
            Connect → Sync verifies login in a headless browser → jobs land here live.
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button component={RouterLink} to="/automation" variant="outlined">
            Watch logs
          </Button>
          <Button variant="contained" onClick={() => setOpen(true)}>
            Connect portal
          </Button>
        </Stack>
      </Stack>

      <Alert severity="info" sx={{ borderRadius: 2 }}>
        <strong>Sync flow:</strong> credentials are saved on Connect (that is not a full login).
        Sync queues a background fetch — the worker logs into the portal, pulls jobs, then saves
        the session. While it runs you&apos;ll see <em>Syncing live…</em>; when login works the
        Login column flips to <em>Logged in</em>.
      </Alert>

      {anySyncing && (
        <Alert severity="success" sx={{ borderRadius: 2 }}>
          Live sync in progress — this table refreshes every few seconds. Step-by-step progress is
          also on{' '}
          <Button component={RouterLink} to="/automation" size="small" sx={{ verticalAlign: 'baseline' }}>
            Automation
          </Button>
          .
        </Alert>
      )}

      <DataGrid
        autoHeight
        getRowHeight={() => 72}
        rows={rows}
        columns={columns}
        loading={isFetching && !rows.length}
        pageSizeOptions={[10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        disableRowSelectionOnClick
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%' }}
        localeText={{ noRowsLabel: 'No portals yet — connect LinkedIn, Naukri, or Indeed to start.' }}
      />

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Connect portal</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Alert severity="warning" sx={{ borderRadius: 2 }}>
              Saving credentials marks the portal connected, but login is only verified when you
              press Sync (or Re-auth).
            </Alert>
            <TextField select label="Portal" value={name} onChange={(e) => setName(e.target.value)} fullWidth>
              {PORTALS.map((p) => (
                <MenuItem key={p} value={p}>{p}</MenuItem>
              ))}
            </TextField>
            <TextField label="Username / Email" value={username} onChange={(e) => setUsername(e.target.value)} fullWidth />
            <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} fullWidth />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || !username || !password}
          >
            Connect
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(reauthOpen)} onClose={() => setReauthOpen(null)} fullWidth maxWidth="sm">
        <DialogTitle>Re-auth {reauthOpen?.name}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Update credentials, clear the pause, and start a fresh sync. Login succeeds only if
              the worker can sign in.
            </Typography>
            <TextField
              label="Username / Email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReauthOpen(null)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!reauthOpen || reauthMutation.isPending || !username || !password}
            onClick={() => {
              if (!reauthOpen) return;
              reauthMutation.mutate({
                id: reauthOpen.id,
                user: username,
                pass: password,
              });
            }}
          >
            {reauthMutation.isPending ? 'Starting…' : 'Save & sync'}
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
