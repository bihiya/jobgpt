import { DeleteOutline, MoreHoriz } from '@mui/icons-material';
import {
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
import { useMemo, useState } from 'react';
import { portalsApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import { useRequireAuth } from '../../hooks/useRequireAuth';
import { fromNowLocal } from '../../utils/datetime';
import { accountFromPortal, compactProfileUrl } from '../../utils/portalIdentity';
import { hasAuthCookie, parseCookiePaste } from '../../utils/sessionCookies';

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
  sync_started_at?: string | null;
  username?: string;
  has_credentials?: boolean;
  has_password?: boolean;
  has_session?: boolean;
  session_updated_at?: string | null;
  session_identity?: {
    display_name?: string;
    headline?: string;
    location?: string;
    profile_url?: string;
    public_id?: string;
    captured_at?: string | null;
  };
  health?: {
    auto_paused?: boolean;
    last_error?: string;
  };
};

function isSyncing(portal: PortalRow): boolean {
  if (!portal.sync_started_at) return false;
  const started = Date.parse(portal.sync_started_at);
  return Number.isFinite(started) && Date.now() - started < SYNC_STALE_MS;
}

function portalChip(portal: PortalRow): { label: string; color: 'success' | 'warning' | 'info' | 'default' } | null {
  if (isSyncing(portal)) return { label: 'Syncing', color: 'info' };
  if (portal.has_session) return { label: 'Connected', color: 'success' };
  if (portal.name === 'linkedin') return { label: 'Needs session', color: 'warning' };
  if (portal.has_credentials) return { label: 'Saved', color: 'default' };
  return { label: 'Needs login', color: 'warning' };
}

function PortalAccountDetails({ portal }: { portal: PortalRow }) {
  const account = accountFromPortal(portal);
  const waiting =
    portal.name === 'linkedin' && Boolean(portal.has_session) && !account.name && !account.location;
  const when = [
    portal.session_updated_at ? `Logged in ${fromNowLocal(portal.session_updated_at)}` : '',
    portal.last_sync_at ? `Last synced ${fromNowLocal(portal.last_sync_at)}` : '',
  ].filter(Boolean);
  const error = (portal.health?.last_error || '').trim();
  return (
    <Stack spacing={0.25} sx={{ mt: 1 }}>
      {account.name ? (
        <Typography sx={{ fontWeight: 700 }}>{account.name}</Typography>
      ) : null}
      {account.location ? (
        <Typography variant="body2" color="text.secondary">
          {account.location}
        </Typography>
      ) : null}
      {account.headline ? (
        <Typography variant="body2" color="text.secondary">
          {account.headline}
        </Typography>
      ) : null}
      {account.email ? (
        <Typography variant="body2" color="text.secondary">
          {account.email}
        </Typography>
      ) : null}
      {account.profileUrl ? (
        <Typography
          variant="body2"
          component="a"
          href={account.profileUrl}
          target="_blank"
          rel="noreferrer"
          sx={{ color: 'primary.main', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
        >
          {compactProfileUrl(account.profileUrl)}
        </Typography>
      ) : null}
      {waiting ? (
        <Typography variant="body2" color="text.secondary">
          Name and location appear after the next successful sync.
        </Typography>
      ) : null}
      {when.length ? (
        <Typography variant="caption" color="text.secondary">
          {when.join(' · ')}
        </Typography>
      ) : null}
      {error ? (
        <Typography variant="caption" color="error">
          {error}
        </Typography>
      ) : null}
    </Stack>
  );
}

export default function PortalsPage() {
  const [dialog, setDialog] = useState(false);
  const [name, setName] = useState('linkedin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [sessionPaste, setSessionPaste] = useState('');
  const [cardPaste, setCardPaste] = useState('');
  const [menu, setMenu] = useState<{ portal: PortalRow; anchor: HTMLElement } | null>(null);
  const queryClient = useQueryClient();
  const { isAuthenticated } = useRequireAuth();

  const { data, isLoading } = useQuery({
    queryKey: ['portals'],
    queryFn: async () => (await portalsApi.list()).data as PortalRow[],
  });
  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const dialogPortalName = name;
  const dialogLinkedin = dialogPortalName === 'linkedin';
  const dialogCookies = useMemo(
    () => parseCookiePaste(sessionPaste, dialogPortalName),
    [sessionPaste, dialogPortalName],
  );
  const cardCookies = useMemo(() => parseCookiePaste(cardPaste, 'linkedin'), [cardPaste]);
  const dialogCookieReady = hasAuthCookie(dialogCookies, dialogPortalName);
  const cardCookieReady = hasAuthCookie(cardCookies, 'linkedin');

  const closeDialog = () => {
    setDialog(false);
    setUsername('');
    setPassword('');
    setSessionPaste('');
    setName('linkedin');
  };

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['portals'] });
  };

  const createMutation = useMutation({
    mutationFn: async () => {
      const created = await portalsApi.create({
        name,
        ...(dialogLinkedin
          ? { cookies: sessionPaste.trim() }
          : { credentials: { username, password } }),
      });
      const id = String(created.data?.id || '');
      if (id && isAuthenticated) await portalsApi.sync(id);
      return created;
    },
    meta: { successMessage: 'Saved', errorMessage: 'Could not save' },
    onSuccess: () => {
      refresh();
      closeDialog();
    },
  });

  const saveSessionMutation = useMutation({
    mutationFn: ({ id, cookies }: { id: string; cookies: string }) =>
      portalsApi.reauth(id, { cookies }),
    meta: { successMessage: 'Session saved — syncing', errorMessage: 'Could not save session' },
    onSuccess: () => {
      setCardPaste('');
      setSessionPaste('');
      closeDialog();
      refresh();
    },
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => portalsApi.sync(id),
    meta: { successMessage: 'Sync started', errorMessage: 'Sync failed' },
    onSuccess: refresh,
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => portalsApi.remove(id),
    meta: { successMessage: 'Disconnected', errorMessage: 'Could not disconnect' },
    onSuccess: refresh,
  });

  const dialogBusy = createMutation.isPending || saveSessionMutation.isPending;
  const otherCanSubmit = Boolean(username.trim()) && Boolean(password);
  const dialogCanSubmit = dialogLinkedin ? dialogCookieReady : otherCanSubmit;

  return (
    <PageShell loading={isLoading} busy={dialogBusy} stagger={false}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Typography variant="h4">Job portals</Typography>
        <Button
          variant="contained"
          onClick={() => {
            const taken = new Set(rows.map((row) => row.name));
            setName(PORTALS.find((p) => !taken.has(p)) || 'linkedin');
            setDialog(true);
          }}
        >
          Connect portal
        </Button>
      </Stack>

      {!rows.length && (
        <Typography color="text.secondary">Connect a portal to start.</Typography>
      )}

      {rows.map((portal) => {
        const chip = portalChip(portal);
        const syncing = isSyncing(portal) || (portal.name === 'linkedin' && saveSessionMutation.isPending);
        if (portal.name === 'linkedin') {
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
              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>LinkedIn</Typography>
                  {chip && <Chip size="small" color={chip.color} label={chip.label} />}
                </Stack>
                <IconButton
                  size="small"
                  aria-label="LinkedIn actions"
                  onClick={(event) => setMenu({ portal, anchor: event.currentTarget })}
                >
                  <MoreHoriz />
                </IconButton>
              </Stack>
              <PortalAccountDetails portal={portal} />
              <TextField
                label="Session key"
                value={cardPaste}
                onChange={(e) => setCardPaste(e.target.value)}
                fullWidth
                multiline
                minRows={2}
                sx={{ mt: 1.5 }}
                placeholder="Paste li_at"
                helperText={
                  cardCookieReady ? 'Looks good' : cardPaste.trim() ? 'Could not read that key' : ' '
                }
              />
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.25 }}>
                <Button
                  variant="contained"
                  disabled={!cardCookieReady || syncing}
                  onClick={() => saveSessionMutation.mutate({ id: portal.id, cookies: cardPaste.trim() })}
                >
                  {saveSessionMutation.isPending ? 'Saving…' : 'Save and sync'}
                </Button>
                {portal.has_session && (
                  <Button
                    size="small"
                    disabled={syncing || syncMutation.isPending}
                    onClick={() => syncMutation.mutate(portal.id)}
                  >
                    {syncing ? 'Syncing…' : 'Sync'}
                  </Button>
                )}
              </Stack>
            </Box>
          );
        }

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
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="h6" sx={{ textTransform: 'capitalize', fontWeight: 700 }}>
                  {portal.name}
                </Typography>
                {chip && <Chip size="small" color={chip.color} label={chip.label} />}
              </Stack>
              <Stack direction="row" spacing={0.75} alignItems="center">
                <Button
                  size="small"
                  variant="contained"
                  disabled={syncing || syncMutation.isPending}
                  onClick={() => syncMutation.mutate(portal.id)}
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
            <PortalAccountDetails portal={portal} />
          </Box>
        );
      })}

      <Menu open={Boolean(menu)} anchorEl={menu?.anchor} onClose={() => setMenu(null)}>
        {menu && (
          <MenuItem
            disabled={removeMutation.isPending}
            onClick={() => {
              const portal = menu.portal;
              setMenu(null);
              if (window.confirm(`Disconnect ${portal.name}?`)) removeMutation.mutate(portal.id);
            }}
          >
            <DeleteOutline fontSize="small" sx={{ mr: 1 }} /> Disconnect
          </MenuItem>
        )}
      </Menu>

      <Dialog open={Boolean(dialog)} onClose={closeDialog} fullWidth maxWidth="sm">
        <DialogTitle>Connect portal</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
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
            {dialogLinkedin ? (
              <TextField
                label="Session key"
                value={sessionPaste}
                onChange={(e) => setSessionPaste(e.target.value)}
                fullWidth
                multiline
                minRows={3}
                placeholder="Paste li_at"
                helperText={
                  dialogCookieReady ? 'Looks good' : sessionPaste.trim() ? 'Could not read that key' : ' '
                }
              />
            ) : (
              <>
                <TextField
                  label="Email"
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
                />
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={closeDialog}>Cancel</Button>
          <Button
            variant="contained"
            disabled={dialogBusy || !dialogCanSubmit}
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </PageShell>
  );
}
