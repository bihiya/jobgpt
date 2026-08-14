import {
  Alert,
  Button,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { automationApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import SyncRunList from '../../components/portals/SyncRunList';
import { useUserTimeZone } from '../../hooks/useUserTimeZone';
import { formatWhen, formatWhenLong } from '../../utils/datetime';
import { groupPortalRuns, type AutomationLogItem } from '../../utils/loginStory';

type LogRow = AutomationLogItem & {
  level: string;
};

function levelColor(level?: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  if (level === 'success') return 'success';
  if (level === 'warning') return 'warning';
  if (level === 'error') return 'error';
  if (level === 'info') return 'info';
  return 'default';
}

export default function AutomationPage() {
  const queryClient = useQueryClient();
  const timeZone = useUserTimeZone();

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['automation-status'],
    queryFn: async () => (await automationApi.status()).data,
  });
  const { data: logs, isLoading } = useQuery({
    queryKey: ['automation-logs'],
    queryFn: async () => (await automationApi.logs({ page_size: 200 })).data,
  });
  const loading = statusLoading || isLoading;

  const runMutation = useMutation({
    mutationFn: (jobType: string) => automationApi.run(jobType),
    meta: { successMessage: 'Worker triggered', errorMessage: 'Could not run worker' },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['automation-status'] });
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
      void queryClient.invalidateQueries({ queryKey: ['portals'] });
    },
  });

  const rows = useMemo<LogRow[]>(() => logs?.items || [], [logs?.items]);
  const syncRuns = useMemo(() => groupPortalRuns(rows), [rows]);
  const playwrightAvailable = status?.playwright_available !== false;
  const playwrightMessage =
    typeof status?.playwright_message === 'string' ? status.playwright_message : null;
  const emptyHint =
    !rows.length &&
    (playwrightAvailable
      ? 'No automation logs yet. Click “Run fetch” — progress will appear here (portal sync, jobs found, errors).'
      : 'Browser automation is unavailable in this environment. Match/report can still run; fetch/apply need the Docker stack.');

  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: 'created_at',
        headerName: 'Time',
        flex: 0.9,
        minWidth: 150,
        valueFormatter: (value: string) => formatWhenLong(value, timeZone),
      },
      {
        field: 'portal',
        headerName: 'Portal',
        width: 130,
        renderCell: (params) => params.value || '—',
      },
      {
        field: 'action',
        headerName: 'Action',
        width: 150,
      },
      {
        field: 'level',
        headerName: 'Level',
        width: 110,
        renderCell: (params) => (
          <Chip size="small" label={params.value || 'info'} color={levelColor(params.value)} />
        ),
      },
      {
        field: 'message',
        headerName: 'Message',
        flex: 1.8,
        minWidth: 220,
      },
    ],
    [timeZone],
  );

  return (
    <PageShell loading={loading} busy={runMutation.isPending} stagger={false}>
      <Typography variant="h4">Automation</Typography>
      <Typography color="text.secondary">
        Total logs: {status?.total_logs ?? 0}. Trigger workers manually when needed.
      </Typography>

      {!playwrightAvailable && playwrightMessage ? (
        <Alert severity="warning">{playwrightMessage}</Alert>
      ) : (
        <Alert severity="info" sx={{ alignItems: 'center' }}>
          Fetch needs a connected portal. Go to{' '}
          <Button component={RouterLink} to="/job-portals" size="small" sx={{ ml: 0.5 }}>
            Job Portals
          </Button>{' '}
          first, then run fetch — each sync is audited and listed below as a collapse/expand step trail.
        </Alert>
      )}

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {['fetch', 'match', 'apply', 'report'].map((job) => {
          const needsBrowser = job === 'fetch' || job === 'apply';
          const disabled = runMutation.isPending || (needsBrowser && !playwrightAvailable);
          return (
            <Button
              key={job}
              variant={job === 'fetch' ? 'contained' : 'outlined'}
              onClick={() => runMutation.mutate(job)}
              disabled={disabled}
            >
              {runMutation.isPending ? 'Running…' : `Run ${job}`}
            </Button>
          );
        })}
      </Stack>

      {!!syncRuns.length && (
        <Stack spacing={0.75}>
          <Typography variant="subtitle2" fontWeight={700}>
            Sync history
          </Typography>
          <SyncRunList runs={syncRuns} timeZone={timeZone} showPortal />
        </Stack>
      )}

      {!!status?.recent?.length && !syncRuns.length && (
        <Stack spacing={0.75}>
          <Typography variant="subtitle2" fontWeight={700}>
            Latest
          </Typography>
          {status.recent.map((item: LogRow) => (
            <Typography key={item.id} variant="body2" color="text.secondary">
              {formatWhen(item.created_at, timeZone)} — {item.message || item.action}
            </Typography>
          ))}
        </Stack>
      )}

      <DataGrid
        autoHeight
        rows={rows}
        columns={columns}
        getRowId={(row) => row.id}
        loading={runMutation.isPending}
        pageSizeOptions={[10, 25, 50]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        localeText={{ noRowsLabel: emptyHint || 'No rows' }}
        sx={{ bgcolor: 'background.paper', borderRadius: 3, width: '100%', minHeight: 280 }}
      />
    </PageShell>
  );
}
