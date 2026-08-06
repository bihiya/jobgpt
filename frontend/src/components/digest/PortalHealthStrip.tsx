import { Box, Button, Chip, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo } from 'react';

export type PortalHealthItem = {
  id: string;
  name: string;
  status?: string;
  has_session?: boolean;
  session_updated_at?: string | null;
  last_sync_at?: string | null;
  health?: {
    score?: number;
    auto_paused?: boolean;
    last_error?: string;
    consecutive_failures?: number;
  };
};

function tone(score = 100, paused = false): 'success' | 'warning' | 'error' {
  if (paused || score < 40) return 'error';
  if (score < 70) return 'warning';
  return 'success';
}

function PortalHealthStrip({
  portals,
  onReauth,
  busyId,
}: {
  portals: PortalHealthItem[];
  onReauth: (id: string) => void;
  busyId?: string | null;
}) {
  if (!portals.length) {
    return (
      <Typography color="text.secondary" variant="body2">
        No portals connected yet.
      </Typography>
    );
  }

  return (
    <Stack direction="row" spacing={1.25} flexWrap="wrap" useFlexGap>
      {portals.map((p) => {
        const score = p.health?.score ?? 100;
        const paused = Boolean(p.health?.auto_paused);
        const color = tone(score, paused);
        const last = p.session_updated_at || p.last_sync_at;
        return (
          <Box
            key={p.id}
            sx={{
              px: 1.5,
              py: 1.25,
              minWidth: 180,
              borderRadius: 2.5,
              border: '1px solid',
              borderColor: 'divider',
              bgcolor: (t) => alpha(t.palette[color].main, 0.08),
            }}
          >
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
              <Typography sx={{ fontWeight: 700, textTransform: 'capitalize' }}>{p.name}</Typography>
              <Chip size="small" color={color} label={`${Math.round(score)}`} />
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              {paused
                ? 'Paused'
                : p.has_session
                  ? `Session${last ? ` · ${new Date(last).toLocaleDateString()}` : ''}`
                  : 'Needs login'}
            </Typography>
            {(paused || color !== 'success' || !p.has_session) && (
              <Button
                size="small"
                sx={{ mt: 0.75, px: 0 }}
                disabled={busyId === p.id}
                onClick={() => onReauth(p.id)}
              >
                Re-auth
              </Button>
            )}
          </Box>
        );
      })}
    </Stack>
  );
}

export default memo(PortalHealthStrip);
