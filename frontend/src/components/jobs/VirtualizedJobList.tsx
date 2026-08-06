import { Box, Chip, Stack, Typography } from '@mui/material';
import { memo, useCallback } from 'react';
import { FixedSizeList as List, type ListChildComponentProps } from 'react-window';

export type VirtualJob = {
  id: string;
  title: string;
  company: string;
  location: string;
  match_score: number;
  status: string;
};

type Props = {
  jobs: VirtualJob[];
  height?: number;
  onSelect: (id: string) => void;
};

const Row = memo(function JobRow({
  index,
  style,
  data,
}: ListChildComponentProps<{ jobs: VirtualJob[]; onSelect: (id: string) => void }>) {
  const job = data.jobs[index];
  return (
    <Box
      style={style}
      sx={{
        px: 2,
        display: 'flex',
        alignItems: 'center',
        borderBottom: '1px solid',
        borderColor: 'divider',
        cursor: 'pointer',
        '&:hover': { bgcolor: 'action.hover' },
      }}
      onClick={() => data.onSelect(job.id)}
    >
      <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%' }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography noWrap fontWeight={600}>
            {job.title}
          </Typography>
          <Typography noWrap variant="body2" color="text.secondary">
            {job.company} · {job.location}
          </Typography>
        </Box>
        <Chip size="small" label={`${Math.round((job.match_score || 0) * 100)}%`} />
        <Chip size="small" variant="outlined" label={job.status} />
      </Stack>
    </Box>
  );
});

function VirtualizedJobListComponent({ jobs, height = 480, onSelect }: Props) {
  const itemData = { jobs, onSelect };

  const itemKey = useCallback((index: number, data: typeof itemData) => data.jobs[index].id, []);

  if (!jobs.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
        No jobs to display
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        bgcolor: 'background.paper',
        overflow: 'hidden',
      }}
    >
      <List
        height={height}
        width="100%"
        itemCount={jobs.length}
        itemSize={72}
        itemData={itemData}
        itemKey={itemKey}
      >
        {Row}
      </List>
    </Box>
  );
}

export default memo(VirtualizedJobListComponent);
