import {
  Box,
  Button,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { memo, useMemo, useState } from 'react';
import { calendarApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import PageSkeleton from '../../components/common/PageSkeleton';

function CalendarPage() {
  const [cursor, setCursor] = useState(dayjs());
  const queryClient = useQueryClient();
  const month = cursor.month() + 1;
  const year = cursor.year();

  const { data: events, isLoading } = useQuery({
    queryKey: ['calendar', year, month],
    queryFn: async () => (await calendarApi.month(month, year)).data as Array<any>,
  });

  const { data: due } = useQuery({
    queryKey: ['reminders-due'],
    queryFn: async () => (await calendarApi.dueReminders()).data as Array<any>,
  });

  const complete = useMutation({
    mutationFn: (id: string) => calendarApi.completeReminder(id),
    meta: { successMessage: 'Follow-up completed', errorMessage: 'Could not complete reminder' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders-due'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
    },
  });

  const byDay = useMemo(() => {
    const map: Record<string, any[]> = {};
    for (const event of events || []) {
      const day = dayjs(event.date).format('YYYY-MM-DD');
      map[day] = map[day] || [];
      map[day].push(event);
    }
    return map;
  }, [events]);

  const daysInMonth = cursor.daysInMonth();
  const startWeekday = cursor.startOf('month').day();

  if (isLoading) return <PageSkeleton />;

  return (
    <PageShell>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Typography variant="h4">Application calendar</Typography>
        <Stack direction="row" spacing={1} justifyContent="center">
          <Button onClick={() => setCursor((c) => c.subtract(1, 'month'))}>Prev</Button>
          <Typography sx={{ minWidth: 140, textAlign: 'center', pt: 1, fontWeight: 700 }}>
            {cursor.format('MMMM YYYY')}
          </Typography>
          <Button onClick={() => setCursor((c) => c.add(1, 'month'))}>Next</Button>
        </Stack>
      </Stack>

      {!!due?.length && (
        <Box
          sx={{
            p: 2,
            borderRadius: 3,
            border: '1px solid',
            borderColor: 'divider',
            background: (t) =>
              `linear-gradient(135deg, ${alpha(t.palette.warning.main, 0.12)}, ${alpha(t.palette.secondary.main, 0.06)})`,
          }}
        >
          <Typography variant="h6" sx={{ mb: 1 }}>
            Follow-ups due
          </Typography>
          <Stack spacing={1}>
            {due.map((item) => (
              <Stack
                key={item.id}
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                alignItems={{ sm: 'center' }}
              >
                <Typography sx={{ flex: 1 }}>{item.title}</Typography>
                <Button size="small" variant="contained" onClick={() => complete.mutate(item.id)}>
                  Done
                </Button>
              </Stack>
            ))}
          </Stack>
        </Box>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(2, 1fr)',
            sm: 'repeat(4, 1fr)',
            md: 'repeat(7, 1fr)',
          },
          gap: 1,
        }}
      >
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <Typography
            key={d}
            variant="caption"
            sx={{
              textAlign: 'center',
              fontWeight: 700,
              display: { xs: 'none', md: 'block' },
            }}
          >
            {d}
          </Typography>
        ))}
        {Array.from({ length: startWeekday }).map((_, i) => (
          <Box key={`empty-${i}`} sx={{ display: { xs: 'none', md: 'block' } }} />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const key = cursor.date(day).format('YYYY-MM-DD');
          const dayEvents = byDay[key] || [];
          return (
            <Box
              key={key}
              sx={{
                minHeight: { xs: 72, md: 88 },
                p: 1,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
                transition: 'transform 0.2s ease, border-color 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  borderColor: 'secondary.main',
                },
              }}
            >
              <Typography variant="caption" fontWeight={700}>
                {day}
              </Typography>
              <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                {dayEvents.slice(0, 3).map((ev) => (
                  <Chip
                    key={ev.id}
                    size="small"
                    label={ev.type === 'follow_up' ? 'Follow-up' : 'Applied'}
                    color={ev.type === 'follow_up' ? 'warning' : 'success'}
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Box>
          );
        })}
      </Box>
    </PageShell>
  );
}

export default memo(CalendarPage);
