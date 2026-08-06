import { Box, Grid, Skeleton, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { reportsApi } from '../../api';
import StatCard from '../../components/dashboard/StatCard';

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: async () => (await reportsApi.analytics()).data,
  });

  if (isLoading || !data) {
    return (
      <Stack spacing={2}>
        <Skeleton height={48} width={280} />
        <Grid container spacing={2}>
          {[1, 2, 3, 4].map((i) => (
            <Grid key={i} size={{ xs: 12, sm: 6, md: 3 }}>
              <Skeleton variant="rounded" height={120} />
            </Grid>
          ))}
        </Grid>
      </Stack>
    );
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4">Operations overview</Typography>
        <Typography color="text.secondary">
          Live snapshot of discovery, matching, and application outcomes.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard label="Jobs Found" value={data.jobs_found} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard label="Applied" value={data.applied} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard label="Pending" value={data.pending} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard label="Success Rate" value={`${data.success_rate}%`} accent />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Box sx={{ p: 2.5, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Daily applications
            </Typography>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data.daily_applications}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="date" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#0F6E56" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Box sx={{ p: 2.5, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Portal statistics
            </Typography>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.portal_stats}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="portal" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#C15F3C" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Grid>
      </Grid>
    </Stack>
  );
}
