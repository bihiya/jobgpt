import {
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { memo, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { activityApi } from '../../api';
import ActivityTimeline from '../../components/activity/ActivityTimeline';
import PageShell from '../../components/common/PageShell';
import PageSkeleton from '../../components/common/PageSkeleton';

function ActivityPage() {
  const navigate = useNavigate();
  const [resourceType, setResourceType] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['user-activity', resourceType],
    queryFn: async () =>
      (
        await activityApi.list({
          page_size: 100,
          resource_type: resourceType || undefined,
        })
      ).data,
  });

  const openJob = useCallback(
    (jobId: string) => {
      navigate(`/jobs?focus=${jobId}`);
    },
    [navigate],
  );

  if (isLoading) return <PageSkeleton />;

  return (
    <PageShell>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Typography variant="h4">Activity</Typography>
        <TextField
          select
          size="small"
          label="Filter"
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value)}
          sx={{ minWidth: { sm: 180 } }}
        >
          <MenuItem value="">All activity</MenuItem>
          <MenuItem value="job">Jobs</MenuItem>
          <MenuItem value="application">Applications</MenuItem>
          <MenuItem value="approval">Approvals</MenuItem>
          <MenuItem value="user">Profile</MenuItem>
          <MenuItem value="auth">Auth</MenuItem>
          <MenuItem value="portal">Portals</MenuItem>
          <MenuItem value="settings">Settings</MenuItem>
          <MenuItem value="automation">Automation</MenuItem>
        </TextField>
      </Stack>
      <Typography color="text.secondary">
        Every meaningful action on your account and jobs is recorded here.
      </Typography>
      <ActivityTimeline
        items={data?.items || []}
        emptyText="No activity yet — track a job or update your profile to get started."
        onJobClick={openJob}
      />
    </PageShell>
  );
}

export default memo(ActivityPage);
