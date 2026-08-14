import { DeleteOutline, EditOutlined, MoreHoriz } from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { automationApi, portalsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import SyncRunList from '../../components/portals/SyncRunList';
import { useRequireAuth } from '../../hooks/useRequireAuth';
import { useUserTimeZone } from '../../hooks/useUserTimeZone';
import { playDemoSync } from '../../lib/demoSync';
import { fromNowLocal } from '../../utils/datetime';
import {
  groupPortalRuns,
  isSyncRunFinished,
  newSyncId,
  withLiveRun,
  type AutomationLogItem,
} from '../../utils/loginStory';

const PORTALS = [
  'linkedin', 'naukri', 'indeed', 'foundit', 'wellfound', 'greenhouse',
  'lever', 'ashby', 'workday', 'smartrecruiters', 'oracle', 'sap_successfactors', 'taleo',
];

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
  health?: {
    score?: number;
    auto_paused?: boolean;
    last_error?: string;
    paused_reason?: string;
  };
};

type CredsDialog =
  | { mode: 'connect' }
  | { mode: 'edit'; portal: PortalRow }
  | { mode: 'reauth'; portal: PortalRow };

type LiveSync = {
  portalId: string;
  portalName: string;
  syncId: string;
  aliasIds: string[];
};

function isSyncInFlight(portal: PortalRow, live?: LiveSync | null): boolean {
  if (live && portal.id === live.portalId) return true;
  if (!portal.sync_started_at) return false;
  const started = Date.parse(portal.sync_started_at);
  return Number.isFinite(started) && Date.now() - started < SYNC_STALE_MS;
}

function loginState(portal: PortalRow): { label: string; color: 'success' | 'warning' | 'error' | 'default' } {
  if (portal.health?.auto_paused) return { label: 'Paused', color: 'error' };
  if (portal.status === 'error') return { label: 'Login failed', color: 'error' };
  if (portal.has_session) return { label: 'Logged in', color: 'success' };
  if (portal.has_credentials) return { label: 'Saved', color: 'warning' };
  return { label: 'Needs login', color: 'warning' };
}

export default function PortalsPage() {
  const [dialog, setDialog] = useState<CredsDialog | null>(null);
  const [name, setName] = useState('linkedin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [menu, setMenu] = useState<{ portal: PortalRow; anchor: HTMLElement } | null>(null);
  const [live, setLive] = useState<LiveSync | null>(null);
  const [liveLogs, setLiveLogs] = useState<AutomationLogItem[]>([]);
  const [pollUntil, setPollUntil] = useState(0);
  const demoCancel = useRef<(() => void) | null>(null);
  const queryClient = useQueryClient();
  const timeZone = useUserTimeZone();
  const { isAuthenticated } = useRequireAuth();

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['portals'],
    queryFn: async () => (await portalsApi.list()).data as PortalRow[],
    refetchInterval: Date.now() < pollUntil ? 1500 : false,
  });
  const { data: logsData } = useQuery({
    queryKey: ['automation-logs'],
    queryFn: async () => (await automationApi.logs({ page_size: 200 })).data,
    refetchInterval: Date.now() < pollUntil ? 1200 : false,
  });

  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);
  const logItems = useMemo<AutomationLogItem[]>(() => {
    const fromApi: AutomationLogItem[] = Array.isArray(logsData?.items) ? logsData.items : [];
    if (!liveLogs.length) return fromApi;
    const seen = new Set(fromApi.map((item) => item.id));
    return [...liveLogs.filter((item) => !seen.has(item.id)), ...fromApi];
  }, [logsData, liveLogs]);

  useEffect(() => () => demoCancel.current?.(), []);

  useEffect(() => {
    if (!live) return;
    const current = withLiveRun(groupPortalRuns(logItems, live.portalName), live).find(
      (run) => run.id === live.syncId,
    );
    if (!current || !isSyncRunFinished(current)) return;
    setPollUntil((until) => {
      const next = Date.now() + 4_000;
      return until > next ? next : until;
    });
  }, [live, logItems]);

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
    setMenu(null);
    setUsername(portal.username || '');
    setPassword('');
    setDialog({ mode: 'edit', portal });
  };

  const openReauth = (portal: PortalRow) => {
    setMenu(null);
    setUsername(portal.username || '');
    setPassword('');
    setDialog({ mode: 'reauth', portal });
  };

  const pinLive = (portal: PortalRow, syncId: string, aliasIds: string[] = []) => {
    demoCancel.current?.();
    setLive({ portalId: portal.id, portalName: portal.name, syncId, aliasIds });
    setLiveLogs([
      {
        id: `${syncId}-queued`,
        created_at: new Date().toISOString(),
        portal: portal.name,
        action: 'fetch.portal',
        level: 'info',
        message: `Sync queued for ${portal.name}…`,
        correlation_id: syncId,
      },
    ]);
    setPollUntil(Date.now() + 90_000);
  };

  const adoptSyncId = (syncId: string) => {
    const fromId = live?.syncId;
    setLive((prev) => {
      if (!prev || prev.syncId === syncId) return prev;
      return { ...prev, syncId, aliasIds: [...new Set([...prev.aliasIds, prev.syncId])] };
    });
    if (fromId && fromId !== syncId) {
      setLiveLogs((logs) =>
        logs.map((item) =>
          item.correlation_id === fromId ? { ...item, correlation_id: syncId } : item,
        ),
      );
    }
  };

  const createMutation = useMutation({
    mutationFn: () =>
      portalsApi.create({
        name,
        credentials: { username, password },
      }),
    meta: { successMessage: 'Portal connected', errorMessage: 'Could not connect portal' },
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
    meta: { successMessage: 'Sync started', errorMessage: 'Sync failed' },
    onSuccess: (res, portalId) => {
      const cid = String(res.data?.correlation_id || '').trim();
      if (cid) adoptSyncId(cid);
      const row = rows.find((p) => p.id === portalId);
      if (row && !live) pinLive(row, cid || newSyncId());
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
      void queryClient.invalidateQueries({ queryKey: ['automation-logs'] });
    },
    onError: () => {
      setLive(null);
      setLiveLogs([]);
    },
  });

  const reauthMutation = useMutation({
    mutationFn: ({ id, user, pass }: { id: string; user: string; pass: string }) =>
      portalsApi.reauth(id, {
        credentials: { username: user, password: pass },
      }),
    meta: { successMessage: 'Saved — sync started', errorMessage: 'Re-auth failed' },
    onMutate: ({ id }) => {
      const portal = rows.find((p) => p.id === id);
      if (portal) pinLive(portal, newSyncId());
    },
    onSuccess: (res) => {
      const cid = String(res.data?.correlation_id || '').trim();
      if (cid) adoptSyncId(cid);
      closeDialog();
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
      void queryClient.invalidateQueries({ queryKey: ['approval-blockers'] });
      void queryClient.invalidateQueries({ queryKey: ['automation-logs'] });
    },
    onError: () => {
      setLive(null);
      setLiveLogs([]);
    },
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

  const startSync = (portal: PortalRow) => {
    const syncId = newSyncId();
    pinLive(portal, syncId);
    if (!isAuthenticated) {
      demoCancel.current = playDemoSync(portal.name, syncId, (step, index, done) => {
        if (index === 0) return;
        setLiveLogs((prev) => [step, ...prev.filter((item) => item.id !== step.id)]);
        if (done) setPollUntil(Date.now() + 4_000);
      });
      return;
    }
    syncMutation.mutate(portal.id);
  };

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
      busy={dialogBusy || clearMutation.isPending}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Stack spacing={0.25}>
          <Typography variant="h4">Job portals</Typography>
          <Typography color="text.secondary" variant="body2">
            Press Sync — this page opens that run and streams every step into it.
          </Typography>
        </Stack>
        <Button variant="contained" onClick={openConnect}>
          Connect portal
        </Button>
      </Stack>

      {!rows.length && !isFetching && (
        <Typography color="text.secondary">
          No portals yet — connect LinkedIn, Naukri, or Indeed to start.
        </Typography>
      )}

      {rows.map((portal) => {
        const state = loginState(portal);
        const runs = withLiveRun(
          groupPortalRuns(logItems, portal.name),
          live?.portalId === portal.id ? live : null,
        );
        const liveRun = live?.portalId === portal.id ? runs.find((run) => run.id === live.syncId) : undefined;
        const syncing = Boolean(liveRun && !isSyncRunFinished(liveRun)) || isSyncInFlight(portal, null);
        return (
          <Box
            key={portal.id}
            sx={{
              bgcolor: 'background.paper',
              borderRadius: 3,
              p: { xs: 1.5, sm: 2 },
              border: '1px solid',
              borderColor: syncing ? 'secondary.main' : 'divider',
              transition: 'border-color 0.25s ease, box-shadow 0.25s ease',
            }}
          >
            <Stack
              direction="row"
              spacing={1.5}
              alignItems="center"
              justifyContent="space-between"
              flexWrap="wrap"
              useFlexGap
            >
              <Stack spacing={0.25} sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography variant="h6" sx={{ textTransform: 'capitalize', fontWeight: 700 }}>
                    {portal.name}
                  </Typography>
                  <Chip size="small" color={state.color} label={state.label} />
                  {syncing && <Chip size="small" color="info" label="Syncing" />}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {portal.username || 'No email saved'}
                  {portal.last_sync_at ? ` · last sync ${fromNowLocal(portal.last_sync_at)}` : ' · never synced'}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={0.75} alignItems="center">
                <Button
                  size="small"
                  variant="contained"
                  disabled={syncing || syncMutation.isPending}
                  onClick={() => startSync(portal)}
                >
                  {syncing ? 'Syncing…' : 'Sync'}
                </Button>
                <IconButton
                  size="small"
                  aria-label={`${portal.name} actions`}
                  onClick={(event) => setMenu({ portal, anchor: event.currentTarget })}
                >
                  <MoreHoriz />
                </IconButton>
              </Stack>
            </Stack>

            <Stack spacing={0.75} sx={{ mt: 1.5 }}>
              <SyncRunList
                runs={runs}
                timeZone={timeZone}
                liveId={live?.portalId === portal.id ? live.syncId : null}
                maxRuns={4}
                emptyText="Press Sync to start a run. Steps will appear under that sync id."
              />
            </Stack>
          </Box>
        );
      })}

      <Menu
        open={Boolean(menu)}
        anchorEl={menu?.anchor}
        onClose={() => setMenu(null)}
      >
        {menu && (
          <div>
            <MenuItem onClick={() => openEdit(menu.portal)}>
              <EditOutlined fontSize="small" sx={{ mr: 1 }} /> Edit credentials
            </MenuItem>
            <MenuItem onClick={() => openReauth(menu.portal)}>Save & sync</MenuItem>
            <MenuItem
              disabled={!menu.portal.has_credentials && !menu.portal.has_password}
              onClick={() => {
                const portal = menu.portal;
                setMenu(null);
                if (window.confirm(`Delete saved ${portal.name} email/password?`)) {
                  clearMutation.mutate(portal.id);
                }
              }}
            >
              Clear credentials
            </MenuItem>
            <MenuItem
              disabled={removeMutation.isPending}
              onClick={() => {
                const portal = menu.portal;
                setMenu(null);
                if (window.confirm(`Disconnect ${portal.name}?`)) {
                  removeMutation.mutate(portal.id);
                }
              }}
            >
              <DeleteOutline fontSize="small" sx={{ mr: 1 }} /> Disconnect
            </MenuItem>
          </div>
        )}
      </Menu>

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
            ) : (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                Leave password blank to keep the stored one.
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
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={closeDialog}>Cancel</Button>
          {dialog?.mode === 'connect' && (
            <Button
              variant="contained"
              onClick={() => createMutation.mutate()}
              disabled={dialogBusy || !canSubmit}
            >
              {createMutation.isPending ? 'Saving…' : 'Save'}
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
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
