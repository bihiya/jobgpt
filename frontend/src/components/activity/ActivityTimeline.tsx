import {
  Box,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { memo } from 'react';

dayjs.extend(relativeTime);

export type ActivityItem = {
  id: string;
  action: string;
  message: string;
  resource_type?: string;
  job_id?: string;
  severity?: string;
  source?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
};

type Props = {
  items: ActivityItem[];
  emptyText?: string;
  dense?: boolean;
  onJobClick?: (jobId: string) => void;
};

function severityColor(severity?: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  if (severity === 'success') return 'success';
  if (severity === 'warning') return 'warning';
  if (severity === 'error') return 'error';
  if (severity === 'info') return 'info';
  return 'default';
}

function ActivityTimelineComponent({
  items,
  emptyText = 'No activity yet',
  dense,
  onJobClick,
}: Props) {
  if (!items.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        {emptyText}
      </Typography>
    );
  }

  return (
    <Stack spacing={dense ? 1 : 1.5} className="jp-stagger">
      {items.map((item) => (
        <Box
          key={item.id}
          sx={{
            position: 'relative',
            pl: 2.5,
            py: dense ? 1 : 1.25,
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            transition: 'transform 0.2s ease, border-color 0.2s ease',
            '&:hover': {
              transform: 'translateY(-1px)',
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
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            justifyContent="space-between"
            alignItems={{ sm: 'center' }}
            sx={{ pl: 1 }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant={dense ? 'body2' : 'subtitle2'} fontWeight={700}>
                {item.message || item.action}
              </Typography>
              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                <Chip size="small" label={item.action} variant="outlined" />
                {item.resource_type && (
                  <Chip size="small" label={item.resource_type} color="info" variant="outlined" />
                )}
                {item.source && <Chip size="small" label={item.source} />}
                <Chip size="small" label={item.severity || 'info'} color={severityColor(item.severity)} />
                {item.job_id && onJobClick && (
                  <Chip
                    size="small"
                    label="View job"
                    color="primary"
                    onClick={() => onJobClick(item.job_id!)}
                    clickable
                  />
                )}
              </Stack>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
              {dayjs(item.created_at).fromNow()}
            </Typography>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

export default memo(ActivityTimelineComponent);
