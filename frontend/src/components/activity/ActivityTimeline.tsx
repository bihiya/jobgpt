import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Box,
  Chip,
  Collapse,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo, useCallback, useMemo, useState, type MouseEvent, type ReactNode } from 'react';
import { formatLocal, fromNowLocal } from '../../utils/datetime';

export type ActivityChange = {
  field: string;
  from?: unknown;
  to?: unknown;
};

export type ActivityItem = {
  id: string;
  action: string;
  message: string;
  summary?: string;
  outcome?: string;
  next_step?: string;
  actor_name?: string;
  resource_type?: string;
  resource_id?: string;
  job_id?: string;
  application_id?: string;
  severity?: string;
  source?: string;
  ip?: string;
  user_agent?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
};

type Props = {
  items: ActivityItem[];
  emptyText?: string;
  dense?: boolean;
  onJobClick?: (jobId: string) => void;
};

const HIDDEN_META_KEYS = new Set(['changes', 'fields', 'outcome', 'next_step', 'steps']);

function severityColor(severity?: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  if (severity === 'success') return 'success';
  if (severity === 'warning') return 'warning';
  if (severity === 'error') return 'error';
  if (severity === 'info') return 'info';
  return 'default';
}

function outcomeColor(outcome?: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  const value = (outcome || '').toLowerCase();
  if (value.includes('pass') || value.includes('success')) return 'success';
  if (value.includes('fail')) return 'error';
  if (value.includes('need') || value.includes('stop') || value.includes('attention')) return 'warning';
  if (value.includes('progress')) return 'info';
  return 'default';
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return String(value);
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 0);
  } catch {
    return String(value);
  }
}

function humanizeField(field: string): string {
  return field
    .replace(/^profile\./, '')
    .replace(/[._]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractSteps(metadata?: Record<string, unknown>): { label: string; status?: string; detail?: string }[] {
  const raw = metadata?.steps;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
    .map((row) => ({
      label: String(row.label || row.key || ''),
      status: row.status ? String(row.status) : '',
      detail: row.detail ? String(row.detail) : '',
    }))
    .filter((row) => row.label);
}

function extractChanges(metadata?: Record<string, unknown>): ActivityChange[] {
  if (!metadata) return [];
  const raw = metadata.changes;
  if (Array.isArray(raw)) {
    return raw
      .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
      .map((row) => ({
        field: String(row.field ?? ''),
        from: row.from,
        to: row.to,
      }))
      .filter((row) => row.field);
  }
  if (Array.isArray(metadata.fields)) {
    return (metadata.fields as unknown[])
      .map((field) => String(field))
      .filter(Boolean)
      .map((field) => ({ field, from: undefined, to: '(updated)' }));
  }
  return [];
}

function headline(item: ActivityItem): string {
  return item.summary || item.message || item.action;
}

function outcomeOf(item: ActivityItem): string {
  if (item.outcome) return item.outcome;
  const meta = item.metadata?.outcome;
  if (typeof meta === 'string' && meta) return meta;
  if (item.severity === 'success') return 'Passed';
  if (item.severity === 'error') return 'Failed';
  if (item.severity === 'warning') return 'Needs attention';
  return 'Happened';
}

function nextStepOf(item: ActivityItem): string {
  if (item.next_step) return item.next_step;
  const meta = item.metadata?.next_step;
  if (typeof meta === 'string' && meta) return meta;
  return '';
}

function DetailBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box sx={{ mt: 1.25 }}>
      <Typography
        variant="caption"
        sx={{
          display: 'block',
          mb: 0.75,
          fontWeight: 700,
          letterSpacing: 0.4,
          textTransform: 'uppercase',
          color: 'text.secondary',
        }}
      >
        {label}
      </Typography>
      {children}
    </Box>
  );
}

function ActivityDetails({ item }: { item: ActivityItem }) {
  const changes = useMemo(() => extractChanges(item.metadata), [item.metadata]);
  const steps = useMemo(() => extractSteps(item.metadata), [item.metadata]);
  const extraMeta = useMemo(() => {
    if (!item.metadata) return [];
    return Object.entries(item.metadata).filter(([key, value]) => {
      if (HIDDEN_META_KEYS.has(key)) return false;
      if (value === null || value === undefined || value === '') return false;
      return true;
    });
  }, [item.metadata]);

  const nextStep = nextStepOf(item);
  const outcome = outcomeOf(item);

  return (
    <Box
      sx={{
        mt: 1.25,
        ml: 1,
        pl: 1.5,
        pr: 1,
        py: 1.25,
        borderRadius: 1.5,
        bgcolor: (t) => alpha(t.palette.secondary.main, t.palette.mode === 'dark' ? 0.12 : 0.06),
        border: '1px solid',
        borderColor: (t) => alpha(t.palette.secondary.main, 0.18),
      }}
    >
      <DetailBlock label="What happened">
        <Typography variant="body2" sx={{ mb: 0.75 }}>
          {headline(item)}
        </Typography>
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
          <Chip size="small" color={outcomeColor(outcome)} label={outcome} />
          {item.actor_name && <Chip size="small" variant="outlined" label={`By ${item.actor_name}`} />}
          {item.source && <Chip size="small" variant="outlined" label={`Source: ${item.source}`} />}
        </Stack>
      </DetailBlock>

      {nextStep && (
        <DetailBlock label="Further steps">
          <Typography variant="body2">{nextStep}</Typography>
        </DetailBlock>
      )}

      {steps.length > 0 && (
        <DetailBlock label={`Sync steps (${steps.length})`}>
          <Stack spacing={0.75}>
            {steps.map((step, idx) => (
              <Stack key={`${step.label}-${idx}`} direction="row" spacing={1} alignItems="flex-start">
                <Chip size="small" label={idx + 1} sx={{ minWidth: 36 }} />
                <Stack spacing={0}>
                  <Typography variant="body2">{step.label}</Typography>
                  {(step.detail || step.status) && (
                    <Typography variant="caption" color="text.secondary">
                      {[step.status, step.detail].filter(Boolean).join(' · ')}
                    </Typography>
                  )}
                </Stack>
              </Stack>
            ))}
          </Stack>
        </DetailBlock>
      )}

      {changes.length > 0 && (
        <DetailBlock label={`What changed (${changes.length})`}>
          <Box
            sx={{
              overflowX: 'auto',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'divider',
              bgcolor: 'background.paper',
            }}
          >
            <Table size="small" aria-label="Changed fields">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, width: '28%' }}>Field</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Before</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>After</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {changes.map((change) => (
                  <TableRow key={change.field} hover>
                    <TableCell sx={{ fontWeight: 600, verticalAlign: 'top' }}>
                      {humanizeField(change.field)}
                      <Typography
                        component="span"
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: 'block', fontFamily: 'ui-monospace, monospace' }}
                      >
                        {change.field}
                      </Typography>
                    </TableCell>
                    <TableCell
                      sx={{
                        verticalAlign: 'top',
                        color: 'error.main',
                        fontFamily: 'ui-monospace, monospace',
                        fontSize: '0.78rem',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {formatValue(change.from)}
                    </TableCell>
                    <TableCell
                      sx={{
                        verticalAlign: 'top',
                        color: 'success.dark',
                        fontFamily: 'ui-monospace, monospace',
                        fontSize: '0.78rem',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {formatValue(change.to)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </DetailBlock>
      )}

      {extraMeta.length > 0 && (
        <DetailBlock label="Details">
          <Stack spacing={0.75}>
            {extraMeta.map(([key, value]) => (
              <Stack
                key={key}
                direction={{ xs: 'column', sm: 'row' }}
                spacing={{ xs: 0.25, sm: 1.5 }}
                sx={{
                  py: 0.5,
                  borderBottom: '1px dashed',
                  borderColor: 'divider',
                  '&:last-child': { borderBottom: 0 },
                }}
              >
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ minWidth: 140, fontWeight: 700 }}
                >
                  {humanizeField(key)}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontFamily: 'ui-monospace, monospace',
                    fontSize: '0.8rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {formatValue(value)}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </DetailBlock>
      )}

      <DetailBlock label="Event info">
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
          <Chip size="small" variant="outlined" label={`When: ${formatLocal(item.created_at)}`} />
          <Chip size="small" variant="outlined" label={`Action: ${item.action}`} />
          {item.resource_type && (
            <Chip size="small" variant="outlined" label={`Resource: ${item.resource_type}`} />
          )}
          {item.job_id && <Chip size="small" variant="outlined" label={`Job: ${item.job_id}`} />}
        </Stack>
      </DetailBlock>
    </Box>
  );
}

function ActivityTimelineComponent({
  items,
  emptyText = 'No activity yet',
  dense,
  onJobClick,
}: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  if (!items.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        {emptyText}
      </Typography>
    );
  }

  return (
    <Stack spacing={dense ? 1 : 1.5} className="jp-stagger">
      {items.map((item) => {
        const open = !!expanded[item.id];
        const outcome = outcomeOf(item);
        const nextStep = nextStepOf(item);
        const changes = extractChanges(item.metadata);
        return (
          <Box
            key={item.id}
            sx={{
              position: 'relative',
              pl: 2.5,
              py: dense ? 1 : 1.25,
              borderRadius: 2,
              border: '1px solid',
              borderColor: open ? 'secondary.main' : 'divider',
              bgcolor: 'background.paper',
              transition: 'transform 0.2s ease, border-color 0.2s ease',
              '&:hover': {
                transform: open ? 'none' : 'translateY(-1px)',
                borderColor: 'secondary.main',
              },
              '&::before': {
                content: '""',
                position: 'absolute',
                left: 10,
                top: 16,
                bottom: 16,
                width: 3,
                borderRadius: 2,
                background: (t) =>
                  `linear-gradient(180deg, ${t.palette.secondary.main}, ${alpha(t.palette.info.main, 0.5)})`,
              },
            }}
          >
            <Stack direction="row" spacing={0.5} alignItems="flex-start" sx={{ pl: 1 }}>
              <Box
                component="button"
                type="button"
                onClick={() => toggle(item.id)}
                aria-expanded={open}
                aria-controls={`activity-detail-${item.id}`}
                sx={{
                  flex: 1,
                  minWidth: 0,
                  border: 0,
                  background: 'transparent',
                  p: 0,
                  m: 0,
                  textAlign: 'left',
                  cursor: 'pointer',
                  color: 'inherit',
                  font: 'inherit',
                }}
              >
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  spacing={1}
                  justifyContent="space-between"
                  alignItems={{ sm: 'flex-start' }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant={dense ? 'body2' : 'subtitle2'} fontWeight={700}>
                      {headline(item)}
                    </Typography>
                    <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 0.75 }}>
                      <Chip size="small" color={outcomeColor(outcome)} label={outcome} />
                      {item.actor_name && (
                        <Chip size="small" variant="outlined" label={item.actor_name} />
                      )}
                      {item.resource_type && (
                        <Chip size="small" label={item.resource_type} color="info" variant="outlined" />
                      )}
                      <Chip
                        size="small"
                        label={item.severity || 'info'}
                        color={severityColor(item.severity)}
                        variant="outlined"
                      />
                      {item.job_id && onJobClick && (
                        <Chip
                          size="small"
                          label="View job"
                          color="primary"
                          onClick={(e: MouseEvent) => {
                            e.stopPropagation();
                            onJobClick(item.job_id!);
                          }}
                          clickable
                        />
                      )}
                    </Stack>
                    {!open && nextStep && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: 'block', mt: 0.75 }}
                      >
                        Next: {nextStep}
                      </Typography>
                    )}
                    {!open && !nextStep && changes.length > 0 && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: 'block', mt: 0.75 }}
                      >
                        {changes.length} field{changes.length === 1 ? '' : 's'} changed — expand for
                        before/after
                      </Typography>
                    )}
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ whiteSpace: 'nowrap' }}
                  >
                    {fromNowLocal(item.created_at)}
                  </Typography>
                </Stack>
              </Box>
              <IconButton
                size="small"
                onClick={() => toggle(item.id)}
                aria-label={open ? 'Collapse activity details' : 'Expand activity details'}
                sx={{
                  mt: -0.25,
                  transition: 'transform 0.2s ease',
                  transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
                }}
              >
                <ExpandMoreIcon fontSize="small" />
              </IconButton>
            </Stack>

            <Collapse in={open} timeout="auto" unmountOnExit>
              <Box id={`activity-detail-${item.id}`}>
                <ActivityDetails item={item} />
              </Box>
            </Collapse>
          </Box>
        );
      })}
    </Stack>
  );
}

export default memo(ActivityTimelineComponent);
